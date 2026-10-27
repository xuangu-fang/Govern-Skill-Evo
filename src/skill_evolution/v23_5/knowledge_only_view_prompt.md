## Knowledge Only input view — memory_knowledge_only_v1

`memory` contains only `format` and all active `entries`. Each entry has `id`
and a nonempty `knowledge` array; each item has its own `text` and `evidence`.
There are no Knowledge IDs or entry-level evidence fields. Empty Memory has
`entries: []`. A legacy entry may be wrapped as one item without splitting claims.

Historical raw Parents, Diffs, execution traces, observations, action menus, and
pairing records are not included in this model input. Their absence means not
provided here, not absent evidence. Complete sources remain archived externally;
there is no historical lookup or rereading step in this call.

You may directly use supplied Knowledge without rereading unavailable sources.
Keep its conditions, material comparisons, counterexamples, and uncertainty.
Historical understanding is revisable, not a universal law. Distinguish current
direct observations from reported historical understanding. New evidence may
refine an interpretation or its scope, but cannot rewrite what occurred in an old
experiment. Do not invent historical details or claim to have rechecked originals.
Unresolved ambiguity or contradiction must not be resolved by inventing facts.

Only exact historical Evidence IDs present in the supplied Knowledge evidence
arrays may be cited. They preserve provenance, not access to original sources.
A supplied step does not authorize the run, its outcome, initial state, neighboring
steps, or associated Diff unless each is explicitly supplied. No ranges or aliases.
Current references still refer to the supplied current facts. Memory IDs identify
historical understandings; they are not execution evidence. Existence and citation
permission do not prove semantic support for a claim.
