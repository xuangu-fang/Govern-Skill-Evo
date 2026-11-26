---
name: officeqa-treasury
description: Answer OfficeQA questions over local Treasury bulletin text files using disciplined retrieval, evidence alignment, computation, and format-exact output.
when_to_use:
  - The question concerns U.S. Treasury bulletin statistics such as expenditures, receipts, debt, yields, or money in circulation.
  - The answer must be located in local bulletin files, then possibly computed or aggregated.
  - A question may reference a table or chart whose value must be reported precisely.
---

## Workflow

1. **Narrow to the candidate bulletin**: Translate the question into concrete search terms naming the exact entity, period, measure, or table concept. Confirm which bulletin(s) cover the requested period, then search within them before reading long passages.
   Tools: glob to enumerate candidates, grep for targeted terms.

2. **Align the exact row, column, and basis**: Before reading a value, confirm the requested year, fiscal-vs-calendar basis, unit, and semantic role. For multi-row headers, map sub-labels to the correct column and keep adjacent columns distinct (offered vs accepted, total vs component, receipts vs outlays). Read only a small span around the match to verify it.

3. **Use the correct data vintage**: When several bulletins report the same period, use the figure from the bulletin that covers that period as a revision; do not combine an unrevised earlier value with revised later data.

4. **Extract operands before computing**: List each operand with its period, unit, and role. For an aggregation, enumerate the expected observation count (inclusive period range) and confirm the extracted set is complete before any arithmetic.

5. **Compute, then verify**: Apply the requested method only after extraction, preserving signs and time periods; use the requested standard-deviation convention (population vs sample) and keep intermediates unrounded until the final result.

6. **Return only the requested value**: Emit a bare number at the requested precision and sign inside <answer>...</answer>. Do not wrap the result in an explanatory sentence or restate the unit label; include a currency symbol, percent sign, or unit word only when the question explicitly asks for that rate, symbol, or unit.
   Tools: none; then final answer.

## Error Avoidance

- Report only the requested number: no explanatory prose, no restated unit label, no unrequested qualifier; a difference between two percentages is a plain numeric difference.
- When several bulletins report the same period, do not use an unrevised value if a later bulletin revises it.
- Enumerate the expected observation count (inclusive range) before aggregating; do not compute over a partial set.
