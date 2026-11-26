---
name: officeqa-treasury-bulletin
description: Answer questions from local U.S. Treasury Bulletin text files with accurate retrieval, operand selection, and bare numeric output.
when_to_use:
  - Questions answered from Treasury Bulletin tables, charts, or narrative text
  - Questions requiring arithmetic over fiscal- or calendar-period figures
---

## Workflow

1. **Resolve a valid file path before searching.** Enumerate the bulletin files with a broad glob (e.g. all `*.txt`), pick the issue covering the requested period, and reuse that exact resolved path for later grep and read calls. If a glob returns nothing, widen the pattern rather than repeating a rejected call.

2. **Narrow to the exact table or section.** Grep for the exact entity, measure, table label, or section heading from the question, then read only a small span around the hit. Confirm the match is the requested year, basis (calendar vs fiscal), and unit before trusting it.

3. **Read the authoritative row directly.** When a table already provides the requested total, net, change, or balance row/column, read that value itself instead of summing subcomponents, which may use different sign conventions or omit categories.

4. **Target the exact row and column.** Map multi-row headers to columns; adjacent columns (competitive vs noncompetitive, received vs accepted, opening balance vs period change, general vs trust fund) hold similar-looking numbers. For a time-series range, enumerate the expected observations with inclusive endpoints and confirm the set is complete.

5. **Prefer the latest revision.** When the same period appears in bulletins of different dates, a later issue may revise the figure. Use the value from the most recent bulletin covering the period unless the question fixes an as-of date.

6. **Compute only from extracted operands.** Keep units and signs consistent across operands and settle the formula convention before computing: simple vs compound/log growth. When the reported answer is itself a dispersion statistic (standard deviation, variance, coefficient of variation), default to the population form (divide by n) unless the question explicitly asks for the sample. When a standard deviation is only an intermediate in a z-score or test statistic computed from a small sample of observed prior values, use the sample form (n−1). Keep intermediates unrounded, and round only the final result.

7. **Return the bare numeric result.** Copy the answer from a checked value and, unless the question explicitly asks for a unit or rate word, report the number alone.

## Error Avoidance

- Do not grep or read an unverified path; resolve it with a glob first.
- Do not reconstruct a total/net from subcomponents when an authoritative row already exists.
- Do not mix values across adjacent columns or confuse calendar- vs fiscal-year sections.
- Do not use a superseded preliminary figure when a later bulletin revises the same period.
- Do not append extra unit words such as "percentage points", "percent", or "basis points" to an answer the question requested as a bare number.
