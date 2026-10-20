"""Decision-focused Fusion/Editor prompts over the effective Memory consumption view.

Inputs are full frozen payloads. Only messages use the projected view; callers keep
the original payload for apply_fusion/validate_editor and provenance. Output shapes
remain the compact update contract, with no additional diagnostic certification.
"""

from copy import deepcopy
import json

from .compact_update import COMMON, EDITOR_SHAPE, FUSION_SHAPE
from .effective_memory import effective_consumption_payload


PROFILE = "v22.effective_update.v1"

EVIDENCE_BOUNDARY = """
Use the effective Memory view as fallible scoped knowledge, not as a command.
Current runs/sources describe current evidence. H1::/H2:: references and historical
snapshots belong to their historical contexts, even if task or step aliases match.
Use only current source keys or unchanged effect IDs in output basis. Historical
snapshots are retained for provenance; corrected or superseded assertions are not
active support. Preserve applicable limits and counterexamples when consuming a claim.
Do not reconstruct omitted historical action lists or treat factual counters as meaning.
"""

FUSION_RULES = """
Construct an update decision from the same frozen initial Plan and supplied evidence.
Perform this reasoning within this one response; do not emit a per-rule checklist:

1. Align an applicable response belief with a SPECIFIC decision in the current
   requirement: its visible trigger, chosen strategy, obligation/range, or coordination
   with another requirement. Check actual Parent dependencies, execution conditions,
   corrected observations and remaining limits. Similar wording alone is not alignment.
2. Check whether the initial Plan already handles that issue. If so, retain it unless
   another applicable observation identifies a remaining problem. An already suitable
   draft is not evidence that Memory is useless, and a longer reason is not a transform.
3. When a concrete remaining mismatch warrants action, make a bounded decision:
   change direction/ordering to an executable alternative; change the obligation's
   visible conditions, strength or scope; or coordinate overlapping/dependent choices.
   State in the existing change.reason how the relevant response supports that specific
   difference. Unchanged requirements are inherited; do not rewrite unrelated rules.
4. Retain or revise the important observation questions, including what would falsify
   this decision and preservation that could be harmed. These are execution questions,
   not certificates that a proposed change will work.

Unidentified isolated causal effects do NOT automatically prohibit bounded exploration.
When mechanism evidence and visible conditions motivate an exploratory revision, label
it as an unverified construction in reason and retain an appropriate watch. Do not claim
causal benefit, necessity, synergy or generalization from a bundle comparison.
A successful alternative path can challenge an overly strong necessity claim only in
the applicable observed conditions. It may justify relaxing/conditioning that obligation
while preserving the goal and valid safeguards; it does not license hard-coding the
alternative as a new universal mandatory sequence. Do not discard an existing obligation
merely because it was absent in a noncomparable or unverified trace.
Correcting an event count or factual description is not evidence of an editing effect.
It does not by itself justify strengthening an action filter, adding mandatory checks,
or assigning a difference to one edit. Absence of side effects does not justify expansion.
Repeated noncompliance does not by itself justify a stronger command.

Identity is legitimate: use changes=[] and give a concrete reason identifying how the
initial requirements already cover the relevant decision, or which applicability or
mechanism gap prevents a defensible increment. A generic 'causality is unproven' is not
enough when the evidence supports a more specific decision. Do not force any requirement
to change, invent missing observations, or optimize for producing a nonidentity result.

Keep intent fixed. Each change.from names existing requirements once; replace rewrites
their COMPLETE valid obligations in change.to, including conditions, local preservation,
fallback/recovery, dependencies and stopping. Do not replace a whole group with only the
new phrase or 'others unchanged'. The program adds inherited and change basis references.
replace requires nonempty to; withdraw/hold require to=[]. hold requires needs_revision.
An unresolved target, contradictory requirement or unavailable necessary capability
returns needs_revision; unproved behavioral benefit alone belongs in watch/limits.
Every affected watch has an explicit destination in watch_changes; retain adverse
questions and give each changed requirement an observation destination or blocking open.
New watch questions may use from=[]. Original open persists; open adds actual blockers.
Only return the existing compact output shape. No new evidence matrix or self-rating.
"""

EDITOR_RULES = """
Realize the supplied effective Plan faithfully, including jointly conditioned requirements.
The provided Memory subset explains requirements already chosen; it is not permission to
choose another strategy or reinstate a superseded historical assertion. Do not independently
strengthen an obligation, broaden a condition, turn unknown into false, or encode a
successful observed path as mandatory unless the effective Plan actually requires it.
Preserve intent, local valid obligations, observable conditions, recovery, dependencies
and stopping in the resulting text. Equivalent wording and placement are allowed.
Substantive conflicts or unavailable capabilities need needs_revision with a small number
of important, actionable issues; do not silently omit the affected requirement or publish
a partial Candidate. Unverified behavioral predictions alone are not construction blockers.

candidate returns full reusable English Skill and no unresolved issues. no_change returns
candidate_text=null and maps all active requirements to existing Parent text. needs_revision
returns candidate_text=null and concrete issues; mappings may be empty. Group-level exact
excerpts may serve several requirements, and a requirement may use multiple excerpts.
Use Candidate text for additions/changes and Parent text for deletions/unchanged obligations;
do not claim an obligation is preserved by mapping Parent text that the Candidate drops.
Account for meaningful changes without character coverage or six-dimensional self-proof.
Empty issues means no exception reported, not semantic equivalence established. Inherit
existing watch questions and add only new important implementation uncertainty. The runner
validates references and text locations, not the correctness of your semantic judgment.
"""


def _messages(payload, instructions, shape):
    view = effective_consumption_payload(payload)
    return [{"role": "system", "content": COMMON + EVIDENCE_BOUNDARY + instructions
             + "\nOutput shape:\n" + json.dumps(shape, ensure_ascii=False)},
            {"role": "user", "content": json.dumps(view, ensure_ascii=False, separators=(",", ":"))}]


def fusion_messages_effective(payload):
    """Read a full frozen input; emit the same compact Fusion increment contract."""
    return _messages(payload, FUSION_RULES, FUSION_SHAPE)


def editor_messages_effective(payload):
    """Present only effects cited by the effective requirements, with their limits."""
    selected = deepcopy(payload)
    used = {ref for row in payload["plan"]["requirements"] for ref in row["basis"]}
    selected["memory"] = [effect for effect in selected.get("memory", []) if effect["id"] in used]
    return _messages(selected, EDITOR_RULES, EDITOR_SHAPE)
