
import frappe

def _ensure_field(dt, field):
    df = frappe.get_all("DocField", filters={"parent": dt, "fieldname": field["fieldname"]})
    if df: return
    doc = frappe.get_doc("DocType", dt)
    doc.append("fields", field)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

def _create_ar_followup():
    if frappe.db.exists("DocType", "AR Followup"):
        return
    dt = frappe.get_doc({
        "doctype": "DocType",
        "name": "AR Followup",
        "module": "Receivables Hub",
        "custom": 1,
        "autoname": "naming_series:ARF-.#####",
        "is_submittable": 0,
        "fields": [
            {"fieldname":"customer","label":"Customer","fieldtype":"Link","options":"Customer","reqd":1},
            {"fieldname":"amount","label":"Amount","fieldtype":"Currency"},
            {"fieldname":"promise_text","label":"Promise Text","fieldtype":"Data","in_list_view":1},
            {"fieldname":"due_date","label":"Follow-up Date","fieldtype":"Date","in_list_view":1,"reqd":1},
            {"fieldname":"remind_at","label":"Remind At","fieldtype":"Datetime"},
            {"fieldname":"status","label":"Status","fieldtype":"Select","options":"Open\nDone\nSnoozed\nCancelled","default":"Open","in_list_view":1},
            {"fieldname":"notes","label":"Notes","fieldtype":"Small Text"},
            {"fieldname":"whatsapp_to","label":"WhatsApp To (E.164)","fieldtype":"Data"},
            {"fieldname":"last_sent_at","label":"Last Sent At","fieldtype":"Datetime"},
            {"fieldname":"assigned_to","label":"Assigned To","fieldtype":"Link","options":"User"},
            {"fieldname":"ref_doctype","label":"Reference Doctype","fieldtype":"Data"},
            {"fieldname":"ref_docname","label":"Reference Name","fieldtype":"Data"}
        ]
    })
    dt.insert(ignore_permissions=True)

def execute():
    _create_ar_followup()
    if not frappe.db.exists("DocType","Receivables Settings"):
        return
    _ensure_field("Receivables Settings", {"fieldname":"reminder_template","label":"Reminder Template (Jinja)","fieldtype":"Text","default":"Hi {{ customer }}, this is a reminder for your payment follow-up on {{ followup_date }} for {{ currency }} {{ amount or '' }}."})
    _ensure_field("Receivables Settings", {"fieldname":"remind_before_days","label":"Remind Before (days)","fieldtype":"Int","default":0})
    _ensure_field("Receivables Settings", {"fieldname":"auto_create_todo","label":"Auto-create ToDo","fieldtype":"Check","default":1})
