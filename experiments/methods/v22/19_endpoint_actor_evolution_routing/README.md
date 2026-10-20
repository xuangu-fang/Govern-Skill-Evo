# V22 Actor and evolution endpoint routing

Runtime revision: `v22.endpoint_models.v2`. Algorithm remains `v22.unified_dsc.v3`.
This revision corrects and extends `18_endpoint_model_routing` without
rewriting its code, tests, archives or failed requests.

| OPENAI_BASE_URL | Actor (Parent and Candidate) | Classification and all update/learning calls |
| --- | --- | --- |
| `http://llm-proxy.intra.xiaojukeji.com` | `deepseek-v4-flash` | `deepseek-v4-pro` |
| `https://api.deepseek.com` | `deepseek-flash` | `deepseek-flash` |

`deepseek-flash` is the official API ID for V4.1 Flash. This revision does not claim
that an identical model ID on different providers identifies identical weights.
Trailing slash and `/v1` forms are supported; other endpoints retain the source
plan's Actor and evolution assignments. No fallback or additional requests are added.

## Usage

New entry point: `experiments/methods/v22/19_endpoint_actor_evolution_routing/run.py`.
It defaults to the repository root `.env`; existing process environment variables
still take precedence. It does not alter `.env` or store credentials.

Example **new preparation only**, not a checkpoint recovery or experiment run:

```bash
/Users/didi/miniforge3/envs/alfworld/bin/python \
  experiments/methods/v22/19_endpoint_actor_evolution_routing/run.py preflight \
  --plan artifacts/methods/v22/13_unified_dsc_v3_continuation_control_20261016/plan.json \
  --output-dir artifacts/methods/v22/NEW_PREPARATION_DIRECTORY
```

The CLI resolves both models before freezing. The effective plan records
`models.actor`, `models.evolution`, `classification.model`, and `model_route`.
The original input plan is not rewritten. Runtime freezing and dispatch validate
the route so an already prepared run cannot silently switch endpoint or models.
Programmatic callers use `load_bundle(plan_path, base_url=base)` after loading
the environment. Omission of `base_url` preserves the legacy fixed-plan behavior.

Old frozen runners and recovery scripts do not automatically use this revision.
Any checkpoint continuation must explicitly bind the new revision and model
boundary. Historical Parent traces must retain their original recorded model;
changing route does not relabel old trajectories or prove their comparability.
No experiment or checkpoint recovery is started by this implementation work.

The five-module algorithm, prompts, Schema, Gate, token budgets and call counts
are unchanged. This is a runtime model-selection change only.

## Files and verification

- `revision/src/skill_evolution/v22/model_routing.py`: explicit mapping.
- `continual_runtime.py`: resolve both models and validate dispatch against route.
- `continual_runner.py`: load environment before resolution; preserve frozen route.
- `revision/tests/skill_evolution/v22/test_continual_runtime.py`: both providers,
  every semantic stage, Parent/Candidate Actor dispatch, legacy behavior, endpoint
  identity matching and rejection of changes after freezing. All calls are mocks.

## Shared source layout

The four source/test differences listed above remain local. Package paths search
revision 19 first, `12_contract_alignment/revision` second, and the project tree
last. Common adapters, contract tests, other source modules, and experiment inputs
are referenced rather than copied.

The additional local `bounded_evaluation.py` starts Actor subprocesses in
revision 19, following the approach used by revisions 12, 17, and 18. Runtime
source lookup follows the same package order. The routing module stays at its
original path for revision 17's `official_flash_validation/route_control.py`.

The existing JSON inventories, route-check result, and test logs are records of
the original implementation, not inventories or test results for this layout.

## Offline checks

From the project root:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/19_endpoint_actor_evolution_routing/offline_tests.py
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/17_p1_input/official_flash_validation -q
```

The suite also works by absolute path from another directory. Module-name test
loading preserves revision-first imports and selects the local runtime tests.
The later mainline `test_chunked_retry.py` is outside the historical adapter suite.
Import-wiring checks cover shared modules, Actor child imports, and runtime source
selection. The existing routing tests cover both Actor and evolution dispatch.
`run.py --help` exposes the CLI without starting a model request.

After deduplication, all 439 suite tests (401 V22, 35 adapter, and 3 import-wiring
checks) and both revision 17 official Flash route checks passed. No model
requests or ALFWorld episodes were executed.
