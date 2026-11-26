---
name: treasury-bulletin-qa
description: Retrieve, extract, compute, and format answers from local Treasury Bulletin text files.
when_to_use:
  - A question requires locating a figure, table, or chart in local Treasury Bulletin text files.
  - A question requires arithmetic, aggregation, growth, regression, or unit conversion on extracted bulletin data.
---

## Workflow

1. **Resolve real file paths before searching.** A bare guessed filename passed to grep or read is rejected and wastes turn budget. Enumerate candidates with a glob first — broadening the pattern when the first attempt returns nothing or the path is rejected — then run every search and read against the returned full paths. Candidate tools: glob to list files, then grep/read on the resolved paths.

2. **Narrow from bulletins to the one relevant table.** Search with exact terms naming the entity, period, measure, or table concept in the question. Read a small span around the hit and confirm the year, fiscal-versus-calendar basis, and units before trusting it as evidence.

3. **Align the exact row, column, and scope.** Map multi-row headers to the correct column and keep semantically distinct series separate: receipts vs outlays, offered amount vs tenders received vs tenders accepted, competitive vs noncompetitive, adjacent-year and adjacent-maturity columns. Read footnotes — they state what a column already includes or excludes, so honor them instead of adding or subtracting proxy columns.

4. **For chart questions, use the backing data.** Treasury Bulletin charts almost always plot figures that also appear in a table in the same or a nearby issue. Locate that table and derive the answer from it rather than trying to read plotted points from the text extraction.

5. **Compute only after operands are confirmed.** For an inclusive month range spanning multiple years, enumerate the expected observation count and check the extracted set is complete and unit-consistent. Fix the formula convention before computing. Keep full precision until the final rounding, and sanity-check that an aggregate sits in a plausible range relative to its inputs.

## Error Avoidance

- Never grep or read a guessed filename — obtain full paths from a glob first, then search those.
- When combining values from multiple yearly issues, confirm units and row labels match across issues before aggregating; a scale or label change between issues silently corrupts the result.
- Honor table footnotes on inclusion and exclusion before summing or offsetting proxy columns, and never mix distinct series roles such as receipts vs outlays, tenders received vs accepted, or competitive vs noncompetitive.
- When a question cites a chart, find the underlying data table instead of inventing plotted values.
- Round only the final result and keep intermediates unrounded; report the value in the requested numeric form without adding percent signs or currency symbols that were not asked for.
