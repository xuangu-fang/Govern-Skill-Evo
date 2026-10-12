"""Standard-library CLI: validate, private evaluate, or agent-facing JSON-lines serve."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from . import VERSION
from .core import ROOT, FIXTURE
from .evaluation import evaluate
from .session import build, AgentSession
from .validation import cases, run_case


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def metadata():
    sources = sorted((ROOT / "src/benchmark_v5").glob("*.py")) + [FIXTURE]
    sources += sorted((ROOT / "tests/benchmarks/v5/prototypes").glob("*.py"))
    return {"version": VERSION, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python": sys.version, "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            "model_calls": 0, "split": "dev", "purpose": "engineering_validation_not_agent_calibration"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Run public-tool engineering cases, no models")
    validate.add_argument("--output", required=True, type=Path, help="New private evidence directory (must not exist)")
    serve = commands.add_parser("serve", help="JSON-lines agent tool interface, no evaluator/private state on stdout")
    serve.add_argument("task", choices=["S2", "G2", "I1", "K2"])
    serve.add_argument("--audit-out", required=True, type=Path, help="Host-only evidence file (must not exist)")
    grade = commands.add_parser("evaluate", help="Privately rescore an archived audit")
    grade.add_argument("audit", type=Path)
    args = parser.parse_args(argv)
    if args.command == "validate":
        args.output.mkdir(parents=True, exist_ok=False)
        summary = {"metadata": metadata(), "cases": []}
        for case in cases():
            try:
                result, audit = run_case(case)
                write_new(args.output / f'{case[0]}.audit.json', audit)
            except Exception as exc:
                result = {"name": case[0], "passed": False, "valid_execution": False,
                          "infrastructure_error": f"{type(exc).__name__}: {exc}"}
            summary["cases"].append(result)
        summary["passed"] = sum(c["passed"] for c in summary["cases"])
        summary["total"] = len(summary["cases"])
        write_new(args.output / "summary.json", summary)
        print(json.dumps({"passed": summary["passed"], "total": summary["total"], "output": str(args.output)}))
        return int(summary["passed"] != summary["total"])
    if args.command == "evaluate":
        print(json.dumps(evaluate(json.loads(args.audit.read_text())), ensure_ascii=False, indent=2))
        return 0
    if args.audit_out.exists():
        raise FileExistsError(args.audit_out)
    env = build(args.task)
    agent = AgentSession(env)
    print(json.dumps({"request": agent.request, "tools": agent.tools, "max_calls": env.scenario["max_calls"]}), flush=True)
    for line in sys.stdin:
        try:
            item = json.loads(line)
            if type(item) is not dict or set(item) != {"tool", "arguments"} or type(item["tool"]) is not str:
                raise ValueError("invalid envelope")
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            result = env.call("__malformed_request__", {})
        else:
            # Runtime failures must propagate as infrastructure errors, not be
            # reclassified as malformed agent input by the parsing handler.
            result = env.call(item["tool"], item["arguments"])
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if env.state["closed"]:
            break
    env.end_budget()
    write_new(args.audit_out, env.audit())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
