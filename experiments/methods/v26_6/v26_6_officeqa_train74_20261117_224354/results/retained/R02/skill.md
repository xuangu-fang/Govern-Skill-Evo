# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- When a calculation uses multiple periods and the same period appears in both an earlier bulletin table and a later bulletin table, check the later table for an explicit revision marker on any period included in the calculation. If the later table marks that period's value as revised, substitute the revised value before computing instead of the earlier unrevised value. Use the complete earlier table for periods without a later revised value, and use the later revised values for the periods they cover. Apply this only when the later table visibly ties the revised value to the same measure and period; do not substitute a merely similar label or a different measure.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- Inside the `<answer>` element, return only the requested answer value. For a numeric result, give the number alone in the unit the question already specifies; do not append unit words, labels, explanatory prose, or parenthetical alternative conversions inside the tags. Include a percent sign only when the question explicitly asks for a percent; when the question instead asks for a value in thousands or millions, or for a decimal number of percentage points, give the number alone. A short explanation or consistency check may appear before the final answer tag if useful, but not inside it. The final-answer response does not request another tool.
