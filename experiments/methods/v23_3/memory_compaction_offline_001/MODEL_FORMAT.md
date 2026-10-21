## Historical Memory evidence view

`memory.format = memory_evidence_view_v1` is a model-input projection, not the
complete stored Memory. Entries and evidence references are unchanged. Historical
edit sources still contain their original Parent, actual Diff and execution
context. Do not accept a knowledge claim as verified merely because it is listed.

Every historical execution contains its original task, initial state, outcome and
the complete ordered `trace` of step IDs, actions and raw feedback. A trace omits
observations and candidate menus except where detailed windows supply them.

Each window covers inclusive step numbers `start..end`. Its `before` is the full
state immediately before `start`; `after[i]` is the full state after step
`start+i`. Within a window the next before-state equals the preceding after-state.
`omitted_detail_ranges` explicitly identifies steps without full before/after
evidence; the initial state and each window boundary may additionally expose a
neighboring state. Never fill a gap by carrying a state across it.

Each state's local `commands_ref` resolves in that source's `command_sets`.
If `policy.shared_menus` is true, each local value is a key into the top-level
`command_pool`; otherwise it is the original command list. C IDs in different
sources have separate namespaces. A null command reference is unknown, not empty.

Precise evidence anchors are expanded by the fixed radius in `policy`. Sources
without a numeric anchor retain all details. All actions, feedback and outcomes
remain visible regardless of detail coverage. Do not infer an omitted observation,
inventory condition, candidate list, or object absence. An action trace can show
recorded actions and order; it cannot establish all state-dependent preconditions.
Cite original context-qualified source/step IDs. If the supplied detail is
insufficient for a state-dependent change, state the limitation rather than
inventing evidence. No additional evidence-reading or model-selection call is
available in this input format.
