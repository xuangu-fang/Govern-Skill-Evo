"""Pure governed Proposal operators for Autonomous GSE v0.1.

The operators accept an isolated current-batch context and an injected Learner
callable. They perform no API calls and no filesystem writes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from src.learners.stwebagentbench.generate_governed_s2 import (
    apply_edits,
    build_candidate_provenance,
    parse_edits,
    validate_edits,
)
from src.learners.stwebagentbench.generate_governed_skill import (
    validate_governed_provenance,
)
from src.learners.stwebagentbench.generate_skill import (
    parse_learner_output,
    validate_skill,
)


GOVERNED_EXPERIENCE_SCHEMA = "governed_experience_0.1.0"
PROPOSAL_PROVENANCE_SCHEMA = "autonomous_gse_proposal_provenance_0.1.0"
ELIGIBLE_STATES = {"compliant_success", "violating_success"}
ALL_STATES = {
    "violating_failure",
    "violating_success",
    "compliant_failure",
    "compliant_success",
}
PROPOSAL_STATUSES = {"CANDIDATE", "NO_CANDIDATE", "INVALID_PROPOSAL"}


class ProposalIntegrityError(ValueError):
    """Raised when frozen Proposal inputs or output lineage are inconsistent."""


@dataclass(frozen=True)
class ProposalContext:
    candidate_id: str
    batch_id: str
    task_ids: tuple[int, ...]
    parent: dict[str, Any]
    parent_skill: str | None
    experience: dict[str, Any]
    governed_dataset: dict[str, Any]


@dataclass(frozen=True)
class LearnerRequest:
    """The only data visible to a Proposal Learner."""

    candidate_id: str
    operator: str
    parent_skill: str | None
    evidence: tuple[dict[str, Any], ...]


Learner = Callable[[LearnerRequest], str]


@dataclass(frozen=True)
class CandidateBundle:
    candidate: dict[str, Any]
    skill: str
    provenance: dict[str, Any]
    provenance_payload: dict[str, Any]


@dataclass(frozen=True)
class ProposalDecision:
    status: str
    learner_calls: int
    candidate: CandidateBundle | None
    reason: str


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(
        (value.rstrip() + "\n").encode("utf-8")
    ).hexdigest()


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ProposalIntegrityError(f"{label} must be a SHA-256 digest.")
    return value


def _require_artifact(
    value: Any,
    label: str,
    *,
    kind: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    required = {"kind", "version", "path", "sha256"}
    if not isinstance(value, dict) or set(value) != required:
        raise ProposalIntegrityError(
            f"{label} must contain exactly {sorted(required)}."
        )
    for field in ("kind", "version", "path"):
        if not isinstance(value[field], str) or not value[field]:
            raise ProposalIntegrityError(f"{label}.{field} is invalid.")
    _require_sha256(value["sha256"], f"{label}.sha256")
    if kind is not None and value["kind"] != kind:
        raise ProposalIntegrityError(f"{label} must have kind {kind!r}.")
    if version is not None and value["version"] != version:
        raise ProposalIntegrityError(f"{label} must have version {version!r}.")
    return value


def _contains_forbidden_split_key(value: Any) -> bool:
    forbidden = {
        "selection",
        "test",
        "selection_data",
        "test_data",
        "selection_results",
        "test_results",
    }
    if isinstance(value, dict):
        if any(str(key).lower() in forbidden for key in value):
            return True
        return any(_contains_forbidden_split_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_split_key(item) for item in value)
    return False


def _validate_parent(context: ProposalContext, operator: str) -> None:
    parent = _require_artifact(context.parent, "Parent")
    if operator == "bootstrap":
        if parent["kind"] != "no_skill" or parent["version"] != "S0":
            raise ProposalIntegrityError("Bootstrap requires no_skill S0 Parent.")
        if context.parent_skill is not None:
            raise ProposalIntegrityError(
                "Bootstrap must not receive an injected Parent Skill."
            )
        return

    if parent["kind"] != "accepted_skill":
        raise ProposalIntegrityError(
            "Incremental requires an accepted_skill Parent."
        )
    version = parent["version"]
    try:
        number = int(version[1:]) if version.startswith("S") else 0
    except ValueError as error:
        raise ProposalIntegrityError(
            "Incremental Parent version must be S1 or later."
        ) from error
    if number < 1 or version != f"S{number}":
        raise ProposalIntegrityError(
            "Incremental Parent version must be S1 or later."
        )
    if not isinstance(context.parent_skill, str) or not context.parent_skill:
        raise ProposalIntegrityError("Incremental requires Parent Skill text.")
    if _text_sha256(context.parent_skill) != parent["sha256"]:
        raise ProposalIntegrityError("Parent Skill hash does not match Parent.")
    try:
        validate_skill(context.parent_skill)
    except ValueError as error:
        raise ProposalIntegrityError("Parent Skill is invalid.") from error


def _validate_dataset(context: ProposalContext) -> list[dict[str, Any]]:
    dataset = context.governed_dataset
    expected_keys = {
        "schema_version",
        "experience_count",
        "state_counts",
        "sources",
        "experiences",
        "lineage",
    }
    if not isinstance(dataset, dict) or set(dataset) != expected_keys:
        raise ProposalIntegrityError(
            "Governed dataset must contain only the current-batch contract."
        )
    if _contains_forbidden_split_key(dataset):
        raise ProposalIntegrityError(
            "Selection or Test data cannot enter Proposal input."
        )
    if dataset.get("schema_version") != GOVERNED_EXPERIENCE_SCHEMA:
        raise ProposalIntegrityError("Unexpected governed-experience schema.")
    if _json_sha256(dataset) != context.experience["sha256"]:
        raise ProposalIntegrityError("Governed Experience hash mismatch.")

    experiences = dataset.get("experiences")
    sources = dataset.get("sources")
    if not isinstance(experiences, list) or not isinstance(sources, list):
        raise ProposalIntegrityError("Experience and sources must be lists.")
    if (
        len(experiences) != 17
        or len(sources) != 17
        or dataset.get("experience_count") != 17
    ):
        raise ProposalIntegrityError(
            "Proposal input must contain exactly the current 17-Task batch."
        )

    lineage = dataset.get("lineage")
    if not isinstance(lineage, dict) or set(lineage) != {
        "batch_id",
        "parent_sha256",
        "task_ids",
    }:
        raise ProposalIntegrityError("Governed Experience lineage is incomplete.")
    if lineage["batch_id"] != context.batch_id:
        raise ProposalIntegrityError("Governed Experience batch lineage mismatch.")
    if lineage["parent_sha256"] != context.parent["sha256"]:
        raise ProposalIntegrityError("Governed Experience Parent lineage mismatch.")
    if lineage["task_ids"] != list(context.task_ids):
        raise ProposalIntegrityError("Governed Experience Task lineage mismatch.")

    source_ids: list[str] = []
    source_task_ids: list[int] = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {
            "source_id",
            "task_id",
            "path",
            "sha256",
        }:
            raise ProposalIntegrityError("Governed source is malformed.")
        if not isinstance(source["source_id"], str) or not source["source_id"]:
            raise ProposalIntegrityError("Governed source_id is invalid.")
        if not isinstance(source["task_id"], int):
            raise ProposalIntegrityError("Governed source task_id is invalid.")
        if not isinstance(source["path"], str) or not source["path"]:
            raise ProposalIntegrityError("Governed source path is invalid.")
        _require_sha256(source["sha256"], "Governed source sha256")
        source_ids.append(source["source_id"])
        source_task_ids.append(source["task_id"])
    if len(set(source_ids)) != 17 or source_task_ids != list(context.task_ids):
        raise ProposalIntegrityError("Governed source index is out of batch.")

    experience_ids: list[str] = []
    observed_counts = {state: 0 for state in ALL_STATES}
    for item in experiences:
        if not isinstance(item, dict):
            raise ProposalIntegrityError("Every governed experience must be an object.")
        source_id = item.get("source_id")
        state = item.get("state")
        task_success = item.get("task_success")
        feedback = item.get("process_feedback")
        if not isinstance(source_id, str) or not source_id:
            raise ProposalIntegrityError("Experience source_id is invalid.")
        if state not in ALL_STATES or not isinstance(task_success, bool):
            raise ProposalIntegrityError("Experience outcome state is invalid.")
        if not isinstance(feedback, dict):
            raise ProposalIntegrityError("Experience process feedback is invalid.")
        expected_success = state in ELIGIBLE_STATES
        if task_success is not expected_success:
            raise ProposalIntegrityError("Experience state and outcome disagree.")
        experience_ids.append(source_id)
        observed_counts[state] += 1
    if experience_ids != source_ids or len(set(experience_ids)) != 17:
        raise ProposalIntegrityError(
            "Governed source index does not match experiences."
        )
    if dataset.get("state_counts") != observed_counts:
        raise ProposalIntegrityError("Governed state_counts are inconsistent.")

    return [
        copy.deepcopy(item)
        for item in experiences
        if item["state"] in ELIGIBLE_STATES
    ]


def validate_proposal_context(
    context: ProposalContext,
    *,
    operator: str,
) -> tuple[dict[str, Any], ...]:
    """Validate frozen lineage and return isolated eligible evidence."""

    if not isinstance(context, ProposalContext):
        raise ProposalIntegrityError("Proposal Context is invalid.")
    if operator not in {"bootstrap", "incremental"}:
        raise ProposalIntegrityError("Unknown Proposal Operator.")
    candidate_match = re.fullmatch(
        r"epoch_001_step_00([1-3])_candidate", context.candidate_id
    )
    if candidate_match is None:
        raise ProposalIntegrityError("Candidate identity is invalid.")
    step = int(candidate_match.group(1))
    if context.batch_id != f"batch_{step:03d}":
        raise ProposalIntegrityError("Batch identity does not match Candidate.")
    if (
        not isinstance(context.task_ids, tuple)
        or len(context.task_ids) != 17
        or len(set(context.task_ids)) != 17
        or not all(isinstance(task_id, int) for task_id in context.task_ids)
    ):
        raise ProposalIntegrityError("Proposal requires 17 unique Task IDs.")
    _validate_parent(context, operator)
    _require_artifact(
        context.experience,
        "Governed Experience",
        kind="governed_experience",
    )
    return tuple(_validate_dataset(context))


def _candidate_artifact(candidate_id: str, skill: str) -> dict[str, str]:
    return {
        "kind": "candidate_skill",
        "version": candidate_id,
        "path": f"memory://autonomous_gse_proposal/{candidate_id}/skill.md",
        "sha256": _text_sha256(skill),
    }


def _provenance_artifact(
    candidate_id: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    return {
        "kind": "candidate_provenance",
        "version": candidate_id,
        "path": (
            f"memory://autonomous_gse_proposal/{candidate_id}/provenance.json"
        ),
        "sha256": _json_sha256(payload),
    }


def _candidate_bundle(
    context: ProposalContext,
    *,
    operator: str,
    skill: str,
    proposal_payload: dict[str, Any],
) -> CandidateBundle:
    candidate = _candidate_artifact(context.candidate_id, skill)
    provenance_payload = {
        "schema_version": PROPOSAL_PROVENANCE_SCHEMA,
        "candidate_id": context.candidate_id,
        "operator": operator,
        "parent": copy.deepcopy(context.parent),
        "batch": {
            "batch_id": context.batch_id,
            "task_ids": list(context.task_ids),
        },
        "experience": copy.deepcopy(context.experience),
        "candidate_skill_sha256": candidate["sha256"],
        "proposal": copy.deepcopy(proposal_payload),
    }
    provenance = _provenance_artifact(
        context.candidate_id, provenance_payload
    )
    return CandidateBundle(
        candidate=candidate,
        skill=skill.rstrip(),
        provenance=provenance,
        provenance_payload=provenance_payload,
    )


def validate_proposal_decision(
    context: ProposalContext,
    decision: ProposalDecision,
    *,
    operator: str,
) -> None:
    """Apply the unified status, hash, and lineage validation contract."""

    evidence = validate_proposal_context(context, operator=operator)
    if not isinstance(decision, ProposalDecision):
        raise ProposalIntegrityError("Proposal Decision is invalid.")
    if decision.status not in PROPOSAL_STATUSES:
        raise ProposalIntegrityError("Proposal status is invalid.")
    if decision.learner_calls not in {0, 1}:
        raise ProposalIntegrityError("A Step may call the Learner at most once.")
    if not isinstance(decision.reason, str) or not decision.reason:
        raise ProposalIntegrityError("Proposal reason is required.")
    if decision.status != "CANDIDATE":
        if decision.candidate is not None:
            raise ProposalIntegrityError(
                "Terminal non-Candidate status cannot contain a Candidate."
            )
        if decision.status == "INVALID_PROPOSAL" and (
            decision.learner_calls != 1
        ):
            raise ProposalIntegrityError(
                "INVALID_PROPOSAL must consume one Learner call."
            )
        return
    if decision.learner_calls != 1 or not isinstance(
        decision.candidate, CandidateBundle
    ):
        raise ProposalIntegrityError(
            "CANDIDATE requires one Learner call and one Candidate bundle."
        )

    bundle = decision.candidate
    candidate = _require_artifact(
        bundle.candidate,
        "Candidate",
        kind="candidate_skill",
        version=context.candidate_id,
    )
    provenance = _require_artifact(
        bundle.provenance,
        "Candidate provenance",
        kind="candidate_provenance",
        version=context.candidate_id,
    )
    if _text_sha256(bundle.skill) != candidate["sha256"]:
        raise ProposalIntegrityError("Candidate Skill hash mismatch.")
    if _json_sha256(bundle.provenance_payload) != provenance["sha256"]:
        raise ProposalIntegrityError("Candidate provenance hash mismatch.")
    expected = {
        "schema_version": PROPOSAL_PROVENANCE_SCHEMA,
        "candidate_id": context.candidate_id,
        "operator": operator,
        "parent": context.parent,
        "batch": {
            "batch_id": context.batch_id,
            "task_ids": list(context.task_ids),
        },
        "experience": context.experience,
        "candidate_skill_sha256": candidate["sha256"],
    }
    for key, value in expected.items():
        if bundle.provenance_payload.get(key) != value:
            raise ProposalIntegrityError(
                f"Candidate provenance {key} lineage mismatch."
            )
    if "proposal" not in bundle.provenance_payload:
        raise ProposalIntegrityError("Candidate proposal provenance is missing.")
    proposal = bundle.provenance_payload["proposal"]
    try:
        validate_skill(bundle.skill)
        if operator == "bootstrap":
            if not isinstance(proposal, dict) or set(proposal) != {
                "format",
                "rules",
            }:
                raise ValueError("Bootstrap proposal payload is malformed.")
            if proposal["format"] != "complete_skill_with_rule_provenance":
                raise ValueError("Bootstrap proposal format is invalid.")
            validate_governed_provenance(
                bundle.skill, proposal["rules"], list(evidence)
            )
        else:
            if not isinstance(proposal, dict):
                raise ValueError("Incremental proposal payload is malformed.")
            edits = proposal.get("edits")
            if not isinstance(edits, list) or not edits:
                raise ValueError("Incremental Candidate requires edits.")
            validate_edits(
                edits, context.parent_skill or "", list(evidence)
            )
            expected_skill = apply_edits(context.parent_skill or "", edits)
            if bundle.skill != expected_skill:
                raise ValueError("Incremental Candidate does not match edits.")
            expected_proposal = build_candidate_provenance(
                context.parent_skill or "", edits
            )
            if proposal != expected_proposal:
                raise ValueError("Incremental provenance does not match edits.")
    except (KeyError, TypeError, ValueError) as error:
        raise ProposalIntegrityError(
            "Candidate proposal semantics are invalid."
        ) from error


def _no_candidate(reason: str, learner_calls: int) -> ProposalDecision:
    return ProposalDecision(
        status="NO_CANDIDATE",
        learner_calls=learner_calls,
        candidate=None,
        reason=reason,
    )


def _invalid_proposal() -> ProposalDecision:
    return ProposalDecision(
        status="INVALID_PROPOSAL",
        learner_calls=1,
        candidate=None,
        reason="learner_output_invalid",
    )


class BootstrapProposalOperator:
    name = "bootstrap"

    def propose(
        self,
        context: ProposalContext,
        learner: Learner,
    ) -> ProposalDecision:
        evidence = validate_proposal_context(context, operator=self.name)
        if not evidence:
            return _no_candidate("no_eligible_evidence", 0)
        request = LearnerRequest(
            candidate_id=context.candidate_id,
            operator=self.name,
            parent_skill=None,
            evidence=copy.deepcopy(evidence),
        )
        response = learner(request)
        if not isinstance(response, str):
            return _invalid_proposal()
        try:
            skill, provenance = parse_learner_output(response)
            validate_skill(skill)
            validate_governed_provenance(skill, provenance, list(evidence))
        except (KeyError, TypeError, ValueError):
            return _invalid_proposal()

        bundle = _candidate_bundle(
            context,
            operator=self.name,
            skill=skill,
            proposal_payload={
                "format": "complete_skill_with_rule_provenance",
                "rules": copy.deepcopy(provenance),
            },
        )
        decision = ProposalDecision(
            status="CANDIDATE",
            learner_calls=1,
            candidate=bundle,
            reason="valid_bootstrap_candidate",
        )
        validate_proposal_decision(context, decision, operator=self.name)
        return decision


class IncrementalProposalOperator:
    name = "incremental"

    def propose(
        self,
        context: ProposalContext,
        learner: Learner,
    ) -> ProposalDecision:
        evidence = validate_proposal_context(context, operator=self.name)
        if not evidence:
            return _no_candidate("no_eligible_evidence", 0)
        request = LearnerRequest(
            candidate_id=context.candidate_id,
            operator=self.name,
            parent_skill=context.parent_skill,
            evidence=copy.deepcopy(evidence),
        )
        response = learner(request)
        if not isinstance(response, str):
            return _invalid_proposal()
        try:
            edits = parse_edits(response)
            validate_edits(edits, context.parent_skill or "", list(evidence))
            if not edits:
                return _no_candidate("empty_valid_patch", 1)
            skill = apply_edits(context.parent_skill or "", edits)
            provenance = build_candidate_provenance(
                context.parent_skill or "", edits
            )
        except (KeyError, TypeError, ValueError):
            return _invalid_proposal()

        bundle = _candidate_bundle(
            context,
            operator=self.name,
            skill=skill,
            proposal_payload=provenance,
        )
        decision = ProposalDecision(
            status="CANDIDATE",
            learner_calls=1,
            candidate=bundle,
            reason="valid_incremental_candidate",
        )
        validate_proposal_decision(context, decision, operator=self.name)
        return decision
