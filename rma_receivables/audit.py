
import frappe, json
def log_receivables_action(action_type, document=None, user=None, details=None):
    user = user or frappe.session.user
    try:
        doc = frappe.get_doc({"doctype":"Receivables Audit Log","action_type":action_type,
            "document_type": getattr(document, "doctype", None) if document else None,
            "document_name": getattr(document, "name", None) if document else None,
            "user": user, "timestamp": frappe.utils.now_datetime(),
            "details": json.dumps(details) if isinstance(details,(dict,list)) else (details or None),
            "ip_address": getattr(frappe.local, "request_ip", None)})
        doc.insert(ignore_permissions=True)
    except Exception:
        pass
