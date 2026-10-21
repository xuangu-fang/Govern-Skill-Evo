"""Run only P1-R and existing pure-function tests; deny live-stage entrypoints."""
import contextlib
import io
import json
from pathlib import Path
import socket
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

import pytest
from src.skill_evolution.v23 import diagnosis, editor, grouping, preconditioner, replay, gate

blocked_attempts = []


def deny(*args, **kwargs):
    blocked_attempts.append("forbidden_stage_or_network")
    raise AssertionError("P1-R forbids model, Actor/environment, Replay/Gate and network calls")


socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
for module in [diagnosis, editor, grouping, preconditioner, replay, gate]:
    for name in list(vars(module)):
        if name.startswith("run_") or name in {"live_generator", "build_replay", "build_gate", "decide_gate"}:
            setattr(module, name, deny)

records = []


class Results:
    def pytest_runtest_logreport(self, report):
        if report.when == "call" or report.failed:
            records.append({"test": report.nodeid, "outcome": report.outcome,
                            "details": dict(report.user_properties),
                            **({"failure": str(report.longrepr)} if report.failed else {})})


buffer = io.StringIO()
with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
    code = pytest.main([
        "-q", "-p", "no:cacheprovider", str(HERE / "test_compatibility.py"),
        *[str(ROOT / "tests/skill_evolution/v23/test_editor.py") + "::" + name for name in [
            "test_exact_patch_examples", "test_invalid_patch_is_rejected_without_repairs",
            "test_eof_marker_without_final_framing_newline",
            "test_no_semantic_validation_or_automatic_revision"]],
    ], plugins=[Results()])
results = HERE / "results"
results.mkdir(exist_ok=True)
(results / "pytest.log").write_text(buffer.getvalue(), encoding="utf-8")
(results / "tests.json").write_text(json.dumps({
    "kind": "offline_human_fixture_compatibility_not_method_results",
    "exit_code": int(code), "forbidden_call_attempts": blocked_attempts,
    "passed": sum(r["outcome"] == "passed" for r in records),
    "failed": sum(r["outcome"] == "failed" for r in records),
    "tests": records,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(buffer.getvalue())
assert not blocked_attempts, blocked_attempts
raise SystemExit(code)
