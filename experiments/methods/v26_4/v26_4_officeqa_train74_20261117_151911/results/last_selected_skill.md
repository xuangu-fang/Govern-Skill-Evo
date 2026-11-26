# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- When a multi-part question asks for a rate and an elasticity using midpoint percentage change but supplies only one measured series, compute the midpoint percentage change of that series for the elasticity and do not divide it by a midpoint time change or another implicit denominator. If the question explicitly names a second variable and asks for elasticity of one quantity with respect to that other quantity, compute both midpoint percentage changes and divide them. Keep the requested component order and rounding, and derive each component only from retrieved operands.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.
- When multiple source pages or files for the same measure cover overlapping periods, treat the later supplied source as the revised record for the overlapping periods.
- Before computing a series, compare each overlapping period and replace the earlier figure with the later published value, including values marked as revised; then fill the remaining periods from the earlier source.
- Do not treat a complete-looking row in one source as final when another supplied source updates any part of the same period.
- If the later source covers only a subset of the needed months, use it only for those months and keep the non-overlapping months from the earlier source.
- Apply this only when the sources describe the same measure, basis, and period, and keep different measures or classifications separate.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- The final `<answer>` element should contain only the requested answer payload, not the derivation, restatement, markdown emphasis, or supporting explanation.
- Follow the question's requested format exactly: if it asks for a single value, put only that value and include a unit label, including a percent sign, only when the question explicitly asks for that unit-bearing form; if it asks for no commas or words, omit them; if it asks for bracket-enclosed or comma-separated values, put only the ordered tuple in that format. Do not add connective words or restate the question's unit phrase around the value.
- For a single quantitative answer, treat any unit phrase in the question, such as a scale, a currency, a percentage, or percentage-point wording, as the scale of the number rather than as text to repeat.
- After extracting and computing, return only the numeric payload in the requested precision and format, without appending or restating the question's unit phrase or adding words that describe scale, currency, or percentage points.
- A question that merely asks for a percentage, or states a scale such as "in thousands of dollars", does not by itself require repeating that unit.
- Perform any extraction, comparison, or arithmetic before the final response, then emit the final `<answer>` with the answer alone. This does not require adding explanatory prose outside the answer element; it only prevents explanatory or formatted material from being mixed into the answer payload.
