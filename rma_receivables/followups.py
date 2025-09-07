
from __future__ import annotations
import re
from typing import Optional, Dict, Any, Tuple
import frappe
from frappe.utils import nowdate, now_datetime, add_days, getdate
from dateutil.parser import parse as dt_parse
from .whatsapp import normalize_phone, _bridge_config, send_text_only, _render_caption
from .ar_core import get_customer_display_and_phone, get_company_currency

DATE_PATTERNS = [
    r"(on\s+)?(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    r"(on\s+)?(?P<date>\d{1,2}(st|nd|rd|th)?\s+[A-Za-z]{3,9}[,]?\s*\d{2,4})",
    r"(on\s+)?(?P<date>[A-Za-z]{3,9}\s+\d{1,2}(st|nd|rd|th)?[,]?\s*\d{2,4})"
]
RELATIVE_DAYS = [
    r"(in|within|after)\s+(?P<days>\d{1,4})\s+day(s)?",
    r"(?P<days>\d{1,4})\s+day(s)?\s+(later|from\s+now)"
]

def parse_promise_text(text: str) -> Tuple[str, str]:
    """Return (due_date ISO, normalized_text). Supports 'on 7 Dec 2025' or 'within 7 days'."""
    text = (text or '').strip()
    if not text:
        return (nowdate(), text)
    for pat in DATE_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                dt = dt_parse(m.group('date'), dayfirst=True).date()
                return (dt.isoformat(), text)
            except Exception:
                pass
    for pat in RELATIVE_DAYS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            days = int(m.group('days'))
            return (add_days(nowdate(), days), text)
    try:
        dt = dt_parse(text, dayfirst=True).date()
        return (dt.isoformat(), text)
    except Exception:
        return (nowdate(), text)

def _ensure_todo(fu_name: str, user: Optional[str], due_date: str, desc: str):
    if not int(frappe.get_single('Receivables Settings').auto_create_todo or 0):
        return
    td = frappe.get_doc({'doctype':'ToDo','date': due_date,'description': desc,'reference_type': 'AR Followup','reference_name': fu_name})
    if user: td.assigned_by = frappe.session.user; td.allocated_to = user
    td.insert(ignore_permissions=True)

@frappe.whitelist()
def create_followup(customer: str, promise_text: Optional[str] = None, amount: Optional[float] = None, notes: Optional[str] = None, assign_to: Optional[str] = None, remind_before_days: Optional[int] = None, ref_doctype: Optional[str] = None, ref_docname: Optional[str] = None) -> Dict[str, Any]:
    if not customer:
        frappe.throw('Customer is required')
    due, norm = parse_promise_text(promise_text or '')
    remind_before_days = int(remind_before_days) if remind_before_days is not None else int(frappe.get_single('Receivables Settings').remind_before_days or 0)
    remind_at = add_days(due, -remind_before_days) if remind_before_days>0 else due
    display, phone = get_customer_display_and_phone(customer)
    e164 = normalize_phone(phone, _bridge_config().get('default_cc'))
    doc = frappe.get_doc({'doctype':'AR Followup','customer': customer,'amount': amount or 0.0,'promise_text': norm,'due_date': due,'remind_at': remind_at,'status':'Open','notes': notes or '','whatsapp_to': e164 or None,'assigned_to': assign_to or None,'ref_doctype': ref_doctype,'ref_docname': ref_docname})
    doc.insert(ignore_permissions=True)
    _ensure_todo(doc.name, assign_to, due, f'Follow-up {customer}: {norm}')
    return {'ok': True, 'name': doc.name, 'due_date': due}

@frappe.whitelist()
def list_followups(customer: Optional[str] = None, status: Optional[str] = "Open"):
    filters={'status': status} if status else {}
    if customer: filters['customer'] = customer
    rows = frappe.get_all('AR Followup', fields=['name','customer','amount','promise_text','due_date','remind_at','status','assigned_to'], filters=filters, order_by='due_date asc')
    return rows

@frappe.whitelist()
def mark_followup_done(name: str):
    doc = frappe.get_doc('AR Followup', name)
    doc.status = 'Done'
    doc.save(ignore_permissions=True)
    return {'ok': True}

@frappe.whitelist()
def snooze_followup(name: str, days: int = 1):
    doc = frappe.get_doc('AR Followup', name)
    doc.remind_at = add_days(doc.remind_at or doc.due_date, int(days or 1))
    doc.status = 'Snoozed'
    doc.save(ignore_permissions=True)
    return {'ok': True, 'remind_at': doc.remind_at}

def _render_reminder_text(customer: str, due_date: str, amount: float) -> str:
    currency = get_company_currency()
    tmp = frappe.get_single('Receivables Settings').reminder_template or 'Hi {{ customer }}, this is a reminder for your payment follow-up on {{ followup_date }} for {{ currency }} {{ amount or "" }}.'
    return _render_caption(tmp, {'customer': customer, 'followup_date': due_date, 'amount': amount, 'currency': currency})

def send_due_followup(docname: str) -> Dict:
    doc = frappe.get_doc('AR Followup', docname)
    if doc.status not in ('Open','Snoozed'):
        return {'ok': False, 'error': 'Not open'}
    display, phone = get_customer_display_and_phone(doc.customer)
    from .whatsapp import _bridge_config, send_text_only, normalize_phone
    cfg = _bridge_config()
    to = doc.whatsapp_to or normalize_phone(phone, cfg.get('default_cc'))
    if not to: 
        return {'ok': False, 'error': 'No phone'}
    text = _render_reminder_text(display or doc.customer, str(doc.due_date), float(doc.amount or 0))
    base = cfg.get('primary_url'); token = cfg.get('primary_token')
    res = send_text_only(base, token, to, text) if base and token else {'ok': False}
    if not res.get('ok'):
        b2 = cfg.get('backup_url'); t2 = cfg.get('backup_token')
        if b2 and t2:
            res = send_text_only(b2, t2, to, text)
    if res.get('ok'):
        doc.last_sent_at = frappe.utils.now_datetime()
        doc.status = 'Open'  # keep open for manual completion
        doc.save(ignore_permissions=True)
    return res
