"""Hash-only historical protection and local report link verification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parent


def snapshot():
    names = ("src", "experiments/methods", "artifacts/methods", "docs", "tests", "benchmarks")
    result = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for name in names for p in (ROOT / name).rglob("*")
              if p.is_file() and not p.is_relative_to(EXP)
              and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}
    result[".gitignore"] = hashlib.sha256((ROOT / ".gitignore").read_bytes()).hexdigest()
    return result


if __name__ == "__main__":
    before = json.loads((EXP / "config/protected_before.json").read_text())
    after = snapshot()
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    links = []
    for report in (EXP / "reports").glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", report.read_text()):
            if target.startswith(("https:", "http:")):
                continue
            target = re.sub(r":\d+$", "", target.split("#")[0])
            path = Path(target) if target.startswith("/") else report.parent / target
            assert path.exists(), (report, target)
            links.append(str(path))
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True)
    (EXP / "results/git_status_after.txt").write_text(status)
    result = {
        "at": datetime.now(timezone.utc).isoformat(), "checked_files": len(before),
        "after_files": len(after), "unchanged": not changed, "changed": changed,
        "drift": {p: {"before": before.get(p), "after": after.get(p)} for p in changed},
        "report_links_checked": len(links), "model_calls": 0, "environment_calls": 0,
        "test_usage": "Hash protection only; no Test trajectory used for analysis.",
        "excluded": ["This new P1-C directory", "__pycache__", ".pytest_cache"],
    }
    (EXP / "results/protection.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
