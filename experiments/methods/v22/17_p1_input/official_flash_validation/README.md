# Authorized P1 model-ID recovery: completed

User authorized eight fresh once-only probes after correcting the official model
name to `deepseek-flash`. `route_control.py` imports only the model-routing helper
from revision 19; it uses the existing revision 17 P1 fixtures, algorithms and
validators. It does not run revision 19's v3 environment campaign.

Inputs, messages, criteria and all other request parameters match the original
preparation. Original pre-dispatch failure and all eight earlier HTTP400 requests
remain intact. The new freeze is under
`artifacts/methods/v22/17_p1_input/official_flash_validation/`.

Outcome: 8 HTTP200, 8 complete JSON outputs, 6 accepted contracts. Both learning
outputs were rejected for nonempty retirement field names, which were not fully
specified in either actual model message. No output repair, semantic retry,
environment episode, Gate execution or official Skill/Memory publication occurred.

Do not rerun the controller: all eight cases have permanent attempt locks, and
this recovery budget is exhausted. `analyze_outputs.py` performs read-only usage
accounting and price-based estimates; it never dispatches requests. It was added
for post-response analysis, not used to construct or alter frozen requests.

Report: `docs/methods/v22/UNIFIED_DSC_P1_FLASH_RECOVERY_VALIDATION.md`.
