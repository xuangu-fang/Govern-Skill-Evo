# Experiment artifact policy

`experiments/` stores the small, reviewable inputs and conclusions needed to
understand or reproduce an experiment. Raw model rollouts and per-attempt runtime data live under `artifacts/methods/`
and must not be committed to Git. Old runtime aliases have been removed.

Commit these artifacts:

- method definitions and frozen configurations in `methods/<version>/<experiment-id>/config/`;
- benchmark experiment definitions and curated results in `benchmarks/`;
- other baseline configurations remaining in `configs/`;
- manifests and fixed input definitions in `manifests/`;
- human-curated annotation data, including `annotations/*/gold/`;
- concise experiment reports and aggregate result summaries.

Do not commit these generated artifacts:

- versioned runtime directories such as `v17_*/`;
- any `attempt*` directory;
- per-run model requests, responses, provenance, validation records, task
  diagnoses, and sanitized runtime inputs;
- semantic evaluation runs and stability runs.

Generated artifacts remain available locally for debugging. Move a conclusion
that must be reviewed or cited into a concise report outside an ignored runtime
directory; do not add raw JSON back to Git.

## Navigation

[Method experiments v01–v21](methods/README.md) · [Benchmark experiments](benchmarks/README.md)

## Local runtime organization

See [method runtime navigation](methods/RUNTIME.md) and [experiment index](INDEX.md).
Method runs now live in `artifacts/methods/<version>/`; historical pilot/formal/archive
stages and run IDs are preserved. `artifacts/methods/v17`, `v18`, `v19` and older runtime
entries are compatibility symlinks, not independent copies. Reviewable historical
indexes live in each method version's `runtime-history/` directory. New runs should
use `scripts/run_method.py` or explicitly set an output under `artifacts/methods/`.
