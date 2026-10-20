# V22 Memory contract clarification

Profile: `v22.unified_dsc.v5`. This revision clarifies the existing retirement
fields and includes a synthetic format example. The original algorithm and
validation functions retain their behavior.

## Shared source layout

Imports search revision 20, revision 17 (`17_p1_input`), revision 12
(`12_contract_alignment`), then the project tree.

Seven source/test differences remain local:

- `memory_contract.py`: the v5 profile and learning-format clarification.
- `effective_memory.py`, `grouped_representation.py`, `grouped_update.py`:
  support for the v5 contract.
- `continual_runtime.py`, `continual_verify.py`: runtime/profile integration.
- `test_memory_contract_v5.py`: contract, historical-message and algorithm checks.

These source files are under `revision/src/skill_evolution/v22`; the test is under
`revision/tests/skill_evolution/v22`. Common source, tests, adapters and experiment
inputs are referenced. Local package initializers establish that search order.
The small subprocess-directory adaptation in `bounded_evaluation.py` keeps Actor
children in revision 20. Runtime source lookup follows the imported packages.

The import-wiring tests are shared with revision 21 and check whichever revision
is selected by its entry point. Revision 21 changes only the contract and its
corresponding test; it reuses this implementation.

## Offline checks

From the project root:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/20_memory_contract_fix/offline_tests.py
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/20_memory_contract_fix/validation -q
```

`offline_tests.py` and `run.py --help` also work by absolute path from another
directory. Tests are loaded by module name so inherited tests use this revision.
The later mainline `test_chunked_retry.py` is outside the historical adapter suite.

The existing `validation/` files and `artifacts/methods/v22/20_memory_contract_fix/`
describe historical probes. The commands above run offline tests only; the old
preparation/controller is not rerun and saved experiment results are not rewritten.

After deduplication, all 459 suite tests (421 V22, 35 adapter, and 3 import-wiring
checks) and both validation-controller tests passed. No model requests or ALFWorld
episodes were executed.
