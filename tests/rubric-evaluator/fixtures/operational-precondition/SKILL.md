---
name: operational-precondition
description: Reconcile CSV invoice exports against CSV bank transactions. Use when asked to match invoice payments or identify unpaid invoices from CSV exports.
---

# Reconcile invoices

Before reconciling, require invoice_id, amount, and currency in both files.
If headers are missing, ask for a column mapping. This is an operational
precondition for reconciliation, not a separate invocation condition.

1. Match invoice_id exactly, then compare currency and amount to two decimal places.
2. Mark multiple candidate payments as ambiguous instead of choosing the first row.
3. Return a table of paid, unpaid, and ambiguous invoices with row numbers.
