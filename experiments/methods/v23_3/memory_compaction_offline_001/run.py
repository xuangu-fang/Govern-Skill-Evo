"""Build offline comparison files. No model, environment or network calls."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys

import tiktoken

from .compact import compact_memory, restore_complete_memory, validate_view


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FORMAL = ROOT / "artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def serialize(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def project_messages(messages, view):
    result = deepcopy(messages)
    payload = json.loads(result[1]["content"])
    payload["memory"] = view
    result[1]["content"] = serialize(payload)
    result[0]["content"] += "\n\n" + (HERE / "MODEL_FORMAT.md").read_text(encoding="utf-8")
    return result


def token_count(encoding, messages):
    return sum(len(encoding.encode(m["content"], disallowed_special=())) for m in messages)


def block_network(*args, **kwargs):
    raise RuntimeError("This experiment is offline; network access is prohibited")


def main():
    # Encoding files must already be cached. The block also catches accidental API calls.
    socket.socket.connect = block_network
    socket.create_connection = block_network
    encodings = {name: tiktoken.get_encoding(name) for name in ("cl100k_base", "o200k_base")}
    cases = [("R04", FORMAL / "R04/preconditioner/attempts/002"),
             ("R05", FORMAL / "R05/preconditioner/attempts/001"),
             ("R06", FORMAL / "R06/preconditioner/attempts/001"),
             ("P3A_A", ROOT / "experiments/methods/v23_3/p3a_transport_retry_001/runs/A"),
             ("P3A_B", ROOT / "experiments/methods/v23_3/p3a_transport_retry_001/runs/B")]
    summary = {"model_calls": 0, "radius": 2, "tokenizers": list(encodings),
               "runtime": sys.version, "tiktoken_version": tiktoken.__version__, "cases": {}}
    for label, source in cases:
        request_path = source / ("http/001/request.json" if label.startswith("P3A") else "request.json")
        request, response = read(request_path), read(source / "response.json")
        messages = request["body"]["messages"]
        assert messages == read(source / "messages.json")
        payload = json.loads(messages[1]["content"])
        original = payload["memory"]
        assert original == read(source / "input.json")["memory"]
        views = {
            "no_repeated_before": compact_memory(original, full=True, shared_menus=False),
            "shared_menus": compact_memory(original, full=True),
            "reference_windows": compact_memory(original),
        }
        verification = {name: validate_view(view, original) for name, view in views.items()}
        for name in ("no_repeated_before", "shared_menus"):
            assert restore_complete_memory(views[name]) == original
        compact_messages = project_messages(messages, views["reference_windows"])
        compact_payload = json.loads(compact_messages[1]["content"])
        assert {k: v for k, v in compact_payload.items() if k != "memory"} == {
            k: v for k, v in payload.items() if k != "memory"}
        dest = HERE / "cases" / label
        write(dest / "original_payload.json", payload)
        write(dest / "compact_payload.json", compact_payload)
        write(dest / "original_messages.json", messages)
        write(dest / "compact_messages.json", compact_messages)
        write(dest / "verification.json", verification)
        coverage = {}
        for key, value in views["reference_windows"]["sources"].items():
            if key.endswith("/diff"):
                continue
            coverage[key] = {k: value[k] for k in
                             ("detail_reason", "detail_coverage", "omitted_detail_ranges")}
            coverage[key]["windows"] = [[w["start"], w["end"]] for w in value["windows"]]
            coverage[key]["steps"] = len(value["run"]["trace"])
        write(dest / "coverage.json", coverage)
        costs = {}
        actual_input = response["usage"]["prompt_tokens"]
        for name, encoding in encodings.items():
            baseline = token_count(encoding, messages)
            costs[name] = {"original_local_tokens": baseline, "variants": {}}
            for variant, view in views.items():
                count = token_count(encoding, project_messages(messages, view))
                costs[name]["variants"][variant] = {
                    "local_tokens": count,
                    "estimated_model_input_tokens": round(actual_input * count / baseline),
                    "reduction_percent": round(100 * (1 - count / baseline), 2),
                }
        summary["cases"][label] = {
            "source_request": str(request_path.relative_to(ROOT)),
            "original_actual_prompt_tokens": actual_input, "costs": costs,
            "coverage": verification["reference_windows"],
            "lossless_roundtrip_verified": True,
            "current_payload_unchanged": True,
        }
        print(label, actual_input, costs["o200k_base"]["variants"]["reference_windows"],
              verification["reference_windows"], flush=True)
    write(HERE / "results/costs.json", summary)
    baseline = read(HERE / "baseline.json")["existing_files"]
    changed = [rel for rel, st in baseline.items()
               if not (ROOT / rel).is_file()
               or (ROOT / rel).stat().st_size != st["size"]
               or (ROOT / rel).stat().st_mtime_ns != st["mtime_ns"]]
    write(HERE / "results/protection.json", {"checked_files": len(baseline), "changed": changed})
    assert not changed, "Previously existing files changed during offline work"


if __name__ == "__main__":
    main()
