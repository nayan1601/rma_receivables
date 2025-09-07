
from __future__ import annotations
import frappe
from typing import Dict, List
from .ar_core import get_customer_aging_breakup

@frappe.whitelist()
def get_customer_aging_many(customers: List[str], as_on: str) -> Dict[str, Dict]:
    if not customers: return {}
    out = {}
    for c in customers:
        try: out[c] = get_customer_aging_breakup(c, as_on)
        except Exception: out[c] = dict(total=0, b0_30=0, b31_60=0, b61_90=0, b90p=0, currency=None)
    return out
