# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- When a monthly or other period statistic is computed from more than one supplied bulletin, first choose the table that actually contains every requested period and extract the full set from it. Then check the other supplied bulletins for overlapping periods; if a later bulletin shows a revised value for an overlapping period, use the later revised value for that period while retaining the complete table's values for periods it alone covers. Do not switch to a different fiscal-versus-calendar series merely because a later table exists. Reconcile the complete monthly set before computing the statistic.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.

## Final Answer Discipline
- In the final answer element, return only the requested value(s): the numeric result(s), rounded as specified, without derivations, equations, explanatory sentences, markdown emphasis, restated units, alternative conversions, intervening dates, or method. A unit or scale that the question uses only to define the requested quantity, such as a percentage-point or million-dollar basis, is not itself part of the answer string; do not append spelled-out unit phrases. Include a percent sign only when the question explicitly asks for an answer as a percent; when it asks for a difference in percentage points as a decimal, give the decimal alone. If the question provides an explicit output template, reproduce it exactly with only the requested entries, preserving its brackets, commas, spacing, ordering, and any required no-comma or no-decimal formatting. Before finishing, re-read the answer element and confirm it contains the requested value(s) and nothing else; continue to derive and verify the value from retrieved evidence before emitting it.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
