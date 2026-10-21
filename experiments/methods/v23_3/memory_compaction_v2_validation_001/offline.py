"""Generate immutable v2 views and costs without network or model calls."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys

import tiktoken

from experiments.methods.v23_3.memory_compaction_live_validation_001.run import read, save
from .compact_v2 import explicit_view, validate_explicit
from .probes_v2 import adapted_probe


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
V1 = HERE.parent / "memory_compaction_offline_001"
OLD_LIVE = HERE.parent / "memory_compaction_live_validation_001"


def messages_v2(original, view):
    result = deepcopy(original)
    payload = json.loads(result[1]["content"])
    payload["memory"] = view
    result[1]["content"] = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    result[0]["content"] += "\n\n" + (HERE / "MODEL_FORMAT.md").read_text(encoding="utf-8")
    return result


def tokens(encoding, messages):
    return sum(len(encoding.encode(m["content"], disallowed_special=())) for m in messages)


def no_network(*args, **kwargs):
    raise RuntimeError("Offline preparation cannot access the network")


def main():
    socket.socket.connect = no_network
    socket.create_connection = no_network
    encodings = {name: tiktoken.get_encoding(name) for name in ("cl100k_base", "o200k_base")}
    old_costs = read(V1 / "results/costs.json")
    summary = {"model_calls": 0, "runtime": sys.version, "cases": {}}
    for case in ("R04", "R05", "R06", "P3A_A", "P3A_B"):
        source = V1 / "cases" / case
        original = read(source / "original_payload.json")
        prior = read(source / "compact_payload.json")
        view, aliases = explicit_view(prior["memory"])
        metrics = validate_explicit(view, original["memory"], prior["memory"], aliases)
        messages = messages_v2(read(source / "original_messages.json"), view)
        payload = json.loads(messages[1]["content"])
        assert {k: v for k, v in payload.items() if k != "memory"} == {
            k: v for k, v in original.items() if k != "memory"}
        dest = HERE / "cases" / case
        save(dest / "compact_payload.json", payload)
        save(dest / "compact_messages.json", messages)
        save(dest / "audit_menu_aliases.json", aliases)
        save(dest / "verification.json", metrics)
        original_messages = read(source / "original_messages.json")
        old_messages = read(source / "compact_messages.json")
        costs = {}
        actual = old_costs["cases"][case]["original_actual_prompt_tokens"]
        for name, encoding in encodings.items():
            baseline = tokens(encoding, original_messages)
            v1_count, v2_count = tokens(encoding, old_messages), tokens(encoding, messages)
            costs[name] = {
                "original_actual_prompt_tokens": actual,
                "original_local_tokens": baseline, "v1_local_tokens": v1_count, "v2_local_tokens": v2_count,
                "v1_estimated_model_tokens": round(actual * v1_count / baseline),
                "v2_estimated_model_tokens": round(actual * v2_count / baseline),
                "v2_reduction_vs_original_percent": round(100 * (1 - v2_count / baseline), 2),
                "v2_increase_vs_v1_percent": round(100 * (v2_count / v1_count - 1), 2),
            }
        summary["cases"][case] = {"costs": costs, "verification": metrics}
        if case in ("R05", "R06"):
            questions, expected, changes = adapted_probe(original, prior, payload, case=case)
            # Check the base builder still matches the actual previous frozen experiment.
            from experiments.methods.v23_3.memory_compaction_live_validation_001.probes import build_probe
            old_questions, old_expected = build_probe(original, prior, case=case)
            assert old_questions == read(OLD_LIVE / "config" / case / "questions.json")
            assert old_expected == read(OLD_LIVE / "config" / case / "expected.json")
            save(dest / "questions.json", questions)
            save(dest / "expected.json", expected)
            save(dest / "question_changes.json", changes)
        print(case, costs["o200k_base"], flush=True)
    a, b = (read(HERE / "cases" / arm / "compact_messages.json") for arm in ("P3A_A", "P3A_B"))
    assert a[1] == b[1]
    summary["ab_user_equal"] = True
    save(HERE / "results/offline.json", summary)


if __name__ == "__main__":
    main()
