
import frappe
def execute():
    stmts = [
        "CREATE INDEX idx_gl_entry_receivables ON `tabGL Entry` (party_type, party, account, posting_date)",
        "CREATE INDEX idx_journal_entry_receivable_type ON `tabJournal Entry` (posting_date, modified)",
        "CREATE INDEX idx_journal_entry_account_party ON `tabJournal Entry Account` (party_type, party, account)"
    ]
    for sql in stmts:
        try: frappe.db.sql(sql)
        except Exception: pass
