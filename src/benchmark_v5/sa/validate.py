"""Write a fresh offline record, or verify its immutable sources and trajectories."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from .environment import replay
from .evaluation import evaluate, learning_observation
from .offline import validate

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read(path):
    return json.loads(path.read_text())


def check_hashes(base, mapping):
    changed = [p for p, expected in mapping.items() if not (base/p).is_file() or sha(base/p) != expected]
    if changed:
        raise ValueError("HASH_MISMATCH: " + ", ".join(changed[:5]))


def verify(output):
    manifest = read(output/"manifest.json")
    check_hashes(ROOT, manifest["sources"])
    check_hashes(output, manifest["artifacts"])
    protected = read(output/"protected_before.json")
    check_hashes(ROOT, protected)
    scores = read(output/"scores.json")
    for key, expected in scores.items():
        audit = read(output/"private"/(key+".json"))
        replay(audit)
        if evaluate(audit) != expected:
            raise ValueError("RESCORE_MISMATCH: " + key)
    train = read(output/"private/authorized_history.json")
    if learning_observation(train) != read(output/"evidence/train_observation.json"):
        raise ValueError("PUBLIC_EVIDENCE_MISMATCH")
    results = read(output/"results.json")
    for row in results["outcomes"]:
        if row["reference"] != scores[row["case_id"]+"__reference"]:
            raise ValueError("REFERENCE_REPORT_MISMATCH")
        for policy, score in row["policies"].items():
            if score is not None and score != scores[row["case_id"]+"__"+policy]:
                raise ValueError("POLICY_REPORT_MISMATCH")
    return dict(exact_replays=len(scores), same_scores=True, evidence_rebuilt=True,
                protected_files=len(protected), protected_unchanged=True,
                source_and_artifact_hashes_verified=True, model_calls=0)


def run(output):
    if (output/"manifest.json").exists() or (output/"results.json").exists():
        raise ValueError("REFUSE_TO_OVERWRITE_EXISTING_RUN")
    # Capture protection before any implementation/run, not retrospectively here.
    check_hashes(ROOT, read(output/"protected_before.json"))
    results, traces, observation = validate()
    write(output/"results.json", results)
    write(output/"scores.json", {k: evaluate(a) for k, a in traces.items()})
    for key, audit in traces.items():
        write(output/"private"/(key+".json"), audit)
    write(output/"evidence/train_observation.json", observation)
    sources = sorted((ROOT/"src/benchmark_v5/sa").glob("*.py"))
    sources += sorted((ROOT/"tests/benchmarks/v5/sa").glob("*.py"))
    sources += [(Path(__file__).resolve().parents[3] / 'docs/benchmarks/v5/SA.md')]
    write(output/"manifest.json", dict(
        kind="offline_engineering", git_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        model=None, temperature=None, repetitions=1, final_test_used=False,
        sources={str(p.relative_to(ROOT)): sha(p) for p in sources},
        artifacts={str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*.json"))}))
    checks = verify(output)
    write(output/"validation.json", checks)
    return results, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.output), ensure_ascii=False))
    else:
        results, checks = run(args.output)
        print(json.dumps(dict(decision=results["decision"], policy_successes=results["policy_successes"],
                              validation=checks), ensure_ascii=False))


if __name__ == "__main__":
    main()
