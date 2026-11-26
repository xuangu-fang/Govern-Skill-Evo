# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.
- When a read or grep call against a bare candidate filename returns a path-not-allowed error, or a recursive glob such as `**/filename` returns no matches, do not repeat the identical failing call or conclude that the document is unavailable.
- Issue a non-recursive glob using the candidate filename itself or a top-level wildcard, then pass the exact path returned by that successful glob to subsequent read and grep calls.
- When initial parsed-page excerpts already contain the values needed for the requested value or calculation, continue from those excerpts rather than spending rounds on local path recovery.

## External Factors
- When a requested calculation depends on a currency conversion rate, external constant, or other factor that is not present in the retrieved document text and is not explicitly supplied in the question, search the candidate files for that factor, its period, and its units before computing; use targeted terms for the factor's name, currency pair, and period (such as a currency name with "per U.S. dollar" or an exchange-rate table title), rather than searching only for a guessed numeric rate.
- If the factor is still not retrieved after those targeted checks of the candidate files, stop searching; do not substitute a remembered, standard, or inferred rate, do not treat a guessed numeric probe as retrieval unless the surrounding table or context identifies the requested currency pair and period, and do not reconstruct the missing value from adjacent periods. Do not present a numeric result that depends on the missing factor; report the missing factor and the portion of the calculation that cannot be completed from retrieved evidence.
- If the factor is retrieved or explicitly supplied in the question, use its stated period and requested rounding, and continue with the retrieved receipts or other operands without changing the requested period, units, or deliverable.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.
- When the question names a statistical variant, apply that exact definition instead of a default: use the population denominator N for 'population standard deviation' (or variance) and N−1 for 'sample standard deviation' (or variance).
- When the question asks for a 'standard deviation' or 'variance' without naming a variant, use the population denominator N as the default unless the wording or context indicates a sample.
- For a z-score that standardizes one target observation against a small, explicitly named set of prior observations used to estimate the reference distribution, first derive each observation's change from the underlying cumulative series if the question asks about increases.
- Use the mean and the sample standard deviation with the N−1 denominator of that named reference set to standardize the target observation, unless the question explicitly identifies the reference set as the entire population; do not use the standard error of the mean unless the question asks for a test of the mean. Do not apply the general population-denominator default for an unnamed standard deviation or variance to this z-score reference-sample calculation.
- Compare the resulting z-score to the stated threshold and report the classification with the requested rounding.
- Before finalizing, verify that the denominator and the included observations match the wording and period of the question; do not substitute the sample formula when population is requested or when the variant is unspecified, except for the z-score reference-sample calculation above, where N−1 is required unless the reference set is explicitly the entire population.
- When a final answer is produced through multiple derived values, such as year-over-year percentage changes followed by a percentile or interpolation, keep full precision for all intermediate values and do not round them before the next operation.
- For a historical-simulation percentile with linear interpolation, sort the unrounded derived returns and interpolate between adjacent order statistics; round only the final requested statistic to the specified number of decimal places.
- Apply any explicitly requested intermediate rounding only if the question states it.
- A chart title, caption, or narrative example in the retrieved text does not establish the chart's underlying data series.
- When a calculation requires a multi-period series and the retrieved text contains only a chart title or isolated period values, do not fill the missing periods with values from memory, general knowledge, or unstated assumptions.
- Continue targeted inspection of the available candidate file(s) for the actual textual series, and compute only after every required operand has been retrieved; do not present a computed result whose operands are absent from the retrieved text.
- If targeted inspection does not locate the textual series, state that the required plotted or multi-period values are unavailable rather than supplying a computed substitute; do not keep repeating the same unsuccessful search.

## Share and Ratio Computation
- When a question asks for a measure that a table presents as a heading grouping several sub-line items, populate the numerator with only those sub-items that are instances of the named measure.
- Exclude adjacent items listed under the same heading that denote a different concept (for example, do not treat an 'accounts receivable' line as a foreign-exchange security holding when the requested quantity is foreign-exchange securities).
- Confirm the numerator's included lines and the requested denominator against the heading and the question's wording before dividing, and keep the stated denominator and rounding.
- Preserve correct share computations when every sub-item under the heading matches the named measure.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- When the question specifies the answer structure—a bare decimal, a percentage-point change, a single number with no other characters, or a bracketed comma-separated list—emit exactly that structure with only the requested numeric tokens.
- For a requested change in percentage points, output the numeric change itself without a percent sign. A request to report the value 'in percentage points' describes the unit of that number; it does not by itself require appending the phrase 'percentage points' or a leading '+' sign.
- When a question asks for a percent change and specifies a rounding precision but does not explicitly ask for the result in percentage terms or as a percentage loss, compute the change from the requested beginning and ending values and return only the numeric percentage value in the final answer, retaining a negative sign when the change is a decrease unless the question asks for the absolute value. Do not append `%` or explanatory words merely because the quantity is called a percent change; retain the percent sign only when the question explicitly asks for the result in percentage terms or as a percentage loss. In either case, keep the requested period, calculation basis, and rounding unchanged.
- When a question asks for an 'absolute percent difference' between two named period values without stating a formula, do not silently default to dividing by the average of the two values; identify which value is the base before dividing.
- For a chronological comparison, compute the change from the earlier period as the base: |later value − earlier value| / |earlier value| × 100. If the question explicitly states a formula, explicitly identifies a starting or reference period (for example, 'from X to Y' or 'relative to X'), or explicitly requests a symmetric/average-based measure, use that stated basis instead.
- Extract both values from the measure the question names (the total row/column, not a sub-component), and apply the requested rounding.
- If the question explicitly supplies a difference formula, follow that formula exactly.
- Return the result in the numeric form the question requests; when it asks for a rounded value without requesting percentage terms or a percent sign, do not append `%` or explanatory words.
- Retain a scale or unit label, such as 'billions', when the question's requested reporting unit or answer template makes that label part of the answer; apply the specified rounding and precision exactly.
