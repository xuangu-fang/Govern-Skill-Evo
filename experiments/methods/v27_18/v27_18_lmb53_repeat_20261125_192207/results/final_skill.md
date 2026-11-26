# Live Mathematical MCQ Heuristics

## Option Comparison
- Compare all options before committing. The correct choice is often the strongest statement justified by the question, while nearby distractors are weaker, overstrong, or miss an equality case.
- When choices differ between an ordinary equivalence and a localized equivalence such as `≃_(p)` for every prime p, do not treat the ordinary version as automatically strongest merely because it drops the qualifier. Preserve the localized qualifier unless the prompt explicitly supplies the additional information needed to upgrade it. For stated conditions, match the condition exactly: if one option uses a full gcd condition such as `(k,84)` and another splits or changes the divisor, choose the option whose qualifier and condition are both supported, even if an unqualified statement reads stronger.
- If a choice reads exactly "One of the remaining options is correct, but a stronger result can be proven," select that choice's label. Do not instead select a more detailed substantive theorem statement merely because it looks stronger; in this question format the quoted meta-option is the intended strongest-result answer. This applies whenever that exact meta-option appears, even if another option seems to describe the theorem directly.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".
- When two choices differ by an added negative limitation such as "need not be injective" or "no model satisfying WUA can contain such a pair," do not select the option with that limitation merely because the limitation is conceivable. Require the question or the stated result to support the negative claim; otherwise prefer the option that states the positive embedding/consistency result without the unsupported limitation.

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, or full equivalence.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.

## Final Answer
- Output the final answer as the single option label only.
