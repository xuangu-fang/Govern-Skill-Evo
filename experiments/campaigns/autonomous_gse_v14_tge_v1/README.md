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

After all three Evolution steps complete, run the held-out Parent-vs-Final
comparison with:

```bash
/Users/didi/miniforge3/envs/tau2/bin/python \
  -m src.skill_evolution.autonomous_gse_v14_tge_v1_runtime \
  test \
  --campaign experiments/campaigns/autonomous_gse_v14_tge_v1/campaign_manifest.json \
  --artifact-root artifacts/autonomous_gse_v14_tge_v1/formal
```

`test` runs only the frozen Test split: 48 tasks × 3 matched seeds for S0 and
the campaign's Final Skill (288 trajectories total). It writes reusable rollout
artifacts and a comparison under `formal/test_evaluation/`; its results never
enter Diagnosis, Editor, or the Monitor Gate.
