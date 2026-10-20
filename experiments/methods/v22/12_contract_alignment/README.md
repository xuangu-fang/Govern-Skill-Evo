# V22 contract alignment revision

`revision/` contains the historical overrides for opt-in `v22.unified_dsc.v3`.
Unchanged modules, tests, experiment inputs and benchmark definitions are read
directly from the project tree. Small package initializers select this revision's
modules first and then the shared modules; there is no full source copy.
Three relative file links retain the paths read directly by experiment 16's
existing audit (`compact_learning.py`, `compact_cycle.py`, `continual_runner.py`).

The 13 historical source/test/document differences remain here. One additional
override, `bounded_evaluation.py`, only changes the Actor subprocess working
directory so that child processes also select this revision. Adapter source
lookup and runtime source collection follow the same shared-module paths.

The original source tree, other revisions and historical run artifacts are not
modified. Existing experiment plans retain their original profiles.

Run the shared V22 tests, historical ALFWorld adapter tests, and local
contract/import tests from the project root. The later mainline
`test_chunked_retry.py` is outside this revision's historical adapter suite:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/12_contract_alignment/offline_tests.py
```

`offline_tests.py` also works when invoked by absolute path from another directory.
It selects the local revision before importing tests and resolves shared inputs
from the project root. Direct discovery of the sparse `revision/tests` directory
alone does not include the shared regression tests.

The existing runner is available through `run.py`; displaying help does not
start a model call or an environment:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/12_contract_alignment/run.py --help
```

The report and continuation proposal are linked below. Continuing requires separate user authorization and a newly archived v3 runtime/config boundary; do not run the existing 11 entry point to activate this revision.

[Report](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_CONTRACT_ALIGNMENT.md)

[Offline evidence and proposed continuation](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/12_contract_alignment_20261016/continuation_proposal.json)
