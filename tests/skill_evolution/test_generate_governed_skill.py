"""Tests for the verifier-guided governed Skill generator."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from src.learners.stwebagentbench.generate_governed_skill import (
    EXPECTED_EXPERIENCE_COUNT,
    build_prompts,
    load_governed_dataset,
    select_learning_evidence,
    validate_governed_provenance,
)
from src.skill_evolution.governed_experience import SCHEMA_VERSION
from src.skill_evolution.two_dimensional_gate import OutcomeState


def make_policy(template_id: str) -> dict:
    return {
        "policy_template_id": template_id,
        "category": "user_consent",
        "source": "user",
        "description": "Ask before saving.",
        "eval_type": "is_ask_the_user",
        "policy_spec": {"must_include": "Save"},
    }


def make_experience(
    source_id: str,
    state: OutcomeState,
) -> dict:
    task_success = state in {
        OutcomeState.VIOLATING_SUCCESS,
        OutcomeState.COMPLIANT_SUCCESS,
    }
    compliant = state in {
        OutcomeState.COMPLIANT_FAILURE,
        OutcomeState.COMPLIANT_SUCCESS,
    }
    policy = make_policy("ask_the_user")
    return {
        "source_id": source_id,
        "state": state.value,
        "goal": "Update a SuiteCRM record.",
        "actions": [
            {
                "step": 1,
                "url": "http://localhost:8080/#/leads",
                "action": "click('Save')",
                "action_error": "",
            }
        ],
        "task_success": task_success,
        "applicable_policies": [policy],
        "process_feedback": {
            "compliant": compliant,
            "violated_policies": [] if compliant else [policy],
        },
    }


def make_dataset() -> dict:
    states = (
        [OutcomeState.VIOLATING_FAILURE] * 22
        + [OutcomeState.VIOLATING_SUCCESS] * 11
        + [OutcomeState.COMPLIANT_FAILURE] * 8
        + [OutcomeState.COMPLIANT_SUCCESS] * 10
    )
    assert len(states) == EXPECTED_EXPERIENCE_COUNT

    experiences = [
        make_experience(f"source_{index:03d}", state)
        for index, state in enumerate(states, start=1)
    ]
    counts = Counter(item["state"] for item in experiences)
    return {
        "schema_version": SCHEMA_VERSION,
        "experience_count": len(experiences),
        "state_counts": {
            state.value: counts[state.value]
            for state in OutcomeState
        },
        "sources": [
            {
                "source_id": item["source_id"],
                "task_id": index,
                "path": f"task_{index}/trajectory.json",
                "sha256": "0" * 64,
            }
            for index, item in enumerate(experiences, start=1)
        ],
        "experiences": experiences,
    }


def write_dataset(tmp_path: Path, dataset: dict) -> Path:
    path = tmp_path / "governed_experiences.json"
    path.write_text(json.dumps(dataset), encoding="utf-8")
    return path


def test_selects_all_successful_cs_and_vs_experience(
    tmp_path: Path,
) -> None:
    dataset = load_governed_dataset(
        write_dataset(tmp_path, make_dataset())
    )

    evidence, source_records = select_learning_evidence(dataset)

    assert len(evidence) == 21
    assert Counter(item["state"] for item in evidence) == {
        "violating_success": 11,
        "compliant_success": 10,
    }
    assert [item["source_id"] for item in evidence] == [
        item["source_id"] for item in source_records
    ]


def test_rejects_sensitive_data_before_building_prompt(
    tmp_path: Path,
) -> None:
    dataset = make_dataset()
    dataset["experiences"][0]["applicable_policies"][0][
        "policy_spec"
    ]["sensitive_data"] = "crm_service_pw!"

    with pytest.raises(ValueError, match="must not contain sensitive_data"):
        load_governed_dataset(write_dataset(tmp_path, dataset))


def test_prompt_requires_behavior_attribution_without_step_claims() -> None:
    experience = make_experience(
        "source_001",
        OutcomeState.VIOLATING_SUCCESS,
    )

    system_prompt, user_prompt = build_prompts([experience])

    assert "behavior attribution" in system_prompt
    assert "do not discard the whole" in system_prompt
    assert "Do not claim a violation occurred at a particular action step" in (
        system_prompt
    )
    assert '"state": "violating_success"' in user_prompt
    assert '"policy_template_id": "ask_the_user"' in user_prompt


def test_validates_preserve_and_repair_provenance() -> None:
    evidence = [
        make_experience(
            "source_001",
            OutcomeState.VIOLATING_SUCCESS,
        )
    ]
    skill = """# SuiteCRM Operational Skill
## Planning and navigation
- Open the relevant module before editing a record.
## Execution patterns
- Before saving, ask for permission in a message that explicitly names Save.
## Form entry and verification
- Verify the intended field value before submission.
## Error recovery and stopping
- Stop when a required record cannot be found."""
    provenance = [
        {
            "clause": "Open the relevant module before editing a record.",
            "attribution": "preserve",
            "source_ids": ["source_001"],
            "policy_template_ids": [],
        },
        {
            "clause": (
                "Before saving, ask for permission in a message that "
                "explicitly names Save."
            ),
            "attribution": "repair",
            "source_ids": ["source_001"],
            "policy_template_ids": ["ask_the_user"],
        },
        {
            "clause": "Verify the intended field value before submission.",
            "attribution": "preserve",
            "source_ids": ["source_001"],
            "policy_template_ids": [],
        },
        {
            "clause": "Stop when a required record cannot be found.",
            "attribution": "preserve",
            "source_ids": ["source_001"],
            "policy_template_ids": [],
        },
    ]

    validate_governed_provenance(skill, provenance, evidence)


def test_rejects_repair_not_supported_by_violated_policy() -> None:
    evidence = [
        make_experience(
            "source_001",
            OutcomeState.COMPLIANT_SUCCESS,
        )
    ]
    skill = """# SuiteCRM Operational Skill
## Planning and navigation
- Ask before saving.
## Execution patterns
## Form entry and verification
## Error recovery and stopping"""
    provenance = [
        {
            "clause": "Ask before saving.",
            "attribution": "repair",
            "source_ids": ["source_001"],
            "policy_template_ids": ["ask_the_user"],
        }
    ]

    with pytest.raises(ValueError, match="not violated by its sources"):
        validate_governed_provenance(skill, provenance, evidence)
