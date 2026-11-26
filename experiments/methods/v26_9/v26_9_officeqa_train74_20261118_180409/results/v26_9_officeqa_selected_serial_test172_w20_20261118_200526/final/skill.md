# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- When the requested quantity is a rate derived from two dated values (a log return, a constant hazard or growth rate, a compound rate), fix the chronological direction before dividing: the earlier period is the base and the later period is the ending value, so growth yields a positive rate and decline a negative one. After computing, compare the rate's sign with the direction of the two values actually extracted from the text; if they disagree, the ratio is inverted, so recompute instead of returning it.
- If the question asks for a transformed or derived quantity, apply the transformation directly from the definition implied by the question only after both operands are confirmed. If one targeted search for the method's name returns no definitional text, stop looking for a formula, auxiliary file or data file in the corpus and compute from the extracted values, so remaining rounds are available for checking operands, direction and rounding.

## Final Answer Discipline
- After retrieval and computation, put only the requested value inside `<answer>`. For a numeric quantity, return the number at the precision the question requests, with a minus sign only if the value is negative; do not wrap it in a sentence, add a currency symbol, or append unit words the question supplies (for example "thousand," "percentage points," or a scale word such as "million"), except as directed by the percentage rule below.
- Decide the final answer's expression from the question's explicit instruction about how to state the answer, not from the units of the quantity being measured. Use a trailing "%" only when the question directs you to report the result in percentage terms or as a percent; when the question merely names a percent-based quantity (a percent change, percentage points, or a share phrased as "what percent of X is Y") and asks for rounding to a stated precision, return the bare number at that precision with no percent sign and no unit words. Keep the sign the question calls for: when it asks for an absolute difference or magnitude, return a nonnegative number, and when it asks for a signed change, retain the minus sign for a decrease. Before emitting, re-read the question's final sentence and check that each symbol or unit placed inside `<answer>` was requested there.
- When the question asks for a period, answer "Month Year" or the year. When the answer is not a quantity, answer in ordinary prose.
- When a table's sign convention already encodes direction, return the signed number without spelling out "inflow" or "outflow," and do not add a second explanatory sentence inside `<answer>`.
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
