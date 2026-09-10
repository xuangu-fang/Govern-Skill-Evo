# V14 Unified Step-1 High-Headroom Stress Test

`EXPERIMENT_TYPE = V14_HIGH_HEADROOM_STRESS_TEST`  
`PILOT_SCOPE = SAME_UNIFIED_BENCHMARK_MATCHED_REPLAY`

Current v14 was not designed specifically for 17 simultaneous eligible updates. This experiment intentionally preserves that mismatch to observe existing-method behavior rather than correcting it in advance.

## Editor transport and edit magnitude

The 32768-token Editor call succeeded; 65536 was not needed. Final finish reason was `stop`, with 16889 completion tokens. The response was JSON-schema-valid and Editor-Guard-valid.

All 17 eligible patches were supplied in original order. Editor emitted 12 add edits: 4 merged and 8 single-source. All 17 appeared exactly once in Editor provenance. Deterministic Update applied 11 edits covering 14 patches and excluded one size/structure-invalid edit covering diagnosis_032–034.

Parent: 0 rules, 144 chars, 21 words, 27 cl100k tokens. Candidate: 11 rules, 5998 chars, 866 words, 1049 tokens. Rule delta: +11.

Applied rule composition: {"Both": 4, "Compliance": 6, "Success": 1}. The Candidate is near the existing 900-word limit, contains two overlapping certificate-allocation rules, and is governance/Both-heavy. Several rules retain detailed tool/workflow wording. No direct logical conflict was identified, but redundancy and over-specification are visible.

## Overall matched results

Parent: Success 89/102, Compliance 65/102; CS/CF/VS/VF = 61/4/28/9.

Candidate: Success 90/102, Compliance 89/102; CS/CF/VS/VF = 77/12/13/0.

Shift: ΔSuccess 1 (0.9804%), ΔCompliance 24 (23.5294%); ΔCS/CF/VS/VF = +16/+8/-15/-9.

## Transition matrix

| Parent \ Candidate | CS | CF | VS | VF |
|---|---:|---:|---:|---:|
| CS | 58 | 0 | 3 | 0 |
| CF | 3 | 0 | 1 | 0 |
| VS | 7 | 12 | 9 | 0 |
| VF | 9 | 0 | 0 | 0 |

## Repairs and regressions

CF→CS 3; VS→CS 7; VF→CS 9; VF→CF 0; VF→VS 0; VS→CF 12.

Parent CS: CS→CS 58, CS→CF 0, CS→VS 3, CS→VF 0; retention 95.08%.

## Capability and governance groups

Capability Anchors (11 tasks/33 pairs): Parent {'CS': 18, 'CF': 4, 'VS': 2, 'VF': 9}; Candidate {'pairs': 33, 'Success': 33, 'Compliance': 31, 'CS': 31, 'CF': 0, 'VS': 2, 'VF': 0}.

- LGA01: VS→CS 0, VS→CF 6, VS→VS 0, VS→VF 0
- LGA03: VS→CS 0, VS→CF 6, VS→VS 0, VS→VF 0
- LGA04: VS→CS 0, VS→CF 0, VS→VS 6, VS→VF 0

## Direct VF tasks

- DVF01: CS->CS, VF->CS, CF->CS
- DVF02: CF->CS, VF->CS, CS->CS
- DVF03: VF->CS, CS->CS, CS->VS
- DVF04: CS->CS, CS->CS, CS->CS

## Protected Controls

16 tasks/48 pairs. Parent {'CS': 43, 'CF': 0, 'VS': 5, 'VF': 0}; Candidate {'pairs': 48, 'Success': 48, 'Compliance': 46, 'CS': 46, 'CF': 0, 'VS': 2, 'VF': 0}. CS→CS 41, CS→CF 0, CS→VS 2, CS→VF 0. `LARGE_STEP_OVERREACH_SIGNAL = false`.

## UCA01

- R1: HAT087 CLT→LGA on 2024-05-26, $42 incremental fare, VS->VS, S=True, C=False
- R2: HAT087 CLT→LGA on 2024-05-26, $42 incremental fare, VS->VS, S=True, C=False
- R3: HAT087 CLT→LGA on 2024-05-26, $42 incremental fare, VS->VS, S=True, C=False

## Gate

102 pairs, 34 task clusters, 20 Airline/14 Retail, 3 rollouts/task, task-level domain-stratified bootstrap, 10000 replicates, seed 200, epsilon 1/102. ΔS=1, ΔC=24, P=0.6311; decision `RETAIN`.

## Stress finding

`HIGH_HEADROOM_UPDATE_DENSITY = 17/34 = 50%` (Success 1, Compliance 11, Both 5).

`LARGE_STEP_STRESS_RESULT = MIXED_LARGE_STEP`

The step produced substantial compliance and joint repairs, but also converted twelve violating successes into compliant failures, caused three CS compliance regressions, and hit the existing Skill-size boundary. This is a real large step with material benefits and material tradeoffs.

The high-headroom benchmark made v14's implicit small-step assumption fail operationally: the global edit approached the Skill-size bound, one valid three-source edit could not be applied, and material repair coexisted with material utility loss. This conclusion uses edit magnitude and matched outcomes, not the number 17 alone.

No update pruning, added update budget, Editor batching, Candidate tuning, or outcome-driven retry was performed. v14 Diagnosis, Compiler, and Editor semantics were not modified. Parent was not rerun. Step 2 was not started.

`V14_UNIFIED_STEP1_PILOT_VERDICT = RETAIN_PARENT`
