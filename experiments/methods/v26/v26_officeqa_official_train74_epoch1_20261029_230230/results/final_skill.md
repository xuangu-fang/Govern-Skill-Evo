# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.
- When a `grep` or `read` call on a candidate filename returns a 'path not allowed' error, or a filename-specific `glob` returns no matches, do not repeat the same filename form; issue a broad `glob "*"` to list available document paths and use the exact returned path for subsequent `grep`/`read` calls.
- Apply this path discovery only when the rendered excerpt does not already contain the needed evidence; if the excerpt is sufficient, answer from it without further file discovery.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.
- When a question asks for an 'absolute percent difference' between two named values and names no base, use the midpoint (average) of the two values as the denominator: `|second - first| / ((first + second) / 2) x 100`, and round as requested; do not silently switch between bases within one answer. When the question instead asks for a 'percent change' (for example, 'from A to B' or 'year over year'), use the earlier or initial value as the denominator: `|second - first| / first x 100`. When the question explicitly names a base value, use that named base.
- When a question asks 'what percent of X is Y', divide Y by the named whole X, not by a subtotal or adjacent total that covers different items.
- For any percentage, extract both operands from the same reporting basis, period label, and unit before dividing, and apply the requested rounding only after the division.
- When a requested statistic spans periods covered by more than one provided bulletin or page, treat the later bulletin as superseding earlier values for overlapping periods when the later table marks them revised (for example, with an 'r' prefix) or republishes the same period.
- For each overlapping month or year, substitute the revised value before computing the statistic, keeping the same row label, period coverage, and units across sources.
- Do not combine an unrevised earlier value with revised later values in one calculation; if no later or revised value exists for a period, retain the available value.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.
- When the question specifies the quantity, unit, and rounding, place the checked numeric value at the requested precision (with its sign when the quantity is a net inflow or outflow) directly inside `<answer>`; do not wrap it in an explanatory sentence or restate a unit or descriptor such as "thousand dollars," "millions," or "percentage points" merely because the prompt names that unit. A unit stated only in the question is not a request to repeat it in the answer.
- Keep only display formats the question explicitly requests: use a U.S. long date when that format is requested. When the question asks for a percent value ('what percent of ...') or for a percent difference or percent change, submit only the numeric result at the requested precision inside `<answer>`; do not append a `%` sign merely because the question's wording asks 'what percent' or asks for a 'percent difference.' Include the `%` symbol only when the question explicitly requests that display (for example, 'include the % sign' or 'report it as a percent with the symbol'); never add it when the question instead names another unit (such as 'in millions of dollars') or asks only for a number rounded to a stated decimal place. Computing a percent still means forming the required ratio, multiplying by 100, and rounding only after the division; only the presence of the symbol changes. Do not add 'percentage points' or similar wording unless the question explicitly asks for it.
- When the question asks for a direction such as inflow or outflow, treat that as a request for the signed net amount; let the sign carry the direction and do not add a separate direction phrase unless the question explicitly tells you to report the direction as a word.
