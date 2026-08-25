# Autonomous GSE v08

v08 reuses the Day 18 `autonomous_gse_v07` Diagnosis Evolution procedure and
runs it on ST-WebAgentBench-Interactive v2. The runtime forces the Interactive
variant, validates every trajectory's UserSimulator lineage, and writes only to
`artifacts/autonomous_gse_v08/`.

v08 freezes `stweb-interactive-user-v6` with
`suitecrm-v03-all-v4`, a cooperative response protocol and scenario set. The
Agent must request missing information and confirmation in separate turns. The
LLM returns only `INFO`, `MISSING`, `CONFIRM`, or `ACK`; the runtime maps the
code to a deterministic user-visible information reply or a fixed reply without
exposing hidden simulator-control text. Yes-or-no questions that repeat concrete
values are confirmations. On an accidental mixed turn,
information takes priority and confirmation is deferred to a later turn. Missing
facts produce a fixed unknown reply and remain visible in interaction metrics.
The UserSimulator does not refuse or correct Agent proposals, so native task and
policy Evaluators remain responsible for exposing Agent errors.
Scenario v3 preserves task parameters, facts, explicit task scope, and stated
preferences while removing the 33 legacy `Do not authorize...` guardrails.

The inherited formal budget is unchanged: three Steps, 153 Train trajectories,
54 initial S0 Selection trajectories, up to 162 Candidate Selection
trajectories, 369 total trajectories, and 156 Learner calls. Test evaluation,
post-hoc replay, three-seed replication, and the legacy Original control are not
part of v08.

## Commands

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo

export PYTHONPATH=.
export NO_PROXY='localhost,127.0.0.1,::1,llm-proxy.intra.didiglobal.com,.intra.didiglobal.com'
export no_proxy="$NO_PROXY"
export GSE_V08_PY=/Users/didi/miniforge3/envs/stwebagentbench/bin/python

set -a
source external/ST-WebAgentBench/.env
set +a
```

Inspect the frozen execution plan:

```bash
"$GSE_V08_PY" -m src.skill_evolution.autonomous_gse_v08_benchmark_runtime \
  plan \
  --campaign experiments/campaigns/autonomous_gse_v08/campaign_manifest.json
```

Create the fresh 54-trajectory S0 Selection checkpoint:

```bash
"$GSE_V08_PY" -m src.skill_evolution.autonomous_gse_v08_benchmark_runtime \
  initial-checkpoint \
  --campaign experiments/campaigns/autonomous_gse_v08/campaign_manifest.json
```

Run the three formal Diagnosis Evolution Steps:

```bash
"$GSE_V08_PY" -m src.skill_evolution.autonomous_gse_v08_benchmark_runtime \
  run \
  --campaign experiments/campaigns/autonomous_gse_v08/campaign_manifest.json
```

The Runtime sets `STWEB_BENCHMARK_VARIANT=interactive` internally for every
rollout subprocess. Existing v07 artifacts are never used as v08 checkpoints
and are not overwritten.
