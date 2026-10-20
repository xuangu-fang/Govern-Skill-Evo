"""P1-B profile: reuse P1's fixed Diagnosis runner; at most three HTTP requests."""
import argparse
from pathlib import Path
from unittest.mock import patch

from experiments.methods.v23_2.v23_2_diagnosis_boundary_001 import run as p1

ROOT, ev, local = p1.ROOT, p1.ev, p1.local
EXP = Path(__file__).resolve().parent
OUTPUT = ROOT / "artifacts/methods/v23_2/v23_2_diagnosis_construction_001"
PROMPT = EXP / "config/diagnosis_prompt.md"
P1_EXP = p1.EXP
ROUNDS = p1.ROUNDS


def protected_files():
    with patch.multiple(p1, EXP=EXP, OUTPUT=OUTPUT):
        return p1.protected_files()


def material(rnd):
    saved, entry = p1.material(rnd)
    assert entry == ev.read(EXP / "config/cases.json")[rnd]
    return saved, entry


def check():
    p1.base.check_baseline()
    for name, base in (("p0_freeze.json", P1_EXP), ("p1_freeze.json", ROOT)):
        for path, digest in ev.read(P1_EXP / "config" / name)["sha256"].items():
            assert p1.digest(base / path) == digest, path
    assert (EXP / "config/cases.json").read_bytes() == (P1_EXP / "config/cases.json").read_bytes()
    for rnd in ROUNDS:
        saved, entry = material(rnd)
        assert "memory" not in saved
        old = ev.read(Path(entry["diagnosis_path"]) / "messages.json")
        d1 = local.messages_for("diagnosis", saved, prompt_path=P1_EXP / "config/diagnosis_prompt.md")
        d2 = local.messages_for("diagnosis", saved, prompt_path=PROMPT)
        expected = d1[0]["content"]
        for change in ev.read(EXP / "config/replacements.json"):
            assert expected.count(change["before"]) == 1
            expected = expected.replace(change["before"], change["after"])
        assert d2[0]["content"] == expected and d2[1:] == d1[1:] == old[1:]
    assert protected_files() == ev.read(EXP / "config/protected_before.json")


def frozen_files():
    files = [Path(__file__), EXP / "tests/test_profile.py", PROMPT,
             EXP / "config/replacements.json", EXP / "config/p1.diff", EXP / "config/v23.diff",
             EXP / "config/cases.json", EXP / "reports/P1B_DESIGN.md",
             Path(local.__file__), Path(p1.__file__)]
    return {str(p.relative_to(ROOT)): p1.digest(p) for p in files}


def prepare():
    assert not OUTPUT.exists() and not (EXP / "config/p1_freeze.json").exists()
    check()
    ev.save(EXP / "config/p1_freeze.json", {
        "stage": "P1-B", "at": ev.now(), "max_logical_calls": 3,
        "max_http_requests": 3, "automatic_retries": 0,
        "sha256": frozen_files(),
    })


def run_one(saved, directory, config, *, generate=None):
    with patch.object(p1, "PROMPT", PROMPT):
        return p1.run_one(saved, directory, config, generate=generate)


def run():
    assert frozen_files() == ev.read(EXP / "config/p1_freeze.json")["sha256"]
    tests = ev.read(EXP / "results/offline_tests.json")
    assert tests["exit_code"] == 0 and tests["network_blocked"] is True
    assert tests["frozen_sha256"] == frozen_files()
    assert not OUTPUT.exists()
    ev.save(EXP / "config/call_receipt.json", {
        "at": ev.now(), "freeze_sha256": p1.digest(EXP / "config/p1_freeze.json"),
        "offline_tests_sha256": p1.digest(EXP / "results/offline_tests.json"),
        "offline_log_sha256": p1.digest(EXP / "results/offline_tests.log"),
        "http_request_limit": 3, "automatic_retries": 0,
    })
    # Existing P1 loop, input loader, local stage, parser and no-retry wrapper.
    with patch.multiple(p1, EXP=EXP, OUTPUT=OUTPUT, PROMPT=PROMPT,
                        verify_p0=check, frozen_files=frozen_files):
        p1.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "prepare", "run"))
    {"check": check, "prepare": prepare, "run": run}[parser.parse_args().action]()
