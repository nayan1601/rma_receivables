# Receivables Hub (Self-Contained)

- Reads existing GL/JE only (no mutation) to compute outstanding & aging.
- Generates Receivables PDF + FY-wise Ledger PDF (Remarks used as Reference).
- WhatsApp sending via bridge (WhatsMeow compatible) with primary/backup.
- Follow-ups/Reminders (parse natural text like "pay on 7 Dec 2025" or "within 7 days").
- Responsive Desk Page + Customer buttons.
- Schedulers: daily reconciliation & hourly follow-up reminders.

## Install
```
bench get-app /path/to/rma_receivables
bench --site erp.chemx.co.in install-app rma_receivables
bench --site erp.chemx.co.in migrate
bench setup requirements
bench build
```

## Configure
- **Receivables Settings**: set bridge URLs/tokens, default country code, message/reminder templates, footer.
- Ensure receivable accounts exist (leaf).

## Use
- Desk > Receivables Hub page: filter, send per customer, send all filtered, include FY ledger, Preflight.
- Customer form: Actions > Send WhatsApp Statement / Add Follow-up / View Follow-ups.
