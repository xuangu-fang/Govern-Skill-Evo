# Live Mathematical MCQ Heuristics

## Option Comparison
- Compare all options before committing. The correct choice is often the strongest statement justified by the question, while nearby distractors are weaker, overstrong, or miss an equality case.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".
- When a question asks for the strongest provable statement and an option says the listed statements are not sharp and a stronger result can be proven, treat that option as a live answer rather than a non-answer. Actively try to refute each concrete option by naming a specific defect (wrong index, sign, coefficient, constant, hypothesis, or dropped clause); commit to a concrete option only if one survives and you can state the exact detail that makes it true. If the concrete options are pinpoint variants of a single claim that you cannot certify, choose the option asserting a stronger result exists.

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, or full equivalence.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.
- Watch for underclaiming, which is just as common: exhibiting one object where the theorem is uniform over all objects, asserting a weaker regularity or integrability class, giving a one-sided limit statement where growth or unboundedness is proved, or restricting to generic/irreducible objects when the result covers all of them.
- Count the conclusions an option asserts at once; an option that preserves all the parallel clauses of the theorem is stronger than a near-miss that silently drops one of them.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.
- Treat any added converse ("every such case actually occurs", "the conclusion survives without the listed exclusions", "holds for every index or model") as a separate existence or uniformity claim that must be justified, since this is the usual route by which a distractor becomes stronger than the theorem.

## Final Answer
- Output the final answer as the single option label only.
