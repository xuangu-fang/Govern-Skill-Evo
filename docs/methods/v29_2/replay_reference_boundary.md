# v29.2 shared citation boundary repair

This records the earlier v3 namespace repair. The subsequent execution-list
repair, current v4 configuration, and explicitly authorized migration are
documented in [execution_reference_boundary.md](execution_reference_boundary.md).

Replay prompt `v29_2_docvqa_replay_v3` and output contract
`v29_2_replay_transition_knowledge_v3` distinguish ordinary prose labels from
formal citations. Knowledge fields, event coverage, attribution, Gate and Memory
semantics are unchanged. Preconditioner now shares this syntax through
`src/skill_evolution/v29_2/explicit_references.py`, with prompt
`v29_2_docvqa_preconditioner_v3` and contract `v29_2_preconditioner_actions_v2`.
The shared v27 parser and v29/v29.1 consumers are unchanged. Diagnosis keeps its
existing implementation, Prompt, versions and unprefixed reference rules; only
regression tests were added for prose labels and denied sources.

## Trigger and syntax

R07 of `v29_2_docvqa160_epoch1_20261103_185548` exhausted six Replay requests
because every response contained ordinary prose like `either implemented
Update: the rule ...`. The old parser reserved every namespace-colon occurrence,
including ordinary prose, and reported only a generic backtick error. Changing
the actual citations did not remove that prose label.

- Outside code spans, `Update: the rule ...` and `Update: u2 concerns ...` are
  ordinary prose. A colon followed by whitespace does not create a formal
  citation or grant any reference permissions.
- Compact expressions such as `Update:u2` or `Evidence:P7:outcome` require
  exactly one enclosing backtick on each side.
- Within code spans, the reserved prefixes Memory, Group, Evidence, Update and
  Check must form a single exact authorized citation, with no internal whitespace.
  Missing/doubled/mismatched delimiters and unknown IDs remain errors.
- Ordinary code spans containing answers remain valid. Independent execution
  reference checks still reject other-task and historical evidence, including
  unprefixed P/Q references.
- Errors include the task ID (Replay) or Update/field such as `u1.reason` and
  `u1.text` (Preconditioner), the 1-based character position within that field,
  the offending token, and the syntax or permission reason. They continue
  through the existing bounded output-feedback path.

Preconditioner applies the shared parser to every reason and each REPLACE text.
It supplies its own permissions: supplied Memory IDs, current Original Update
IDs, supplied current executions and Group provenance inherited in Original
basis. Replay still denies Memory/Group/Check citations and limits execution
references to the current task pair plus diff. Sharing syntax does not merge
these permission sets. KEEP/REPLACE/WITHDRAW compilation is unchanged.

## Validation and configuration

The small fixture in `tests/skill_evolution/v29_2/fixtures/` contains all six
original response texts, their source hashes, and a reduced reference/transition
view. It validates output syntax and scope only, not archive authenticity or
causal interpretation. Tests also exercise malformed citations, denied references,
legacy parser isolation and a complete correction/read-only-reuse stage flow.

`experiments/configs/v29_2_docvqa_optimization160_references_v3.json` is the
current configuration. Only the Preconditioner and Replay prompt/contract version
fields differ from the original configuration. Actor settings, budgets and task
order are unchanged. The previous Replay-only configuration
`v29_2_docvqa_optimization160_replay_v3.json` is preserved as a historical file;
it is intentionally rejected by the new Preconditioner contract.

## Existing stopped campaign

The original campaign, configuration, six responses, failure receipts and request
budget are preserved. New source and contract versions intentionally do not
silently resume an old frozen campaign. This repair neither launches a new run
nor clears errors, rewrites implementation manifests, grants extra attempts, or
starts Test. Applying it to the stopped run requires a separately recorded
migration/revalidation policy; passing the six fixture outputs is not itself
authorization to select or publish one as the original round result.

Verification logs, protected-file hashes and copies of the modified pre-repair
source files are under `artifacts/verification/v29_2_replay_reference_boundary_20261103/`.

Validation on 2026-11-03: 334 v29.2/v29.1 regression tests passed, followed by
35 focused tests against the final parser source. All six original Replay
responses passed the output validator without text edits. The new configuration
passed `--validate-only`; 2,550 protected files matched their pre-repair hashes.
No model requests were made and no experiment was resumed.

The subsequent Preconditioner integration is recorded separately under
`artifacts/verification/v29_2_shared_reference_boundary_20261103/`.
It covers prose labels in all three actions' reasons and REPLACE text, syntax and
scope failures in both fields, module-specific Memory permissions, version gates,
and full correction/read-only-reuse stage flows. Diagnosis tests preserve its
ordinary prose and unprefixed current references while rejecting Memory,
Candidate, historical, unknown execution and unknown Group sources.

Shared-parser integration acceptance on 2026-11-03: 73 focused tests and all
342 v29.2/v29.1 regression tests passed. The source hashes stayed unchanged during
the full suite. The current configuration passed offline preflight; all 2,553
protected files, including Diagnosis source/Prompt and the stopped campaign,
matched their baseline hashes. No model calls, budget reset or resume occurred.
