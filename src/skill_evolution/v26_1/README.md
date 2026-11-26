# OfficeQA v26.1

Independent four-module runtime with v29.4 selective Update Gate and digest HEAD Memory, bound to the unchanged OfficeQA tool Runtime and scorer.

The executable configuration is `experiments/configs/v26_1_officeqa_train74.json`; explicit commands live in `scripts/runs/run_v26_1_campaign.py`. The four reviewed prompts are read verbatim from `docs/methods/v26_1/prompts`.

See `docs/methods/v26_1/IMPLEMENTATION.md` for contracts, offline verification and invocation examples. Importing this package starts no model, training, evaluation or automation. Production use requires explicit credential variable names. Tests use synthetic local documents and denied networking.
