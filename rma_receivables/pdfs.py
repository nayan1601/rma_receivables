
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import os
import frappe
from frappe.utils import nowdate, getdate, flt, get_url
from frappe.modules.utils import get_module_path
from .ar_core import get_default_company, get_company_currency, gl_outstanding_for_customer, get_customer_aging_breakup, build_fy_ledger_rows, get_customer_display_and_phone

def _template_path(name: str) -> Optional[str]:
    try: base = get_module_path("rma_receivables")
    except Exception: return None
    p = os.path.join(base, "templates", "html", name)
    return p if os.path.exists(p) else None

def check_templates_available() -> Tuple[bool, str]:
    base = get_module_path("rma_receivables")
    have_default = os.path.exists(os.path.join(base, "templates", "html", "receivables_statement.html"))
    have_colored = os.path.exists(os.path.join(base, "templates", "html", "receivables_statement_colored.html"))
    have_ledger = os.path.exists(os.path.join(base, "templates", "html", "ledger_fy.html"))
    ok = have_default and have_ledger
    return ok, f"default:{have_default} colored:{have_colored} ledger:{have_ledger}"

def _render_to_pdf(html: str, filename: str) -> Dict:
    from frappe.utils.pdf import get_pdf
    from frappe.utils.file_manager import save_file
    pdf_bytes = get_pdf(html)
    file_doc = save_file(fname=filename if filename.lower().endswith(".pdf") else f"{filename}.pdf", content=pdf_bytes, dt=None, dn=None, folder=None, is_private=1)
    return {"file_url": file_doc.file_url, "file_name": file_doc.file_name}

def _aging_css() -> str:
    return """
    <style>
      .rma-legend { font-size: 10px; color: #666; margin: 6px 0 0 0; }
      .bar { display:flex; width:100%; height:6px; background:#f3f4f6; border-radius: 12px; overflow:hidden; }
      .seg { height:100%; }
      .a0 { background:#d1fae5; } .a1 { background:#fef3c7; } .a2 { background:#fde68a; } .a3 { background:#fecaca; }
      .amt-ok { color:#065f46; } .amt-warn { color:#b45309; } .amt-hot { color:#c2410c; } .amt-bad { color:#b91c1c; }
      .muted { color: #666; }
      table { width: 100%; border-collapse: collapse; }
      th, td { border: 1px solid #e5e7eb; padding: 6px; font-size: 12px; }
      th { background: #f9fafb; text-align:left; }
      h1 { font-size: 18px; margin: 0 0 8px 0; }
      h2 { font-size: 14px; margin: 14px 0 6px 0; }
      .foot { font-size: 10px; color: #6b7280; margin-top: 8px; }
    </style>
    """

def _aging_badge_cls(ag: Dict) -> str:
    if not ag or (ag.get("total") or 0) <= 0: return "muted"
    if (ag.get("b90p") or 0) > 0: return "amt-bad"
    if (ag.get("b61_90") or 0) > 0: return "amt-hot"
    if (ag.get("b31_60") or 0) > 0: return "amt-warn"
    return "amt-ok"

def _aging_bar_html(ag: Dict) -> str:
    total = float(ag.get("total") or 0)
    if total <= 0: return '<div class="muted">—</div>'
    def pct(v): return max(0, round((float(v)/total)*100))
    return f'''
      <div class="bar">
        <div class="seg a0" style="width:{pct(ag.get("b0_30",0))}%"></div>
        <div class="seg a1" style="width:{pct(ag.get("b31_60",0))}%"></div>
        <div class="seg a2" style="width:{pct(ag.get("b61_90",0))}%"></div>
        <div class="seg a3" style="width:{pct(ag.get("b90p",0))}%"></div>
      </div>
    '''

@frappe.whitelist()
def make_receivables_pdf(customer: str, as_on: Optional[str] = None) -> Dict:
    as_on = as_on or nowdate()
    company = get_default_company()
    currency = get_company_currency(company) or "INR"
    display, phone = get_customer_display_and_phone(customer)
    outstanding = gl_outstanding_for_customer(customer, as_on)
    aging = get_customer_aging_breakup(customer, as_on)
    css = _aging_css(); badge_cls = _aging_badge_cls(aging)
    ctx = {"company": company,"customer": display or customer,"customer_code": customer,"as_on": as_on,"currency": currency,
           "outstanding": float(outstanding),"aging": aging,"aging_bar": _aging_bar_html(aging),"badge_cls": badge_cls,
           "phone": phone or "","footer": frappe.get_single("Receivables Settings").pdf_footer or "","site_url": get_url("/")}
    colored = _template_path("receivables_statement_colored.html"); default = _template_path("receivables_statement.html")
    tpl_path = colored or default
    if not tpl_path: frappe.throw("Receivables PDF template not found in app.")
    html = css + frappe.render_template(open(tpl_path, "r", encoding="utf-8").read(), ctx)
    filename = f"Receivables_{customer}_{as_on}.pdf"
    return _render_to_pdf(html, filename)

def _fys_overlapping(from_date: str, to_date: str):
    fys = frappe.get_all("Fiscal Year", fields=["name","year_start_date","year_end_date","is_fiscal_year_closed"])
    if not fys: return []
    fdt, tdt = getdate(from_date), getdate(to_date)
    def overlap(a1, a2, b1, b2): return max(a1, b1) <= min(a2, b2)
    fys2 = [fy for fy in fys if overlap(getdate(fy["year_start_date"]), getdate(fy["year_end_date"]), fdt, tdt)]
    if not fys2: return []
    open_fy = next((fy for fy in fys2 if not int(fy.get("is_fiscal_year_closed") or 0)), None)
    others = [fy for fy in fys2 if fy != open_fy]
    others_sorted = sorted(others, key=lambda x: x["year_end_date"], reverse=True)
    return [open_fy] + others_sorted if open_fy else others_sorted

@frappe.whitelist()
def make_ledger_pdf(customer: str, from_date: str, to_date: str) -> Dict:
    if not (from_date and to_date): frappe.throw("From/To dates are required for Ledger PDF")
    company = get_default_company(); currency = get_company_currency(company) or "INR"; display, _ = get_customer_display_and_phone(customer)
    fy_sections = []
    for fy in _fys_overlapping(from_date, to_date):
        from_seg = max(getdate(from_date), getdate(fy["year_start_date"])).isoformat()
        to_seg = min(getdate(to_date), getdate(fy["year_end_date"])).isoformat()
        rows = build_fy_ledger_rows(customer, from_seg, to_seg)
        running = 0.0
        for r in rows:
            running += float(flt(r.get("debit"))) - float(flt(r.get("credit"))); r["balance"] = running
        fy_sections.append({"fy_name": fy["name"], "from": from_seg, "to": to_seg, "rows": rows})
    ctx = {"company": company,"customer": display or customer,"customer_code": customer,"currency": currency,
           "from_date": from_date,"to_date": to_date,"sections": fy_sections,
           "footer": frappe.get_single("Receivables Settings").pdf_footer or "","site_url": get_url("/")}
    tpl_path = _template_path("ledger_fy.html")
    if not tpl_path: frappe.throw("Ledger PDF template not found in app.")
    html = _aging_css() + frappe.render_template(open(tpl_path, "r", encoding="utf-8").read(), ctx)
    filename = f"Ledger_{customer}_{from_date}_{to_date}.pdf"
    return _render_to_pdf(html, filename)
