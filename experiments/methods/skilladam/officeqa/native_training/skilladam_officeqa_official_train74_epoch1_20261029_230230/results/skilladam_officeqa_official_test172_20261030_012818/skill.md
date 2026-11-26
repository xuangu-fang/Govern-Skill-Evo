# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- Preserve the sign through every step: when the answer is a difference, "change," or net figure, report it as the signed number the question asks for (a decrease is negative) rather than dropping the sign or restating a decline as a positive magnitude.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.
- If a read returns only headings, table-of-contents entries, section labels, footnotes, or annual aggregates instead of the specific numeric data rows for the requested periods, the operands are not yet extracted: keep targeting (grep the exact row label, read the continuation page, or switch to the monthly/annual sub-series) until the actual numbers for every required period are visible, then compute.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- Emit the requested quantity in a single form: do not append a parenthetical restatement, an alternate-unit or alternate-percent version, or explanatory notes after the number (e.g., "0.045 (about 4.5% rate)"). Include only the unit the question itself asks for; extra trailing text becomes extra tokens that break exact match.
