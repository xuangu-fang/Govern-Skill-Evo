"""Pure Proposal validator and operator tests for Autonomous GSE v0.1."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace

import pytest

from src.skill_evolution.autonomous_gse_proposal import (
    BootstrapProposalOperator,
    IncrementalProposalOperator,
    LearnerRequest,
    ProposalContext,
    ProposalDecision,
    ProposalIntegrityError,
    validate_proposal_decision,
)


PARENT_SKILL = """# SuiteCRM Operational Skill
## Planning and navigation
- Open the relevant module before editing a record.
## Execution patterns
- Before a bulk update, identify the target records and request confirmation.
## Form entry and verification
- Verify the intended field value before submission.
## Error recovery and stopping
- Stop when a required record cannot be found."""

BOOTSTRAP_SKILL = """# SuiteCRM Operational Skill
## Planning and navigation
- Open the relevant module before editing a record.
## Execution patterns
- Ask before saving when the applicable policy requires permission.
## Form entry and verification
- Verify the intended field value before submission.
## Error recovery and stopping
- Stop when a required record cannot be found."""


def canonical_json_sha256(payload: dict) -> str:
    data = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256((value.rstrip() + "\n").encode("utf-8")).hexdigest()


def artifact(
    kind: str,
    version: str,
    marker: str,
    *,
    sha256: str | None = None,
) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": f"memory://proposal-test/{marker}",
        "sha256": sha256 or hashlib.sha256(marker.encode("utf-8")).hexdigest(),
    }


def experience(source_id: str, state: str) -> dict:
    successful = state in {"compliant_success", "violating_success"}
    compliant = state in {"compliant_success", "compliant_failure"}
    policy = {
        "policy_template_id": "ask_the_user",
        "category": "user_consent",
        "source": "user",
        "description": "Ask before saving.",
        "eval_type": "is_ask_the_user",
        "policy_spec": {"must_include": "Save"},
    }
    return {
        "source_id": source_id,
        "state": state,
        "goal": "Update a SuiteCRM record.",
        "actions": [{"step": 1, "url": "", "action": "click('Save')"}],
        "task_success": successful,
        "applicable_policies": [policy],
        "process_feedback": {
            "compliant": compliant,
            "violated_policies": [] if compliant else [policy],
        },
    }


def dataset(
    parent: dict,
    *,
    batch_id: str = "batch_001",
    successful: bool = True,
) -> dict:
    task_ids = list(range(1, 18))
    states = [
        "compliant_success" if successful else "compliant_failure",
        "violating_success" if successful else "violating_failure",
        *(["compliant_failure"] * 15),
    ]
    experiences = [
        experience(f"source_{index:03d}", state)
        for index, state in enumerate(states, start=1)
    ]
    counts = {
        state: sum(item["state"] == state for item in experiences)
        for state in (
            "violating_failure",
            "violating_success",
            "compliant_failure",
            "compliant_success",
        )
    }
    return {
        "schema_version": "governed_experience_0.1.0",
        "experience_count": 17,
        "state_counts": counts,
        "sources": [
            {
                "source_id": item["source_id"],
                "task_id": task_id,
                "path": f"memory://train/task_{task_id}.json",
                "sha256": f"{task_id:064x}",
            }
            for task_id, item in zip(task_ids, experiences, strict=True)
        ],
        "experiences": experiences,
        "lineage": {
            "batch_id": batch_id,
            "parent_sha256": parent["sha256"],
            "task_ids": task_ids,
        },
    }


def context(
    *,
    incremental: bool = False,
    successful: bool = True,
    step: int = 1,
) -> ProposalContext:
    parent = (
        artifact(
            "accepted_skill",
            "S1",
            "parent.md",
            sha256=text_sha256(PARENT_SKILL),
        )
        if incremental
        else artifact("no_skill", "S0", "S0.json")
    )
    batch_id = f"batch_{step:03d}"
    task_ids = tuple(range((step - 1) * 17 + 1, step * 17 + 1))
    governed_dataset = dataset(
        parent,
        batch_id=batch_id,
        successful=successful,
    )
    governed_dataset["lineage"]["task_ids"] = list(task_ids)
    for task_id, source in zip(
        task_ids, governed_dataset["sources"], strict=True
    ):
        source["task_id"] = task_id
    return ProposalContext(
        candidate_id=f"epoch_001_step_{step:03d}_candidate",
        batch_id=batch_id,
        task_ids=task_ids,
        parent=parent,
        parent_skill=PARENT_SKILL if incremental else None,
        experience=artifact(
            "governed_experience",
            "step_001",
            "experience.json",
            sha256=canonical_json_sha256(governed_dataset),
        ),
        governed_dataset=governed_dataset,
    )


def bootstrap_response(source_id: str = "source_001") -> str:
    clauses = [
        line[2:]
        for line in BOOTSTRAP_SKILL.splitlines()
        if line.startswith("- ")
    ]
    provenance = [
        {
            "clause": clause,
            "attribution": "preserve",
            "source_ids": [source_id],
            "policy_template_ids": [],
        }
        for clause in clauses
    ]
    return (
        f"<SKILL>\n{BOOTSTRAP_SKILL}\n</SKILL>\n"
        "<PROVENANCE_JSON>\n"
        f"{json.dumps(provenance)}\n"
        "</PROVENANCE_JSON>"
    )


def incremental_response(*, empty: bool = False) -> str:
    edits = []
    if not empty:
        edits = [
            {
                "operation": "replace",
                "section": "Execution patterns",
                "parent_clause": (
                    "Before a bulk update, identify the target records and "
                    "request confirmation."
                ),
                "new_clause": (
                    "Before a bulk update, identify the target records, "
                    "explain the change, and request confirmation."
                ),
                "attribution": "preserve",
                "source_ids": ["source_001"],
                "policy_template_ids": [],
            }
        ]
    return f"<EDITS_JSON>{json.dumps(edits)}</EDITS_JSON>"


def test_bootstrap_builds_valid_candidate_from_isolated_request() -> None:
    observed: list[LearnerRequest] = []

    def learner(request: LearnerRequest) -> str:
        observed.append(request)
        return bootstrap_response()

    current = context()
    decision = BootstrapProposalOperator().propose(current, learner)

    assert decision.status == "CANDIDATE"
    assert decision.learner_calls == 1
    assert decision.candidate is not None
    assert decision.candidate.skill == BOOTSTRAP_SKILL
    assert decision.candidate.candidate["version"] == current.candidate_id
    assert decision.candidate.provenance_payload["operator"] == "bootstrap"
    assert decision.candidate.provenance_payload["batch"]["task_ids"] == (
        list(current.task_ids)
    )
    assert len(observed) == 1
    assert set(observed[0].__dict__) == {
        "candidate_id",
        "operator",
        "parent_skill",
        "evidence",
    }
    assert observed[0].parent_skill is None
    assert {item["state"] for item in observed[0].evidence} == {
        "compliant_success",
        "violating_success",
    }
    validate_proposal_decision(current, decision, operator="bootstrap")


def test_incremental_applies_bounded_edit_to_exact_parent() -> None:
    observed: list[LearnerRequest] = []

    def learner(request: LearnerRequest) -> str:
        observed.append(request)
        return incremental_response()

    current = context(incremental=True)
    decision = IncrementalProposalOperator().propose(current, learner)

    assert decision.status == "CANDIDATE"
    assert decision.candidate is not None
    assert "explain the change" in decision.candidate.skill
    assert decision.candidate.provenance_payload["operator"] == "incremental"
    assert decision.candidate.provenance_payload["parent"] == current.parent
    assert observed[0].parent_skill == PARENT_SKILL
    validate_proposal_decision(current, decision, operator="incremental")


@pytest.mark.parametrize("step", [1, 2, 3])
def test_all_three_step_identities_are_supported(step: int) -> None:
    current = context(step=step)
    decision = BootstrapProposalOperator().propose(
        current, lambda _: bootstrap_response()
    )

    assert decision.status == "CANDIDATE"
    assert decision.candidate is not None
    assert decision.candidate.candidate["version"] == (
        f"epoch_001_step_{step:03d}_candidate"
    )


@pytest.mark.parametrize(
    ("operator", "incremental"),
    [(BootstrapProposalOperator(), False), (IncrementalProposalOperator(), True)],
)
def test_no_eligible_evidence_skips_learner(operator, incremental: bool) -> None:
    calls = 0

    def learner(_: LearnerRequest) -> str:
        nonlocal calls
        calls += 1
        raise AssertionError("Learner must not be called")

    decision = operator.propose(
        context(incremental=incremental, successful=False), learner
    )

    assert decision == ProposalDecision(
        status="NO_CANDIDATE",
        learner_calls=0,
        candidate=None,
        reason="no_eligible_evidence",
    )
    assert calls == 0


def test_incremental_empty_valid_patch_is_no_candidate() -> None:
    decision = IncrementalProposalOperator().propose(
        context(incremental=True),
        lambda _: incremental_response(empty=True),
    )

    assert decision.status == "NO_CANDIDATE"
    assert decision.learner_calls == 1
    assert decision.reason == "empty_valid_patch"


@pytest.mark.parametrize(
    ("operator", "current", "response"),
    [
        (BootstrapProposalOperator(), context(), "invalid"),
        (
            IncrementalProposalOperator(),
            context(incremental=True),
            "<EDITS_JSON>{}</EDITS_JSON>",
        ),
        (
            BootstrapProposalOperator(),
            context(),
            bootstrap_response("unknown_source"),
        ),
    ],
)
def test_invalid_learner_output_is_invalid_proposal(
    operator, current: ProposalContext, response: str
) -> None:
    decision = operator.propose(current, lambda _: response)

    assert decision.status == "INVALID_PROPOSAL"
    assert decision.learner_calls == 1
    assert decision.candidate is None


def test_operator_dispatch_is_enforced() -> None:
    with pytest.raises(ProposalIntegrityError, match="no_skill S0"):
        BootstrapProposalOperator().propose(
            context(incremental=True), lambda _: bootstrap_response()
        )
    with pytest.raises(ProposalIntegrityError, match="accepted_skill"):
        IncrementalProposalOperator().propose(
            context(), lambda _: incremental_response()
        )


def test_incremental_requires_exact_parent_skill_hash() -> None:
    current = context(incremental=True)
    current = replace(
        current,
        parent_skill=(current.parent_skill or "") + "\n- Unbound rule.",
    )

    with pytest.raises(ProposalIntegrityError, match="Parent Skill hash"):
        IncrementalProposalOperator().propose(
            current, lambda _: incremental_response()
        )


@pytest.mark.parametrize("drift", ["batch", "parent", "hash", "test_data"])
def test_context_integrity_failures_are_not_downgraded_to_invalid_proposal(
    drift: str,
) -> None:
    current = context()
    if drift == "batch":
        current.governed_dataset["lineage"]["batch_id"] = "batch_002"
    elif drift == "parent":
        current.governed_dataset["lineage"]["parent_sha256"] = "f" * 64
    elif drift == "hash":
        current.experience["sha256"] = "f" * 64
    else:
        current.governed_dataset["test"] = {"results": []}

    with pytest.raises(ProposalIntegrityError):
        BootstrapProposalOperator().propose(current, lambda _: bootstrap_response())


def test_validator_rejects_tampered_candidate_bundle() -> None:
    current = context()
    decision = BootstrapProposalOperator().propose(
        current, lambda _: bootstrap_response()
    )
    assert decision.candidate is not None
    decision.candidate.candidate["sha256"] = "f" * 64

    with pytest.raises(ProposalIntegrityError, match="Candidate Skill hash"):
        validate_proposal_decision(current, decision, operator="bootstrap")


def test_validator_recomputes_proposal_semantics() -> None:
    current = context()
    decision = BootstrapProposalOperator().propose(
        current, lambda _: bootstrap_response()
    )
    assert decision.candidate is not None
    decision.candidate.provenance_payload["proposal"]["rules"][0][
        "source_ids"
    ] = ["unknown_source"]
    decision.candidate.provenance["sha256"] = canonical_json_sha256(
        decision.candidate.provenance_payload
    )

    with pytest.raises(ProposalIntegrityError, match="semantics"):
        validate_proposal_decision(current, decision, operator="bootstrap")


def test_validator_requires_invalid_proposal_to_consume_learner_call() -> None:
    current = context()
    invalid = ProposalDecision(
        status="INVALID_PROPOSAL",
        learner_calls=0,
        candidate=None,
        reason="learner_output_invalid",
    )

    with pytest.raises(ProposalIntegrityError, match="one Learner call"):
        validate_proposal_decision(current, invalid, operator="bootstrap")


def test_same_fixture_input_produces_identical_decision() -> None:
    current = context(incremental=True)
    operator = IncrementalProposalOperator()

    first = operator.propose(current, lambda _: incremental_response())
    second = operator.propose(current, lambda _: incremental_response())

    assert first == second


def test_operator_does_not_mutate_context() -> None:
    current = context()
    original = copy.deepcopy(current)

    BootstrapProposalOperator().propose(current, lambda _: bootstrap_response())

    assert current == original
