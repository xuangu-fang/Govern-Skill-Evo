# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- When the question specifies an answer shape, put only the requested final element(s) inside <answer>...</answer>: no headings, restated subquestions, operand-by-operand derivations, bullets, bold markers, or explanatory sentences inside the tag. Preserve the requested order, bracket/comma format, precision, sign, percent conversion, and the answer convention the question actually asks for (such as a percent sign when a percent is requested, or a U.S. long-format date when a date is requested); perform any derivation before the tag and copy the checked final value(s) into it.
- Inside <answer>, emit only the answer element the question asks for. When the question states a scale or unit only as context (for example 'in thousands of U.S. dollars' or a rate stated 'as a percent') or asks for a difference between two rates, return the bare numeric value and do not append the scale words, 'percentage points', or a parenthetical direction such as '(net inflow)'.
- Treat the requirement to preserve the 'required unit form' as requiring only the convention the question actually asks for, such as a percent sign when a percent is requested or a U.S. long-format date when a date is requested; do not restate a measurement scale or unit phrase that the question already supplied.
- Keep a percent sign only when the question asks for the answer as a percent; otherwise omit it, and keep the requested precision, comma grouping and sign as written.
- Words belong inside the tag only when they are the requested content itself, such as a U.S. long-format date or a year; otherwise the checked number is the whole answer.
