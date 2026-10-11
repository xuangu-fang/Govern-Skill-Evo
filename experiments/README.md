# Experiment artifact policy

`experiments/` stores the small, reviewable inputs and conclusions needed to
understand or reproduce an experiment. Raw model rollouts and per-attempt runtime data may remain here locally,
but must not be committed to Git.

Commit these artifacts:

- experiment configurations in `configs/`;
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

## Local runtime organization

See [experiment index](INDEX.md). v19 runtime data is organized under `v19/pilot/`,
`v19/formal/`, and `archive/v19/`. The index and path map remain reviewable in Git;
run subdirectories are ignored. v17/v18 now follow the same versioned layout. Frozen configuration and manifest locations are unchanged.
