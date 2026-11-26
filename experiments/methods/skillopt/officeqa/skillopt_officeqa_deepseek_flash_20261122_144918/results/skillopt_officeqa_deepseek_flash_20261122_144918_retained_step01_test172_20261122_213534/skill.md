# OfficeQA Skill

## Retrieval Discipline

- Resolve file paths before searching: run a glob for the candidate basename or use the workspace-prefixed `<officeqa-docs>/...` path; bare relative filenames or relative globs may be rejected as path-not-allowed and waste turns.
- If a glob/grep/read fails, run `glob("*")` or `glob("*.txt")`/`glob("**/*.txt")` once to discover the exact names and `<officeqa-docs>/` prefix, then reuse the resolved full path for all subsequent searches.
- Navigate by anchor: grep a distinctive table title, table ID, exact row label, or column-header phrase from the question to get a line number, then read a bounded window (roughly 20–80 lines) around that anchor instead of scanning whole pages.
- If a requested series appears only in a chart caption or prose without numbers, keep searching the same candidate file(s) for a numeric table or alternate indicator label; do not substitute unrelated keyword hits.
- When several candidate bulletins are supplied, locate and compare the same table in each before selecting a row; never carry a value from one file into another period.
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline

- For tabular evidence, map the requested concept to its exact column header (including multi-level header hierarchy) and period row, then list all required operands before extracting. Do not include adjacent subtotal lines, another period's balance, nearby prose, or chart estimates just because they are close. If the exact requested period is not present in the candidate set, do not substitute an adjacent period—locate the exact period or report the retrieval gap.
- Anchor extraction to the table title, unit line, and header hierarchy. Table text may carry pandas multi-index noise (`Unnamed: ...`, `Total.1`, trailing `nan`); match columns by semantic label. For side-by-side panels or repeated month labels, reconstruct the correct year/column before reading values; if bare month rows follow a year-labeled row, carry the running year forward.
- Use the change/delta column for "excluding endpoints" requests and the row whose period-end matches "between ... and ..." intervals.
- Before arithmetic, normalize units across operands and confirm FX quote direction; record the source table with each operand so overlapping revised and unrevised values from different bulletins are not mixed.
- Read footnotes and column headers for revisions, inclusion/exclusion rules, and special items already included in a total; adjust only when the footnote says an item is excluded. If a table reports cumulative levels, subtract adjacent rows to get the requested period change; if a table continues on another page, gather all parts needed for the complete series. Avoid totals, subtotals, and adjacent similar rows unless explicitly requested.
- If a chart page has only labels, locate the underlying source table named in the chart or table of contents and compute the requested percentage from its category totals.
- Statistical operations: for standard deviation over all specified years/months, use the population formula (divide by n) unless the question explicitly says sample; for geometric means, compute the nth root of the product of every included observation and verify the count; for lower-tail/VaR-style questions, identify the return/volatility series and apply the stated probability before converting currencies or units.
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.

## Final Answer Discipline

- Inside the required `<answer>` wrapper, match the requested output schema exactly: number of values, list brackets, units/currency, rounding, and whether units should be omitted. If the question asks for a number in millions or a single numeric value, return only that numeric quantity; do not append extra words such as 'million', 'percentage points', or '%' unless explicitly requested.
- Give only the requested final value after applying the stated rounding. Do not include unrounded source figures, alternative calculations, or explanatory prose.
- If the question's date or period differs slightly from the printed table label (e.g., asks 12/18/52 while the table shows 12/19/52), use the nearest printed row in the correct table rather than concluding the value is absent.
- Preserve signs through conversions and differencing; apply absolute value only when the question explicitly asks for an absolute difference. Match the requested output format exactly: precision, units, bracket/list style, decimal separator, and no commas where specified.
- For derived statistics, enumerate the exact ordered operand series, confirm N and whether population or sample standard deviation is required, keep full precision until the final step, then round and format exactly as requested.
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.

## Source Reconciliation
- If oracle-parsed pages already contain the exact table, treat them as primary evidence and use tools only to verify or resolve ambiguity.
- When the same period appears in multiple bulletin issues, use the issue/table specified by the question (for example, a latest-bulletin table) and keep the series on one consistent basis; do not splice overlapping revised and unrevised values.
