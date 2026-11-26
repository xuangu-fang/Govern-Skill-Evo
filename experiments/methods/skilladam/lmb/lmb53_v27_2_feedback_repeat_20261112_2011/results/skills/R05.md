# Live Mathematical MCQ Heuristics

## Workflow

1. Parse the ask. Restate in one line what the question demands: the strongest provable statement, a complete characterization or list, a specific value, or merely a valid claim. Mark every quantifier and scope word (for all, there exists, at most, exactly, if and only if) and every parameter range together with its endpoints.
2. Calibrate strength. Decide what the underlying result actually guarantees, then classify each option against that baseline as weakened (drops a clause, keeps only one direction of an equivalence, restricts to a subfamily, relaxes a constant), overstated (adds a converse, upgrades regularity, widens a parameter range, turns "some" into "every"), or exact.
3. Compare all options, including meta-options. Do not stop at the first plausible choice; line up near-duplicates and locate their exact difference: strict versus non-strict inequality, included versus excluded endpoint, an appended converse clause, a different divisor or index condition. A self-referential option (one saying another listed option is right but a stronger statement is provable, or that only a weaker statement holds) is a live candidate, not filler: it is the intended answer exactly when no concrete option attains the true full strength. When the question asks for the strongest provable statement and the concrete options are several near-identical precise formulations, that condition is usually met, so hold them to a high bar and prefer the meta-option unless one concrete option can be positively certified as the exact full-strength statement.
4. Verify and format. Re-read the chosen option against the hypotheses and, for each rejected option, name the single clause that rules it out. Then output one label inside <answer></answer>.

## Error Avoidance
- Specificity is not strength: a long, confident-looking option can still be an overstatement. Accept an extra clause (a converse, stronger regularity, a wider range) only when it belongs to the result itself, not to what the setup merely suggests.
- When the question asks for the strongest provable statement, do not retreat to a hedged or timid option if a stronger listed option is fully entailed.
- Among near-identical options the deciding difference is usually a boundary (strict versus non-strict, endpoint included or not) or an appended converse clause; check those first.
- Do not discard a meta-option just because some concrete option looks detailed and complete; discard it only when one concrete option can be certified to carry exactly the full strength.
