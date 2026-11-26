---
name: officeqa-treasury-bulletin-qa
description: Retrieval and computation discipline for answering OfficeQA questions over local Treasury bulletin text files.
when_to_use:
  - The question asks for a numeric value, aggregate, projection, or formatted tuple drawn from Treasury bulletin tables, charts, or text.
  - The answer requires locating a specific bulletin, page, table, chart, or time-series window before computing.
---

## Workflow

1. **Narrow to the relevant bulletin(s) before reading long passages.** Establish valid file paths first, then search for the exact entity, period, measure, or table concept. Read a small surrounding span to confirm the year, basis, and unit match. Candidate tools: file lookup/listing, glob, targeted grep, bounded reads.

2. **Cover the full requested time window.** Enumerate every bulletin year that could hold the earliest observation — an early month's data may sit in a bulletin published near the start of the window, not only the latest years. Confirm the discovered file set spans the whole range before extracting.

3. **Target the exact row, column, chart, or page.** When the question names a page, table, or chart identifier, navigate to that location via the table of contents and confirm the evidence actually sits there. For tables, map multi-row headers and align each value by exact row label and column header.

4. **Extract exact operands and verify the observation set.** Record each value's period, unit, and semantic role. For an aggregate over a date range, enumerate the expected observation count (inclusive of both endpoints) and confirm the retrieved series is complete before computing.

5. **Compute only after operands are confirmed.** Apply the requested method (e.g., geometric mean as the exponential of the mean log, OLS projection, unit conversion, ratio, absolute difference), keep intermediate values unrounded, and round only the final result to the requested precision.

6. **Final consistency check.** Re-verify units, sign, precision, and tuple ordering against the question, then emit a value copied from checked evidence inside <answer>...</answer>.

## Error Avoidance

- Do not answer from memory or inference when retrieval fails; rephrase search terms or check an adjacent bulletin, and never emit a value not grounded in retrieved text.
- When the requested period spans years, do not drop the bulletin covering the earliest month; an incomplete series silently corrupts sums, means, and geometric means.
- When the question names a page, table, or chart, do not answer from a topically similar section; go to the exact referenced location, using the table of contents for page numbers.
- Do not mix adjacent columns or similarly named rows; confirm each value's header matches the requested semantic role, period, and unit.
- Round only the final result to the requested precision; keep intermediate operands unrounded.
