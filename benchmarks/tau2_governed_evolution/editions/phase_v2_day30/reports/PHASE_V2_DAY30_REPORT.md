# Phase Benchmark v2 — Day 30

This edition packages the research state reached through Phase 17C as one
directly runnable benchmark. Git history supplies versioning; there is no
separate freeze, admission, candidate, or snapshot lifecycle.

## Composition

- 54 Phase-v1 baseline tasks.
- 9 advanced-control tasks retained from Phases 13–15.
- 7 non-duplicate latent-G tasks from Phase 16.
- 2 cross-axis tasks from Phase 17.
- Total: 72 tasks.

Four exact-payload duplicates (`travel_request_027`, `031`, `033`, and `035`)
remain in construction history but are excluded from the runnable task set to
avoid accidental weighting bias.

## Construction principles

1. Task-relevant truth may be latent.
2. Information hidden from the Base Agent is also hidden from the Learner.
3. Historical interaction evidence must make the target truth recoverable in
   principle.
4. Headroom claims are supported by rollout evidence rather than task retuning.

## Coverage evidence

- Capability focal-headroom mechanisms: P1, P3, P4, P5, and certificate allocation.
- Governance focal-headroom mechanisms: LGA01, LGA03, LGA04, and LGV16B_001–004.
- `travel_request_036` supplies observed joint Capability/Governance headroom.
- `travel_request_037` supplies Capability headroom in the combined setting.

The detailed retained evidence is in `coverage.json`, `evidence_summary.json`,
`known_issues.json`, and `task_role_inventory.json`. Exact executable membership
is defined only by `../benchmark/task_manifest.json`.

## Rebuild

```bash
python -m benchmarks.tau2_governed_evolution.editions.phase_v2_day30.assemble_benchmark
python -m benchmarks.tau2_governed_evolution.validate_editions phase_v2_day30
```
