
from __future__ import annotations
import frappe
from frappe.utils import nowdate
from typing import Optional
from .ar_core import get_receivables_dashboard_summary, list_customers_with_outstanding
from .pdfs import make_receivables_pdf, make_ledger_pdf
from .whatsapp import send_customer_statements
from .diagnostics import preflight

@frappe.whitelist()
def get_dashboard_summary(as_on: Optional[str] = None):
    return get_receivables_dashboard_summary(as_on or nowdate())

@frappe.whitelist()
def list_customers(search: str = "", limit: int = 100, overdue_only: int = 0, customer_group: str = ""):
    return list_customers_with_outstanding(search=search or "", limit=int(limit or 100), overdue_only=int(overdue_only or 0), customer_group=customer_group or "", as_on=nowdate())

@frappe.whitelist()
def send_for_customer(customer: str, as_on: Optional[str] = None, include_ledger: int = 0, from_date: Optional[str] = None, to_date: Optional[str] = None) -> dict:
    if not customer: frappe.throw("Customer is required")
    as_on = as_on or nowdate()
    pre = preflight(customer=customer, as_on=as_on) or {}
    if not pre.get("ok"):
        frappe.throw("Preflight failed. Open Preflight from Actions to review issues.")
    rec_pdf = make_receivables_pdf(customer=customer, as_on=as_on)
    attachments = []
    if rec_pdf and rec_pdf.get("file_url"): attachments.append(rec_pdf["file_url"])
    if int(include_ledger or 0) and from_date and to_date:
        led_pdf = make_ledger_pdf(customer=customer, from_date=from_date, to_date=to_date)
        if led_pdf and led_pdf.get("file_url"): attachments.append(led_pdf["file_url"])
    res = send_customer_statements(customer=customer, as_on=as_on, file_urls=attachments, include_ledger=bool(int(include_ledger or 0) and from_date and to_date), from_date=from_date, to_date=to_date)
    return {"ok": True, "sent": bool(res.get("ok")), "details": res}
