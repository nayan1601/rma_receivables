
from __future__ import annotations
import frappe
from frappe.utils import nowdate, flt, getdate
from typing import Dict, List, Optional, Tuple

def get_default_company() -> Optional[str]:
    return (frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company"))

def get_company_currency(company: Optional[str] = None) -> Optional[str]:
    company = company or get_default_company()
    return frappe.db.get_value("Company", company, "default_currency") if company else None

def get_receivable_accounts(company: Optional[str] = None) -> List[str]:
    company = company or get_default_company()
    if not company: return []
    rows = frappe.db.sql("""SELECT name FROM `tabAccount` WHERE company=%s AND account_type='Receivable' AND ifnull(is_group,0)=0""", (company,), as_dict=True)
    return [r["name"] for r in rows]

def get_customer_display_and_phone(customer: str) -> Tuple[str, Optional[str]]:
    cust = frappe.db.get_value("Customer", customer, ["customer_name", "mobile_no", "phone", "customer_primary_contact"], as_dict=True)
    if not cust: return (customer, None)
    first = cust.mobile_no or cust.phone
    if first: return (cust.customer_name or customer, first)
    if cust.get("customer_primary_contact"):
        ct = frappe.db.get_value("Contact", cust.customer_primary_contact, ["mobile_no","phone"], as_dict=True)
        if ct: return (cust.customer_name or customer, ct.mobile_no or ct.phone)
    return (cust.customer_name or customer, None)

def gl_outstanding_for_customer(customer: str, as_on: Optional[str] = None) -> float:
    company = get_default_company(); as_on = as_on or nowdate(); accounts = get_receivable_accounts(company)
    if not accounts: return 0.0
    placeholders = ", ".join(["%s"] * len(accounts))
    params = [customer] + accounts + [as_on, company]
    row = frappe.db.sql(f"""
        SELECT COALESCE(SUM(debit - credit), 0) AS bal
        FROM `tabGL Entry`
        WHERE party_type='Customer' AND party=%s AND account IN ({placeholders})
          AND posting_date <= %s AND company = %s AND IFNULL(is_cancelled,0)=0
    """, tuple(params), as_dict=True)
    return float(row[0]["bal"] if row else 0.0)

def get_receivables_dashboard_summary(as_on: Optional[str] = None) -> Dict:
    company = get_default_company(); as_on = as_on or nowdate(); currency = get_company_currency(company) or "INR"
    accounts = get_receivable_accounts(company)
    if not accounts: return dict(total_outstanding=0.0, customers_with_outstanding=0, as_on=as_on, currency=currency)
    placeholders = ", ".join(["%s"] * len(accounts))
    params = accounts + [as_on, company]
    rows = frappe.db.sql(f"""
        SELECT party, COALESCE(SUM(debit - credit),0) AS bal
        FROM `tabGL Entry`
        WHERE party_type='Customer' AND account IN ({placeholders})
          AND posting_date <= %s AND company = %s AND IFNULL(is_cancelled,0)=0
        GROUP BY party
    """, tuple(params), as_dict=True)
    total = sum([flt(r["bal"]) for r in rows if r.get("bal")])
    cnt = sum([1 for r in rows if flt(r.get("bal")) > 0])
    return dict(total_outstanding=float(total), customers_with_outstanding=int(cnt), as_on=as_on, currency=currency)

def list_customers_with_outstanding(search: str = "", limit: int = 100, overdue_only: int = 0, customer_group: str = "", as_on: Optional[str] = None) -> List[Dict]:
    company = get_default_company(); as_on = as_on or nowdate(); accounts = get_receivable_accounts(company)
    if not accounts: return []
    placeholders = ", ".join(["%s"] * len(accounts))
    conditions = ["gle.party_type='Customer'", f"gle.account IN ({placeholders})", "gle.posting_date <= %s", "gle.company = %s", "IFNULL(gle.is_cancelled,0)=0"]
    values: List = accounts[:] + [as_on, company]
    if search:
        conditions.append("(c.name LIKE %s OR c.customer_name LIKE %s)")
        like = f"%{search}%"; values.extend([like, like])
    if customer_group:
        conditions.append("c.customer_group = %s"); values.append(customer_group)
    where = " AND ".join(conditions)
    sql = f"""
        SELECT c.name AS customer, c.customer_name, COALESCE(SUM(gle.debit - gle.credit),0) AS outstanding
        FROM `tabGL Entry` gle JOIN `tabCustomer` c ON c.name = gle.party
        WHERE {where}
        GROUP BY c.name, c.customer_name
        ORDER BY outstanding DESC
        LIMIT {int(limit)}
    """
    rows = frappe.db.sql(sql, tuple(values), as_dict=True)
    if overdue_only: rows = [r for r in rows if flt(r.get("outstanding")) > 0]
    return rows


def get_customer_aging_breakup(customer: str, as_on: Optional[str] = None) -> Dict:
    company = get_default_company(); as_on = as_on or nowdate(); accounts = get_receivable_accounts(company)
    if not accounts: return dict(total=0, b0_30=0, b31_60=0, b61_90=0, b90p=0, currency=get_company_currency(company))
    placeholders = ", ".join(["%s"] * len(accounts))
    params = [customer] + accounts + [as_on, company]
    rows = frappe.db.sql(f"""
        SELECT CASE
                WHEN DATEDIFF(%s, posting_date) <= 30 THEN 'b0_30'
                WHEN DATEDIFF(%s, posting_date) <= 60 THEN 'b31_60'
                WHEN DATEDIFF(%s, posting_date) <= 90 THEN 'b61_90'
                ELSE 'b90p' END AS bucket,
               SUM(debit - credit) AS amt
        FROM `tabGL Entry`
        WHERE party_type='Customer' AND party=%s AND account IN ({placeholders})
          AND posting_date <= %s AND company = %s AND IFNULL(is_cancelled,0)=0
        GROUP BY bucket
    """, tuple([as_on, as_on, as_on] + params), as_dict=True)
    out = dict(total=0.0, b0_30=0.0, b31_60=0.0, b61_90=0.0, b90p=0.0, currency=get_company_currency(company))
    for r in rows:
        out[r["bucket"]] = float(flt(r["amt"])); out["total"] += float(flt(r["amt"])) 
    return out

def build_fy_ledger_rows(customer: str, from_date: str, to_date: str) -> List[Dict]:
    rows = frappe.db.sql("""
        SELECT je.posting_date, je.name AS voucher_no, COALESCE(je.remarks, '') AS reference,
               COALESCE(je.receivable_type, '') AS receivable_type,
               COALESCE(jea.debit_in_account_currency, 0) AS debit,
               COALESCE(jea.credit_in_account_currency, 0) AS credit
        FROM `tabJournal Entry` je
        JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
        WHERE je.docstatus = 1 AND jea.party_type = 'Customer' AND jea.party = %s
          AND je.posting_date BETWEEN %s AND %s
        ORDER BY je.posting_date ASC, je.name ASC
    """, (customer, from_date, to_date), as_dict=True)
    return rows
