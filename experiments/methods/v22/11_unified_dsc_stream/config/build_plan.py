"""Build the user-approved 8+8 preparation; never starts a campaign."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.adapters.alfworld.skill_runtime import load_skill


def read(path):
    return json.loads(path.read_text())


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    old = ROOT / "experiments/methods/v22/08_grouped_continual/config"
    plan = read(old / "plan_parallel8.json")
    manifest = read(HERE / "task_manifest.json")
    plan.update(protocol="v22.grouped_continual.v4", update_profile="v22.unified_dsc.v2",
                status="prepared_pending_start_authorization", date="2026-10-16")
    plan["question"].append("Does the same Update remain traceable through actual Skill realization, behavior opportunity, response and Memory revision?")
    plan["data"].update(task_manifest_sha256=checksum(HERE / "task_manifest.json"),
        round1_task_ids=manifest["rounds"][0]["task_ids"], round2_task_ids=manifest["rounds"][1]["task_ids"],
        old_train_results_use="Identity exclusion only; no old outcomes, Skill or Effects are learner input.",
        approved_adjustment="User explicitly selected two rounds of eight previously unexposed Train tasks after only sixteen were available.")
    for row in plan["rounds"]:
        row["episodes_max"] = 16
    plan["gate"].update(required_pairs=8,
        accept="candidate_success_count > parent_success_count for the same complete comparable task batch",
        eligibility="Distinct actual Candidate; all eight pairs complete, provenance valid and recorded conditions matching. Legal no-change needs eight complete Parent runs and no fabricated comparison.",
        no_change="Legal no candidate/change: RETAIN with reason=no_change after complete Parent verification; no Candidate score is fabricated.")
    plan["budget"].update(tasks_per_round=8, unique_tasks=16, environment_episodes_max=32,
        actor_logical_requests_max=1600, logical_requests_max=1609, http_attempts_max=9609,
        semantic_http_attempts_per_request_max=1, per_request_output_tokens_max=65536,
        semantic_output_tokens_max=360448, actor_output_tokens_max=157286400,
        actor_logical_output_tokens_max=26214400,
        input_character_measure="len(json.dumps(messages,ensure_ascii=False,separators=(',',':')))",
        token_limits="Request declarations, not a guaranteed provider billing ceiling. Reasoning is included in completion.",
        monetary_cost=None, monetary_cost_status="Internal proxy tariff unavailable; actual usage is recorded, never assumed free.")
    plan["models"]["semantic_requests"] = {
        stage: {"max_tokens": 65536 if stage == "post_gate_learning" else 32768,
                "timeout_seconds": 600, "transport_policy": "single_attempt"}
        for stage in ("classification", "diagnosis", "fusion", "main_editor", "post_gate_learning")}
    plan["models"].update(actor_response_archival=True,
        request_parameters_scope="Actor only; semantic requests use the same temperature/thinking/reasoning/stream plus explicit per-stage overrides.",
        response_format="Existing prompt-defined JSON for semantic stages; existing action-tag projection for Actor. No provider response_format override.")
    plan["transport"] = {"actor_http_attempts_max": 6,
        "actor_retry_statuses": [429, 500, 502, 503, 504], "actor_backoff_seconds": [1, 2, 4, 8, 16],
        "semantic_http_attempts_max": 1, "connection_timeout_seconds": 10,
        "network_exception_retries": 0, "allow_redirects": False,
        "response_archival": "raw_http_body_v1", "failed_attempt_usage": "Included; missing values remain unknown."}
    plan["stop_rules"] = [text.replace("ten complete", "eight complete") for text in plan["stop_rules"]]
    plan["freeze"].update(implementation_ready=True,
        prepared_start="Run only after separate authorization, using run --prepared in the exact preflight directory.",
        recovery="No automatic resume. New independent recovery protocol and authorization required; no completed work reruns.")
    plan["claims_excluded"] = [text.replace("ten tasks", "eight tasks") for text in plan["claims_excluded"]]
    materials = ["../PROTOCOL.md", "../REPORT_TEMPLATE.md", "../TASK_SELECTION.md", "task_inventory.json",
                 "inventory_tasks.py", "freeze_task_manifest.py", "budget_evidence.json",
                 "extract_budget_evidence.py", "initial_state.json", "build_plan.py"]
    plan["preparation_materials"] = [{"path": name, "sha256": checksum(HERE / name)} for name in materials]
    return plan


def serialized(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    initial = {"schema": "v22.initial_content.v1", "profile": "v22.unified_dsc.v2",
               "skill": load_skill(), "memory": [], "import_previous_skills_or_effects": False}
    prompt = ROOT / "experiments/methods/v22/08_grouped_continual/config/grouping_prompt.md"
    if args.check:
        assert (HERE / "initial_state.json").read_text() == serialized(initial)
        assert (HERE / "grouping_prompt.md").read_bytes() == prompt.read_bytes()
        assert (HERE / "plan.json").read_text() == serialized(build())
    else:
        with (HERE / "initial_state.json").open("x") as stream:
            stream.write(serialized(initial))
        with (HERE / "grouping_prompt.md").open("xb") as stream:
            stream.write(prompt.read_bytes())
        with (HERE / "plan.json").open("x") as stream:
            stream.write(serialized(build()))
    print("Approved 8+8 configuration " + ("verified" if args.check else "created") + "; no execution.")


if __name__ == "__main__":
    main()
