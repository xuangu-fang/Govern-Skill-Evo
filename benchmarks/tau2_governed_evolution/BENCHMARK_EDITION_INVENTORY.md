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

## Shared infrastructure

The following former top-level packages now live under `shared/`: `boundary`,
`compiler`, `compliance`, `composition`, `concepts`, `evaluation`, `realization`,
`registry`, and `surface`. They define reusable machinery rather than a sixth
benchmark edition.
