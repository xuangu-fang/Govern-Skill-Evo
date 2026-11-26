# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages. If a direct path or exact filename is rejected or returns no matches, broaden the glob pattern (down to a bare wildcard if needed) to discover where the documents actually live, then grep inside the resolved files; do not abandon local search after one failed pattern.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.
- Confirm the statistical convention before computing: use the population form (divide by n) only when the question says "population standard deviation," and default a plain "standard deviation" over a finite observation set to the sample form (n−1). Use a geometric mean (product root or mean of logs) for growth rates and compound series, not the arithmetic mean. A common deflator applied to both numerator and denominator of a share cancels, so do not stall on extracting it.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- When the question specifies a unit and precision, emit only the numeric value in that format. Do not repeat the amount in another unit, add parenthetical conversions, append qualifier words such as "percentage points," or write the value as a prose sentence, since any extra token beyond the requested value can break exact match.
