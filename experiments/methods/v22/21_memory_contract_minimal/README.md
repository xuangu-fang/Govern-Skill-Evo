# V22 minimal Memory contract clarification

Profile: `v22.unified_dsc.v5.minimal`. This revision keeps the prior learning rules
and adds only the exact field names for nonempty `retire_limits` entries.

## Shared source layout

Imports search revision 21, revision 20 (`20_memory_contract_fix`), revision 17
(`17_p1_input`), revision 12 (`12_contract_alignment`), then the project tree.

Only two source/test differences from revision 20 remain local:

- `revision/src/skill_evolution/v22/memory_contract.py`
- `revision/tests/skill_evolution/v22/test_memory_contract_v5.py`

The rest of the implementation, including import-wiring tests, is inherited.
Local package initializers establish the search order, and the small subprocess
directory adaptation in `bounded_evaluation.py` keeps Actor children in revision
21. The validation fixture checks the local contract and revision 20's shared
`grouped_update.py`.

Revisions 22, 23 and the capacity amendment explicitly include the inherited
directories in their package paths. Their runtime source lookup follows those
paths, and revision 23's test entry point loads inherited tests by module name.
Revision 23 excludes the 20/21 import-wiring checks and skips the assertion that
compact learning uses the unchanged historical file: revision 23 intentionally
overrides it. That identity assertion remains covered by both 20/21 suites; the
remaining inherited behavioral tests and revision 23's own tests still run.

## Offline checks

From the project root:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/21_memory_contract_minimal/offline_tests.py
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/21_memory_contract_minimal/validation -q
```

`offline_tests.py` and `run.py --help` also work by absolute path from another
directory. Tests are loaded by module name so inherited tests use this revision.
The later mainline `test_chunked_retry.py` is outside the historical adapter suite.

The existing `validation/` files and `artifacts/methods/v22/21_memory_contract_minimal/`
describe historical probes. The commands above run offline tests only; the old
preparation/controller is not rerun and saved experiment results are not rewritten.

After deduplication, all 459 suite tests (421 V22, 35 adapter, and 3 shared
import-wiring checks) and both validation-controller tests passed. No model
requests or ALFWorld episodes were executed.

Downstream checks also passed: 14 revision 22 checks, 420 inherited revision 23
tests (with the one identity check described above skipped), and 3 revision 23
five-round synthetic tests. The capacity amendment's imports and offline runtime
source selection were verified separately.
