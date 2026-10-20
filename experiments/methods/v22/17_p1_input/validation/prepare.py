"""Prepare all fixed P1 probes without network calls or ALFWorld execution.

The parent controller must freeze these files and the tested revision before it
dispatches any request. This script deliberately has no execution option.
"""
import json
from pathlib import Path

from fixtures import (OUT, V3, V4, GROUP_PROMPT, build_cases, source_manifest,
                      baseline_audit, grouped_update, object_digest)
from src.skill_evolution.v22.grouped_representation import grouping_messages
from src.skill_evolution.v22.p1_input import decode, VIEW_SCHEMA
from src.skill_evolution.v22.effective_memory import effective_consumption_payload


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    assert not (OUT / "protocol.json").exists(), "Preparation already exists; do not overwrite frozen inputs."
    cases = build_cases()
    entries = []
    for case in cases:
        stage, profile, payload = case["stage"], case["profile"], case["payload"]
        messages = (grouping_messages(payload, GROUP_PROMPT.read_text(), profile=profile)
                    if stage == "classification" else grouped_update.grouped_messages(stage, payload))
        consumed = json.loads(messages[1]["content"])
        expected = payload if stage in ("classification", "diagnosis") else effective_consumption_payload(payload)
        if profile == V4:
            assert consumed["view"] == VIEW_SCHEMA
            assert decode(consumed) == expected
        else:
            assert consumed == expected
        directory = OUT / "cases" / case["id"]
        save(directory / "payload.json", payload)
        save(directory / "messages.json", messages)
        save(directory / "request.json", {**case["parameters"], "messages": messages})
        save(directory / "criteria.json", {"material": case["material"], "checks": case["criteria"],
                                           "scope": "Single independent probe; no executed new Skill, no publication, no causal performance claim."})
        if case["classification_binding"] is not None:
            save(directory / "classification_binding.json", case["classification_binding"])
        entries.append({k: case[k] for k in ("id", "stage", "profile", "material", "parameters", "timeout_seconds")} | {
            "messages_sha256": object_digest(messages), "payload_sha256": object_digest(payload),
            "messages_chars": len(json.dumps(messages, ensure_ascii=False, separators=(",", ":"))),
            "content_chars": sum(len(message["content"]) for message in messages),
            "decoded_facts_equal": True, "criteria_file": f"cases/{case['id']}/criteria.json"})
    save(OUT / "source_manifest.json", source_manifest())
    save(OUT / "protocol.json", {
        "schema_version": "v22.p1_semantic_validation.v1", "baseline_profile": V3,
        "profile": V4, "consumption_encoding": VIEW_SCHEMA, "cases": entries,
        "logical_calls_max": 8, "http_attempts_max": 8, "http_attempts_per_case": 1,
        "transport_retries": 0, "semantic_retries": 0, "environment_episodes": 0,
        "max_concurrent_requests": 2, "completion_tokens_total_cap": 327680,
        "model": "deepseek-v4-pro", "model_or_endpoint_fallback": False,
        "endpoint_policy": "Use the authorized existing internal Pro route only; root records actual non-secret endpoint metadata before dispatch. No unrelated endpoint-routing revision is imported.",
        "failure_policy": "Archive failure unchanged. Continue other predeclared independent probes; never replace a case, retry, repair output, raise budget, or sample again. Critical P1 comprehension failure blocks promotion, not the remaining independent diagnostic/control probes.",
        "strict_content": "Only the complete provider content is parsed as output. No reasoning/tag stripping or suffix JSON extraction. Prior Editor reasoning/content contamination is a known transport risk, not a reason to alter this test.",
        "independence": "All eight cases fixed before dispatch. Classification, Diagnosis, Fusion and Editor are independent. Learning uses only actual archived 08 R2 Plan/Editor/Skill/diff/paired executions, never outputs generated in this validation.",
        "comparison": "Diagnosis/Fusion/learning share identical underlying real facts between v3 and P1, except necessary profile/binding identity. Temperature=1, one sample per condition; differences are not causal estimates.",
        "publication": False, "algorithm_changes": False,
        "cost_reporting": "Record provider prompt/completion/reasoning/cache usage, response/raw archive, wall time, full-message chars, contract/source checks. Reasoning is an output subset; maxima are caps, not consumption. Monetary charge stays unknown without an actual applicable tariff.",
        "budget_basis": "Prior classification/learning exhausted 16384 completion budget. Construction/classification use 32768, learning65536 including reasoning and visibleJSON, medium effort, 600second timeout. No post-failure change.",
        "launch_precondition": "Root must first verify full offline fidelity/regressions and create an immutable live freeze covering inputs, criteria, controller, codec and revision."})
    if not (OUT / "baseline_fixture_audit.json").exists():
        baseline_audit()
    print(json.dumps({"prepared": len(entries), "cases": [{k: row[k] for k in ("id", "messages_chars")} for row in entries]}, indent=2))


if __name__ == "__main__":
    main()
