# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- For a dispersion or volatility statistic over several periods in a table whose rows are categories, first decide whether the requested quantity is one entity or a government-wide total. For a government-wide amount, such as monthly or annual net outlays, use the table's bottom net-total line as the series; a table title saying `by function` or `by agency` does not make the category cells the sample. For a named department, agency, function, or object class, use that entity's row. Read only the columns for the requested fiscal or calendar year; when both current-year and prior-year columns are printed, use the requested year's column, not both, and exclude the adjacent column for the neighbouring year. Do not pool category-by-period cells into one sample, because that mixes magnitudes of very different scale and can import malformed cells. Before computing, state in ordinary text which row and which column span the sample uses, so the series choice is auditable; keep the answer element limited to the resulting value.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
