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
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
