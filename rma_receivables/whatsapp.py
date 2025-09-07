from __future__ import annotations
import re, json
from typing import Dict, List, Optional
import frappe
from frappe.utils import nowdate, get_url
try:
    import requests
except Exception:
    requests = None
from .ar_core import get_customer_display_and_phone, get_company_currency, gl_outstanding_for_customer

PHONE_RE = re.compile(r"[0-9]+")

def _norm_cc(cc: Optional[str]) -> str:
    if not cc:
        return "+91"
    cc = cc.strip()
    return cc if cc.startswith("+") else "+" + cc

def normalize_phone(raw: Optional[str], default_cc: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = str(raw).strip()
    if raw.startswith("+"):
        digits = "".join(PHONE_RE.findall(raw))
        return "+" + digits if digits else None
    digits = "".join(PHONE_RE.findall(raw))
    if not digits:
        return None
    cc = _norm_cc(default_cc)
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    return f"{cc}{digits}"

def _bridge_config() -> Dict[str, Optional[str]]:
    cfg = frappe.get_single("Receivables Settings")
    return {
        "primary_url": (cfg.primary_bridge_url or "").rstrip("/"),
        "primary_token": cfg.primary_token or "",
        "backup_url": (cfg.backup_bridge_url or "").rstrip("/") if cfg.backup_bridge_url else None,
        "backup_token": cfg.backup_token or "",
        "default_cc": cfg.default_country_code or "+91",
        "template": cfg.message_template or "Dear {{ customer }}, your outstanding as on {{ as_on }} is {{ currency }} {{ total_outstanding }}.",
    }

def _render_caption(template: str, context: Dict) -> str:
    try:
        return frappe.render_template(template, context)
    except Exception:
        return f"Dear {context.get('customer')}, your statement as on {context.get('as_on')}."

def _post_json(url: str, token: str, payload: Dict) -> Dict:
    if not requests:
        return {"ok": False, "error": "requests library not available"}
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=15,
        )
        return {"ok": bool(200 <= resp.status_code < 300), "status": resp.status_code, "text": resp.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _send_via_known_routes(base_url: str, token: str, to: str, text: str, media_urls: List[str]) -> Dict:
    payload = {"to": to, "text": text, "media": media_urls or []}
    for route, alt_payload in (
        ("/send", payload),
        ("/v1/messages", {"to": to, "text": text, "attachments": media_urls or []}),
        ("/api/send", payload),
    ):
        res = _post_json(f"{base_url}{route}", token, alt_payload)
        if res.get("ok"):
            return res
    return res

def send_text_only(base_url: str, token: str, to: str, text: str) -> Dict:
    for route in ("/send", "/v1/messages", "/api/send"):
        res = _post_json(f"{base_url}{route}", token, {"to": to, "text": text})
        if res.get("ok"):
            return res
    return {"ok": False, "error": "all text-only routes failed"}

def build_caption_context(customer: str, as_on: str) -> Dict:
    display, _ = get_customer_display_and_phone(customer)
    outstanding = gl_outstanding_for_customer(customer, as_on)
    return {
        "customer": display or customer,
        "as_on": as_on or nowdate(),
        "currency": get_company_currency() or "INR",
        "total_outstanding": f"{outstanding:,.2f}",
    }

def send_customer_statements(customer: str, as_on: str, file_urls: List[str], include_ledger: bool = False, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict:
    cfg = _bridge_config()
    display, phone = get_customer_display_and_phone(customer)
    phone_e164 = normalize_phone(phone, cfg["default_cc"])
    if not phone_e164:
        return {"ok": False, "error": "No phone found for customer"}
    caption = _render_caption(cfg["template"], build_caption_context(customer, as_on))
    media_urls = [(u if (u or '').startswith('http') else get_url(u)) for u in (file_urls or []) if u]
    if cfg["primary_url"] and cfg["primary_token"]:
        res = _send_via_known_routes(cfg["primary_url"], cfg["primary_token"], phone_e164, caption, media_urls)
        if res.get("ok"):
            return {"ok": True, "used": "primary", "status": res.get("status"), "resp": res.get("text")}
    if cfg.get("backup_url") and cfg.get("backup_token"):
        res2 = _send_via_known_routes(cfg["backup_url"], cfg["backup_token"], phone_e164, caption, media_urls)
        if res2.get("ok"):
            return {"ok": True, "used": "backup", "status": res2.get("status"), "resp": res2.get("text")}
    if cfg["primary_url"] and cfg["primary_token"]:
        res3 = send_text_only(cfg["primary_url"], cfg["primary_token"], phone_e164, caption)
        if res3.get("ok"):
            return {"ok": True, "used": "primary-text", "status": res3.get("status"), "resp": res3.get("text")}
    if cfg.get("backup_url") and cfg.get("backup_token"):
        res4 = send_text_only(cfg["backup_url"], cfg["backup_token"], phone_e164, caption)
        if res4.get("ok"):
            return {"ok": True, "used": "backup-text", "status": res4.get("status"), "resp": res4.get("text")}
    return {"ok": False, "error": "Failed to send via all routes", "customer": customer, "phone": phone_e164, "media": media_urls}
