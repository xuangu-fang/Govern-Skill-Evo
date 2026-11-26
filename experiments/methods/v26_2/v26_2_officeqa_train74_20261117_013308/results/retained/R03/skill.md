# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.
- When a question attributes a value to a chart or figure on a named page, first check whether the supplied page text actually contains plotted values or legend labels; if it holds only the figure's title or heading, treat the plotted numbers as unrecovered rather than available.
- Then search the figure's caption terms and any distinctive category labels, and read the table the caption or chart refers to as the fallback source, bounding this to a few targeted calls so rounds remain for the final answer.
- When mapping a chart category to such a table, use the table's own group headings and include every subrow under a selected heading; do not assemble a partial total from selected subrows or omit adjacent subrows (for example, a supplies/materials subrow under a larger services-and-supplies group). Sum across headings only when the chart label itself supports that aggregation; component-wise summation remains appropriate when the requested total requires it.
- If no table heading or caption literally supports the quoted category, state outside the <answer> tag which rows were mapped and that the figure's own breakdown was unavailable, and prefer the best-supported mapping over an unsupported exact-sounding claim. Do not describe the proxy table as having 'confirmed' the figure's values.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- Put only the requested value in the final <answer> element: the number with the required sign, rounding/precision and percent convention — no sentence, no restatement of period, entity, table or method, and no hedging or 'approximately' wording.
- Do not append unit or scale wording that is not part of the computed number, such as 'thousand', 'percentage points' or 'basis points'. A question phrased 'in thousands of dollars' or 'in millions of dollars' describes how to read the table and does not have to be copied into the answer; the answer string drops commas and the words million/millions/billion/billions/dollar(s)/nominal but keeps any other word, so 'million dollars' is harmless while 'thousand' or 'percentage points' changes the answer.
- Attach a '%' symbol only when the question asks for a percent or percentage rate; when it asks for a decimal or for a stated number of decimal places, return the bare rounded number with no '%' and no 'percentage points'.
- Keep any evidence summary, mapping assumption or arithmetic rationale outside the <answer> tag, and still end the response without requesting another tool.
