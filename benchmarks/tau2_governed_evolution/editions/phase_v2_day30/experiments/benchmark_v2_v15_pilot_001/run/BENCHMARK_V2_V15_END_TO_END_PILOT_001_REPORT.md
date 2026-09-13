# BENCHMARK_V2_V15_END_TO_END_PILOT_001 Report

`RUN_TYPE = END_TO_END_PILOT`

The fixed selection set was `FIXED_MONITOR_V2_PILOT_001` (41 tasks × 3 matched rollouts). Same-Evolution-Set replay, extra test sets, task mining, benchmark tuning, and parameter retuning were not used.

## Step 1

Evolution Parent: Success=0.8000, Compliance=0.4667, CS/CF/VS/VF=11/3/13/3.

Diagnosis: tasks=10, evidence_status={'recurrent_support': 5, 'contrastive_support': 5}, skill_issue=10, update-worthy=10, positive=2.

Candidate: generated=yes; editor status=CANDIDATE_CREATED.

Fixed Monitor Parent: S=0.8943, C=0.6016, CS/CF/VS/VF=71/3/39/10, CuP=0.5772.

Fixed Monitor Candidate: S=0.8618, C=0.7154, CS/CF/VS/VF=75/13/31/4, CuP=0.6098.

Delta: Success=-0.0325, Compliance=+0.1138, CS=+4; repairs=20, regressions=16, unchanged good=55, unchanged bad=24.

Transition matrix: CS->CS=55, CS->CF=4, CS->VS=12, CS->VF=0, CF->CS=0, CF->CF=3, CF->VS=0, CF->VF=0, VS->CS=17, VS->CF=3, VS->VS=18, VS->VF=1, VF->CS=3, VF->CF=3, VF->VS=1, VF->VF=3.

Tasks with at least one repair: 53, 75, airline_pa_b2_1n99u6_lexicographic_return, airline_pa_v2_5hk4lr_preserved_segment_valuation, retail_pa_o1b_w8327915_items_payment, retail_pa_r4b_w9132840_one_shot_helmets, retail_request_003, travel_request_004, travel_request_008, travel_request_020, travel_request_021, travel_request_025, travel_request_029.

Tasks with at least one CS regression: 53, 75, airline_pa_a2a_6zqnos_fixed_8accrd_buffer, airline_pa_b2_1n99u6_lexicographic_return, airline_s3_mohamed_ahmed_3350_certificate_lifecycle, retail_request_001, travel_request_004, travel_request_007, travel_request_011, travel_request_019, travel_request_020, travel_request_021, travel_request_024, travel_request_037.

Same-mechanism summary: Capability={'matched_rollouts': 21, 'delta_success': 2, 'delta_compliance': 1, 'repairs': 4, 'regressions': 3}; Governance={'matched_rollouts': 51, 'delta_success': -4, 'delta_compliance': 7, 'repairs': 9, 'regressions': 6}; Both={'matched_rollouts': 36, 'delta_success': -2, 'delta_compliance': 5, 'repairs': 4, 'regressions': 5}; Control={'matched_rollouts': 15, 'delta_success': 0, 'delta_compliance': 1, 'repairs': 3, 'regressions': 2}. Protected-boundary CS regressions=7/63.

Gate: P=0.2721, threshold=0.80, decision=RETAIN.

## Step 2

Evolution Parent: Success=0.9333, Compliance=0.3667, CS/CF/VS/VF=11/0/17/2.

Diagnosis: tasks=10, evidence_status={'contrastive_support': 3, 'conflicting': 1, 'recurrent_support': 6}, skill_issue=9, update-worthy=9, positive=2.

Candidate: generated=yes; editor status=CANDIDATE_CREATED.

Fixed Monitor Parent: S=0.8943, C=0.6016, CS/CF/VS/VF=71/3/39/10, CuP=0.5772.

Fixed Monitor Candidate: S=0.8699, C=0.6667, CS/CF/VS/VF=74/8/33/8, CuP=0.6016.

Delta: Success=-0.0244, Compliance=+0.0650, CS=+3; repairs=14, regressions=11, unchanged good=60, unchanged bad=33.

Transition matrix: CS->CS=60, CS->CF=3, CS->VS=5, CS->VF=3, CF->CS=0, CF->CF=2, CF->VS=0, CF->VF=1, VS->CS=10, VS->CF=0, VS->VS=28, VS->VF=1, VF->CS=4, VF->CF=3, VF->VS=0, VF->VF=3.

Tasks with at least one repair: 75, airline_pa_b2_1n99u6_lexicographic_return, airline_pa_v2_5hk4lr_preserved_segment_valuation, retail_pa_o1b_w8327915_items_payment, retail_pa_r4b_w9132840_one_shot_helmets, retail_request_003, travel_request_004, travel_request_020, travel_request_021, travel_request_029.

Tasks with at least one CS regression: airline_dd_hxdubj_multistage_propagation, airline_pa_e2_fatima_distinct_operations, airline_s3_mohamed_ahmed_3350_certificate_lifecycle, retail_request_001, travel_request_004, travel_request_007, travel_request_021, travel_request_024, travel_request_037.

Same-mechanism summary: Capability={'matched_rollouts': 21, 'delta_success': 0, 'delta_compliance': 1, 'repairs': 4, 'regressions': 3}; Governance={'matched_rollouts': 51, 'delta_success': -1, 'delta_compliance': 1, 'repairs': 3, 'regressions': 2}; Both={'matched_rollouts': 36, 'delta_success': -2, 'delta_compliance': 4, 'repairs': 5, 'regressions': 6}; Control={'matched_rollouts': 15, 'delta_success': 0, 'delta_compliance': 2, 'repairs': 2, 'regressions': 0}. Protected-boundary CS regressions=2/63.

Gate: P=0.3398, threshold=0.80, decision=RETAIN.

## Step 3

Evolution Parent: Success=0.7667, Compliance=0.6000, CS/CF/VS/VF=14/4/9/3.

Diagnosis: tasks=10, evidence_status={'recurrent_support': 5, 'contrastive_support': 5}, skill_issue=10, update-worthy=10, positive=1.

Candidate: generated=yes; editor status=CANDIDATE_CREATED.

Fixed Monitor Parent: S=0.8943, C=0.6016, CS/CF/VS/VF=71/3/39/10, CuP=0.5772.

Fixed Monitor Candidate: S=0.8943, C=0.6098, CS/CF/VS/VF=71/4/39/9, CuP=0.5772.

Delta: Success=+0.0000, Compliance=+0.0081, CS=+0; repairs=15, regressions=15, unchanged good=56, unchanged bad=34.

Transition matrix: CS->CS=56, CS->CF=1, CS->VS=11, CS->VF=3, CF->CS=0, CF->CF=2, CF->VS=1, CF->VF=0, VS->CS=11, VS->CF=0, VS->VS=27, VS->VF=1, VF->CS=4, VF->CF=1, VF->VS=0, VF->VF=5.

Tasks with at least one repair: 75, airline_pa_b2_1n99u6_lexicographic_return, airline_pa_v2_5hk4lr_preserved_segment_valuation, retail_pa_r4b_w9132840_one_shot_helmets, retail_request_001, retail_request_003, travel_request_007, travel_request_020, travel_request_021, travel_request_023, travel_request_025, travel_request_029, travel_request_030.

Tasks with at least one CS regression: 53, airline_pa_a1a_dkgiih_business_seat_bottleneck, retail_pa_r4a_w5918442_one_shot_cameras, retail_request_001, retail_request_003, travel_request_004, travel_request_007, travel_request_017, travel_request_019, travel_request_020, travel_request_024, travel_request_025, travel_request_037.

Same-mechanism summary: Capability={'matched_rollouts': 21, 'delta_success': -1, 'delta_compliance': 0, 'repairs': 3, 'regressions': 3}; Governance={'matched_rollouts': 51, 'delta_success': 0, 'delta_compliance': -1, 'repairs': 5, 'regressions': 6}; Both={'matched_rollouts': 36, 'delta_success': 1, 'delta_compliance': 3, 'repairs': 6, 'regressions': 4}; Control={'matched_rollouts': 15, 'delta_success': 0, 'delta_compliance': -1, 'repairs': 1, 'regressions': 2}. Protected-boundary CS regressions=8/63.

Gate: P=0.4720, threshold=0.80, decision=RETAIN.

## Final

```text
Initial Skill
      ↓
Step1 Candidate
RETAIN
      ↓
Step2 Candidate
RETAIN
      ↓
Step3 Candidate
RETAIN
      ↓
Final Skill = /Users/didi/Desktop/Govern-Skill-Evo/experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md
```

Accepted updates = 0 / 3.

Initial Monitor: Success=0.8943, Compliance=0.6016, CS/CF/VS/VF=71/3/39/10, CuP=0.5772.

Final Monitor: Success=0.8943, Compliance=0.6016, CS/CF/VS/VF=71/3/39/10, CuP=0.5772.

Net delta: Success=+0.0000, Compliance=+0.0000; net repairs=0, net regressions=0.

## Mechanism findings

Update-eligible diagnoses across all steps: Capability=11, Governance=13, Both=3, Control=2.

Latent Governance experience did trigger Skill edits, but none of the three Candidates passed the fixed-monitor Gate. Step-level same-mechanism results above show that compliance gains were accompanied by capability losses or CS regressions.

`travel_request_036` produced a meaningful diagnosis and edit: evidence=recurrent_support, update=True, mechanism=When planning to use a travel certificate for payment, the agent did not inform the user that any remaining balance would be forfeited and did not obtain explicit confirmation for the loss. Additionally, in R001 the agent attempted to use the same certificate (certificate_8846424) across two separate bookings, causing a 'certificate not found' error on the second booking because the certificate was removed after the first use. Target hypothesis=Before executing a booking that uses a travel certificate, the agent should state the exact amount to be charged and the remaining balance that will be lost ('Using certificate … for $X will leave $Y as a non‑refundable balance.'), then wait for user confirmation. When multiple bookings require the same certificate, the agent must allocate the entire certificate to a single booking or ask the user to provide an alternative payment method.

Because all three Candidates were retained out, the final Skill equals S0 and the Initial→Final mechanism deltas are all zero. Candidate-level overreach was nevertheless visible: protected-boundary CS regressions were 7, 2, and 8 rollouts in Steps 1–3 respectively.

Runtime counts: {"agent_user_rollouts_started": 582, "judge_provider_calls": 600, "infra_recoveries": 18, "invalid_behavioral_trajectories": 0, "saved_trajectory_evaluator_recoveries": 7, "judge_evaluator_recoveries": 4, "learner_provider_calls": 49, "learner_stage_recoveries": 1, "discarded_learner_outputs_after_runtime_failure": 11, "interrupted_redundant_editor_calls": 1, "learner_contract_failures": 1, "empty_responses": 1, "length_failures": 0}

`BENCHMARK_V2_V15_END_TO_END_PILOT_001_STATUS = COMPLETED`

`V15_END_TO_END_BEHAVIOR = NO_CLEAR_IMPROVEMENT`
