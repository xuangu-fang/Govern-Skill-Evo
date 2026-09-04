# Autonomous GSE v14 — TGE benchmark v1

This campaign changes only the benchmark/runtime adapter. The v14 Diagnosis,
Editor, proposal compiler, serial three-step orchestration, and Pareto bootstrap
Gate retain their existing semantics.

- Frozen Train: 48 tasks, assigned as three fixed 16-task family-preserving batches.
- Fixed Monitor: 20 tasks, three matched rollouts per Skill, used only for selection.
- Held-out Test: 48 tasks, inaccessible to evolution and selection; final evaluation only.
- Task Success: TGE v1 outcome evaluator, including deterministic denial semantics.
- Compliance: deterministic atomic, ordering, or composition Oracle; no LLM judge.
- Formal artifacts: `artifacts/autonomous_gse_v14_tge_v1/formal`.

Run `plan` first. It validates frozen hashes, split lineage, batch integrity,
evaluator coverage, and Test access guards without an LLM call or rollout. The
`run` command refuses a non-empty artifact root; interrupted campaigns use
`resume`, which verifies the campaign and frozen hashes before continuing.
