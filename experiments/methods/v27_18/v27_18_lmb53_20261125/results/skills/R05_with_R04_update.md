# Live Mathematical MCQ Heuristics

## Option Comparison
- Compare all options before committing. The correct choice is often the strongest statement justified by the question, while nearby distractors are weaker, overstrong, or miss an equality case.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".

## Meta-Options Asserting a Stronger Result
- Before doing substantive theorem comparison, scan every option for a grammatically coherent meta-option asserting that one of the remaining options is correct but a stronger result can be proven, or that the listed alternatives are not maximal. Treat such an option as a live answer and, when the trigger below applies, as the default answer.
- Compare substantive options for signs that they are weakened versions of the full theorem: a dropped converse or exhaustiveness clause, weaker regularity, strict versus non-strict boundary cases, omitted exceptional cases, or a merely sufficient rather than complete classification. When comparing only substantive options (that is, when no applicable meta-option controls), do not treat an option as stronger or more complete merely because it is more elaborate. If an option appends a converse such as "and conversely every such construction yields the required object," or replaces an unconditional universal claim with a "precisely when" restricted characterization, select the elaborated option only if the prompt explicitly asks for that converse or exact characterization and the stated hypotheses support the added assertion; otherwise choose the option that asserts the established claim for every object or pair, or only the established direction, even when the question uses words such as "complete classification" or "strongest statement." Genuinely supported stronger clauses may still be chosen; this rule targets added converses and iff/restriction clauses whose support is missing.
- Treat any stem asking which statement holds, is correct, is equivalent, characterizes the situation, or is the strongest as a question about competing candidates of different strength; the literal word "strongest" is not required. Select the meta-option even if another substantive option exactly matches the hypotheses, adds a sign or positivity condition, gives a congruence or equality, includes a full iff or equality clause, refines an exponent, or resembles the known theorem. Do not displace it merely because a concrete statement appears exact or maximal. Override the meta-option only when it is syntactically inapplicable, it refers incorrectly to the remaining options, or the prompt makes a meta-answer impossible. If no such meta-option is present, compare substantive options normally.

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, or full equivalence, but do not assume that a more elaborate converse or "precisely when" characterization is stronger unless the prompt explicitly asks for it and the stated hypotheses support it.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.

## Final Answer
- Output the final answer as the single option label only.
