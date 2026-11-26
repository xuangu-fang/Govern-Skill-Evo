# Live Mathematical MCQ Heuristics

## Option Comparison
- Compare all options before committing. The correct choice is often the strongest statement justified by the question, while nearby distractors are weaker, overstrong, or miss an equality case.
- When one choice gives an unrestricted global unboundedness or divergence statement and another gives a bound that holds only under an extra restriction, such as a smaller parameter range, a subclass of functions, or frequency support, first check the scope required by the question. A restricted bound is not automatically the stronger or more complete statement; do not choose it over the unrestricted result unless the restriction covers the whole scope of the question.
- When one option asserts an ordinary global equivalence, isomorphism, or homotopy equivalence under a stated invariant condition, while another asserts only a p-local equivalence for every prime under the same condition, do not treat the ordinary global equivalence as automatically stronger or more provable. Unless the hypotheses themselves supply the global upgrade, prefer the strongest local statement supported by the condition and reject the unsupported global upgrade.
- When an item contains an option saying that one of the remaining choices is correct but a stronger result can be proved, and the other choices are concrete mathematical formulas, estimates, classifications, or theorem variants, treat that stronger-result option as the answer whenever the item asks what can be proved, which estimate or statement holds, what is complete, which statement is equivalent, or what is strongest. Select it rather than replacing it with a detailed specific statement merely because that statement is precise or uses the notation. Use the weaker-version comparison - one solution rather than every solution, a special or low-dimensional case rather than the general case, an existence or sufficient condition rather than a characterization, one orientation rather than a complete classification, a sparse or lower bound rather than the full bound, or a special regularity rather than the best regularity - to recognize such remaining choices.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".
- Do not choose a choice merely because it adds a cautious negative caveat, such as saying a map need not be injective, a phenomenon may fail, or no model with an extra property can contain an example. A negative caveat must be forced by the hypotheses or by the theorem being asked about. When the positive structural statement is otherwise the strongest available statement and the negative clause is not supplied, select the positive statement.

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, or full equivalence.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.
- In classification or complete-description items, an option that adds a converse, such as saying every solution of an auxiliary equation produces an object of the original class, is stronger than a description that only lists the possible objects. Select the converse version only if the question explicitly asks for that converse or the hypotheses already supply it; otherwise prefer the option without the unsupported converse. Do not apply the general stronger-result preference to an added converse that the item does not authorize.
- When an option states a blow-up or divergence criterion for an integral of a norm, compare the exponent or parameter range exactly. Choose the critical-power divergence supported by the theorem; do not strengthen it to divergence for every smaller exponent, every epsilon-neighborhood, or a wider range unless the hypotheses separately guarantee that stronger range.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.

## Final Answer
- Output the final answer as the single option label only.
