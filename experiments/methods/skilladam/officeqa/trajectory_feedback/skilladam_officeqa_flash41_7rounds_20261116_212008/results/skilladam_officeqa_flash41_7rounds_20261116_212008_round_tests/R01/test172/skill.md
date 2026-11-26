---
name: treasury-bulletin-qa
description: Retrieve, align, and compute answers from local Treasury Bulletin text files.
when_to_use:
  - The question points at Treasury Bulletin tables, financing operations, trust funds, budget receipts or outlays, money in circulation, or bond yields.
  - The answer requires locating one row or column, a chart series, or a multi-month value series before computing.
---

## Workflow

1. **Resolve the document set before searching.** A grep against a guessed or unresolved filename is rejected and burns turns from a limited budget. Start with a broad glob over the text-file tree, then grep only the paths the glob actually returned, and reuse the resolved path verbatim for every later search and read. Candidate tools: glob, grep.

2. **Narrow to the right table.** Search on table titles or numbers and on the exact entity-plus-measure phrases from the question. Before reading a long span, confirm the section basis (fiscal vs calendar year), the unit (thousands, millions, billions), and whether this issue even covers the requested period; if not, move to the neighboring issue, because a given month's figures are often printed in a later bulletin than the one you first guess. Candidate tools: grep, read.

3. **Lock the row and column role.** Multi-row headers and adjacent columns frequently hold different transaction or measurement roles (offered vs tenders received vs tenders accepted; competitive vs noncompetitive; receipts vs outlays; gross vs net). Read the header block and the footnotes together with the data row. When a footnote defines a column as already including the components the question names, or already excluding the ones it excludes, that column value is the operand — do not re-sum or re-adjust the sub-items. Candidate tools: read, grep.

4. **Assemble the complete operand set.** For questions spanning many months, enumerate the expected observations (start month through end month inclusive) and confirm the extracted count matches before computing. In tables that interleave monthly rows with calendar-year or fiscal-year total rows, take only the monthly rows. Record which bulletin issue each value came from, since the same month can be restated across vintages. Candidate tools: read, grep.

5. **Settle the convention, then compute.** Decide the method the question asks for before touching the numbers — geometric mean via the log-average (or product then nth root), population vs sample dispersion, simple vs compound growth, regression against a numeric period, ratio vs percentage-point difference — then convert to the requested unit and carry full precision until the final rounding. Re-check the operand lines against your notes after computing. Candidate tools: read (to re-verify the operand lines).

6. **Chart and exhibit questions.** A chart's series is usually restated in a table elsewhere in the same bulletin. Search for the series by name, by the exhibit title, and by characteristic axis values before trying to read a plotted line from parsed text. Count peaks, crossings, or exceedances only from points you actually extracted; if the parsed text yields no usable series, report that the chart data could not be extracted rather than answering a guessed number. Candidate tools: grep, read.

7. **Format the answer from the checked value.** Emit only the requested value, at the requested precision, sign, unit convention, and date style — nothing else. Candidate tools: none (final formatting).

## Error Avoidance

- Never grep a filename you have not confirmed exists; run a broad glob first and reuse the resolved path for every subsequent search and read.
- Never mix calendar-year or fiscal-year total rows into a monthly series; verify the extracted count equals the inclusive month span.
- Never substitute an adjacent column, or a sum of sub-components, for the column the question names; confirm the header role and footnotes first.
- Never answer a chart question with a count, peak, or comparison you did not derive from extracted points; find the tabulated equivalent or state that the series is unavailable.
- Never append unit words, percent signs, currency symbols, or period-type qualifiers to the answer unless the question asks for them; round only the final value.
