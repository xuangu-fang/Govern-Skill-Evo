"""Versioned, same-evidence update policies for a bounded frozen comparison.

Both proposal arms receive the same complete effective Memory view and emit the
existing compact increment contract. Their subsequent realization policy is shared.
This compares update instructions, not a numerical optimizer or proven causal effect.
Callers retain full inputs and raw responses for the existing validators/provenance.
"""

import json

from .compact_update import COMMON, DIAGNOSIS_SHAPE, EDITOR_SHAPE, FUSION_SHAPE
from .effective_memory import effective_consumption_payload
from .effective_update import EVIDENCE_BOUNDARY


PROFILE = "v22.conditional_update.v1"

DIAGNOSIS_RULES = """
Diagnosis: construct a serious initial Plan from the supplied current Parent runs,
without historical Memory. Distinguish a Skill-addressable gap from infrastructure,
stochastic execution or noncompliance with an already adequate base protocol. A
successful run may expose avoidable behavior, but success alone is not a defect.

Write intent as the desired behavior/outcome and common preservation obligations,
not a particular route for reaching it. Put proposed implementation strategies in
requirements, with visible triggers, scope, relevant continuation/recovery and stopping.
Distinguish what a task asks from how this trace happened to achieve it: for example,
delivery to a named destination is conditional on a task actually requiring delivery,
not a universal final phase inferred from one execution. Do not encode instance answers.
Available commands describe executable options, not which option satisfies the goal.
Unknown state remains unknown; use only the actor's available observation and short
history. Never require a new global notebook or infer completion from an action's name.

Each requirement needs supplied current sources. Retain useful behavior when proposing
a change. Use a few watch questions that can affect the decision, including important
counterexamples or preservation. Do not weaken the initial draft to help a later arm.
revise requires a nonempty Plan; no_change and need_evidence require plan=null and a
specific reason. A processing failure is not a semantic stop. Use only the shown fields.
"""

PROPOSAL_CONTRACT = """
Revise the same frozen initial Plan using the supplied current evidence and effective
historical Memory. Its intent is fixed and means the desired goal and common obligations;
do not silently reinterpret it as a different goal or as a mandatory implementation.
Historical claims are fallible, scoped evidence. Consider their actual observations,
comparison conditions, counterexamples and remaining limits. Do not promote absent
events into impossibility or a successful bundle into a proved isolated editing effect.
Correcting a factual count or description is not itself evidence of an editing effect.

Identity is legitimate: if the existing draft already handles the relevant issue, or
the history does not support a useful applicable revision, return changes=[] with a
specific reason. Unproven benefit alone does not forbid bounded exploratory construction;
state uncertainty in reason/watch rather than claiming established effectiveness.
Do not force a change, add unrelated repairs or assume history must apply to every task.

Emit only increments in the existing shape. Each from names existing requirements once.
replace rewrites COMPLETE retained obligations in to, including conditions, recovery,
dependencies and stopping; it cannot consist of a new phrase plus 'others unchanged'.
Unchanged requirements are inherited. The program assembles inherited and added basis.
replace requires nonempty to; withdraw/hold require to=[]. hold requires needs_revision.
Use needs_revision for a contradictory target or genuinely unavailable necessary
capability. Every affected watch needs an explicit destination in watch_changes;
retain important adverse questions. New requirements need a watch destination or a
blocking open. watch_changes.from=[] adds a question. Original open persists; add only
actual construction blockers. Cite current source keys or unchanged Memory effect IDs.
Use the existing reason fields for concise rationale, not extra analysis or audit fields.
"""

DIRECT_RULES = """
Direct history-assisted revision: review the current draft against current execution
feedback and relevant earlier attempts. Use that information to produce the best
reusable revision you can, retaining useful parts and correcting supported weaknesses.
You may change, coordinate or leave requirements unchanged as appropriate. Explain the
substantive choices briefly, accounting for historical limitations and conflicting
evidence. This is an ordinary competent revision task; no particular transformation
or nonidentity result is required.
"""

CONDITIONED_RULES = """
Construct the actual update by using what the evidence says about update effects.
Within this one response, locate the specific decision in the draft that an applicable
historical response bears on. Compare the relevant visible conditions and actual
Parent/Skill dependencies; topic similarity is not enough. If the draft already handles
that decision, keep it unless another supported mismatch remains.

Adjust direction when another executable strategy better targets the desired behavior;
adjust scale by changing an obligation's strength or visible scope; adjust interaction
by coordinating dependent, redundant or conflicting requirements. Choose only the
adjustments supported for this draft, not one of each. In change.reason connect the
observed response and its limits to the particular resulting update decision.

Before relaxing an obligation because an alternative succeeded, compare the states
where that alternative worked with states where the earlier route or continuation was
still needed. A success supports relaxation only in the observed applicable conditions.
It does not prove the omitted action is unnecessary in other states. Preserve the
known completion/recovery path outside that support, or return needs_revision if the
necessary distinction cannot be expressed using available actor information. An
untested extension may be proposed as such, but cannot erase known counterexamples.

For example, completion after an action in one visible configuration does not imply
that the same action completes the task in another configuration. Current done/goal
feedback, available actions and visibly held versus placed objects may distinguish
continuation branches when the environment exposes them. Do not assume such signals
exist or infer done from an action name. When no completion is reported, preserve the
applicable next step/recovery rather than treating the successful alternative as a
universal stopping rule. Never hard-code the observed alternative as a new mandatory
sequence. These are general state-dependent decisions, not task-instance templates.

Preserve the goal while replacing its strategy. When several requirements jointly
define a usable route, revise their affected conditions and ordering together without
dropping local obligations. Observation count corrections, absent side effects and
repeated noncompliance alone do not justify stronger or broader rules. Keep uncertainty
about attribution and transfer, and retain an execution question that can challenge
the proposed decision. Do not output a checklist, extra matrix or self-certification.
"""

REALIZATION_RULES = """
Editor: faithfully realize the supplied effective Plan as a complete reusable English
Skill. Both update policies use this same Editor. All supplied effective Memory remains
available for context and limitations; it does not authorize another strategy choice,
broader condition, stronger obligation or reinterpretation of the goal. Realize the
chosen visible triggers, scope, ordering, local/common preservation, continuation,
recovery and stopping. Do not turn an unknown state into false or an observed path into
a universal requirement. Equivalent wording and placement are allowed.

candidate requires full candidate_text and no unresolved issues. no_change requires
candidate_text=null and maps all requirements to existing Parent text. needs_revision
requires candidate_text=null and a few concrete actionable issues; do not publish a
partial Skill when the requirements conflict or need unavailable actor information.
Unproven behavioral benefit alone is not a realization blocker.

Map all active requirements with short exact Parent/Candidate excerpts. Shared excerpts
may cover related requirements; several excerpts may realize one requirement. Use
Candidate text for added/modified obligations and Parent text for deletions/unchanged
obligations. A Parent excerpt cannot prove preservation if Candidate drops that text's
obligation. Account for substantive edits without character coverage or proof tables.
The program automatically inherits plan.watch: output watch=[] unless you discover a
NEW important implementation uncertainty. Never copy inherited watch entries. Empty
issues means no exception reported, not semantic equivalence proved. The runner checks
routing and text references, not the truth of the semantic judgment. Use only shown fields.
"""


def _messages(payload, instructions, shape, *, project=True):
    view = effective_consumption_payload(payload) if project else payload
    return [{"role": "system", "content": f"Profile: {PROFILE}\n" + COMMON
             + EVIDENCE_BOUNDARY + instructions
             + "\nOutput shape:\n" + json.dumps(shape, ensure_ascii=False)},
            {"role": "user", "content": json.dumps(view, ensure_ascii=False, separators=(",", ":"))}]


def diagnosis_messages_conditional(payload):
    """Current-only serious draft; output still uses validate_diagnosis."""
    return _messages(payload, DIAGNOSIS_RULES, DIAGNOSIS_SHAPE, project=False)


def proposal_messages(payload, mode):
    """Both arms receive exactly the same view; only update instructions differ."""
    if mode not in ("direct", "conditioned"):
        raise ValueError("mode must be direct or conditioned")
    rules = DIRECT_RULES if mode == "direct" else CONDITIONED_RULES
    return _messages(payload, PROPOSAL_CONTRACT + rules, FUSION_SHAPE)


def realization_messages(payload):
    """Shared Editor policy with all Memory; no arm-specific filtering or rules."""
    return _messages(payload, REALIZATION_RULES, EDITOR_SHAPE)
