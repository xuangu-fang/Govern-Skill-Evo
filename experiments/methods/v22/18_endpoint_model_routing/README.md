# V22 endpoint-specific evolution model routing

Runtime revision `v22.endpoint_evolution.v1`, sharing the historical
`12_contract_alignment/revision` (algorithm profile stays `v22.unified_dsc.v3`).
No archived plan, prompt, source snapshot, or experiment result is overwritten.

The new CLI reads the existing project `.env` before loading the plan:

| OPENAI_BASE_URL | Effective evolution model |
| --- | --- |
| `http://llm-proxy.intra.xiaojukeji.com` | `deepseek-v4-pro` |
| `https://api.deepseek.com` | `deepseek-v4.1-flash` |

Trailing slashes and `/v1` are supported. Other endpoints retain the declared
model. Credentials, query strings and fragments are not accepted in base URLs.
Existing process variables take precedence over `.env` (`override=False`).

The mapping is in `revision/src/skill_evolution/v22/model_routing.py`.
Both `models.evolution` and `classification.model` are resolved in the in-memory
plan. The saved runtime and campaign plan record the resolved model and route;
the original plan file is not rewritten. Every semantic stage uses the same
resolved model. Actor configuration, prompts, request budgets and Gate are unchanged.
The requested official model ID is configured literally; its availability has NOT
been established by this implementation. There are no live calls or fallback models.

## Entry point

Use `run.py` for new preparations, passing the intended source plan and a fresh
output directory. The wrapper defaults to the repository root `.env`:

```bash
/Users/didi/miniforge3/envs/alfworld/bin/python \
  experiments/methods/v22/18_endpoint_model_routing/run.py preflight \
  --plan artifacts/methods/v22/13_unified_dsc_v3_continuation_control_20261016/plan.json \
  --output-dir artifacts/methods/v22/NEW_PREPARATION_DIRECTORY
```

This is a fresh preparation, not a Diagnosis/Editor checkpoint recovery command.
No preparation or experiment was executed as part of implementing this change.
Old recovery scripts continue importing the old frozen runtime and do NOT acquire
this routing automatically. A continuation must explicitly bind this new revision
and its resolved model before executing; old prepared runs cannot silently switch.
Changing the endpoint after preflight requires a new preparation. API keys are not
stored in routing metadata.

Programmatic users opt in with `load_bundle(plan_path, base_url=base_url)` after
loading the environment. `load_bundle(plan_path)` preserves legacy semantics.

## Shared source layout

The revision keeps four source/test differences:

- `src/skill_evolution/v22/model_routing.py`
- `src/skill_evolution/v22/continual_runner.py`
- `src/skill_evolution/v22/continual_runtime.py`
- `tests/skill_evolution/v22/test_continual_runtime.py`

Package paths search this revision first, `12_contract_alignment/revision`
second, and the project tree last. Common adapters, contract tests, other source
modules, and experiment inputs are referenced rather than copied.

The additional local `bounded_evaluation.py` uses revision 18 as the Actor
subprocess directory, as in revisions 12 and 17. Runtime source lookup follows
the same package order. The routing module stays at its original path for
revision 17's `official_validation/route_control.py`.

`implementation_files.json`, `v22_tests.log`, and `adapter_tests.log` are records
of the original implementation, not inventories or test results for this layout.

## Offline checks

From the project root:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/18_endpoint_model_routing/offline_tests.py
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/17_p1_input/official_validation -q
```

The suite also works by absolute path from another directory. Module-name test
loading preserves revision-first imports and selects the local runtime tests.
The later mainline `test_chunked_retry.py` is outside the historical adapter suite.
Import-wiring checks cover shared modules, Actor child imports, and runtime source
selection. The routing tests cover model dispatch and endpoint changes.
`run.py --help` exposes the existing CLI without starting a model request.

After deduplication, all 438 suite tests (400 V22, 35 adapter, and 3 import-wiring
checks) and both revision 17 route checks passed. No model requests or ALFWorld
episodes were executed.
