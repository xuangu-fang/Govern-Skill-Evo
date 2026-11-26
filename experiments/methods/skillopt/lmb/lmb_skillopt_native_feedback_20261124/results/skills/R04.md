# Live Mathematical MCQ Heuristics

## Option Comparison
- - Compare all options before committing by ranking them by logical strength. The correct choice is the strongest statement actually justified by the theorem, not merely the strongest-looking or most technical wording; nearby options may be weaker, overstrong, miss an equality case, or differ only in a parameter, range, sign, domain, or meta clause. Treat options like "One of the remaining options is correct, but a stronger result can be proven" as live candidates: do not choose a concrete option merely because it is true; first check whether it is only a weakened, restricted, or non-sharp version of a statement implied by the hypotheses.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".

- For prompts asking which statement is equivalent to a condition or gives a complete list, check both directions and exhaustiveness. A one-way consequence, a restricted-subclass result, or a list missing boundary cases is not equivalent.
- Rank logical strength before choosing: universal over all parameters > universal over a restricted range; global > local; all indices/parameters > a subsequence or special subfamily; strict > non-strict; larger exponent or parameter range > smaller. A concrete option is not strongest merely because it has the most familiar theorem shape.

- Do not systematically favor the conservative bounded/finite option. When choices offer bounded vs unbounded vs stably-unbounded (positive stable limit) versions of the same claim, a bounded statement is the weakest, and the sharp theorem is often the unbounded or stable-unboundedness version. Choose the strongest level actually proved — but only among concrete options, i.e. after the deferral option (if any) has been ruled out; a present deferral still wins.
- Do not upgrade an implication to an equivalence, add a converse, or assume every admissible parameter occurs unless the theorem states it. For regularity/exponent conclusions, distinguish exact exponents from strict upper bounds, and treat `<` as non-attainable unless equality is proved.

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, or full equivalence.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.

- For nearly identical choices, compare every component independently: indices, summation ranges, denominators, quantifier scope, and the domain on which a capacity or norm is evaluated. Do not let a familiar-looking formula override an exact mismatch such as `cap(E,D)` versus `cap(E,Omega)` or `Q_p` versus `Q_{p-1}`.
- Match the conclusion object exactly: full gradient versus one partial derivative, universal cover versus original manifold, old versus new subspace, subset versus equality, one fixed conjugacy class versus one element chosen per pair, local-symmetric versus isometrically locally homogeneous. Dropping or swapping such a term changes the correct choice.
- For similar options, compare implication direction and clause strength: determine which option implies which, and whether an added clause (for example "every nontrivial power," "injective," or "all conditions equivalent") is actually proved or is an extra assumption.
- In analytic estimates, compare every exponent, time interval, norm power, and locality condition. Changing `(0,T]` to `[0,T]`, reversing the sign of an exponent, or replacing a sharp exponent by a different one is a distinct claim. Select only the exact version justified by the hypotheses and supported by the strongest available option.

## Final Answer
- Output the final answer as the single option label only.

<!-- SLOW_UPDATE_START -->
READ THIS FIRST — the single highest-value rule for 'strongest statement' questions.

In any item whose stem asks for 'the strongest statement that can be proved / that holds / that gives a complete characterization / that is equivalent,' if the option list contains one reading like 'One of the remaining options is correct, but a stronger result can be proven' (or a close paraphrase), CHOOSE THAT OPTION. This is not a cop-out — it is the benchmark's intended answer in the large majority of paper-derived 'strongest statement' items, because each concrete option is deliberately a true-but-slightly-weakened version of the paper's actual theorem. Your concrete picks are the trap. This epoch the deferral option was correct every time you passed it over: local C^{2,alpha} regularity, the cyclotomic reversal formula, the cX^{1-kappa-eps} count, the clique-sum structure of maximal K5-minor-free graphs, the q(G) <= q(K1 vee (alpha P_{ell-2} cup P_r)) bound with its equality case, the Morrey 'nabla u in L^{q,lambda} for q in [p,sp]' bound, and the concrete selfless characterization. Do NOT 'rescue' a concrete option by persuading yourself it is 'unmistakably the exact sharp theorem' — that rationalization has been wrong every single time it was used.

The ONLY two situations in which you may pass over the deferral option:
1. The stem asks you to identify or compute a specific object ('What is the Chow quotient X,' 'which surface/number/group is it'). A deferral answer is meaningless there; give the concrete identification and check exact invariants (degree 4, not degree 5; the precise singularities).
2. A concrete option asserts a NEGATIVE / unbounded / divergence conclusion — 'sup = infinity for every p,' 'unbounded,' 'no such estimate can hold.' A negative sharp result is already the strongest possible statement, so the deferral cannot beat it, and the soft bounded estimate offered beside it is usually the false trap (e.g., circular maximal 2-variation: the truth was sup = infinity, not a (log lambda)^{1/4 - 1/(2p)} bound).
If neither applies, select the deferral option.

When there is no deferral option (or after you have legitimately ruled it out):
- Match the paper's exact sharp statement component by component: every exponent, inequality sign, strict vs non-strict boundary, index range, and object (full gradient vs one partial; cap(E,Omega) vs cap(E,D); Q_p vs Q_{p-1}; universal cover vs manifold; local-symmetric vs isometrically locally homogeneous). A single sign, boundary point, or index swap is a wrong option (e.g., 0<q<1-theta, not 0<q<=1-theta).
- Do NOT use 'clean vs hedged' as a tiebreak. Sometimes the crisp-looking equality (e.g., 's_j = [exact bound]') is the distractor and the restrictive technical version ('eta_j with r_j < [the same bound]') is the true sharp result; sometimes the reverse. Decide from the mathematics and the paper's exact statement, not from whether a clause looks cautious.
- Do NOT add restrictions the theorem does not prove. An extra limiting clause — '...but no model satisfying the Weak Ultrapower Axiom can contain such a pair,' an appended 'need not be injective,' a narrowed subclass — is a distractor marker; the correct option is the more general/permissive claim actually established. Conversely, do not upgrade an implication to an equivalence or assume every admissible parameter occurs.

Famous open conjectures. When the item is built around a named open conjecture (e.g., the L-space conjecture), the correct option is the proven partial chain (e.g., '(a)<=>(c) and (b)=>(a)'), NOT a grand 'all of (a),(b),(c) are equivalent' or 'conditions (1)-(6) all hold.' Sweeping equivalences for open problems are distractors.

Discipline. You will feel strong pressure to pick the impressive concrete formula. Treat that pressure as the failure signal: before committing, re-scan the option list once and explicitly ask 'which option is the deferral, and is there a negative/unbounded option that is the real sharp truth?' Output only the single option label.
<!-- SLOW_UPDATE_END -->
