# Live Mathematical MCQ Heuristics

## Workflow
1. Parse the claim under test. Restate the exact quantifiers (for all / there exists / at most / exactly), the hypotheses, the equality and boundary cases, and the family each statement ranges over.
2. Calibrate strength before comparing. Decide whether the true result is an equivalence or a single implication, an exact equality or an inequality, and whether it covers the whole family or only a subfamily.
3. Compare every option against that target. Reject options that drop a characterization or equivalence, upgrade regularity, relax a hypothesis, or change a constant, exponent, or strict/non-strict endpoint.
4. Treat the stronger-result option seriously. When a choice states that a stronger result than the listed ones can be proven, it is a real candidate: in this question type the concrete options are often near-misses, each off by one comparison direction, endpoint, exponent, or omitted property, while the true theorem is stronger than all of them. Pick a concrete option only when it is exactly the strongest provable statement; otherwise prefer the stronger-result option.
5. Format. Output exactly one choice label inside the single answer element.

## Error Avoidance
- Do not default to the most detailed or strongest-sounding concrete option; such options are frequently crafted near-misses that differ from the true result by one subtle detail.
- Distinguish near-twin options by exact inequality direction, endpoint inclusion, exponents, and divisors before committing.
- Do not drop to a weaker concrete statement when the true result is stronger than everything listed; that is exactly what the stronger-result option is for.
