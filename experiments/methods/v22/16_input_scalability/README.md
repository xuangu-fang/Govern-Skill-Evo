# V22 evidence-input scalability study (offline only)

This directory is an isolated audit/prototype. Nothing here is imported by v3 or an experiment runner.
No model API, environment episode, Gate or publication is executed.

Reproduce from repository root with the existing ALFWorld Python environment:

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v22/16_input_scalability/audit/audit.py
/Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v22/16_input_scalability/prototype/capacity.py
/Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v22/16_input_scalability/prototype/test_views.py
```

- `audit/`: original saved request decomposition and provider-reported input tokens.
- `prototype/views.py`: exact reversible dictionary/table projection; an explicitly lossy Editor role view; an insufficient cards-only history comparator.
- `prototype/capacity.py`: 5 old-evidence re-encodings plus 200 synthetic round/stage scenarios, 12+12+12+12+9. Each full roundtrip is asserted.
- `prototype/test_views.py`: factual/source fidelity tests, not model semantic tests.
- `design_review/notes.md`: independent source-level design/compatibility review.
- Results: `artifacts/methods/v22/16_input_scalability/`.

Synthetic fixtures reuse archived shapes and then clone/extend rows with explicit synthetic identity. They are NOT valid new environment rollouts or classifier outputs; frozen grouping prose is a size template, not a classification of synthetic tasks. Native outcomes are seed-shaped placeholders. No fixture constitutes experimental evidence for Skill quality or causality.

`v3` in capacity results means the current consumption projection plus frozen v3 System text, not a historical API call under v3. 08 actual calls use the earlier profile. Re-encoded payloads have not been accepted by the production runner and must never be resumed as checkpoints.

`role` equals `lossless` except Editor. Editor's event window (explicit basis ±1) is an engineering experiment, not a proven semantic closure. `cards_only_insufficient` intentionally removes raw history and is not recommended as a standalone Fusion/Memory input.

Token ranges use 2–4 message-content characters/token as an uncalibrated sensitivity range for the new encoding, not a context guarantee. Only archived provider token usage is actual. Prototype control text is counted; a future formally aligned Prompt may differ.
