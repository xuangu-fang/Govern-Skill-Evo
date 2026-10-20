"""P2 narrow offline source audit and unsent R05 evidence-size estimates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch

from experiments.methods.v23_2.v23_2_diagnosis_construction_001 import run as h
from src.skill_evolution.v23 import memory, preconditioner as pc, editor
from src.skill_evolution.v23.facts import build_facts

ROOT, ev, SOURCE = h.ROOT, h.ev, h.p1.SOURCE
EXP = Path(__file__).resolve().parent


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def selected(rd, module):
    return rd / module / ev.read(rd / module / "result.json")["path"]


def audit():
    # Whole-source guard has pre-existing model-route/CLI drift (recorded separately).
    # Verify the offline functions actually used, plus exact historical request replay.
    import ast
    expected = ev.read(SOURCE / "contract.json")
    for p in sorted((SOURCE / "recoveries").glob("*.json")):
        expected.update(ev.read(p).get("contract_changes", {}))
    functions = {
        "preconditioner.py": ["load_preconditioner", "messages_for", "preconditioner_input"],
        "editor.py": ["apply_patch"],
        "memory.py": ["load_memory", "run_menus"],
        "facts.py": ["build_facts"],
    }
    for filename, names in functions.items():
        path = "src/skill_evolution/v23/" + filename
        def definitions(source):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        old, current = definitions(expected[path]), definitions((ROOT/path).read_text())
        for name in names:
            assert old[name] == current[name], (path, name)
    snapshots, contexts, runs_index, hashes = {}, {}, {}, {}
    for rnd in ("R05", "R06"):
        rd = SOURCE / "rounds" / rnd
        cp = selected(rd, "preconditioner")
        saved = pc.load_preconditioner(cp)
        msgs = pc.messages_for(saved)
        assert msgs == ev.read(cp / "request.json")["body"]["messages"]
        payload = json.loads(msgs[1]["content"])
        ri = ev.read(rd / "round_input.json")
        active = SOURCE / ri["state"]["active_memory"]
        assert payload["memory"] == saved["memory"] == ri["memory"] == memory.load_memory(active)
        entries = [e for e in payload["memory"]["entries"] if e["id"] in ("M6", "M10")]
        run_meta = ev.read(cp / "run.json")
        assert run_meta["status"] == "valid"
        assert (cp / "response.json").exists() and (cp / "http_response.txt").exists()
        snapshots[rnd] = {"path": str(cp), "active_path": str(active),
                          "active_index": ev.read(active / "active.json"),
                          "active_ids": [e["id"] for e in payload["memory"]["entries"]],
                          "entries": entries, "source_keys": list(payload["memory"]["sources"]),
                          "actual_request_equals_rebuilt": True,
                          "http_status": ev.read(cp / "http_status.json"),
                          "run_status": run_meta["status"],
                          "response_sha256": digest(cp / "response.json"),
                          "started_at": run_meta["started_at"],
                          "preconditioner": saved["preconditioner"]}
        for entry in entries:
            for ref in entry["evidence"]:
                cid, local = ref.rsplit("/", 1)
                archive = active / "archive" / f"{cid}.json"
                context = ev.read(archive)["context"]
                contexts[cid] = context
                src_key = f"{cid}/diff" if local == "diff" else f"{cid}/{local.split(':')[0]}"
                src = payload["memory"]["sources"][src_key]
                if local == "diff":
                    assert src == {"parent": context["payload"]["parent"], "diff": context["payload"]["diff"],
                                   "execution_context": context["execution_context"]}
                else:
                    run = next(x for x in context["payload"]["runs"] if x["ref"] == local.split(":")[0])
                    assert src == {"run": run, "command_sets": memory.run_menus(run, context["payload"]["command_sets"])}
                hashes[str(archive.relative_to(ROOT))] = digest(archive)
        for p in (cp / "input.json", cp / "request.json", active / "active.json", rd / "round_input.json"):
            hashes[str(p.relative_to(ROOT))] = digest(p)
    assert snapshots["R05"]["entries"][0] == snapshots["R06"]["entries"][0]
    assert "M10" not in snapshots["R05"]["active_ids"]
    for cid, context in contexts.items():
        rnd = cid.split("_")[-1]
        rd = SOURCE / "rounds" / rnd
        ep = selected(rd, "editor")
        assert (ep / "actual.diff").read_text() == context["payload"]["diff"]
        assert (ep / "candidate.md").read_text() == context["candidate"]
        assert editor.apply_patch(context["payload"]["parent"], context["payload"]["diff"]) == context["candidate"]
        for side, prefix in (("parent", "P"), ("candidate", "Q")):
            raw = [ev.read(Path(p)) for p in context["record_paths"][side]]
            rebuilt = build_facts(raw)
            expected_skill = context["payload"]["parent"] if side == "parent" else context["candidate"]
            assert rebuilt["facts"]["parent"] == expected_skill
            for i, record in enumerate(raw, 1):
                ref = f"{prefix}{i}"
                run = next(x for x in context["payload"]["runs"] if x["ref"] == ref)
                rebuilt_run = rebuilt["facts"]["runs"][i-1]
                assert rebuilt_run["task"] == run["task"] and rebuilt_run["outcome"] == run["outcome"]
                for st, actual in zip(rebuilt_run["steps"], run["steps"], strict=True):
                    assert st["action"] == actual["action"] and st["feedback"] == actual["feedback"]
                    for state in ("before", "after"):
                        assert st[state]["observation"] == actual[state]["observation"]
                        m1, m2 = st[state]["commands_ref"], actual[state]["commands_ref"]
                        assert (None if m1 is None else rebuilt["facts"]["command_sets"][m1]) == (
                            None if m2 is None else context["payload"]["command_sets"][m2])
                path = context["record_paths"][side][i-1]
                hashes[str(Path(path).relative_to(ROOT))] = digest(path)
                runs_index[f"{cid}/{ref}"] = {
                    "path": path, "task": record["task"], "game_sha256": record["environment"]["game_sha256"],
                    "seed": record["protocol"]["environment_seed"], "initial": run["initial"]["observation"],
                    "initial_candidates": record["initial_admissible_commands"],
                    "outcome": run["outcome"], "steps": len(run["steps"]),
                    "actions": [{"step": s["step"], "action": s["action"], "observation": s["after"]["observation"],
                                 "feedback": s["feedback"]} for s in run["steps"]],
                }
        for pair in context["payload"]["pairs"]:
            a, b = (runs_index[f"{cid}/{pair[k]}"] for k in ("parent", "candidate"))
            assert a["task"] == b["task"] and a["game_sha256"] == b["game_sha256"] and a["seed"] == b["seed"]
            assert a["initial"] == b["initial"] and a["initial_candidates"] == b["initial_candidates"]
        snapshots[cid] = {
            "editor_path": str(ep), "diff": context["payload"]["diff"],
            "actual_candidate_equals_patch_application": True,
            "parent_success": sum(r["outcome"]["success"] is True for r in context["payload"]["runs"] if r["ref"].startswith("P")),
            "candidate_success": sum(r["outcome"]["success"] is True for r in context["payload"]["runs"] if r["ref"].startswith("Q")),
            "paired_tasks": len(context["payload"]["pairs"]), "raw_facts_verified": True,
        }
    # R05 P1-B plan unchanged. Size-only additions are unsent independent conditions.
    dp = ROOT / "artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001"
    new = h.local.load_attempt(dp, prompt_path=h.PROMPT)
    ri = ev.read(SOURCE / "rounds/R05/round_input.json")
    saved = {**new, "memory": ri["memory"]}
    original_messages = pc.messages_for(saved)
    payload = pc.preconditioner_input(saved)
    def measure(extra, empty=False):
        p = deepcopy(payload)
        ids = {x["ref"] for x in p["runs"]} | set(extra)
        p["runs"] = [r for r in new["facts"]["runs"] if r["ref"] in ids]
        menus = {s["commands_ref"] for r in p["runs"] for s in
                 [r["initial"], *[st[k] for st in r["steps"] for k in ("before", "after")]]} - {None}
        p["command_sets"] = {k:v for k,v in new["facts"]["command_sets"].items() if k in menus}
        if empty:
            p["memory"] = memory.empty_memory()
        assert p["plan"] == payload["plan"] and p["grouping"] == payload["grouping"]
        ms = [original_messages[0], {"role":"user", "content":json.dumps(p, ensure_ascii=False, separators=(",",":"))}]
        encoded = json.dumps(ms, ensure_ascii=False)
        return {"chars": len(encoded), "bytes": len(encoded.encode()), "runs":[r["ref"] for r in p["runs"]],
                "commands":len(p["command_sets"]), "sent":False}
    measures = {}
    for label, extra in (("original",[]),("plus_P4",["P4"]),("plus_P2",["P2"]),("plus_P5",["P5"]),
                         ("plus_P9",["P9"]),("plus_P2_P4",["P2","P4"]),("all_missing",["P2","P4","P5","P9"])):
        measures[label] = {"memory":measure(extra), "no_memory":measure(extra,True)}
    base = measures["original"]["memory"]
    for value in measures.values():
        value["added_chars"] = value["memory"]["chars"] - base["chars"]
        value["added_bytes"] = value["memory"]["bytes"] - base["bytes"]
    p3, p4 = (runs_index[f"S1_R05/P{i}"] for i in (3,4))
    selection = {"unsent":True, "original_plan":payload["plan"], "groups":payload["grouping"],
                 "measures":measures, "capacity_chars":4000000, "capacity_bytes":6000000,
                 "P3_P4":{"same_task_id":p3["task"]["id"]==p4["task"]["id"],
                          "same_game_hash":p3["game_sha256"]==p4["game_sha256"],
                          "same_room_listing":p3["initial"].split("Your task is to:")[0]==p4["initial"].split("Your task is to:")[0],
                          "same_initial_candidates":p3["initial_candidates"]==p4["initial_candidates"]},
                 "original_plan_unchanged":True, "groups_unchanged":True}
    ev.save(EXP/"results/memory_audit.json", snapshots)
    ev.save(EXP/"results/run_evidence_index.json", runs_index)
    ev.save(EXP/"results/r05_selection.json",selection)
    ev.save(EXP/"config/source_hashes.json",hashes)
    ev.save(EXP/"results/receipt.json",{"at":ev.now(),"network_blocked":True,"model_calls":0,"tokens":0,
                                      "environment_calls":0,"raw_runs_verified":len(runs_index),
                                      "method_changes":False,"memory_changes":False})
    print(json.dumps(selection["measures"],indent=2))


if __name__ == "__main__":
    with patch.object(socket.socket,"connect",side_effect=AssertionError("Offline P2")), \
         patch.object(socket,"create_connection",side_effect=AssertionError("Offline P2")):
        audit()
