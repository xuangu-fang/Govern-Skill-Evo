"""P1-A: stdlib-only archive audit; writes exclusively inside this directory.

No project stage imports, network clients, model calls, or semantic classifiers.
The two existing pure Actor rendering functions are reused directly from source.
Run from anywhere: python /absolute/path/to/this/audit.py
"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
P1 = ROOT / "experiments/methods/v23_2/v23_2_diagnosis_boundary_001"
FORMAL = ROOT / "artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds"
NEW = ROOT / "artifacts/methods/v23_2/v23_2_diagnosis_boundary_001"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def save(name, value):
    (HERE / "results" / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )


# Only extract the existing side-effect-free functions; never load an executor.
renderer = ROOT / "src/adapters/alfworld/actor_prompt.py"
tree = ast.parse(renderer.read_text())
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
assert [n.name for n in functions] == ["visible_commands", "render_messages"]
namespace = {}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(renderer), "exec"), namespace)
visible, render = namespace["visible_commands"], namespace["render_messages"]
assert visible(["help", " look ", "help ", "look", "look"]) == [
    " look ", "help ", "look", "look"
]

cases = read(P1 / "config/cases.json")
frozen = {}
for name in ("p0_freeze.json", "p1_freeze.json"):
    manifest = read(P1 / "config" / name)
    base = P1 if name == "p0_freeze.json" else ROOT
    for name_, digest in manifest["sha256"].items():
        assert sha(base / name_) == digest, name_
    frozen[name] = len(manifest["sha256"])
source_count = 0
for case in cases.values():
    for name, digest in case["source_hashes"].items():
        assert sha(ROOT / name) == digest, name
        source_count += 1

selected = {
    "R04": {"P1": [28, 31, 37, 41, 44, 50],
            "P2": [6, 7, 8, 9, 10, 11, 13], "P3": [7, 12, 14],
            "P4": [5, 8, 17, 19, 21], "P5": [14, 23, 50],
            "P6": [23, 24, 26, 27, 28, 30], "P7": [28, 35, 36, 47, 50],
            "P8": [1, 2, 4, 7, 8, 10], "P9": [4, 10], "P10": [1, 2, 3]},
    "R05": {"P3": [13, 14, 16], "P4": [1, 2, 4], "P5": [3, 5],
            "P6": [1, 2, 5, 6, 7, 10, 11, 50], "P7": [2, 5, 7, 9],
            "P8": [1, 4, 26, 27, 28, 39, 50], "P9": [2, 4, 6],
            "P10": [5, 6, 25, 32, 33, 35, 38]},
    "R06": {"P1": [34, 35, 37, 40], "P2": [8, 9, 11, 14],
            "P3": [2, 13, 22, 50], "P4": [3, 5, 6, 7, 14, 19, 20, 22],
            "P5": [4, 5, 6, 13, 14, 15, 18],
            "P6": [17, 18, 20, 21, 22, 23, 24], "P7": [1, 5, 7, 8, 10]},
}
index = {}
steps_audited = 0
for rnd, case in cases.items():
    old = Path(case["diagnosis_path"])
    new = NEW / rnd / "attempts/001"
    saved = read(old / "input.json")
    facts = saved["facts"]
    old_messages, new_messages = read(old / "messages.json"), read(new / "messages.json")
    assert saved == read(new / "input.json")
    assert old_messages[1] == new_messages[1]
    expected_system = old_messages[0]["content"]
    for replacement in read(P1 / "config/replacements.json"):
        assert expected_system.count(replacement["before"]) == 1
        expected_system = expected_system.replace(replacement["before"], replacement["after"])
    assert expected_system == new_messages[0]["content"]
    for directory in (old, new):
        stage = directory.parent.parent
        assert (stage / read(stage / "result.json")["path"]).resolve() == directory.resolve()
        assert read(directory / "validation.json")["valid"] is True
        response = read(directory / "response.json")
        assert response["finish_reason"] == "stop"
        assert json.loads(response["content"]) == read(directory / "diagnosis.json")
    payload = json.loads(new_messages[1]["content"])
    assert set(payload) == {"parent", "command_sets", "runs", "grouping"}
    assert payload == {**facts, "grouping": saved["grouping"]}
    grouped = read(Path(case["grouping_path"]) / "input.json")
    assert all(grouped[k] == saved[k] for k in ("facts", "background", "sources"))
    assert saved["grouping"] == read(Path(case["grouping_path"]) / "grouping.json")
    assert facts["parent"] == (FORMAL / rnd / "parent.md").read_text()
    for directory, messages in ((old, old_messages), (new, new_messages)):
        assert read(directory / "request.json")["body"]["messages"] == messages
    old_request, new_request = read(old / "request.json"), read(new / "request.json")
    assert {k: v for k, v in old_request["body"].items() if k != "messages"} == {
        k: v for k, v in new_request["body"].items() if k != "messages"
    }
    raw_records = {}
    for path in (FORMAL / rnd / "parent_runs").rglob("trajectory.json"):
        record = read(path)
        assert record["run_id"] not in raw_records
        raw_records[record["run_id"]] = (path, record)
    info = {
        "original_input": rel(old / "input.json"),
        "original_output": rel(old / "diagnosis.json"),
        "p1_output": rel(new / "diagnosis.json"),
        "p1_request": rel(new / "request.json"),
        "grouping": rel(Path(case["grouping_path"]) / "grouping.json"),
        "parent": rel(FORMAL / rnd / "parent.md"),
        "user_payload_fields": sorted(payload),
        "memory_in_user_payload": False,
        "original_and_p1_user_message_equal": True,
        "runs": [],
    }
    for run, source in zip(facts["runs"], saved["sources"]):
        assert source["ref"] == run["ref"]
        path, record = raw_records[source["run_id"]]
        assert record["task"]["id"] == source["task_id"]
        assert record["skill"]["text"] == facts["parent"]
        protocol = record["protocol"]
        assert protocol["history_length"] == 2
        assert protocol["history"] == "last_2_pre_action_observations"
        assert protocol["max_steps"] == 50
        assert len(record["steps"]) == len(run["steps"])
        assert record["status"] == run["outcome"]["status"]
        observation, history = record["initial_observation"], []
        assert run["initial"]["observation"] == observation
        assert facts["command_sets"][run["initial"]["commands_ref"]] == visible(
            record["initial_admissible_commands"]
        )
        run_info = {"ref": run["ref"], "task": run["task"],
                    "task_id": source["task_id"], "trajectory": rel(path),
                    "trajectory_sha256": sha(path), "outcome": run["outcome"],
                    "selected_steps": []}
        actions = [e["action"] for e in record["steps"]]
        run_info["visited_destinations"] = sorted({
            a.removeprefix("go to ") for a in actions if a.startswith("go to ")
        })
        run_info["opened_containers"] = sorted({
            a.removeprefix("open ") for a in actions if a.startswith("open ")
        })
        run_info["initial_destination_candidates"] = [
            a.removeprefix("go to ") for a in visible(record["initial_admissible_commands"])
            if a.startswith("go to ")
        ]
        for i, (event, fact) in enumerate(zip(record["steps"], run["steps"])):
            assert event["step"] == i + 1 and event["phase"] == "executed"
            commands = event["admissible_commands"]
            actor_visible = visible(commands)
            expected = render(
                observation, commands, record["goal"], history,
                **{k: protocol[k] for k in ("system_prompt", "initial_template", "history_template")}
            )
            expected[0]["content"] += (
                protocol["skill_prefix"] + facts["parent"] + protocol["skill_suffix"]
            )
            assert expected == event["messages"], (rnd, fact["step"], "Actor messages")
            assert fact["before"]["observation"] == observation
            assert facts["command_sets"][fact["before"]["commands_ref"]] == actor_visible
            assert fact["action"] == event["action"]
            assert fact["after"]["observation"] == event["observation"]
            next_visible = None
            if i + 1 < len(record["steps"]):
                next_visible = visible(record["steps"][i + 1]["admissible_commands"])
                assert facts["command_sets"][fact["after"]["commands_ref"]] == next_visible
                assert source["events"][i]["after_menu_source"] == f"{run['ref']}:{i+2}:before"
            else:
                assert fact["after"]["commands_ref"] is None
                assert source["events"][i]["after_menu_source"] is None
            if i + 1 in selected[rnd].get(run["ref"], []):
                item = {
                    "step": fact["step"], "raw_json_pointer": f"/steps/{i}",
                    "fact_json_pointer": f"/facts/runs/{int(run['ref'][1:])-1}/steps/{i}",
                    "before_observation": observation,
                    "raw_environment_pre_action_candidates": commands,
                    "actor_visible_pre_action_candidates": actor_visible,
                    "actor_visible_recent_history": history[-2:],
                    "action": event["action"], "after_observation": event["observation"],
                    "post_action_candidates_from_next_pre_action": next_visible,
                    "post_action_candidates_source": source["events"][i]["after_menu_source"],
                    "actual_actor_messages_verified": True,
                    "feedback": fact["feedback"],
                }
                if rnd == "R04" and fact["step"] in ("P2:6", "P3:7", "P4:5"):
                    # Context for the recorded Actor choice, NOT Diagnosis evidence.
                    assert "model_response" not in fact
                    item["actor_recorded_answer_not_supplied_to_diagnosis"] = (
                        event["model_response"]["content"]
                    )
                run_info["selected_steps"].append(item)
            history.append({"observation": observation, "action": event["action"]})
            observation = event["observation"]
            steps_audited += 1
        info["runs"].append(run_info)
    index[rnd] = info

save("evidence_index.json", index)
save("audit.json", {
    "at": datetime.now(timezone.utc).isoformat(),
    "status": "passed", "freeze_hashes_checked": frozen,
    "case_source_hash_checks": source_count,
    "rounds": list(index), "parent_runs": sum(len(v["runs"]) for v in index.values()),
    "actor_steps_verified": steps_audited,
    "selected_evidence_steps": sum(len(r["selected_steps"]) for v in index.values() for r in v["runs"]),
    "checks": [
        "P0/P1 freeze and original case source SHA-256",
        "Original/P1 Diagnosis saved input and user message equality",
        "System messages differ only by the two frozen P1 replacements",
        "Only result-selected, valid, stop-finished Diagnosis outputs used",
        "Grouping facts, Parent and Grouping output match actual Diagnosis payload",
        "Diagnosis request body matches saved messages; no Memory payload field",
        "Original/P1 model request parameters equal",
        "Every Parent Actor message matches original pure renderer, including Skill",
        "Only exact help removed; candidate order, duplicates and whitespace preserved",
        "Pre-action observation/menu, selected action and post-action observation separated",
        "Post-action menu sourced only from next recorded pre-action; final unknown is null",
        "Actual two-pre-action-pair history preserved",
    ],
    "semantic_verdicts": "Human-readable reports; not computed by this script.",
    "new_model_calls": 0, "new_actor_or_environment_runs": 0,
    "new_tokens": 0, "method_files_written": [],
})

# Include file-set equality, not just previously listed file hashes.
manifest = read(HERE / "config/protected_before.json")
before = manifest["sha256"]
current_paths = {ROOT / p for p in before if (ROOT / p).is_file()}
for name in manifest["roots"]:
    current_paths.update(
        p for p in (ROOT / name).rglob("*")
        if p.is_file() and HERE not in p.parents
        and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts
    )
after = {rel(p): sha(p) for p in current_paths}
changed = sorted(p for p in before.keys() & after.keys() if before[p] != after[p])
added, missing = sorted(after.keys() - before.keys()), sorted(before.keys() - after.keys())
save("protection.json", {
    "at": datetime.now(timezone.utc).isoformat(), "checked_files": len(before),
    "unchanged": not (changed or added or missing),
    "changed": changed, "added_outside_analysis": added, "missing": missing,
    "test_archives": "bytes hashed for protection only; not used as analysis evidence",
})
assert not (changed or added or missing), (changed, added, missing)
print(f"PASS: {steps_audited} Actor steps; {len(before)} protected files unchanged.")
