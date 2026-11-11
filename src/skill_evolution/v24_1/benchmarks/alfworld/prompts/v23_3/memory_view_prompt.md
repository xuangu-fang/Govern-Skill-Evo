## Historical Memory evidence view v3

`memory.format = memory_evidence_view_v3` is a model-input projection, not the full
stored archive. Entries and evidence references are unchanged. Historical edit
sources retain the original Parent, actual Diff and execution context. A knowledge
claim is not automatically verified by being listed.

Every historical execution contains its original task, initial state, outcome and
the complete ordered `trace` of fully qualified step IDs, actions and raw feedback.
Every trace step and detailed step includes its historical source, for example
S1_R03/Q4:13. Identical run/step numbers in different historical sources are
different steps. Match the entire ID, including the historical source prefix.
When an answer requests step IDs, copy these full IDs exactly; never remove or
replace the historical source prefix.

`detailed_steps` contains explicit records with fully qualified step IDs. Each
record gives that exact step's `before`, `action` and `after`. Read these states
directly. You do not need to derive a before-state from another array element.
The step's original feedback is still in the complete trace.

Every non-null `commands_ref` in an initial, before or after state is a DIRECT
global key into `memory.command_pool`. Resolve it once there. There is no local
C-ID mapping to look up. Global keys may be shared only when command lists have
exactly the same contents and ordering. A null reference means unknown, not empty.

`windows` lists inclusive start/end numbers describing which steps have detailed
records. `omitted_detail_ranges` marks steps without full before/after evidence.
Initial states and neighboring detailed records may expose additional boundary
states, but never carry a state across an unobserved gap.

The fixed numeric citation radius and conservative unlocalized-source fallback
are unchanged. All actions, feedback and outcomes remain visible. Do not infer an
omitted observation, inventory condition, command menu or global object absence.
Complete action order is not complete state evidence. Cite original qualified
source/step IDs, and state a limitation if the supplied evidence cannot justify a
state-dependent claim. No extra evidence-reading or model-selection call exists.
