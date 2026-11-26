# Live Mathematical MCQ Heuristics

## Workflow

1. Parse the question's demand before reading the options. Restate whether it asks for the strongest provable statement, a complete characterization or list, a necessary-and-sufficient condition, or an exact value. Record the quantifiers and their scope (for every, there exists, exactly, at most), the hypotheses, and any domain restrictions or exception lists.

2. Calibrate strength. Sort the options by logical strength rather than by how detailed or plausible they look. Flag options strictly weaker than the justified result (dropped clause, one-directional implication, restricted special case) and options that overreach (upgraded regularity, added converse, arbitrary case generalized from a one-dimensional or special case, removed exceptions).

3. Compare every option against that calibrated strength. When the question asks for the strongest provable statement and one option declares that none of the listed statements is the strongest (that a stronger result can be proven), make it the leading choice: the concrete alternatives are near-miss paraphrases that each add or drop a clause, hypothesis, constant, or case, so such a declaration is typically correct while each concrete option is slightly off. Override it only by verifying that some concrete option reproduces the demonstrated result exactly, with nothing added or removed; plausibility or a theorem-like appearance is not verification.

4. Verify before committing. Re-check equality cases, boundary regimes, exception lists, and whether every quantified claim in the chosen option holds across the full stated family. Confirm the chosen option is not strictly implied by another listed option, since that would make it weaker than the strongest.

5. Format. Output the single chosen label inside the answer element with no other text.

## Error Avoidance

- Do not equate detail with strength: more formulas, more cases, or a longer enumeration do not make an option stronger or correct.
- Do not pick a hedged or narrowed restatement because it feels safe; a weakened statement loses to one matching the full justified strength.
- Do not accept added converses, "every such case occurs", or universality that the question does not force.
- Do not treat an option that points to a stronger available result as automatically evasive or wrong.
