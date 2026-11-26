# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Cross-Bulletin Revision Discipline
- When two or more candidate bulletins have tables covering the same month, quarter, or fiscal period, do not stop at the first matching table. Before computing, compare overlapping entries by period and classification.
- For each overlapping entry, use the most recently published revision, including any entry marked revised. Keep the rest of the series from the latest table that supplies the complete requested period.
- If a later bulletin revises only some entries, replace only those entries and retain the other values from the complete-period table. If no later bulletin reports a given period, use the single bulletin that contains it; do not replace values merely because another bulletin exists.
- If the question explicitly anchors the answer to a named earlier bulletin or edition, follow that anchor instead of the general revision preference.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- Inside `<answer>`, return only the final requested result: a single checked value, not a sentence, derivation, alternate restatement, bold markup, or parenthetical arithmetic.
- Express the number in the scale the question asks for, without appending a scale word, currency name, agency abbreviation, or phrases such as percentage points.
- When the answer is in percentage units but the answer format does not explicitly request a percent sign, return the numeric value without `%`; a phrase such as "what percentage" or "percentage point difference" names the units but does not itself request `%`. Append `%` only when the prompt explicitly asks for a percent sign. Preserve any required brackets, comma separation, number of values, and rounding exactly.
- Put reasoning, extraction notes, and verification outside the answer element or omit them, and end with a single checked value that already reflects the requested rounding. Short explanatory text outside the tag is allowed.
