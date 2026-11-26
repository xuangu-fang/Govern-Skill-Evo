"""Audit authorized design changes against the completed offline test report.

Does not execute tests, models, campaigns or subprocesses. Keeps the original
acceptance report: its baseline predates this authorized domain revision.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
DESIGN = ROOT / "docs/methods/v29_6"
OUTPUT = ROOT / "artifacts/verification/v29_6_docvqa_domain_v1"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original_path = OUTPUT / "validation_before_domain_allowlist.json"
    if not original_path.exists():
        original_path.write_bytes((OUTPUT / "validation.json").read_bytes())
    original = read(original_path)
    baseline = read(ROOT / "artifacts/verification/v29_6_implementation_20261105/baseline.json")
    domain = read(DESIGN / "domain_guidance_sources.json")
    design_result = read(DESIGN / "design_validation.json")
    modules = ("diagnosis", "preconditioner", "editor", "replay")
    authorized = {
        f"docs/methods/v29_6/{relative}"
        for module in modules
        for relative in (f"prompts/{module}.md", f"diffs/{module}_from_v29_5.diff")
    }
    assert set(original["changed_baseline_files"]) == authorized
    for path in authorized:
        relative = Path(path).relative_to("docs/methods/v29_6")
        assert digest(DESIGN / domain["original_design"] / relative) == baseline[path]
    untouched = {path: value for path, value in baseline.items() if path not in authorized}
    frozen = {**untouched, **domain["protected_files"]}
    changed = [path for path, value in frozen.items() if digest(ROOT / path) != value]
    assert not changed, changed
    for path, value in original["implementation_sha256"].items():
        assert digest(ROOT / path) == value, path
    assert original["tests_run"] == 844
    assert original["failures"] == original["errors"] == original["skipped"] == 0
    assert not original["blocked_network_or_process_attempts"]
    assert original["check_error"] is None
    assert original["real_training_or_test_started"] is False
    assert design_result["status"] == "passed" and not design_result["failures"]
    report = {**original, "status": "passed", "changed_baseline_files": changed,
              "protected_files": len(frozen),
              "authorized_baseline_changes": sorted(authorized),
              "original_acceptance_report": str(original_path.relative_to(ROOT)),
              "original_acceptance_sha256": digest(original_path),
              "unittest_log_sha256": digest(OUTPUT / "unittest.log"),
              "test_execution_reused": True,
              "acceptance_policy": "Original test execution retained; only the eight authorized design Prompt/diff files are exempted from the original immutable baseline. Their before snapshots match that baseline; current changes are verified by validate_design.py. Runtime code, parameters and recorded historical results remain frozen.",
              "domain_revision": domain["revision"],
              "design_checks_passed": design_result["checks_passed"],
              "model_calls": 0}
    (OUTPUT / "frozen_baseline.json").write_text(json.dumps(frozen, indent=2) + "\n")
    (OUTPUT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in
          ("status", "tests_run", "design_checks_passed", "protected_files",
           "authorized_baseline_changes", "model_calls", "real_training_or_test_started")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
