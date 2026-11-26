# DocVQA v29.6 runtime

Independent v29.6 binding of the v29.5 selective-Gate runtime. Diagnosis,
Preconditioner, Editor and Replay load this package's four `prompts/*.md` files,
byte-identical to the approved design in `docs/methods/v29_6/prompts/`.

Actor execution, scoring, input codecs, structural contracts, patch composition,
Gate, Memory publication and recovery algorithms remain those of v29.5. Method,
stage, runtime, final evaluation and prompt identities are isolated. The formal
configuration preserves every experimental parameter; only method/stage/prompt
identities change. Old v29.5 campaigns cannot resume through this package.

CLI: `scripts/runs/run_v29_6_campaign.py`; configuration:
`experiments/configs/v29_6_docvqa_optimization160.json`. Training and held-out Test
are explicit separate operations. `--validate-only` reads no credentials and
creates no campaign. No experiment is launched by importing this package.

See [implementation and offline acceptance](../../../docs/methods/v29_6/IMPLEMENTATION.md).
