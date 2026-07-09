---
name: model-strong
description: Convert CSV transaction exports into monthly expense reports. Use when asked to summarize expenses, convert csv spend data, build a monthly spending report, or total transactions by category.
---

# Model Strong

Turn a CSV of transactions into a monthly expense report.

## Workflow

1. Confirm the CSV has `date`, `amount`, and `category` columns; ask for a header mapping if not.
2. Parse amounts as decimals; treat parentheses as negative, so `(12.50)` means `-12.50`.
3. Group rows by calendar month and category, then total each group.
4. Flag any single transaction above 500.00 in its own outlier section.
5. Render a markdown table sorted by month, then by descending total.

## Edge cases

- Empty file: report "no transactions" instead of an empty table.
- Duplicate rows: dedupe on (date, amount, description) before totals.
- Mixed currencies: stop and ask which currency to keep.
