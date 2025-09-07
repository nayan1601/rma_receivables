app_name = "rma_receivables"
app_title = "Receivables Hub"
app_publisher = "You"
app_description = "Journal-based Receivables Hub (read-only) with WhatsApp, PDFs, and Follow-ups"
app_email = "you@example.com"
app_license = "MIT"

doctype_js = {"Customer": "rma_receivables/public/js/customer_button.js"}

scheduler_events = {
    "daily": ["rma_receivables.scheduled_tasks.daily_receivables_reconciliation"],
    "hourly": ["rma_receivables.scheduled_tasks.process_due_followups"]
}
