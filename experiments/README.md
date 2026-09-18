# Experiment artifact policy

`experiments/` stores the small, reviewable inputs and conclusions needed to
understand or reproduce an experiment. It is not a storage location for model
rollouts or per-attempt runtime data.

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
