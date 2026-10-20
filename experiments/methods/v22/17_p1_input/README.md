# V22 P1 lossless input implementation

P1 implementation: `revision/`, profile `v22.unified_dsc.v4`, encoding
`v22.p1_shared_input.v1`. D/S/C behavior and model output schemas inherit v3.
All five semantic stages use the same exact shared encoding; no P2 or history
selection is enabled. Old profiles retain their message construction paths.

- `offline/capacity.py`: formal codec capacity and exact roundtrip comparison.
- `validation/`: original immutable eight-case fixtures and once-only controller.
- `official_validation/`: endpoint-policy amendment, not a second sampling run.
  It uses the same frozen facts/messages/criteria and the user-selected official
  model `deepseek-v4.1-flash` via the existing revision 18 routing function.
- Artifacts: `artifacts/methods/v22/17_p1_input/`.

The original launch stopped before HTTP. The amended run sent all eight allowed
requests once; all returned HTTP 400 for an unsupported model name. No model
outputs or usage were returned. Do not rerun either controller: attempts are
permanently reserved and the budget is consumed. A new model choice and request
budget require a separate authorized freeze; do not mutate these archives.

Offline: 414 V22 tests, 35 Adapter tests, 19 exact historical-message rebuilds,
and 205 capacity/roundtrip comparisons passed. Capacity still exceeds 400,000
characters for some changing 50-step and extreme-menu scenarios. Real semantic
comprehension and input-token savings remain unverified.

Full report:
`docs/methods/v22/UNIFIED_DSC_P1_IMPLEMENTATION_VALIDATION.md`.
No ALFWorld episodes, publication, or 57-task campaign were performed.

## Shared source layout

The revision keeps the nine P1 source/test differences. Package paths explicitly
search this revision first, `12_contract_alignment/revision` second, and the
project tree last. Common adapters, contract tests, other source modules, and
experiment inputs are referenced rather than copied.

The additional local `bounded_evaluation.py` has only the subprocess-directory
adaptation used by revision 12: Actor children must start in revision 17 to retain
P1 imports while using revision 12's historical adapter. Runtime source lookup
follows the same package order.

Run shared V22 tests, inherited contract tests, P1 tests, historical adapter tests,
and import-wiring checks from the project root:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/17_p1_input/offline_tests.py
```

The script also works by absolute path from another directory. Module-name test
loading preserves P1-first imports. The later mainline `test_chunked_retry.py`
is outside the historical adapter suite.

Additional existing offline fixture and route checks run in separate processes
because the two route suites use the same module name:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/17_p1_input/validation -q
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/17_p1_input/official_validation -q
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/17_p1_input/official_flash_validation -q
```

`run.py --help` exposes the P1 runner without starting a call. These layout changes
do not restart historical controllers or rewrite their saved outputs. The two
official route controllers continue to reference revisions 18 and 19 respectively.
