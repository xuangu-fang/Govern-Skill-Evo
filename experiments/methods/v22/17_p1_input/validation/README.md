# P1 real-model probe preparation

This directory constructs eight **independent** probes from the real 08 R2
archive. It does not execute ALFWorld or publish Skill/Memory. The parent
controller owns any paid dispatch and must first freeze these scripts, the
tested revision, all prepared files, and the one-attempt transport.

`fixtures.py` exports:

- `build_cases()` -> eight dictionaries containing `id`, `stage`, `profile`,
  original unencoded `payload`, `classification_binding`, fixed `parameters`,
  `timeout_seconds`, `material`, and `criteria`.
- `validate_output(case, value)` -> the existing stage validator result. It
  uses original facts, never a model-decoded reconstruction. Classification
  binds the new output to the actual P1 System prompt and original task map.
- `material(profile)` -> the five legal stage payloads and classification
  binding built by production functions.
- `source_manifest()` -> 36 immutable real-source file identities, including
  all twenty audited trajectories.

`prepare.py` writes new files exclusively under
`artifacts/methods/v22/17_p1_input/preparation`. It has no run command. The
independent controller reads `protocol.json` plus each case's
`payload.json`, `messages.json`, `request.json`, `criteria.json`, and (for
classification) `classification_binding.json`.

The selected materials are fixed before requests:

| Stage | Fixed source | Probes |
| --- | --- | --- |
| Classification | Complete 08 R2 Parent grouping input, original private binding | P1 |
| Diagnosis | Same ten Parents and archived valid decision grouping; no Memory | P1 + v3 |
| Fusion | Archived initial Diagnosis Plan, same Parents, formal R1 Memory | P1 + v3 |
| Editor | Archived effective Plan, real Parent and same evidence | P1 |
| Replay/Memory | Archived actual Editor/Candidate/diff/execution Plan, twenty matched trajectories, R1 Memory | P1 + v3 |

The validation Editor's new text is never used with the old trajectories. The
new classifier output never replaces the grouping in another probe. v3 and P1
controls have equal facts after removing only profile and derived binding
identity; P1's decoded view equals the existing v3-semantic consumption view.

Each request uses `deepseek-v4-pro`, temperature 1, medium enabled thinking,
non-streaming output, and 600-second response timeout. Classification,
Diagnosis, Fusion and Editor have a 32,768 total completion cap; the two
learning probes have 65,536. Eight calls total at most 327,680 completion
tokens; these are caps including reasoning, not predicted usage. There are
no HTTP or semantic retries, no fallback model, and no environment episodes.
All results are diagnostic artifacts only.

Failure handling keeps each raw response and proceeds only to other already
declared independent probes. A critical shared-reference comprehension error
blocks P1 promotion; it does not warrant repairing, resampling, or replacing
the failed case. The known old Editor `reasoning_content`/`content` boundary
problem remains an explicit transport risk. No parser/tag-stripping change is
introduced to make the probe pass.

Run offline checks from the repository root:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -m unittest discover \
  -s experiments/methods/v22/17_p1_input/validation -p test_fixtures.py -v
```

Five fixture tests passed before any requests. These verify identities,
roundtrips and contract compatibility, not model semantic correctness. Raw
input-token comparison must use new provider usage; older 08 Token values
cannot substitute for the v3 controls.
