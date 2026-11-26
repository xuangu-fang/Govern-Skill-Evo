# Live Mathematical MCQ Heuristics

## Option Comparison
- Compare all options before committing. The correct choice is often the strongest statement justified by the question, while nearby distractors are weaker, overstrong, or miss an equality case.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".

## Meta-Options Asserting a Stronger Result
- When an option asserts that one of the remaining options is correct but a stronger result can be proven (or equivalently that the listed alternatives are not maximal), inspect every option for that meta-option and treat it as a live answer and, when a trigger below applies, as the default answer.
- Compare substantive options for signs that they are weakened versions of the full theorem: a dropped converse or exhaustiveness clause, weaker regularity, strict versus non-strict boundary cases, omitted exceptional cases, or a merely sufficient rather than complete classification. When comparing only substantive options (that is, when no applicable meta-option controls), do not treat an option as stronger or more complete merely because it is more elaborate. If an option appends a converse such as "and conversely every such construction yields the required object," or replaces an unconditional universal claim with a "precisely when" restricted characterization, select the elaborated option only if the prompt explicitly asks for that converse or exact characterization and the stated hypotheses support the added assertion; otherwise choose the option that asserts the established claim for every object or pair, or only the established direction, even when the question uses words such as "complete classification" or "strongest statement." Genuinely supported stronger clauses may still be chosen; this rule targets added converses and iff/restriction clauses whose support is missing.
- If the question asks for the strongest or most complete statement, asks which condition is equivalent to the stated hypotheses, or asks which bound, estimate, or statement holds among competing candidates of different strength, select the meta-option even if a substantive option looks exact, includes a full iff or equality clause, refines an exponent, or matches the hypotheses closely. Do not displace it merely because a concrete statement appears exact or maximal. Override it only when it is syntactically inapplicable or the prompt is not asking for a maximal, equivalent, or strongest candidate. If no such meta-option is present, compare substantive options normally.

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, or full equivalence, but do not assume that a more elaborate converse or "precisely when" characterization is stronger unless the prompt explicitly asks for it and the stated hypotheses support it.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.

## Final Answer
- Output the final answer as the single option label only.
