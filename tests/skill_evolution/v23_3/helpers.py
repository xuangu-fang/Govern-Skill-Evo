"""Frozen research inputs and explicitly human-authored responses; no live calls."""
from copy import deepcopy
import json
from pathlib import Path

from src.skill_evolution.v23.preconditioner import preconditioner_input

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "experiments/methods/v23_3/p1r_multiline_001/fixtures"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frozen(case="R05", multiline=True):
    sources = read(FIXTURES / "sources.json")["sources"][case]
    saved = read(ROOT / sources["facts"])
    saved["diagnosis"] = read(FIXTURES / f"{case}.{'multiline' if multiline else 'original'}.json")
    saved["memory"] = read(ROOT / sources["memory"])["memory"]
    return saved


def keep():
    return {"decision": "ready", "reason": "Human offline fixture; no semantic evaluation.",
            "adjustments": [], "checks": None}


def patch_result(saved, patches):
    originals = {u["id"]: u for u in saved["diagnosis"]["plan"]["updates"]}
    return {**keep(), "adjustments": [
        {"from": [uid], "to": [{"id": uid, "patch": patch}],
         "basis": originals[uid]["basis"],
         "reason": "Human-selected edit for offline integration, not a model decision."}
        for uid, patch in patches.items()]}


def scenario(case, name):
    return next(s for s in read(FIXTURES / f"{case}.scenarios.json")["scenarios"]
                if s["name"] == name)


class Fake:
    """One recorded mock response; reuse must reload, not generate again."""
    call_config = {"kind": "offline_fake"}

    def __init__(self, value=None, *, content=None, finish="stop"):
        self.response = {"content": json.dumps(value, ensure_ascii=False) if content is None else content,
                         "finish_reason": finish, "response_model": "offline-human-fixture"}
        self.calls = 0

    def __call__(self, messages, directory):
        self.calls += 1
        assert self.calls == 1, "Unexpected second generation"
        self.messages = deepcopy(messages)
        return deepcopy(self.response)
