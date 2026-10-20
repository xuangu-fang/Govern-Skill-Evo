"""P1-C: offline archive/input/compiler audit. No model or environment execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch

from experiments.methods.v23_2.v23_2_diagnosis_construction_001 import run as history
from src.skill_evolution.v23 import diagnosis, preconditioner as pc, editor, memory
from src.skill_evolution.v23.facts import build_facts

ROOT, ev = history.ROOT, history.ev
EXP = Path(__file__).resolve().parent
KEY_STEPS = {
    "R04": ["P2:6", "P3:7", "P4:5", "P6:23", "P6:24", "P6:27", "P6:28",
            "P8:1", "P8:2", "P8:7", "P8:8"],
    "R05": ["P1:4", "P3:8", "P4:1", "P5:3", "P6:6", "P6:14", "P7:11", "P7:12",
            "P8:39", "P9:4", "P10:25", "P10:33", "P10:35"],
    "R06": ["P1:38", "P2:11", "P3:22", "P4:5", "P4:7", "P5:4", "P5:6",
            "P6:17", "P6:21", "P6:22", "P7:7", "P7:8"],
}


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def selected(rd, stage):
    return rd / stage / ev.read(rd / stage / "result.json")["path"]


def summary(payload, full):
    selected_ids = [r["ref"] for r in payload["runs"]]
    assert all(r == next(x for x in full["runs"] if x["ref"] == r["ref"]) for r in payload["runs"])
    assert all(v == full["command_sets"][k] for k, v in payload["command_sets"].items())
    return {
        "keys": list(payload), "runs": selected_ids,
        "omitted_runs": [r["ref"] for r in full["runs"] if r["ref"] not in selected_ids],
        "groups": {g["group_id"]: g["members"] for g in payload["grouping"]["groups"]},
        "steps": sum(len(r["steps"]) for r in payload["runs"]),
        "command_sets": len(payload["command_sets"]),
        "whole_selected_runs_and_menus_equal": True,
        "memory_ids": [e["id"] for e in payload["memory"]["entries"]],
        "memory_source_keys": list(payload["memory"]["sources"]),
        "payload_sha256": sha(payload),
    }


def compiler_probes(payload):
    """Contract fixtures reuse existing text; do not propose or store new policies."""
    original = payload["plan"]
    ids = [u["id"] for u in original["updates"]]
    def compile_(adjustments, checks=None, decision="ready"):
        return pc.compile_effective_plan(
            {"decision": decision, "reason": "Offline contract fixture.",
             "adjustments": adjustments, "checks": checks}, payload)
    def adj(source, target):
        return {"from": source, "to": target, "basis": original["updates"][0]["basis"],
                "reason": "Offline shape fixture, no semantic proposal."}
    assert compile_([]) == original
    first = original["updates"][0]
    replacement = adj([ids[0]], [{"id": ids[0], "text": first["text"]}])
    assert compile_([replacement]) == original
    withdrawn = compile_([adj([ids[0]], [])], [])
    assert [u["id"] for u in withdrawn["updates"]] == ids[1:]
    assert withdrawn["goal"] == original["goal"]
    merged = compile_([adj(ids, [{"id": "audit_merged", "text": first["text"]}])], [])
    assert merged["goal"] == original["goal"] and len(merged["updates"]) == 1
    assert merged["updates"][0]["basis"] == list(dict.fromkeys(b for u in original["updates"] for b in u["basis"]))
    split = compile_([adj([ids[0]], [{"id": "audit_a", "text": first["text"]},
                                   {"id": "audit_b", "text": first["text"]}])], [])
    assert [u["id"] for u in split["updates"]][:2] == ["audit_a", "audit_b"]
    assert compile_([adj(ids, [])], [], "no_change") is None
    assert compile_([], None, "need_evidence") is None
    assert compile_([], [])["checks"] == []
    rejects = {}
    for name, result in {
        "extra_goal_override": {"decision": "ready", "reason": "Fixture", "adjustments": [],
                               "checks": None, "goal_override": original["goal"]},
        "unanchored_add": {"decision": "ready", "reason": "Fixture",
                          "adjustments": [adj([], [{"id": "audit_new", "text": first["text"]}])], "checks": []},
        "adjust_twice": {"decision": "ready", "reason": "Fixture",
                         "adjustments": [replacement, replacement], "checks": []},
        "dangling_checks": {"decision": "ready", "reason": "Fixture",
                            "adjustments": [adj(ids, [{"id": "audit_new", "text": first["text"]}])], "checks": None},
    }.items():
        try:
            pc.compile_effective_plan(result, payload)
        except ValueError as exc:
            rejects[name] = str(exc)
        else:
            raise AssertionError(name)
    return {"keep": True, "one_to_one": True, "withdraw": True, "merge": True,
            "split": True, "replace_checks": True, "no_change": True, "need_evidence": True,
            "goal_inherited": True, "basis_lineage_union": True, "rejected": rejects,
            "semantics_not_tested": True}


def audit():
    history.p1.base.check_baseline()
    report, evidence = {}, {}
    for rnd in history.ROUNDS:
        rd = history.p1.SOURCE / "rounds" / rnd
        cp = selected(rd, "preconditioner")
        old = pc.load_preconditioner(cp)
        raw_records, raw_paths = [], []
        for source in old["sources"]:
            paths = list((rd / "parent_runs").glob(f"*/attempts/*/{source['run_id']}/trajectory.json"))
            assert len(paths) == 1, paths
            raw_paths.append(str(paths[0]))
            raw_records.append(ev.read(paths[0]))
        rebuilt = build_facts(raw_records)
        assert rebuilt["facts"] == old["facts"]
        assert rebuilt["background"] == old["background"]
        assert rebuilt["sources"] == old["sources"]
        payload = pc.preconditioner_input(old)
        messages = pc.messages_for(old)
        assert ev.read(cp / "request.json")["body"]["messages"] == messages == ev.read(cp / "messages.json")
        assert json.loads(messages[1]["content"]) == payload
        round_input = ev.read(rd / "round_input.json")
        assert payload["memory"] == round_input["memory"]
        active_dir = history.p1.SOURCE / round_input["state"]["active_memory"]
        assert memory.load_memory(active_dir) == payload["memory"]
        # Resolve actual source contents against committed context, not paths alone.
        for key, source in payload["memory"]["sources"].items():
            cid, local = key.rsplit("/", 1)
            context = ev.read(active_dir / "archive" / f"{cid}.json")["context"]
            if local == "diff":
                assert source == {"parent": context["payload"]["parent"], "diff": context["payload"]["diff"],
                                  "execution_context": context["execution_context"]}
            else:
                run = next(r for r in context["payload"]["runs"] if r["ref"] == local)
                assert source["run"] == run
                assert source["command_sets"] == memory.run_menus(run, context["payload"]["command_sets"])
        ep = selected(rd, "editor")
        assert ev.read(ep / "input.json") == editor.editor_input(old)
        assert ev.read(ep / "request.json")["body"]["messages"] == editor.messages_for(old)
        root = history.OUTPUT if rnd != "R05" else ROOT / "artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001"
        dp = root / rnd / "attempts/001"
        new = history.local.load_attempt(dp, prompt_path=history.PROMPT)
        hypothetical = {**new, "memory": deepcopy(old["memory"])}
        hp = pc.preconditioner_input(hypothetical)
        hm = pc.messages_for(hypothetical)
        assert json.loads(hm[1]["content"]) == hp
        assert new["facts"] == old["facts"] and new["grouping"] == old["grouping"]
        assert hp["parent"] == payload["parent"] and hp["memory"] == payload["memory"]
        assert hm[0] == messages[0]  # original V23 system, not any experimental candidate
        evidence[rnd] = {}
        for step_id in KEY_STEPS[rnd]:
            run = next(r for r in new["facts"]["runs"] if r["ref"] == step_id.split(":")[0])
            si = next(i for i, s in enumerate(run["steps"]) if s["step"] == step_id)
            ri = new["facts"]["runs"].index(run)
            step = run["steps"][si]
            evidence[rnd][step_id] = {
                "source": str(dp / "input.json"), "json_pointer": f"/facts/runs/{ri}/steps/{si}",
                "step": step,
                "pre_action_commands": new["facts"]["command_sets"][step["before"]["commands_ref"]],
                "formal_request_contains_run": run["ref"] in {r["ref"] for r in payload["runs"]},
                "unsent_p1b_contains_run": run["ref"] in {r["ref"] for r in hp["runs"]},
            }
        report[rnd] = {
            "formal": {**summary(payload, old["facts"]), "path": str(cp),
                       "raw_parent_trajectories": raw_paths,
                       "raw_actor_messages_facts_rebuilt_exact": True,
                       "raw_parent_steps": sum(len(r["steps"]) for r in raw_records),
                       "request_messages_exact": True, "round_start_memory_exact": True,
                       "active_memory_sources_exact": True, "editor_input_exact": True,
                       "original_plan": payload["plan"], "preconditioner": old["preconditioner"],
                       "effective_plan": old["effective_plan"]},
            "p1b_unsent": {**summary(hp, new["facts"]), "diagnosis_path": str(dp),
                          "original_plan": hp["plan"], "sent": False, "model_result": None,
                          "system_same_as_formal": True, "same_parent_facts_grouping_memory": True,
                          "messages_sha256": sha(hm), "messages_chars": len(json.dumps(hm, ensure_ascii=False)),
                          "message_bytes": len(json.dumps(hm, ensure_ascii=False).encode()),
                          "compiler_contract_probes": compiler_probes(hp)},
        }
        # Selected Group descriptions may refer to omitted members; G alone does not expand runs.
        hp2 = deepcopy(hypothetical)
        hp2["diagnosis"]["reason"] += " P2"
        assert pc.preconditioner_input(hp2) == hp  # Diagnosis reason is not selection/input.
    ev.save(EXP / "results/interface_audit.json", {
        "at": ev.now(), "network_blocked": True, "model_calls": 0, "environment_calls": 0,
        "diagnosis_reason_not_forwarded_or_used_for_selection": True, "rounds": report,
    })
    ev.save(EXP / "results/evidence_index.json", evidence)
    print(json.dumps({k: {"formal_runs": v["formal"]["runs"], "p1b_unsent_runs": v["p1b_unsent"]["runs"],
                         "p1b_omitted": v["p1b_unsent"]["omitted_runs"]} for k, v in report.items()}, indent=2))


if __name__ == "__main__":
    with patch.object(socket.socket, "connect", side_effect=AssertionError("Offline audit forbids network")), \
         patch.object(socket, "create_connection", side_effect=AssertionError("Offline audit forbids network")):
        audit()
