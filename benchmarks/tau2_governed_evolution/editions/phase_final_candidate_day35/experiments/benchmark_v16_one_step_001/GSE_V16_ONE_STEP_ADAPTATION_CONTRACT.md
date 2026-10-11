# GSE-v16 One-Step Adaptation Contract

## Purpose

GSE-v16 is the GSE-v15 experience-grounded learner applied to the formal
73-task final-candidate benchmark with one Evolution step.  It is a protocol
and benchmark-runtime adaptation, not a new Skill Evolution method.

## Inherited without method changes

- v15 learner-safe information boundary and Level-0 boolean supervision;
- exactly three independent Parent rollouts per Evolution task;
- v15 semantic Diagnosis, deterministic compiler, Proposal aggregation and
  bounded Editor;
- matched Parent/Candidate comparison;
- the v15 pilot's task-cluster bootstrap and epsilon-Pareto Gate semantics.

## v16 protocol

```text
S0
 -> 32 Evolution tasks x 3 Parent rollouts
 -> Diagnosis / Proposal / Editor
 -> Candidate S1 (when an update-eligible diagnosis exists)
 -> 41 Monitor tasks x 3 matched Candidate rollouts
 -> one unified distributional Gate
 -> ACCEPT S1 or RETAIN S0
```

The fixed S0 Monitor baseline is the Parent side of every matched comparison.
There is no second or third Evolution step.

## Benchmark and environment

- Edition: `phase_final_candidate_day35`
- Evolution split: `train`, 32 Core tasks
- Monitor split: 41 tasks
  - 32 `CORE_GENERALIZATION`
  - 9 `REGRESSION_GUARD`
- Airline runtime: `airline-final-candidate-unified`
- Retail runtime: `retail-final-candidate-unified`
- Every rollout starts from a newly constructed environment.

The Monitor roles are descriptive metadata.  All 41 tasks enter the same Gate;
there is no role-specific veto or second acceptance decision.

## Evaluation

Every rollout receives deterministic booleans:

```json
{"success": true, "compliant": true, "quadrant": "CS"}
```

The dispatcher uses the admitted family evaluator, the deterministic Airline
trace evaluator where Governance is applicable, and the formal control
evaluator for regression guards.  No LLM Judge participates in benchmark
scoring or learner supervision.

## Learner information boundary

Diagnosis receives only:

- the deployed visible policy and public tool schemas;
- the current Skill;
- observed messages, tool calls and tool results;
- deterministic `success` and `compliant` booleans.

It does not receive task specs, family or Monitor-role labels, evaluator
invariants, hidden mappings, expected actions, or canonical legal paths.

## Unified Gate

The Gate uses all 123 matched Monitor pairs (41 tasks x 3 rollouts), clusters
by task, stratifies the bootstrap by runtime domain, and applies the v15
epsilon-Pareto decision with one paired outcome as epsilon and an acceptance
probability threshold of 0.80.

Core and regression-guard transitions are reported separately for diagnosis,
but only the unified Gate emits `ACCEPT` or `RETAIN`.

## Staged command line

The campaign is run in three resumable commands:

```bash
python -m benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001.run_v16 baseline
python -m benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001.run_v16 evolve
python -m benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.experiments.benchmark_v16_one_step_001.run_v16 candidate-monitor
```

`baseline` produces the fixed S0 Monitor side; `evolve` produces the S0
Evolution experience and Candidate; `candidate-monitor` runs the matched
Candidate Monitor, makes the sole Gate decision, and writes the final Skill.
Completed rollout records are reused when a stage command is restarted.

## Preflight acceptance criteria

- 73 unique tasks load and validate;
- split counts are 32 Evolution and 41 Monitor with no overlap;
- evaluator routing covers 73/73 tasks;
- fresh Airline and Retail environments can be constructed repeatedly;
- the existing 64-Core and 9-control deterministic integration audits pass;
- a three-rollout learner request can be constructed without privileged
  benchmark metadata;
- synthetic matched reports exercise both unified-Gate decisions;
- the runner exposes exactly one Evolution step and one final Gate.
