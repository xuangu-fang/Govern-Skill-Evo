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
- When the question specifies an answer shape, put only the requested final element(s) inside <answer>...</answer>: no headings, restated subquestions, operand-by-operand derivations, bullets, bold markers, or explanatory sentences inside the tag. Preserve the requested order, bracket/comma format, precision, sign, percent conversion, and required unit form; perform any derivation before the tag and copy the checked final value(s) into it.
