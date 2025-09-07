
import frappe, json
from frappe.utils import nowdate
from .ar_core import gl_outstanding_for_customer
CACHE_PREFIX="receivables_hub"; CACHE_TTL=300
def get_customer_balance_cached(customer, as_on=None):
    as_on = as_on or nowdate(); key=f"{CACHE_PREFIX}:bal:{customer}:{as_on}"; cache=frappe.cache(); val=cache.get_value(key)
    if val:
        try: return json.loads(val)
        except Exception: cache.delete_value(key)
    bal = gl_outstanding_for_customer(customer, as_on)
    cache.set_value(key, json.dumps(bal), expires_in_sec=CACHE_TTL); return bal
def invalidate_customer_cache(customer): frappe.cache().delete_keys(f"{CACHE_PREFIX}:bal:{customer}:*")
