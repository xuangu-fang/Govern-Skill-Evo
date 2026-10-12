# Phase Benchmark v3 — Day 34

Benchmark v3 is an independent capability-benchmark development edition. It
does not copy or modify Benchmark v2.

## Current status

The formal runnable set contains `32` tasks. Its Capability-only part consists
of eight Airline EE-01, eight Retail RHP-01, and eight Retail RAP-01 tasks.
JSG-01 passed its Joint Gate and contributes another eight formally admitted
Capability × Governance tasks.

The formal set now runs through two domain-wide environments rather than four
family-specific environments: `airline-v3-unified` for all 16 Airline tasks and
`retail-v3-unified` for all 16 Retail tasks. It is formally divided into 16
Train and 16 entity-disjoint Monitor tasks; there is no Test split. Every
Retail task carries both Retail hidden mechanisms under the same policy, DB,
and tool schema, so task family cannot select which environment fact is hidden.

| Work item | Candidate tasks | Verdict | Meaning |
|---|---:|---|---|
| EE-01 Channel-Conditioned Settlement Commit | 2 Gate seeds + 8 formal Core | `ADMITTED` | Gate 0 passed; Gate 1 E0 2/4 vs ER 4/4; all eight expanded Core tasks passed correct/opposite-path validation. |
| RHP-01 Fulfillment-Conditioned Exchange or Return | 2 Gate seeds + 8 formal Core | `ADMITTED` | Gate 0 passed; Gate 1 E0 2/4 vs ER 4/4; all eight expanded Core tasks passed correct/opposite-path validation. |
| RAP-01 Contract-Conditioned Address Propagation | 2 Gate seeds + 8 formal Core | `ADMITTED` | Gate 0 passed; Gate 1 E0 2/4 vs ER 4/4; all eight expanded Core tasks passed deterministic correct/opposite-path and shortcut validation. |
| JSG-01 Settlement × Destination Scope | 2 Gate seeds + 8 formal Joint Core | `ADMITTED_JOINT_CORE` | Joint Gate 1 E0 2/4 vs ER 3/4. Expanded Core passed all 8 × CS/CF/VS/VF paths and all tested shortcuts scored 4/8. |
| RDS-01 Revision-Conditioned Dual Update Sequence | 2 | `REJECTED_TOO_EASY_REQUEST_ORDER_PROXY` | Gate 0 backend paths passed, but Gate 1 E0 and ER both reached 4/4 because user request order exposed the required operation order. |
| Retail Hidden Operational Path audit | 0 | `COMPLETE_RECOMMEND_RHP_01_GATE_0` | Native terminal exchange/return paths are real, but public rules are visible. RHP-01 is the only candidate recommended for an isolated two-task Gate 0 extension. |
| Dynamic State Refresh / Propagation | 0 | `REJECTED_STRUCTURAL` | Native τ² has no qualifying stale-target dependency. |
| Primitive B structural candidate pool | 0 executable | `PASS_STRUCTURAL_ONLY` | Six mechanisms passed a native dependency audit, but none is admitted; PB-C02 is the only calibrated member. |
| PB-C02 Filter → Rank → Fallback | 8 | `REJECTED_TOO_EASY` | Empty, Relevant, and Irrelevant conditions all reached 24/24 Success. |
| Primitive C Verification / Recovery | 0 | `REJECTED_STRUCTURAL` | Native successful mutations do not expose a qualifying recovery branch. |
| Hidden Single-Use Resource Semantics | 8 | `REJECTED_TOO_EASY` | Core Empty, Relevant, and Irrelevant conditions all reached 12/12 Success. |

Rejected executable Pilot tasks remain available as construction and
calibration evidence. Primitive B's uncalibrated structural candidates remain
research leads, not admitted tasks. None is counted by `VERSION.json`.

## Directory roles

- `benchmark/`: 32 admitted tasks plus the 16 Train / 16 Monitor split.
- `construction/unified_environment/`: official unified Airline and Retail
  policies, fixtures, toolkits, and split-aware task loaders.
- `construction/integration_audit/`: executable global integration,
  information-boundary, split-isolation, balance, and runtime validation.
- `construction/`: candidate specifications, rejected Pilot task material,
  structural audits, evaluators, and offline validation tools.
- `calibration/`: Pilot-only Skills, configurations, and aggregate summaries.
- `experiments/`: reproducible Pilot entry points; raw runtime trajectories
  remain ignored.
- `reports/`: central status plus retained Pilot findings.
- `V3_CAPABILITY_DESIGN_CONTRACT.md`: mandatory admission contract for every
  future capability primitive.
- `construction/environment_extension_audit/`: Airline/Retail extension-point
  audit, native transition evidence, isolation proof, and candidate matrix.
- `construction/retail_hidden_operational_path_audit/`: Stable-Intent Retail
  path audit, reproducible in-memory native probes, six-candidate screen, and
  the bounded RHP-01 Gate 0 recommendation.
- `construction/retail_hidden_operational_path/`: isolated RHP-01 environment,
  two Gate seeds, evaluator, Gate 0/Gate 1 evidence, and an admitted eight-task
  `core_family/`.
- `construction/retail_dual_update_sequence/`: rejected two-task RDS-01
  sequencing Pilot, isolated environment, evaluator, and Gate 0 evidence.
- `construction/joint_settlement_destination_scope/`: JSG-01 isolated joint
  environment, two Gate seeds, evaluator, Gate evidence, and an admitted
  eight-task `core_family/`.
- `calibration/joint_settlement_destination_scope/`: joint Reference Skill,
  matched Gate 1 config, and E0/ER aggregate result.
- `experiments/joint_settlement_destination_scope_gate1/`: reproducible
  eight-rollout Joint Gate 1 entry point; raw trajectories remain ignored.
- `reports/JSG01_GATE1_REPORT.md`: Joint Gate 1 result and limitation.
- `reports/JSG01_JOINT_CORE_ADMISSION_REPORT.md`: expanded-family validation
  and formal admission record.

See `reports/V3_STATUS.md` for the canonical status summary. A future Core
family may enter `benchmark/` after Gate 0, Gate 1, multi-task expansion, and
deterministic family validation. Learned-Skill transfer and targeted controls
are later method diagnostics, not mandatory admission gates.

The extension-point audit's recommended **EE-01 Channel-Conditioned Settlement
Commit** now has a two-task isolated prototype under
`construction/latent_settlement_contract/`. Both correct paths score Success 1;
both opposite choices commit successfully, score Success 0, consume the only
change, and reject correction without rollback. Its valid Gate 1 smoke improved
from E0 2/4 to ER 4/4, with both E0 failures attributed to the hidden settlement
branch. The mechanism was then expanded to eight new entities and four wording
surfaces, balanced across all channel/decision combinations. Every correct path
succeeds; every opposite choice commits, fails semantically, and cannot be
repaired. Those eight tasks are now the formal v3 set.

RHP-01 then reused native Retail's mutually exclusive delivered-order exchange
and return writes under a v3-only fulfillment contract. Its Gate 1 improved
from E0 2/4 to ER 4/4. The admitted Core adds eight new users, orders, and
products across four wording surfaces, balanced 4/4 between consolidated
exchange and partner-direct return. All eight correct paths succeed; all eight
opposite paths commit, fail semantically, and reject correction. At that stage,
the combined formal set contained sixteen tasks; RAP-01 later raised it to 24.

## Validation

Run the offline edition and retained-Pilot checks with:

```bash
python -m scripts.benchmarks.validate_editions phase_v3_day34
python scripts/benchmarks/v3/development/primitive_a/tools/validate_primitive_a.py
python scripts/benchmarks/v3/development/primitive_b/pb_c02/tools/validate_tasks.py
python scripts/benchmarks/v3/development/hidden_resource_semantics/tools/validate_construction.py
python scripts/benchmarks/v3/development/latent_settlement_contract/tools/validate_gate0.py
python scripts/benchmarks/v3/development/latent_settlement_contract/core_family/tools/validate_core.py
python src/benchmark_v3/development/retail_hidden_operational_path_audit/tools/probe_native_retail.py
python scripts/benchmarks/v3/development/retail_hidden_operational_path/tools/validate_gate0.py
python scripts/benchmarks/v3/development/retail_hidden_operational_path/core_family/tools/validate_core.py
python scripts/benchmarks/v3/development/retail_dual_update_sequence/tools/validate_gate0.py
python scripts/benchmarks/v3/development/joint_settlement_destination_scope/tools/validate_gate0.py
python scripts/benchmarks/v3/development/joint_settlement_destination_scope/core_family/tools/validate_core.py --verify-admission
python scripts/benchmarks/v3/development/integration_audit/validate_integration.py
```

The completed calibration runners remain reproducible but are not part of the
formal edition validator:

```bash
python scripts/benchmarks/v3/development/experiments/primitive_b_pb_c02_pilot/run_pilot.py --stage all
python scripts/benchmarks/v3/development/experiments/hidden_resource_semantics_pilot/run_pilot.py --stage all
python scripts/benchmarks/v3/development/experiments/latent_settlement_contract_gate1/run_gate1.py
python scripts/benchmarks/v3/development/experiments/retail_hidden_operational_path_gate1/run_gate1.py
python scripts/benchmarks/v3/development/experiments/retail_dual_update_sequence_gate1/run_gate1.py
python scripts/benchmarks/v3/development/experiments/joint_settlement_destination_scope_gate1/run_gate1.py
```
