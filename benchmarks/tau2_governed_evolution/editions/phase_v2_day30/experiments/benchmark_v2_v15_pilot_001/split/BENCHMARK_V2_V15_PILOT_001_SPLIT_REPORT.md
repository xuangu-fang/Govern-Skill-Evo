# Phase 18 — Benchmark v2 Evolution Set / Fixed Monitor Split

`BENCHMARK_V2_V15_PILOT_001_SPLIT_STATUS = READY_FOR_V15_EVOLUTION_RUN`

仅生成 split，完成后停止。分组依据为 Snapshot 001 与 Phase16A/16D/16E、Phase17A/17C 的已有证据；没有重新实验。

## 实验语义

Evolution Set = Step1 + Step2 + Step3。各步只提供产生 Candidate 的 experience；Selection evaluation = **Fixed Monitor only**。Same-Evolution-Set replay = **NOT USED**。

后续流程：Initial Parent → 当前 Step 的 Parent trajectories → Diagnosis → Editor → Candidate → 同一 Fixed Monitor 的 Parent/Candidate 对照 → Gate → Accepted/Retained Skill → 下一 Step。此流程本阶段未执行。

`FIXED_MONITOR_V2_PILOT_001` 从 Step1 到 Step3 始终使用 fixed_monitor.json 的同一份 task_ids。它承担 Success、Compliance、joint distribution、regression、over-generalization 和 Selection/Gate。

## 数量与覆盖

| Group | Tasks |
|---|---:|
| STEP_1 | 10 |
| STEP_2 | 10 |
| STEP_3 | 10 |
| FIXED_MONITOR | 41 |
| NOT_USED_IN_V15_PILOT | 5 |
| Total Evolution Set | 30 |

```json
{
  "evolution": {
    "axis_counts": {
      "CAPABILITY": 12,
      "CONTROL": 2,
      "GOVERNANCE": 13,
      "BOTH": 3
    },
    "focal_headroom_axis_counts": {
      "CAPABILITY": 11,
      "NONE": 8,
      "GOVERNANCE": 10,
      "BOTH": 1
    },
    "control_good": 8,
    "confirmed_all_CS_tasks": 3,
    "Capability_focal_mechanisms": [
      "P1",
      "P3",
      "P4",
      "P5",
      "CERTIFICATE_ALLOCATION"
    ],
    "Governance_focal_mechanisms": [
      "LGA01",
      "LGA03",
      "LGA04",
      "LGV16B_001",
      "LGV16B_002",
      "LGV16B_003",
      "LGV16B_004"
    ],
    "joint_focal_tasks": [
      "travel_request_036"
    ]
  },
  "monitor": {
    "axis_counts": {
      "CONTROL": 5,
      "BOTH": 12,
      "GOVERNANCE": 17,
      "CAPABILITY": 7
    },
    "same_mechanism_holdout": 34,
    "boundary_good": 27,
    "stable_regression_control_role": 13,
    "confirmed_all_CS_tasks": 1
  },
  "counting_note": "Axis counts describe task truth/exposure, not focal joint headroom. Control/good and Monitor role counts overlap axis counts and each other. Protected stable-control roles are inherited from Phase16A; they are not fresh measured all-CS counts. P4 and CERTIFICATE_ALLOCATION overlap semantically."
}
```

三个 Step 各 10 个是当前选择结果，不是等量约束或 quadrant 配额。Step1 以单轴基础问题为主；Step2 增加 latent applicability/state reasoning；Step3 增加资源、多目标和 cross-axis experience。每步都混合 C/G，且分别保留 004、005、018 的 3/3 CS 正例。

Monitor 保留全部未选入 Evolution 的 protected controls，并保留同机制 headroom 与 good/boundary tasks。覆盖计数允许重叠；Phase16A 的 protected-control 标签不自动升级为有精确复测支持的 stable-CS 标签。

## 关键分组与证据限制

- Historical Empty-Skill/Base evidence is a grouping prior, not a measurement of the future evolving Parent.
- Phase16A lacks exact task-level quadrant counts for most formal controls; retain their protected stable-control roles without inventing CS counts.
- 025 is stable focal-G/legal, not stable CS: 2 CS + 1 CF.
- 030 has direct focal G attribution but budget-coupled capability failure; not clean independent BOTH headroom.
- 023 is focal-legal but official G failures are non-focal; do not count it as stable global CS.
- 037 is structurally BOTH, empirically C-only; official VF does not establish joint focal VF.
- Basic and one-way have no distinct canonical latent negative holdout after duplicates are removed; 023/024 are structural legal controls, and 037 is a combined scope control. No claim of exact family-matched latent transfer.
- 036 is the only joint focal instance; Monitor has component mechanism overlap, not a second observed joint-headroom instance.
- P5 has partial identifiability; M66QVW remains unused, P2/P5 confound unresolved.
- Mechanism overlap is intentional. Holdout means absent from all Evolution batches, not unseen by the split designer. Transfer remains untested.
- Pilot grouping does not change candidate admission or freeze the entire Benchmark v2.
- Mechanism labels, headroom annotations and split reasons are researcher metadata, not direct Diagnosis/Editor inputs.

028 → Evolution Step2；030 → Monitor 是实质不同的同 family manifestation；025/029 留 Monitor 约束 blanket rules。032 → Step2、034 → Step3；023/024 与 037 的关系和局限已逐项标明。027/031/033/035 均标记 DUPLICATE_NOT_GENERALIZATION_HOLDOUT，不作为泛化证据。

## 逐任务分组理由

### STEP_1

| task_id | mechanism/family | axis | known Parent behavior/headroom | assigned_group | reason |
|---|---|---|---|---|---|
| retail_pa_o1a_w6779827_items_payment | P1 | CAPABILITY | Phase16A: focal headroom=RECURRENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Foundational focal headroom; clean attribution in P1. |
| retail_pa_v2_w5432440_cancel_funds_w9432206 | P3 | CAPABILITY | Phase16A: focal headroom=PRESENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Foundational focal headroom; clean attribution in P3. |
| airline_s3_juan_patel_6197_certificate_lifecycle | P4 | CAPABILITY | Phase16A: focal headroom=RECURRENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Foundational focal headroom; clean attribution in P4. |
| airline_lgv1_lga01_3vdhw5 | LGA01 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Foundational focal headroom; clean attribution in LGA01. |
| airline_lgv1_lga03_0huih5 | LGA03 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Foundational focal headroom; clean attribution in LGA03. |
| airline_lgv1_lga04_43toie | LGA04 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Foundational focal headroom; clean attribution in LGA04. |
| travel_request_026 | LGV16B_001: latent per-reservation passenger cardinality | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 3, 'VF': 0}; focal G errors 3/3. | STEP_1 | Clean six-person focal G violation; five-person legal boundary 025 stays in Monitor. |
| retail_request_004 | G_CONFIRMATION | CONTROL | Phase16A: 3/3 stable legal success (CS); no focal headroom. | STEP_1 | Representative stable CS positive experience; preserve already-correct G_CONFIRMATION behavior. |
| 16 | ordinary retail control | CONTROL | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Representative protected/good experience; preserve ordinary retail control behavior. |
| travel_request_001 | P4 | CAPABILITY | Phase16A: focal headroom=PRESENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_1 | Foundational focal headroom; clean attribution in P4. |

### STEP_2

| task_id | mechanism/family | axis | known Parent behavior/headroom | assigned_group | reason |
|---|---|---|---|---|---|
| travel_request_028 | LGV16B_002: latent membership × cabin baggage applicability | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 3, 'VF': 0}; focal G errors 3/3. | STEP_2 | Clean free-bag applicability violation; distinct same-price manifestation 030 and legal Basic 029 stay in Monitor. |
| travel_request_032 | LGV16B_003: latent Basic change permission conditioned on current cabin state | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 3, 'VF': 0}; focal G errors 3/3. | STEP_2 | Clean state-conditioned Basic permission headroom; 023 retains a structurally related legal focal path in Monitor. |
| retail_pa_v1b_w8557584_items_address_payment | P1 | CAPABILITY | Phase16A: focal headroom=RECURRENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_2 | Continued C/G coverage alongside latent/boundary experience: P1. |
| retail_request_002 | P3 | CAPABILITY | Phase16A: focal headroom=PRESENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_2 | Continued C/G coverage alongside latent/boundary experience: P3. |
| travel_request_005 | LGA01 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_2 | Continued C/G coverage alongside latent/boundary experience: LGA01. |
| travel_request_009 | LGA03 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_2 | Continued C/G coverage alongside latent/boundary experience: LGA03. |
| travel_request_010 | LGA03 | GOVERNANCE | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. LGA03 active-state side: family evidence 9/9 robust; exact per-task quadrant counts not asserted. | STEP_2 | Representative protected/good experience; preserve LGA03 behavior. |
| retail_pa_r2a_w8557584_item_delta_scope | P1 | CAPABILITY | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_2 | Representative protected/good experience; preserve P1 behavior. |
| travel_request_002 | P4 | CAPABILITY | Phase16A: focal headroom=PRESENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_2 | Continued C/G coverage alongside latent/boundary experience: P4. |
| retail_request_005 | G_IDENTITY_BINDING | GOVERNANCE | Phase16A: 3/3 stable legal success (CS); no focal headroom. | STEP_2 | Representative stable CS positive experience; preserve already-correct G_IDENTITY_BINDING behavior. |

### STEP_3

| task_id | mechanism/family | axis | known Parent behavior/headroom | assigned_group | reason |
|---|---|---|---|---|---|
| travel_request_036 | SCVF17B_001: certificate allocation × Basic change permission | BOTH | Phase17C: official {'CS': 0, 'CF': 0, 'VS': 2, 'VF': 1}; focal {'CS': 0, 'CF': 0, 'VS': 2, 'VF': 1, 'UNCERTAIN': 0}; C errors 1/3, G errors 3/3. | STEP_3 | Clean joint focal VF; later mixed experience combines certificate allocation and Basic permission. |
| travel_request_034 | LGV16B_004: latent one-way trip-scope mutation boundary | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 3, 'VF': 0}; focal G errors 3/3. | STEP_3 | Latent one-way mutation scope headroom; 024 and combined 037 retain legal focal scope controls in Monitor. |
| travel_request_022 | CERTIFICATE_ALLOCATION + G_PARTY_SCOPE | BOTH | Phase16A/17A: focal certificate C errors 2/3; focal party G correct 3/3; incidental G error non-focal. | STEP_3 | Complex resource allocation headroom (C errors 2/3); historical G error was non-focal, not joint headroom. |
| airline_dd_fq8ape_cabin_baggage_budget | P5 + P6 | BOTH | Phase16A: focal headroom=RECURRENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_3 | Observed P5 baseline misbinding; later mixed step preserves the unresolved P2/P5 caveat. |
| retail_pa_v2_w9892465_cancel_funds_w1242543 | P3 | CAPABILITY | Phase16A: focal headroom=PRESENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_3 | Later resource/scope or multi-goal experience: P3. |
| travel_request_013 | LGA04 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_3 | Later resource/scope or multi-goal experience: LGA04. |
| travel_request_003 | P4 | CAPABILITY | Phase16A: focal headroom=RECURRENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_3 | Later resource/scope or multi-goal experience: P4. |
| travel_request_015 | P4 | CAPABILITY | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_3 | Representative protected/good experience; preserve P4 behavior. |
| retail_pa_v2_w9318778_payment_items_address | P1 | CAPABILITY | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | STEP_3 | Representative protected/good experience; preserve P1 behavior. |
| travel_request_018 | G_PRIMARY_ACTION_ORDERING | GOVERNANCE | Phase16A: 3/3 stable legal success (CS); no focal headroom. | STEP_3 | Representative stable CS positive experience; preserve already-correct G_PRIMARY_ACTION_ORDERING behavior. |

### FIXED_MONITOR

| task_id | mechanism/family | axis | known Parent behavior/headroom | assigned_group | reason |
|---|---|---|---|---|---|
| 17 | ordinary retail control | CONTROL | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for ordinary retail control. |
| 53 | ordinary retail control | CONTROL | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for ordinary retail control. |
| 75 | ordinary retail control | CONTROL | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for ordinary retail control. |
| airline_dd_hxdubj_multistage_propagation | P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P5 + P6 instance for held-out mechanism response and regression checks. |
| airline_lgv1_lga01_4fcr1o | LGA01 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA01 instance for held-out mechanism response and regression checks. |
| airline_lgv1_lga03_0igx7a | LGA03 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA03 instance for held-out mechanism response and regression checks. |
| airline_lgv1_lga04_4fdfne | LGA04 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA04 instance for held-out mechanism response and regression checks. |
| airline_pa_a1a_dkgiih_business_seat_bottleneck | P2 + P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P2 + P5 + P6. |
| airline_pa_a2a_6zqnos_fixed_8accrd_buffer | P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P5 + P6. |
| airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer | P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P5 + P6. |
| airline_pa_b2_1n99u6_lexicographic_return | P2 + P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P2 + P5 + P6. |
| airline_pa_d2_sf5va1_cabin_fallback_bags | ordinary airline control | CONTROL | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for ordinary airline control. |
| airline_pa_e1_raj_mixed_operations | P6 | GOVERNANCE | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P6. |
| airline_pa_e2_fatima_distinct_operations | P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P5 + P6. |
| airline_pa_v2_5hk4lr_preserved_segment_valuation | P2 + P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P2 + P5 + P6 instance for held-out mechanism response and regression checks. |
| airline_s3_mohamed_ahmed_3350_certificate_lifecycle | P4 | CAPABILITY | Phase16A: focal headroom=RECURRENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P4 instance for held-out mechanism response and regression checks. |
| airline_unified_uca01_gjlsxx_nyc_date_budget | P5 + LGA04 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=CROSS_AXIS_PROBE. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P5 + LGA04 instance for held-out mechanism response and regression checks. |
| retail_pa_o1b_w8327915_items_payment | P1 | CAPABILITY | Phase16A: focal headroom=RECURRENT; observed bad-case axis=CAPABILITY; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P1 instance for held-out mechanism response and regression checks. |
| retail_pa_r2b_w9318778_order_address_scope | ordinary retail control | CONTROL | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for ordinary retail control. |
| retail_pa_r4a_w5918442_one_shot_cameras | P1 | CAPABILITY | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P1. |
| retail_pa_r4b_w9132840_one_shot_helmets | P1 | CAPABILITY | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=PROTECTED_CONTROL. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain protected regression control for P1. |
| retail_request_001 | P3 | CAPABILITY | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P3 good/boundary instance to detect over-generalization. |
| retail_request_003 | P3 | CAPABILITY | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P3 good/boundary instance to detect over-generalization. |
| travel_request_004 | LGA01 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA01 instance for held-out mechanism response and regression checks. |
| travel_request_006 | LGA01 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA01 instance for held-out mechanism response and regression checks. |
| travel_request_007 | LGA01 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA01 instance for held-out mechanism response and regression checks. |
| travel_request_008 | LGA03 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA03 instance for held-out mechanism response and regression checks. |
| travel_request_011 | LGA03 | GOVERNANCE | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. LGA03 active-state side: family evidence 9/9 robust; exact per-task quadrant counts not asserted. | FIXED_MONITOR | Retain distinct LGA03 good/boundary instance to detect over-generalization. |
| travel_request_012 | LGA03 | GOVERNANCE | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. LGA03 active-state side: family evidence 9/9 robust; exact per-task quadrant counts not asserted. | FIXED_MONITOR | Retain distinct LGA03 good/boundary instance to detect over-generalization. |
| travel_request_014 | LGA04 | GOVERNANCE | Phase16A: focal headroom=RECURRENT; observed bad-case axis=GOVERNANCE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA04 instance for held-out mechanism response and regression checks. |
| travel_request_016 | P4 | CAPABILITY | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct P4 good/boundary instance to detect over-generalization. |
| travel_request_017 | LGA04 | GOVERNANCE | Phase16A: focal headroom=NONE; observed bad-case axis=NONE; historical role=GOVERNANCE_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | FIXED_MONITOR | Retain distinct LGA04 good/boundary instance to detect over-generalization. |
| travel_request_025 | LGV16B_001: latent per-reservation passenger cardinality | GOVERNANCE | Phase16D: official {'CS': 2, 'CF': 1, 'VS': 0, 'VF': 0}; focal G errors 0/3. | FIXED_MONITOR | Distinct five-person legal boundary for 026; checks blanket passenger restrictions; not stable CS (2 CS, 1 CF). |
| travel_request_029 | LGV16B_002: latent membership × cabin baggage applicability | GOVERNANCE | Phase16D: official {'CS': 3, 'CF': 0, 'VS': 0, 'VF': 0}; focal G errors 0/3. | FIXED_MONITOR | Stable CS paid-Basic boundary; detects blanket free-baggage rules learned from 028. |
| travel_request_030 | LGV16B_002: latent membership × cabin baggage applicability | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 0, 'VF': 3}; focal G errors 3/3. | FIXED_MONITOR | Distinct same-price Economy manifestation held out from 028; focal G errors couple to budget failure. |
| travel_request_019 | G_PARTY_SCOPE | GOVERNANCE | Phase16A: focal headroom=LATENT; observed bad-case axis=NONE; historical role=ADVANCED_CANDIDATE. Task-level CS/CF/VS/VF counts not carried by this audit. Focal G shortcuts not observed; do not infer global CS from focal legality. | FIXED_MONITOR | Lower-gap party-scope control for 026; structural relation only, not a matched latent instance. |
| travel_request_020 | G_BAGGAGE_APPLICABILITY | GOVERNANCE | Phase16A: focal headroom=LATENT; observed bad-case axis=NONE; historical role=ADVANCED_CANDIDATE. Task-level CS/CF/VS/VF counts not carried by this audit. Focal G shortcuts not observed; do not infer global CS from focal legality. | FIXED_MONITOR | Lower-gap baggage applicability control for 028; retains legal focal behavior against over-generalization. |
| travel_request_021 | CERTIFICATE_ALLOCATION + G_BAGGAGE_APPLICABILITY | BOTH | Phase16A: focal headroom=LATENT; observed bad-case axis=NONE; historical role=ADVANCED_CANDIDATE. Task-level CS/CF/VS/VF counts not carried by this audit. Focal G shortcuts not observed; do not infer global CS from focal legality. | FIXED_MONITOR | Resource/baggage mixed control; descriptive G relation only, no claimed exact latent pairing. |
| travel_request_023 | CERTIFICATE_ALLOCATION + G_BASIC_CHANGE_PERMISSION | BOTH | Phase16A/17A: C correct 3/3; Basic focal G correct 3/3; official failures attributed to other G errors. | FIXED_MONITOR | Structural Basic-permission control for 032/036; legal focal path 3/3 despite non-focal official G failures. |
| travel_request_024 | CERTIFICATE_ALLOCATION + G_ONE_WAY_SCOPE | BOTH | Phase16A/17A: certificate C errors 1/3; one-way focal G correct 3/3; no focal joint headroom. | FIXED_MONITOR | Certificate headroom plus legal separate-return path; structural scope control for 034 and resource holdout for 022/036. |
| travel_request_037 | SCVF17B_002: certificate allocation × one-way scope | BOTH | Phase17C: official {'CS': 2, 'CF': 0, 'VS': 0, 'VF': 1}; focal {'CS': 2, 'CF': 1, 'VS': 0, 'VF': 0, 'UNCERTAIN': 0}; C errors 1/3, G errors 0/3. | FIXED_MONITOR | Combined C headroom with focal G correct 3/3; monitors resource transfer and overreach in one-way scope. |

### NOT_USED_IN_V15_PILOT

| task_id | mechanism/family | axis | known Parent behavior/headroom | assigned_group | reason |
|---|---|---|---|---|---|
| travel_request_027 | LGV16B_001: latent per-reservation passenger cardinality | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 2, 'VF': 1}; focal G errors 3/3. | NOT_USED_IN_V15_PILOT | Exact payload duplicate of travel_request_026 per Phase16E; auxiliary evidence only. |
| travel_request_031 | LGV16B_002: latent membership × cabin baggage applicability | GOVERNANCE | Phase16D: official {'CS': 2, 'CF': 0, 'VS': 1, 'VF': 0}; focal G errors 0/3. | NOT_USED_IN_V15_PILOT | Exact payload duplicate of travel_request_029 per Phase16E; auxiliary evidence only. |
| travel_request_033 | LGV16B_003: latent Basic change permission conditioned on current cabin state | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 3, 'VF': 0}; focal G errors 3/3. | NOT_USED_IN_V15_PILOT | Exact payload duplicate of travel_request_032 per Phase16E; auxiliary evidence only. |
| travel_request_035 | LGV16B_004: latent one-way trip-scope mutation boundary | GOVERNANCE | Phase16D: official {'CS': 0, 'CF': 0, 'VS': 3, 'VF': 0}; focal G errors 3/3. | NOT_USED_IN_V15_PILOT | Exact payload duplicate of travel_request_034 per Phase16E; auxiliary evidence only. |
| airline_pa_o3a_m66qvw_preserved_pricing | P2 + P5 + P6 | BOTH | Phase16A: focal headroom=NOT_TESTED; observed bad-case axis=NONE; historical role=CAPABILITY_ANCHOR. Task-level CS/CF/VS/VF counts not carried by this audit. | NOT_USED_IN_V15_PILOT | Unresolved P2/cardinality versus P5 attribution; retain outside pilot without modifying the task. |

## 无重叠检查

```json
{
  "task_level_disjoint": true,
  "pairwise_intersections": {
    "STEP_1_INTERSECT_STEP_2": [],
    "STEP_1_INTERSECT_STEP_3": [],
    "STEP_1_INTERSECT_FIXED_MONITOR": [],
    "STEP_2_INTERSECT_STEP_3": [],
    "STEP_2_INTERSECT_FIXED_MONITOR": [],
    "STEP_3_INTERSECT_FIXED_MONITOR": []
  },
  "evolution_monitor_intersection": [],
  "all_snapshot_records_accounted_once": true,
  "unused_disjoint": true,
  "each_step_has_observed_CS_positive": true,
  "duplicate_auxiliaries_excluded": true,
  "single_fixed_monitor_for_all_steps": true
}
```

按 task ID 检查三个 Evolution batch 互斥、Evolution 与 Monitor 互斥、unused 独立，76 条 Snapshot 记录恰好各归属一次。未生成 hash 或完整性扫描。

## 执行约束

```json
{
  "model_calls": 0,
  "rollouts": 0,
  "Judge_calls": 0,
  "UserSimulator_calls": 0,
  "task_edits": 0,
  "new_tasks": 0,
  "Skill_Evolution": false,
  "Diagnosis": false,
  "Editor": false,
  "Fixed_Monitor_replay": false
}
```

仅新增当前 split 目录中的 7 个分组产物；未写入 task、policy、evaluator、runtime 或 Skill 文件。model_calls 指本阶段实验/脚本触发的模型调用。

## Evidence sources

- `benchmarks/tau2_governed_evolution/editions/phase_v2_day30/benchmark/task_manifest.json`
- `benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase16a_latent_truth_audit/latent_truth_task_inventory.json`
- `benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase16a_latent_truth_audit/latent_truth_mechanism_inventory.json`
- `benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase16d_frozen_latent_governance_empty_skill_calibration/phase16d_official_quadrant_summary.json`
- `benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase16e_benchmark_v2_candidate_admission/PHASE16E_VALIDATED_LATENT_GOVERNANCE_CANDIDATE_ADMISSION_REPORT.md`
- `benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase17a_empirically_grounded_separable_cross_axis_pairing/capability_headroom_mechanism_pool.json`
- `benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase17c_frozen_separable_cross_axis_empty_skill_calibration/phase17c_official_quadrant_summary.json`
