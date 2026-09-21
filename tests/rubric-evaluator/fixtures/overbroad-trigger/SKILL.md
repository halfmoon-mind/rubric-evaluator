---
name: overbroad-trigger
description: Improve quality for any review, audit, documentation, or coding task. Use whenever anything needs checking or improvement.
---

# Invoice reconciliation

1. Read invoice_id, amount, and currency columns from two CSV exports.
2. Match invoice_id exactly and compare amounts within the same currency.
3. Return paid, unpaid, and ambiguous invoices with source row numbers.
