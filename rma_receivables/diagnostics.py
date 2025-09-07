
from __future__ import annotations
import frappe
from frappe.utils import nowdate, flt
from typing import Dict, Optional
from .ar_core import get_default_company, get_receivable_accounts, gl_outstanding_for_customer, get_customer_display_and_phone
from .pdfs import check_templates_available

def _check_bridge_config():
    cfg = frappe.get_single("Receivables Settings")
    ok = bool(cfg.primary_bridge_url and cfg.primary_token)
    detail = "Primary bridge configured" if ok else "Primary bridge URL/token missing"
    return ok, detail

def _check_receivable_accounts():
    company = get_default_company()
    accs = get_receivable_accounts(company)
    ok = bool(accs)
    detail = f"{len(accs)} receivable account(s) found" if ok else "No leaf receivable accounts in Company"
    return ok, detail

def _check_phone(customer: str):
    _, phone = get_customer_display_and_phone(customer)
    ok = bool(phone)
    detail = f"Phone found: {phone}" if ok else "No phone/mobile for customer/primary contact"
    return ok, detail

def _check_gl_vs_je_parity(customer: str, as_on: str):
    glb = gl_outstanding_for_customer(customer, as_on)
    je_row = frappe.db.sql("""
        SELECT COALESCE(SUM(jea.debit_in_account_currency - jea.credit_in_account_currency),0) AS bal
        FROM `tabJournal Entry` je
        JOIN `tabJournal Entry` j2 ON j2.name = je.name
        JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
        WHERE je.docstatus = 1 AND je.posting_date <= %s AND jea.party_type='Customer' AND jea.party = %s
    """, (as_on, customer), as_dict=True)
    jeb = float(je_row[0]["bal"] if je_row else 0.0)
    diff = float(flt(glb) - flt(jeb))
    ok = abs(diff) <= 0.01
    detail = f"GL vs JE delta: {diff:.2f}"
    return ok, detail, {"gl_balance": float(glb), "je_balance": float(jeb), "difference": diff}

@frappe.whitelist()
def preflight(customer: str, as_on: Optional[str] = None) -> Dict:
    as_on = as_on or nowdate()
    checks = []
    ok1, d1 = _check_bridge_config(); checks.append({"name":"Bridge Config","ok":ok1,"detail":d1})
    ok2, d2 = _check_receivable_accounts(); checks.append({"name":"Receivable Accounts","ok":ok2,"detail":d2})
    ok3, d3 = _check_phone(customer); checks.append({"name":"Customer Phone","ok":ok3,"detail":d3})
    ok4, d4, meta = _check_gl_vs_je_parity(customer, as_on); checks.append({"name":"GL vs JE Parity","ok":ok4,"detail":d4,"meta":meta})
    t_ok, t_detail = check_templates_available(); checks.append({"name":"PDF Templates","ok":t_ok,"detail":t_detail})
    overall_ok = all(c["ok"] for c in checks if c["name"] in ("Bridge Config","Receivable Accounts","Customer Phone"))
    return {"ok": bool(overall_ok), "as_on": as_on, "checks": checks}
