"""Persist one human Mock chain using frozen R05 evidence; no model or environment."""
import json
from contextlib import nullcontext
from pathlib import Path
import socket
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

import requests
from src.skill_evolution.v23.editor import actual_diff
from src.skill_evolution.v23_3 import diagnosis, editor, preconditioner
from tests.skill_evolution.v23_3.helpers import Fake, frozen, patch_result, scenario


from experiments.methods.v23_3.archive_io import load_saved, resolve, raw_path, materialized

def deny(*args, **kwargs):
    raise AssertionError("Offline fixture builder: no network")


socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
requests.Session.send = deny


def build():
    source = HERE / "mock_chain"
    context = materialized(source) if resolve(source / "manifest.json").exists() else nullcontext(raw_path(source))
    with context as root:
        original = frozen()
        grouping = ROOT / "artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/grouping/attempts/002"
        diag, pc, ed = (root / name for name in ("diagnosis", "preconditioner", "editor"))
        dg = Fake(original["diagnosis"])
        diagnosis.run_diagnosis(grouping, diag, generate=dg, max_input_chars=4000000)
        raw = patch_result(original, scenario("R05", "cross")["patches"])
        pg = Fake(raw)
        saved = preconditioner.run_preconditioner(
            grouping, diag, pc, generate=pg, memory=original["memory"], max_input_chars=4000000)
        parent = saved["facts"]["parent"]
        candidate = parent + "\n## Offline human fixture\n" + "\n".join(
            u["text"] for u in saved["effective_plan"]["updates"])
        eg = Fake({"patch": actual_diff(parent, candidate),
                   "reason": "Human mock Skill patch; semantic implementation quality not evaluated."})
        result = editor.run_editor(pc, ed, generate=eg, max_input_chars=4000000)
        assert result == load_saved(editor.load_editor, ed)
        manifest = {
            "kind": "HUMAN_MOCK_NOT_LLM_OR_BEHAVIOR_RESULT",
            "case": "R05", "scenario": "cross", "grouping_directory": str(grouping),
            "fixture_sources": "experiments/methods/v23_3/p1r_multiline_001/fixtures/sources.json",
            "mock_response_model": "offline-human-fixture",
            "fresh_mock_calls_or_reload": {"diagnosis": dg.calls, "preconditioner": pg.calls, "editor": eg.calls},
            "reload_verified": True, "real_llm_calls": 0, "environment_calls": 0,
            "semantic_validity": "not_evaluated",
        }
        # The initial manifest remains truthful when this command is used only to reload.
        if not resolve(root / 'manifest.json').exists():
            (resolve(root / "manifest.json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
