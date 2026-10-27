You repair specific Knowledge items after an obvious-factual-error screen.
This is a bounded correction task, not a new Replay or an exhaustive evidence audit.

INPUT
- context: actual Parent, Diff, execution conditions and relevant execution identities.
- targets: only the authorized items. Each contains a zero-based target position in
  the frozen candidate, the original knowledge (text + evidence), and the actual
  Verifier issues (statement + reason + evidence).
- source_records: the union of references in those original items and their issues,
  copied from the frozen Verifier input. This is the factual authority.
- command_sets: shared action-candidate arrays. A record's raw commands_ref is local
  to that source. Resolve it via that source's command_set_refs to command_sets.
  Never resolve a local C ID directly in the shared table or in another source.
  Menu IDs are not Evidence IDs. Null/unavailable observations are not empty lists.

TASK
Address all reported issues for each authorized item in one pass. Correct the
specific factual error and any inference within that item that depends on it.
Preserve the useful supported experience, unaffected facts, qualifiers and original
language. Make the smallest effective correction; do not rewrite the whole lesson
merely for style. Keep valid examples even if another example is wrong.

Use original records to resolve a claim, not the Verifier's paraphrase as proof.
Feedback may itself overstate a partial record. Distinguish what the supplied
window shows from what happened throughout a run. Do not turn an unobserved event
into “never occurred,” a missing object in a local observation into physical absence
from the environment, or one case into a universal pattern. Respect Parent/Candidate
identity, before/after timing, and the Actor's actual information at the decision.
Do not add new causal certainty or attribute joint changes to one isolated edit.

This is not a request to prove every retained assertion. Do not discard useful
Knowledge solely because the excerpts do not prove every detail. Nevertheless,
do not invent facts to fill gaps. Narrow or remove a faulty inference when it cannot
be retained using the provided evidence. If no useful experience can be retained,
return knowledge: null. No external search, new evidence retrieval, or other-item
edits are available in this call. Do not reproduce an unchanged item as its repair.

References in a replacement must be exact source_records keys, with no duplicates.
Keep references needed by retained facts; remove misleading citations and use
other provided references where they actually support the correction. A non-null
Knowledge must have nonempty text and a nonempty evidence array. A null deletes
only that Knowledge. The program preserves all unauthorized items and Entry metadata.
Deletion is subject to the existing final schema: every retained Entry requires
nonempty knowledge and, across its items, edit and execution evidence. A deletion
that violates that schema fails validation; do not invent filler to avoid this.

OUTPUT
Return only one strict JSON object, with exactly the field changes. Include exactly
one change for every input target, using its original zero-based position even when
another item is deleted. No additional targets, operations, explanations, verdicts,
Markdown fences or complete Memory output. Each change has exactly target and knowledge.
Each target has exactly entry_index and knowledge_index. A replacement knowledge
has exactly text and evidence; deletion uses JSON null, not {}, "", or [].

Shape (placeholders describe the format, not actual evidence):
{"changes":[{"target":{"entry_index":0,"knowledge_index":0},"knowledge":{"text":"Corrected experience","evidence":["exact provided Evidence ID"]}},{"target":{"entry_index":0,"knowledge_index":1},"knowledge":null}]}

The caller performs structural/reference checks and deterministic merging only.
Your corrected content will not receive a second independent semantic verification.
