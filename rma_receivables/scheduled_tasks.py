
import frappe
from frappe.utils import nowdate, flt
def daily_receivables_reconciliation():
    reconciliation_date = nowdate()
    company = (frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults","default_company"))
    if not company: return
    gl_balance = frappe.db.sql("""
        SELECT party as customer, SUM(debit - credit) as balance
        FROM `tabGL Entry`
        WHERE party_type = 'Customer'
          AND account IN (SELECT name FROM `tabAccount` WHERE account_type = 'Receivable' AND company=%s AND ifnull(is_group,0)=0)
          AND posting_date <= %s AND IFNULL(is_cancelled,0)=0
        GROUP BY party
    """, (company, reconciliation_date), as_dict=True)
    journal_balance = frappe.db.sql("""
        SELECT jea.party as customer, SUM(jea.debit_in_account_currency - jea.credit_in_account_currency) as balance
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE jea.party_type = 'Customer' AND je.docstatus = 1 AND je.posting_date <= %s
        GROUP BY jea.party
    """, reconciliation_date, as_dict=True)
    jmap = {r.customer: float(r.balance or 0) for r in journal_balance}
    discrepancies = []
    for g in gl_balance:
        jb = jmap.get(g.customer, 0.0); diff = float(flt(g.balance) - flt(jb))
        if abs(diff) > 0.01: discrepancies.append({'customer': g.customer,'gl_balance': float(g.balance or 0),'journal_balance': float(jb),'difference': diff})
    if discrepancies: frappe.log_error("Receivables Reconciliation Discrepancies", str(discrepancies))

def process_due_followups():
    """Send WhatsApp reminders for due AR Followups whose remind_at <= now and status is Open/Snoozed."""
    now = frappe.utils.now_datetime()
    due = frappe.get_all('AR Followup', filters={'status':['in',['Open','Snoozed']], 'remind_at':['<=', now]}, fields=['name'])
    for r in due:
        try:
            from .followups import send_due_followup
            send_due_followup(r['name'])
        except Exception as e:
            frappe.log_error(f'Followup send failed for {r.get("name")}: {e}')
