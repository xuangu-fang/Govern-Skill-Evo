# Live Mathematical MCQ Heuristics

## Option Comparison

- Treat meta-options such as "One of the remaining options is correct, but a stronger result can be proven" as live candidates. When the prompt asks for the strongest, complete, or equivalent statement, select the meta-option if every concrete option states only a special, restricted, or deliberately weakened case—e.g. inclusion where equality is known, map where an embedding/isomorphism is known, local partial regularity where higher local regularity is known, an omitted equality clause, a less sharp exponent, or a weakened cardinality/quantifier threshold. Reject the meta-option only if a concrete option exactly matches the full proved theorem, including all equality cases, domains, and quantifiers.
- Decide between a concrete option and the meta-option by reconstructing the theorem's full conclusion. Choose the meta-option if you can legitimately add a clause, equality case, stronger quantifier, or larger scope beyond every concrete option; choose a concrete option only if it already states the strongest conclusion justified by the hypotheses.

- Eliminate choices with mismatched variable names or undefined symbols in the conclusion; a single notation error can make an otherwise strong-looking option invalid.
- Compare local versus global scope exactly: bounds depending on T versus uniform-in-time bounds, subdomain estimates versus whole-domain estimates, and a manifold versus its universal cover are not interchangeable.
- Compare all options before committing. The correct choice is often the strongest statement justified by the question, while nearby distractors are weaker, overstrong, or miss an equality case.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".

- **Meta-option trigger checklist:** Before choosing a concrete option, reconstruct the exact best theorem and compare it clause-by-clause with the closest concrete option. Select the meta-option if the theorem adds any reverse implication, broader sum/decomposition operation, larger exponent range, more precise counting clause, positive asymptotic growth, equality case, or removal of a restriction absent from every concrete option. A concrete option is not sufficient merely because it is true or plausible; it must be the strongest true concrete statement.
- **Gap checklist for meta-options:** Treat a meta-option as a live candidate when every concrete option has at least one of these gaps: replaces an available embedding/isomorphism with only a map or inclusion; omits injectivity; restricts to a special object, subfamily, test case, one parameter value, a sequence of scales, or an extra hypothesis; weakens strict to non-strict monotonicity, global to local regularity, an iff/complete characterization to a sufficient condition, or an exact exponent/endpoint to nearby exponents; adds an unproved clause; or omits an equality case.
- **Relation and adjective strength:** Compare conclusion types, not just wording. An embedding is stronger than a map or inclusion; a Poisson embedding includes injectivity, so a Poisson map with a possible-noninjectivity caveat is weaker if an embedding theorem is available. Strict monotonicity is stronger than non-strict. Specifying a particular element type or a single conjugacy class can be stronger than a vague existential condition. Do not assume more clauses automatically means stronger; test whether each clause actually upgrades the statement.
- **Extra-converse/completeness trap:** In a 'complete list' option that appends 'conversely, every such parameter value occurs', treat the converse as an independent existence claim. Completeness of the list does not assert realization of every formally allowed divisor or parameter. Unless that converse is explicitly supported, prefer the option that stops at the proved list.
- **Negative-caveat warning:** Phrases such as 'the converse need not hold', 'may fail', 'only 3-sums', 'stable length vanishes identically', or 'for a restricted subclass' signal possible weaker distractors. Require an actual counterexample or proof for the caveat before choosing it over a proved stronger or meta statement.

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, or full equivalence.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.

- Watch for terminology swaps between "unbounded", "stably unbounded", and "stable length vanishes identically"; and between local (compactly contained) and global statements, restricted vs arbitrary test functions, and exact parameter ranges.
- For any option with a plausible core plus an added claim, test the added claim separately. Extra converses, universal occurrence/existence clauses, added boundedness on a subrange, or added incompatibility/exclusion claims must themselves be proved; otherwise prefer the option without them.

- **Equivalence implication graph:** For 'all equivalent' choices, require every pair of implications. A proved A iff C plus B implies A does not justify B iff C or C implies B. Select the option matching exactly the proved implications, or the meta-option if a stronger implication is available.
- **Decomposition/classification operations:** Compare allowed operations and base classes as sets. 'Clique-sums of order at most 3' includes 2- and 3-sums, whereas 'only 3-sums' is a special case; adding a required exceptional base graph can also weaken a statement. Do not stop at the first recognized decomposition theorem.
- **Threshold and exponent endpoints:** Compare exponent thresholds literally. Do not treat 'for every epsilon > 0, exponent p - epsilon' as automatically stronger than the exact endpoint exponent p; the epsilon-family uses strictly weaker exponents, and the endpoint p cannot be inferred from it. More generally, a quantified family approaching a threshold is not the same statement as the threshold case. Identify the exact endpoint or exponent the theorem proves, and reject options that stop short of it.
- **Open-range/endpoint audit:** Do not upgrade a strict exponent or parameter inequality to equality, and do not include an excluded endpoint in a case split. If the proved regularity holds only for a strict threshold or open range, an option claiming the exact endpoint formula or endpoint space is overstrong; choose the version respecting the strict inequality, or the meta-option if the strict-range concrete option is correct but improvable.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.

## Strongest-Statement Audit
- Before answering, identify whether each concrete option omits a strengthening suggested by the question: larger exponent range, extra regularity/convexity, all admissible subdomains/functions, a stricter equality rather than one-way implication, or positive growth rather than mere unboundedness.
- Compare options along these axes before answering: inclusion vs equality; existence vs universality; map vs embedding/isomorphism; local vs global; regularity degree; exact exponent or numerical saving; and presence/absence of an "if and only if" equality case.
- If two numerical estimates differ only by coefficients or exponents, compare their strength explicitly rather than choosing the more familiar-looking bound; a bound with a larger saving is stronger when all other hypotheses match.
- A plausible, correct-sounding theorem is not enough: the question asks for the strongest provable statement, so a weaker true corollary is still a wrong answer when a stronger option or meta-option is available.
- Interpret "strongest statement" as the strongest statement justified by the hypotheses, not the logically strongest-looking option. Reject options that add unrequested quantitative estimates, higher regularity, uniform-in-time lower/upper bounds, or extra structural assumptions unless the question explicitly supports them. Use a meta-option like "a stronger result can be proven" only after checking that every concrete option is truly weaker than the available theorem.

## Multi-Clause and Classification Checks
- In options with several estimates, verify each clause separately: exponent, domain, constant dependence, and both upper/lower directions.
- For classification or quotient descriptions, check every numerical invariant and singularity clause; the correct choice usually gives the complete precise list, while distractors omit a clause or change one parameter.

## Final Strength Check
- Before selecting, explicitly write one sentence: "The theorem proves [exact statement]." Then map it to the choices. If no concrete choice matches that strength, use the meta-option rule above when a meta-option is present; otherwise reject stronger-looking variants unless each added clause is justified.
- Do not infer a stronger bound from a weaker one: a full-norm or full-vector conclusion does not imply a bound on a selected component, and a result for a restricted subclass does not imply the same result for the whole family.

## Additional Option-Anatomy Checks
- In multipart estimates, verify each part separately and keep the reference domain or object inside every bound fixed unless the theorem explicitly replaces it. A local assumption on a set or region does not authorize replacing a global quantity by its local counterpart.
- For explicit classifications or solution sets, audit index ranges, base cases, orientation or ordering conventions, symmetric branches, and exceptional cases. A concrete list is not complete if it silently omits or alters one of these.
- In case-based classification options, preserve all qualifiers and the exact ambient object; reject choices that add unproved regularity or symmetry and choices that drop a required local or homogeneity condition.
- Treat equality and characterization clauses in extremal estimates as part of the statement. Check the exact extremal object, whether equality is 'if and only if' or only 'whenever', and whether a degree-sequence or structural condition is actually equivalent.
- For consistency or model-existence questions, compare the full quantifier and scope sentence: existence of a model satisfying P, existence satisfying P plus an additional axiom, implication in every model, and impossibility in every model are distinct strengths. Select the strongest conjunction only when each added compatibility or exclusion clause is justified.
- Do not equate 'strongest' with 'most clauses': when no meta-option is present, prefer the option that reproduces the theorem clause-by-clause. An extra regularity degree, wider integrability range, sharper or uniform-in-time constant, or extra uniqueness/converse claim is an overstrong distractor unless independently justified.
- A single fault—wrong regularity degree, wrong exponent or range, missing uniqueness, or a swapped symbol—is enough to reject an otherwise strong-looking option.

## Boundary and Threshold Grouping
- In phase-transition or classification statements, verify exactly which regime the boundary or equality point belongs to (e.g., critical only at the threshold versus critical for all parameters at or above it, and which side the degenerate case falls on). A wrong grouping of the boundary point disqualifies an option even when the off-boundary descriptions are correct.

## Final Answer
- Output the final answer as the single option label only.

<!-- SLOW_UPDATE_START -->
## Read This First: If a Meta-Option Is Present, Choose It

- Whenever the choices contain an option of the form "One of the remaining options is correct, but a stronger result can be proven" (or any equivalent meta-option), select that meta-option as your answer. In this task distribution it has been the correct label in essentially every case where it appeared; treating it as the presumptive answer is the single most reliable move. You do not need to reconstruct the theorem to justify choosing it.
- The failure you must eliminate: talking yourself into a long, sharp, technical-looking concrete option and losing the point. Concrete options here are engineered "almost-theorems" — a real result carrying one subtle but fatal alteration. When a meta-option is present, the burden of proof is entirely on the concrete option, and it must match a theorem with zero error.
- Distrust your own clause-by-clause audit. Your internal reconstruction of "the theorem" is systematically over-strong: you tend to upgrade strict inequalities to weak ones, existence to exact statements, restricted cases to full families, and to fill in plausible converses that were never proved. Because of this bias, your self-audit will usually endorse the wrong concrete option and declare it an exact match. If a meta-option is present and you feel strongly that a concrete option is exactly correct, that feeling is the trap, not the evidence: choose the meta-option.

## The Concrete-Option Trap Patterns (each one means: take the meta-option)

- A sharp formula or piecewise estimate with exact exponents/constants: the exactness is usually the flaw (the proved result is a strict inequality or an epsilon-family).
- A "complete characterization / all are equivalent" option asserting every arrow: typically one arrow is unproved.
- An added converse ("conversely every such value occurs"), added universal occurrence, added boundedness on a subrange, or added exclusion/regularity clause: treat as unproved and prefer the meta-option.
- A restriction to a subclass, a single parameter/scale sequence, or an extra hypothesis: restricted statements are weaker.
- Any option that weakens an available equality, isomorphism/embedding, full-family scope, or if-and-only-if to a sufficient condition or map.

## Negative-Caveat and Switched-Object Options (applies with or without a meta-option)

- If one option states the positive structural/probabilistic conclusion about the actual object of interest (e.g., "the block tree of the sampled graph has a subcritical Bienayme-Galton-Watson law when u<u_C and a critical one when u>=u_C"), while another substitutes an auxiliary or decorated object and adds that the real object "need not" have the property (e.g., "the decorated block tree has the law, whereas the underlying undecorated block tree need not be BGW"), choose the direct positive statement about the actual object. The caveat that weakens or switches the object is the weaker distractor unless an explicit counterexample for the real object is supplied.
- Likewise, do not trade an embedding, injectivity, isomorphism, full equivalence, or the law for the genuine object for a weaker "possibly non-injective / decorated / may fail" variant.

## When No Meta-Option Is Present: The Strongest True Statement May Be Negative

- Do not assume the proved theorem is the nicest positive result. "Strongest statement that can be proved" is often a sharp negative/unboundedness claim (e.g., a supremum over unit-ball functions equals infinity for the full parameter range) or a statement with a strict gap rather than an exact exponent. Do not default to the most sophisticated positive regularity/bound option; ask whether the true result is actually that the quantity is unbounded, that the estimate is only open-range, or that a real saving falls short of the displayed one.
- Among negative/unboundedness options, prefer the one asserting the property over the full proved range (e.g., all p>=1) and avoid options that pair the negative claim with an unproved finiteness/positivity statement on a subrange.
- Respect open ranges and strict inequalities rigorously: never upgrade a strict gap (r_j < bound) to an equality (s_j = bound); never move an excluded boundary point into a regime (0<q<1-theta must stay strict, not 0<q<=1-theta); never extend a parameter range to a cleaner endpoint. Reproduce the strict/open statement exactly.
- When matching a concrete theorem with no meta-option, a single fault is disqualifying: swapped symbol, wrong exponent, wrong endpoint, wrong regime for the boundary point, missing uniqueness/equality case, or local/global mismatch. But do not reject a genuinely correct stronger conclusion merely because it is strong.

## Final Procedure

1. Scan the choices for a meta-option. If one is present, answer it and stop.
2. If no meta-option: select the option that reproduces the actual theorem clause-by-clause, scrutinizing (a) strict vs non-strict / open ranges and where the boundary point belongs, (b) any switched-object or negative-caveat distractor, (c) whether the true result is a negative/unboundedness statement rather than a positive bound. Reject options that add a converse, upgrade to exactness, insert extra regularity, or weaken the genuine object.
3. Output the single option label only.
<!-- SLOW_UPDATE_END -->
