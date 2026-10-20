"""Same-call Editor requirement checks, with explicit structural limits.

The program binds all requirements and checks declared departures/capabilities.
Whether natural-language text is equivalent remains the Editor's fallible judgment;
neither these checks nor a later successful episode prove semantic preservation.
"""

from copy import deepcopy

from src.adapters.alfworld.skill_runtime import object_digest
from .diagnosis_editor import (
    EDITOR_INSTRUCTIONS, EDITOR_SCHEMA, EDITOR_SHAPE, _array, _messages,
    _object, _strings, _text, _validate_editor_v0, validate_diagnosis,
)


EDITOR_SCHEMA_V1 = "v22.editor.v1"
ASPECTS = ("trigger", "strategy", "scope", "preserve", "interactions", "capabilities")
STATUSES = ("faithful", "expression_only", "needs_revision")
ACTOR_CAPABILITIES = {
    "current_observation": True,
    "current_admissible_commands": True,
    "task_description": True,
    "recent_two_preaction_pairs": True,
    "full_episode_history": False,
    "persistent_notes": False,
    "hidden_environment_state": False,
}

EDITOR_SHAPE_V1 = deepcopy(EDITOR_SHAPE)
EDITOR_SHAPE_V1.update({
    "schema_version": EDITOR_SCHEMA_V1,
    "requirements_sha256": "Copy preservation_contract.requirements_sha256 exactly",
    "requirement_checks": [{
        "proposal_id": "p1",
        "status": "faithful | expression_only | needs_revision",
        "required_capabilities": ["current_observation"],
        "checks": [{
            "aspect": "trigger | strategy | scope | preserve | interactions | capabilities",
            "status": "faithful | expression_only | needs_revision",
            "excerpts": ["Exact short Candidate/Parent text supporting this aspect"],
            "reason": "Brief comparison with every source assigned to this aspect",
        }],
    }],
})

PRESERVATION_INSTRUCTIONS = """
This is Editor v1: perform requirement-preservation checks IN THIS SAME response,
not in an extra review call. The preservation_contract maps each proposal/aspect
to exact JSON-pointer sources in effective_requirements; inspect ALL those sources.
Copy its requirements_sha256 exactly. Do not repeat the requirements themselves.
Return one requirement_checks row per proposal, with exactly six checks: trigger,
strategy, scope, preserve, interactions, capabilities. Check literal resulting
text against requirements, not your intended explanation. Preserve includes ALL
proposal-specific and global preserved behavior. Interactions includes the full
relation and handling of every supplied interaction involving this proposal.
Use faithful when no departure is identified; expression_only only for wording or
organization changes that keep conditions, order, scope, obligations and dependencies
equivalent. Briefly explain the equivalence, including unknown-condition handling.
Use needs_revision for a substantive departure, missing information, or unsupported
capability. Replacing a history-dependent condition with an unrestricted action,
replacing an actual state condition with absence of a current observation, or
silently dropping a condition is NOT an expression-only change. Recent two pairs are not complete visit
history; learner traces do not add actor memory. A fixed Skill cannot create a
mutable notebook. State exactly which supplied actor_capabilities implementation
requires, including unavailable capabilities when the requirements need them.
For candidate/no_change, every check must cite at least one EXACT short excerpt of
the actual Candidate/Parent, except interactions with no supplied interactions,
which has empty excerpts and a brief 'none supplied' explanation. A quoted excerpt
can support several aspects. These short excerpts supplement full clause mappings.
For needs_revision, release NO Candidate and use empty excerpts in all checks;
faithful/expression_only there mean no identified departure in that aspect of the
proposed construction, not a claim that an absent executable text was verified.
Any aspect needing revision makes its proposal status needs_revision, makes the
whole Editor decision needs_revision, and requires actionable upstream_feedback
for that proposal. Every feedback proposal must have a needs_revision check. Other
proposal rows are still required so unsatisfied requirements cannot disappear.
If no check needs revision, aggregate expression_only when any check has that
status, otherwise faithful. Unsupported required capabilities force the capabilities
check to needs_revision. Do not declare unsupported dependencies available just to
release a candidate. A passing self-check is uncertain model judgment, not proof of
semantic equivalence, environment success, or generalization. Keep reasons concise.
"""


def preservation_contract(parent_skill, diagnosis, evidence):
    """Bind immutable requirements and exact obligation sources without an LLM."""
    validate_diagnosis(diagnosis, parent_skill, evidence)
    if diagnosis["decision"] != "revise":
        raise ValueError("editor: Diagnosis stop outcome skips the Editor call")
    rows = []
    for index, proposal in enumerate(diagnosis["proposals"]):
        prefix = f"/proposals/{index}"
        sources = {aspect: [prefix + "/" + aspect] for aspect in ASPECTS[:3]}
        sources["preserve"] = [
            *[f"{prefix}/preserve/{i}" for i in range(len(proposal["preserve"]))],
            *[f"/preserve/{i}/behavior" for i in range(len(diagnosis["preserve"]))],
        ]
        sources["interactions"] = [
            f"/interactions/{i}/{field}"
            for i, interaction in enumerate(diagnosis["interactions"])
            if proposal["id"] in interaction["proposal_ids"]
            for field in ("relation", "handling")
        ]
        sources["capabilities"] = ["preservation_contract.actor_capabilities"]
        rows.append({"proposal_id": proposal["id"], "aspect_sources": sources})
    return {
        "schema_version": "v22.editor_preservation_contract.v1",
        "requirements_sha256": object_digest(diagnosis),
        "parent_skill_sha256": object_digest(parent_skill),
        "evidence_sha256": object_digest(evidence),
        "actor_capabilities": dict(ACTOR_CAPABILITIES),
        "proposal_sources": rows,
        "limits": "Source coverage and declared dependencies are checked by code; semantic preservation is fallible model judgment.",
    }


def editor_messages_v1(parent_skill, diagnosis, evidence):
    contract = preservation_contract(parent_skill, diagnosis, evidence)
    return _messages(EDITOR_INSTRUCTIONS + PRESERVATION_INSTRUCTIONS, EDITOR_SHAPE_V1, {
        "parent_skill": parent_skill,
        "effective_requirements": diagnosis,
        "train_evidence": evidence,
        "preservation_contract": contract,
    })


def validate_editor_v1(value, parent_skill, diagnosis, evidence):
    contract = preservation_contract(parent_skill, diagnosis, evidence)
    _object(value, EDITOR_SHAPE_V1, "editor")
    if value["schema_version"] != EDITOR_SCHEMA_V1:
        raise ValueError("editor: unsupported schema")
    if value["requirements_sha256"] != contract["requirements_sha256"]:
        raise ValueError("editor: requirement identity mismatch")
    # Reuse the unchanged v0 checks for mappings, feedback, literal text and scope.
    base = {key: value[key] for key in EDITOR_SHAPE}
    base["schema_version"] = EDITOR_SCHEMA
    _validate_editor_v0(base, parent_skill, diagnosis, evidence)
    sources = {row["proposal_id"]: row["aspect_sources"] for row in contract["proposal_sources"]}
    seen, needs_revision = set(), set()
    text = value["candidate_text"] if value["decision"] == "candidate" else (parent_skill.get("text") or "")
    for row in _array(value["requirement_checks"], "requirement_checks", nonempty=True):
        _object(row, EDITOR_SHAPE_V1["requirement_checks"][0], "requirement_checks")
        proposal_id = _text(row["proposal_id"], "requirement_checks.proposal_id")
        if proposal_id not in sources or proposal_id in seen:
            raise ValueError("requirement_checks: unknown or duplicate proposal")
        seen.add(proposal_id)
        capabilities = _strings(row["required_capabilities"], "required_capabilities", nonempty=True)
        if len(capabilities) != len(set(capabilities)) or not set(capabilities) <= ACTOR_CAPABILITIES.keys():
            raise ValueError("requirement_checks: unknown or duplicate capability")
        checks = {}
        for check in _array(row["checks"], "requirement_checks.checks", nonempty=True):
            _object(check, EDITOR_SHAPE_V1["requirement_checks"][0]["checks"][0], "requirement_checks.checks")
            aspect = _text(check["aspect"], "requirement_checks.aspect")
            if aspect not in ASPECTS or aspect in checks:
                raise ValueError("requirement_checks: unknown or duplicate aspect")
            checks[aspect] = check
            if check["status"] not in STATUSES:
                raise ValueError("requirement_checks: invalid status")
            _text(check["reason"], "requirement_checks.reason")
            excerpts = _strings(check["excerpts"], "requirement_checks.excerpts")
            if value["decision"] == "needs_revision":
                if excerpts:
                    raise ValueError("requirement_checks: no released text exists for revision excerpts")
            elif aspect == "interactions" and not sources[proposal_id][aspect]:
                if excerpts:
                    raise ValueError("requirement_checks: no interaction was supplied")
            elif not excerpts or any(excerpt not in text for excerpt in excerpts):
                raise ValueError("requirement_checks: missing or absent actual-text excerpt")
        if set(checks) != set(ASPECTS):
            raise ValueError("requirement_checks: every aspect must be checked exactly once")
        if any(not ACTOR_CAPABILITIES[capability] for capability in capabilities):
            if checks["capabilities"]["status"] != "needs_revision":
                raise ValueError("requirement_checks: unavailable capability requires revision")
        statuses = {check["status"] for check in checks.values()}
        expected = "needs_revision" if "needs_revision" in statuses else ("expression_only" if "expression_only" in statuses else "faithful")
        if row["status"] != expected:
            raise ValueError("requirement_checks: aggregate status disagrees with aspect checks")
        if expected == "needs_revision":
            needs_revision.add(proposal_id)
    if seen != set(sources):
        raise ValueError("requirement_checks: every proposal must be checked")
    feedback_ids = {p for row in value["upstream_feedback"] for p in row["proposal_ids"]}
    if value["decision"] == "needs_revision":
        if not needs_revision or feedback_ids != needs_revision:
            raise ValueError("requirement_checks: revision checks and upstream feedback must match")
    elif needs_revision:
        raise ValueError("requirement_checks: substantive departure blocks release")
    return value
