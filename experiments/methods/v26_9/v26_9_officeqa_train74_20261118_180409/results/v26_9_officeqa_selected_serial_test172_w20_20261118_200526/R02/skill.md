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
- After retrieval and computation, put only the requested value inside `<answer>`. For a numeric quantity, return the number at the precision the question requests, with a minus sign only if the value is negative; do not wrap it in a sentence, add a currency symbol, or append unit words the question supplies (for example "thousand," "percent," "percentage points," or a scale word such as "million"), except for the explicit percentage case below.
- Use a trailing "%" only when the question explicitly asks for a percentage or to report the answer as a percent; do not add "%" merely because the underlying measure is a rate, growth rate, or a change expressed in percentage points.
- When the question asks for a period, answer "Month Year" or the year. When the answer is not a quantity, answer in ordinary prose.
- When a table's sign convention already encodes direction, return the signed number without spelling out "inflow" or "outflow," and do not add a second explanatory sentence inside `<answer>`.
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
