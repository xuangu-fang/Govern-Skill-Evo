"""P2 stage gates. All generators are mocks; live and environment entrypoints fail."""
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
import requests
from src.skill_evolution.v23 import diagnosis, editor, grouping, preconditioner, replay, gate, evolution

attempts = []


from experiments.methods.v23_3.archive_io import archive_glob

def deny(*args, **kwargs):
    attempts.append("forbidden_live_or_environment_entry")
    raise AssertionError("P2 forbids live API, Actor/environment, Replay, Gate and evolution")


socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
# Existing regression tests exercise the request adapter with mocked Session.post.
# Block the real transport, not construction of that offline-tested adapter.
requests.Session.send = deny
for module in [replay, gate, evolution]:
    if hasattr(module, "live_generator"):
        module.live_generator = deny
for module in [replay, gate, evolution]:
    for name in list(vars(module)):
        if name.startswith(("run_", "build_replay", "build_gate", "decide_gate")):
            setattr(module, name, deny)

stage = sys.argv[1]
assert stage in ("A", "B", "C", "D")
files = {
    "A": ["tests/skill_evolution/v23_3/test_update_patch.py",
          "tests/skill_evolution/v23/test_editor.py", "tests/skill_evolution/v23/test_preconditioner.py"],
    "B": ["tests/skill_evolution/v23_3/test_update_patch.py", "tests/skill_evolution/v23_3/test_preconditioner.py"],
    "C": ["tests/skill_evolution/v23_3", "tests/skill_evolution/v23/test_diagnosis.py",
          "tests/skill_evolution/v23/test_editor.py"],
    "D": ["tests/skill_evolution/v23_3", "tests/skill_evolution/v23/test_diagnosis.py",
          "tests/skill_evolution/v23/test_preconditioner.py", "tests/skill_evolution/v23/test_editor.py",
          "experiments/methods/v23_3/p1r_multiline_001/test_compatibility.py"],
}[stage]
records = []


class Results:
    def pytest_runtest_logreport(self, report):
        if report.when == "call" or report.failed:
            records.append({"test": report.nodeid, "outcome": report.outcome,
                            "properties": dict(report.user_properties),
                            **({"failure": str(report.longrepr)} if report.failed else {})})


buffer = io.StringIO()
with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
    code = pytest.main(["-q", "-p", "no:cacheprovider", *files], plugins=[Results()])
results = HERE / "results"
results.mkdir(exist_ok=True)
# Preserve every run, including failures, rather than overwrite a favorable result.
index = 1 + len(list(archive_glob(results, f'P2-{stage}-*.json')))
stem = f"P2-{stage}-{index:02}"
(results / f"{stem}.log").write_text(buffer.getvalue(), encoding="utf-8")
(results / f"{stem}.json").write_text(json.dumps({
    "stage": stage, "kind": "offline_mock_engineering_only", "exit_code": int(code),
    "forbidden_attempts": attempts, "tests": records,
    "passed": sum(x["outcome"] == "passed" for x in records),
    "failed": sum(x["outcome"] == "failed" for x in records),
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(buffer.getvalue())
assert not attempts, attempts
raise SystemExit(code)
