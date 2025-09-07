import frappe
def execute(filters=None):
    filters = filters or {}
    conditions = ["je.docstatus = 1"]; vals = {}
    if filters.get("company"): conditions.append("je.company = %(company)s"); vals["company"] = filters["company"]
    if filters.get("customer"): conditions.append("jea.party_type = 'Customer' and jea.party = %(customer)s"); vals["customer"] = filters["customer"]
    if filters.get("from_date"): conditions.append("je.posting_date >= %(from_date)s"); vals["from_date"] = filters["from_date"]
    if filters.get("to_date"): conditions.append("je.posting_date <= %(to_date)s"); vals["to_date"] = filters["to_date"]
    if filters.get("receivable_type"): conditions.append("je.receivable_type = %(receivable_type)s"); vals["receivable_type"] = filters["receivable_type"]
    where = " and ".join(conditions)
    rows = frappe.db.sql(f"""
        select je.posting_date, je.name as voucher_no, coalesce(je.remarks,'') as reference,
               coalesce(je.receivable_type,'') as receivable_type, coalesce(jea.debit_in_account_currency,0) as debit,
               coalesce(jea.credit_in_account_currency,0) as credit,
               @bal:=coalesce(@bal,0) + (coalesce(jea.debit_in_account_currency,0) - coalesce(jea.credit_in_account_currency,0)) as balance
        from (select @bal:=0) as vars, `tabJournal Entry` je
        join `tabJournal Entry Account` jea on jea.parent = je.name
        where {where} and jea.party_type='Customer'
        order by je.posting_date asc, je.name asc
    """, vals, as_dict=True)
    columns = [
        {"label":"Posting Date","fieldname":"posting_date","fieldtype":"Date","width":110},
        {"label":"Voucher","fieldname":"voucher_no","fieldtype":"Link","options":"Journal Entry","width":150},
        {"label":"Reference (Remarks)","fieldname":"reference","fieldtype":"Data","width":300},
        {"label":"Type","fieldname":"receivable_type","fieldtype":"Data","width":120},
        {"label":"Debit","fieldname":"debit","fieldtype":"Currency","width":110},
        {"label":"Credit","fieldname":"credit","fieldtype":"Currency","width":110},
        {"label":"Balance","fieldname":"balance","fieldtype":"Currency","width":120},
    ]
    return columns, rows
