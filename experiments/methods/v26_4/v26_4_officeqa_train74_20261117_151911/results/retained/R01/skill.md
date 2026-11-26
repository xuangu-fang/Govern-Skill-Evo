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
- The final `<answer>` element should contain only the requested answer payload, not the derivation, restatement, markdown emphasis, or supporting explanation.
- Follow the question's requested format exactly: if it asks for a single value, put only that value and, if the format calls for one, a short unit label; if it asks for no commas or words, omit them; if it asks for bracket-enclosed or comma-separated values, put only the ordered tuple in that format. Do not add connective words or restate the question's unit phrase around the value.
- Perform any extraction, comparison, or arithmetic before the final response, then emit the final `<answer>` with the answer alone. This does not require adding explanatory prose outside the answer element; it only prevents explanatory or formatted material from being mixed into the answer payload.
