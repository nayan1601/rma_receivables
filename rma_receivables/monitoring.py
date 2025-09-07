
import frappe
@frappe.whitelist()
def get_system_health():
    out={'status':'healthy','checks':[]}
    try:
        recent=frappe.db.count("Journal Entry", filters={'creation':['>', frappe.utils.add_days(frappe.utils.nowdate(), -1)]})
        out['checks'].append({'name':'Journal Read','status':'ok' if recent>=0 else 'warning','value':recent})
    except Exception as e:
        out['checks'].append({'name':'Journal Read','status':'error','error':str(e)})
    try:
        probe=frappe.db.sql("select 1")[0][0]
        out['checks'].append({'name':'DB Probe','status':'ok','value':probe})
    except Exception as e:
        out['checks'].append({'name':'DB Probe','status':'error','error':str(e)})
    return out
