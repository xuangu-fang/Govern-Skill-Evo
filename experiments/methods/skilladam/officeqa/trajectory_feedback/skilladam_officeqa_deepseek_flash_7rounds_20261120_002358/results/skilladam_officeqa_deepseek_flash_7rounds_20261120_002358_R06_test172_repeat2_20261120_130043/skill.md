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

3. **Align the exact row, column, and scope.** Map multi-row headers to the correct column and keep semantically distinct series separate: receipts vs outlays, offered amount vs tenders received vs tenders accepted, competitive vs noncompetitive, adjacent-year and adjacent-maturity columns. Distinguish level series from percent-change, ratio, and transaction-value series — a percent-change or index table is not the absolute level operand you need, so keep looking for the level table. Where a table reports cumulative or year-to-date figures, difference consecutive rows to get the monthly or annual increment. Read footnotes — they state what a column already includes or excludes, so honor them instead of adding or subtracting proxy columns.

4. **For chart questions, use the backing data.** Treasury Bulletin charts almost always plot figures that also appear in a table in the same or a nearby issue. Locate that table and derive the answer from it rather than trying to read plotted points from the text extraction.

5. **Compute only after operands are confirmed.** For an inclusive month range spanning multiple years, enumerate the expected observation count and check the extracted set is complete and unit-consistent. In multi-part questions, list every required operand first — the primary series plus any auxiliary rate, index, benchmark, or deflator the question relies on — and confirm each is found before computing; a missing auxiliary operand is not a license to substitute a guessed value. Fix the formula convention before computing. For order-statistic questions (percentiles, VaR, trimmed mean), sort the extracted observations and apply the exact rank or plotting-position rule the question names — e.g., nearest-rank, linear interpolation, Hazen — rather than defaulting to the single largest or smallest value. Keep full precision until the final rounding, and sanity-check that an aggregate sits in a plausible range relative to its inputs.

## Error Avoidance

- Never grep or read a guessed filename — obtain full paths from a glob first, then search those.
- When combining values from multiple yearly issues, confirm units and row labels match across issues before aggregating; a scale or label change between issues silently corrupts the result.
- Honor table footnotes on inclusion and exclusion before summing or offsetting proxy columns, and never mix distinct series roles such as receipts vs outlays, tenders received vs accepted, or competitive vs noncompetitive.
- When a question cites a chart, find the underlying data table instead of inventing plotted values.
- Round only the final result and keep intermediates unrounded. Prefer returning just the numeric value at the requested precision — do not append percent signs, unit words, or currency names/abbreviations (e.g., INR, DEM, yen, rupees) unless the question explicitly requests that unit in the answer; a correct number with an extra trailing qualifier no longer matches.
