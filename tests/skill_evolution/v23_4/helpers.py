"""Synthetic offline fixtures; no historical artifact or service dependency."""
from copy import deepcopy
import json

from experiments.methods.v23_4.archive_io import resolve
from src.skill_evolution.v23.editor import actual_diff


class Fake:
    call_config = {"kind": "offline_fixture"}

    def __init__(self, value, *, finish="stop", content=None):
        self.response = {"content": json.dumps(value) if content is None else content,
                         "finish_reason": finish}
        self.calls = 0

    def __call__(self, messages, directory):
        self.calls += 1
        assert self.calls == 1, "Unexpected retry"
        self.messages = deepcopy(messages)
        return deepcopy(self.response)


def keep(payload):
    return {"adjustments": [{"target": u["id"], "focus": [], "change": "KEEP",
                            "reason": "Current `P1:1` does not establish a necessary revision.",
                            "to": None} for u in payload["plan"]["updates"]], "checks": None}


def revise(payload, index=0, replacement="Allow relevant inspections while retaining the visible goal.\n"):
    u = payload["plan"]["updates"][index]
    return {"target": u["id"], "focus": ["S"],
            "change": "Permit relevant inspections; retain the visible goal.",
            "reason": "Current `P1:1` motivates exploration; the wider permission remains unverified.",
            "to": {"patch": actual_diff(u["text"], replacement)}}


def withdraw(uid):
    return {"target": uid, "focus": ["C"], "change": "Withdraw this redundant proposal.",
            "reason": "Synthetic fixture assumes Parent already covers the requirement; `P1:1` is inconclusive.",
            "to": []}


def memory(payload):
    # All historical sources are synthetic copies with explicit qualified IDs.
    return {"entries": [{"id": "M1", "knowledge": "Synthetic joint-edit response, uncertain attribution.",
                         "evidence": ["R1/diff", "R1/P1:1"]}],
            "sources": {"R1/diff": {"parent": None, "diff": actual_diff(None, "Synthetic guidance.\n"),
                                     "execution_context": {"fixture": "offline"}},
                        "R1/P1": {"run": deepcopy(payload["runs"][0]),
                                  "command_sets": deepcopy(payload["command_sets"])}}}


def read(path):
    return json.loads(resolve(path).read_text())
