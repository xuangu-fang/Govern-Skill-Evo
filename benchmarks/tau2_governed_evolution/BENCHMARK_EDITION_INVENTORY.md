# Benchmark Edition Inventory

This inventory is the canonical ownership map after the benchmark cleanup.

## Governed lineage

### `governed_v1_day27`

- `benchmark/final_v1/`: 116 executable Train/Monitor/Test tasks.
- `construction/distribution/`: population design, family assignment, split and audit material.
- `calibration/`: calibration runners, summaries and retained reports.

Legacy roots replaced: `final_v1/`, `distribution/`, `calibration/`.

### `governed_v2_day28`

- `benchmark/v2/`: 28-task structural pilot and representation.
- `construction/complex_workflow/`: complex-workflow exploration used by this edition.
- `calibration/v2_oracle_repair/`: oracle repair material specific to this edition.

Legacy roots replaced: `v2/`, `complex_workflow/`, `calibration/v2_oracle_repair/`.

### `governed_v3_day29`

- `benchmark/v3/`: 20 manually augmented Airline tasks and their calibration material.

Legacy root replaced: `v3/`.

## Phase lineage

### `phase_v1_day30`

- `benchmark/phase_a_final_unified_benchmark_v1/`: earlier 34-task Phase-A checkpoint.
- `benchmark/formal_manifestation_admission/`: 54-task edition used as Phase v1.
- `construction/`: Phase-A construction, state expansion, manifestation expansion,
  calibration analyses and admission history leading to the 54-task edition.

Legacy roots replaced: all `phase_a_*` roots, the state/manifestation admission
roots, and the Day30 pre-Phase-12 construction roots.

### `phase_v2_day30`

- `benchmark/tasks.json`: 72-task default runnable set.
- `benchmark/task_manifest.json`: exact membership and source paths.
- `construction/advanced_structure/`: Phase 12–17 construction and calibration evidence.
- `construction/information_boundary/`: learner information-boundary work used by v2.
- `experiments/`: the v15 end-to-end pilot.
- `reports/`: retained coverage, evidence and issue reports from the former
  `benchmark_v2_snapshot_001` directory.

The 72 tasks are the 54 Phase-v1 tasks, nine existing advanced controls, seven
non-duplicate latent-G tasks, and two Phase-17 cross-axis tasks. Exact duplicate
tasks `travel_request_027`, `031`, `033`, and `035` remain in construction
history but are excluded from the runnable set.

Legacy roots replaced: `advanced_structure/`, `information_boundary/`,
`experiments/benchmark_v2_v15_pilot_001/`, and
`snapshots/benchmark_v2_snapshot_001/`.

### `phase_v3_day34`

- `benchmark/tasks.json`: 32 formally admitted tasks across the eight-task
  EE-01, RHP-01, RAP-01, and JSG-01 Core families.
- `benchmark/splits.json`: formal 16-task Train and 16-task Monitor membership;
  no Test split.
- `benchmark/task_manifest.json`: exact membership, source family, admission
  evidence, design contract, and status report.
- `construction/primitive_a/`: rejected structural candidate inventory, empty
  candidate task set, audit, and offline consistency validator.
- `construction/primitive_b/pb_c02/`: eight rejected-too-easy candidate tasks,
  their evaluator, construction specs, Stage 0.5 audit, and validation tools.
- `construction/primitive_c/`: structurally rejected Verification / Recovery
  candidate inventory and audit; no executable task was admitted or run.
- `calibration/primitive_a/`: calibration-only Relevant/Irrelevant Skills,
  matched rollout configuration, and the not-run aggregate summary.
- `calibration/primitive_b/pb_c02/`: calibration-only Skills, matched rollout
  configuration, and the Smoke/formal aggregate results.
- `experiments/primitive_a_pilot/`: fail-closed Pilot entry point.
- `experiments/primitive_b_pb_c02_pilot/`: PB-C02 Smoke, calibration, and
  offline-analysis entry point; full runtime trajectories remain ignored.
- `reports/primitive_a/`: Primitive A structural Pilot report.
- `reports/primitive_b/`: completed PB-C02 report with `FAIL_TOO_EASY` verdict.
- `construction/hidden_resource_semantics/`: eight rejected-too-easy candidate
  tasks and evaluator plus native-backend, information-boundary,
  identifiability, and deterministic good/bad allocation validation.
- `calibration/hidden_resource_semantics/`: the v3-only Agent-visible policy
  omission, calibration Skills/configuration, and aggregate results.
- `experiments/hidden_resource_semantics_pilot/`: matched Pilot entry point;
  complete runtime trajectories remain ignored.
- `reports/hidden_resource_semantics/`: independent Pilot report with the
  `FAIL_TOO_EASY` verdict.
- `reports/V3_STATUS.md`: canonical current state and Pilot verdict summary.
- `V3_CAPABILITY_DESIGN_CONTRACT.md`: mandatory structure, shortcut,
  information-boundary, experiment, and admission rules for future families.
- `construction/environment_extension_audit/`: completed Airline/Retail
  extension-point audit that selected EE-01 for Gate 0.
- `construction/retail_hidden_operational_path_audit/`: Stable-Intent Retail
  follow-up audit with in-memory native transition probes, six candidate
  mechanisms, and a bounded recommendation to prototype RHP-01 at Gate 0.
- `construction/retail_hidden_operational_path/`: isolated RHP-01 environment,
  two counter-directional Gate tasks, evaluator, passed Gate 0 record, and an
  admitted eight-task `core_family/` with deterministic validation.
- `calibration/retail_hidden_operational_path/`: RHP-01 Reference Skill,
  matched Gate 1 configuration, and E0 2/4 versus ER 4/4 aggregate result.
- `experiments/retail_hidden_operational_path_gate1/`: reproducible RHP-01
  eight-rollout Gate 1 entry point; full trajectories remain ignored.
- `reports/retail_hidden_operational_path/`: RHP-01 Gate 1 and Core admission
  reports.
- `construction/retail_dual_update_sequence/`: rejected RDS-01 hidden-sequence
  Pilot with a valid backend state machine but a request-order answer proxy.
- `calibration/retail_dual_update_sequence/`: RDS-01 Reference Skill,
  configuration, and E0 4/4 versus ER 4/4 aggregate result.
- `experiments/retail_dual_update_sequence_gate1/`: reproducible eight-rollout
  Gate 1 entry point; raw trajectories remain ignored.
- `reports/retail_dual_update_sequence/`: RDS-01 Gate findings and shortcut
  analysis.
- `construction/retail_address_propagation/`: RAP-01 isolated Retail
  environment, two counter-directional address-propagation tasks, evaluator,
  passed Gate 0 surface/backend validation, and an admitted eight-task
  `core_family/` with deterministic validation.
- `calibration/retail_address_propagation/`: RAP-01 Reference Skill, matched
  Gate 1 configuration, and E0 2/4 versus ER 4/4 aggregate result.
- `experiments/retail_address_propagation_gate1/`: reproducible RAP-01
  eight-rollout Gate 1 entry point; full trajectories remain ignored.
- `reports/retail_address_propagation/`: RAP-01 Gate 0/Gate 1 findings and Core
  admission report.
- `construction/capability_governance_compatibility_audit/`: cross-axis audit
  of the three admitted Capability families against retained Phase-v2
  Governance mechanisms; selects only JSG-01 for Gate 0.
- `construction/joint_settlement_destination_scope/`: isolated JSG-01 EE-01 ×
  LGA04 environment, two candidate tasks, joint evaluator, and passed Gate 0
  CS/CF/VS/VF replay evidence. Its admitted `core_family/` contains eight new
  tasks balanced across Horizon/Summit × preferred/fallback.
- `calibration/joint_settlement_destination_scope/`: task-general joint
  Reference Skill, matched Gate 1 config, and E0 2/4 versus ER 3/4 Joint
  Success summary.
- `experiments/joint_settlement_destination_scope_gate1/`: reproducible
  eight-rollout Joint Gate 1 runner; raw trajectories remain ignored.
- `reports/JSG01_GATE0_REPORT.md` and `reports/JSG01_GATE1_REPORT.md`: bounded
  structural and model-calibration verdicts.
- `reports/JSG01_JOINT_CORE_ADMISSION_REPORT.md`: 32-path deterministic
  validation, shortcut controls, and formal admission record.
- `construction/unified_environment/`: common Airline environment for EE-01
  and JSG-01 plus common Retail environment carrying both RHP-01 and RAP-01
  hidden mechanisms for every Retail task.
- `construction/integration_audit/`: global task/split isolation, uniform
  information-boundary, surface-balance, task-loader, and 32-path runtime
  validation.
- `reports/V3_INTEGRATION_AUDIT.md`: human-readable global integration verdict.
- `construction/latent_settlement_contract/`: isolated EE-01 environment,
  original two-task Gate 0/Gate 1 evidence, and an eight-task `core_family/`
  spanning all Horizon/Summit × preferred/fallback combinations. All correct
  and opposite committed paths are deterministically validated; the Core family
  is admitted.
- `calibration/latent_settlement_contract/`: EE-01 Reference Skill, matched
  Gate 1 configuration, valid aggregate result, and invalidated first-run record.
- `experiments/latent_settlement_contract_gate1/`: reproducible eight-rollout
  Gate 1 entry point; full trajectories remain ignored.
- `reports/latent_settlement_contract/`: EE-01 Gate 1 findings and limits.

This edition is independent and does not copy `phase_v2_day30`. Its formal set
contains eight tasks each from EE-01, RHP-01, RAP-01, and the JSG-01 Joint Core.
Primitive
A failed structurally; PB-C02 and Hidden Resource Semantics failed Skill sensitivity. Their 16
executable tasks remain reproducible construction artifacts but are not formal
v3 benchmark members.

### `phase_final_candidate_day35`

- `benchmark/tasks.json`: 64-task formal Core candidate, with eight tasks from
  each of EE-01, RHP-01, RAP-01, P4-01, GPC-01, GMB-01, GIR-01, and JSG-01.
- `benchmark/splits.json`: entity-disjoint 32-task Evolution and 41-task
  Monitor; Monitor contains 32 Core-generalization tasks and nine regression
  guards; no Test split.
- `benchmark/lineage.json`: exact v3 or pre-ID construction origin for every
  formal task.
- `benchmark/new_family_specs.json`: evaluator-side semantic specifications for
  P4 and the three new Governance families.
- `environment/`: exact unified Airline and Retail environments. Deferred and
  rejected construction fixtures are excluded from the formal Airline DB.
- `construction/integration_audit/`: schema, count, split, shortcut,
  information-boundary, loader, 64-path Core oracle validation, 9/9 Control
  legal paths, 10/10 targeted regression detections, and 9/9 E0 sanity.
- `benchmark/control_tasks.json`: nine freshly realized regression guards,
  included in Monitor but kept outside the 64-task Core improvement rates.
- `benchmark/protected_controls.json`: lineage-to-formal-Control mapping and
  passed audit evidence for all nine Controls.

The Joint portfolio is closed with JSG-01 only. P4 × Cardinality and P4 ×
Baggage remain rejected construction hypotheses and receive no formal IDs.

## Shared infrastructure

The following former top-level packages now live under `shared/`: `boundary`,
`compiler`, `compliance`, `composition`, `concepts`, `evaluation`, `realization`,
`registry`, and `surface`. They define reusable machinery rather than a sixth
benchmark edition.
