# Replay main Prompt candidate 001

Freeze the user's replay_prompt_v23_4.md byte-for-byte as candidate_prompt.md.
Programmatically append the unchanged Actor execution context, Memory v3 format
description and Replay paired-view description, exactly once each. This is the
formal candidate for this experiment, not an automatic promotion to the default.
No production module, schema, base prompt or historical artifact is overwritten.

Reuse replay_input_view_live_001 R05/R06 full bundles, model input, history source
manifests and original Memory snapshots. Assert exact equality of user messages
and all call settings. Only the main instructions and execution-context placement
change. The previous default main prompt contained its context inline; the supplied
candidate requests the context appended. No prior proposal or human review enters
the request. Keep the existing independent evaluation lineage limitation.

Use the unchanged shared runner, transport and technical retry policy: one logical
Replay call per case; initial attempt plus at most three technical retries; first
structurally valid output selected; no semantic resampling or response repair.
Explicit request budget remains 1,200,000 characters; do not truncate inputs.

Review factual accuracy, material comparison coverage and Knowledge adoptability
against the actual model-visible input. Include historical context/object identity,
unknown versus absent, local versus total steps, applicability and joint-edit causal
limits, and evidence sufficient for future compressed views. Do not count omission
of an old error as successful reasoning if its meaningful comparison disappears.
Treat empty output as contract-valid but assess whether meaningful learning was lost.
One sample per case cannot establish reliable accuracy or isolate all prompt effects.

Preserve every request, response, error and unmodified proposal. Validate Memory in
independent copies, retaining full bundle context for future verified historical
pairs. No automatic Active Memory publication, Candidate promotion or Actor work.
