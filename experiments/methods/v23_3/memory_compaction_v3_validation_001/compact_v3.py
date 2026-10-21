"""Qualify all trace step IDs; preserve every v2 fact and selection."""
from copy import deepcopy

from experiments.methods.v23_3.memory_compaction_v2_validation_001.compact_v2 import (
    explicit_view as v2_view, validate_explicit as validate_v2,
)

FORMAT = "memory_evidence_view_v3"


def qualify(source, step):
    context, run = source.rsplit("/", 1)
    assert step.startswith(run + ":") and step.count(":") == 1 and "/" not in step
    assert step.split(":")[1].isdigit()
    return context + "/" + step


def explicit_view(v1):
    view, aliases = v2_view(v1)
    view["format"] = FORMAT
    for key, source in view["sources"].items():
        if "run" in source:
            for row in source["run"]["trace"]:
                row["step"] = qualify(key, row["step"])
    return view, aliases


def validate_explicit(view, original, v1, aliases):
    expected, expected_aliases = explicit_view(v1)
    assert view == expected and aliases == expected_aliases
    restored = deepcopy(view)
    restored["format"] = "memory_evidence_view_v2"
    all_ids = set()
    for key, source in restored["sources"].items():
        if "run" not in source:
            continue
        rows = {row["step"]: row for row in source["run"]["trace"]}
        assert len(rows) == len(source["run"]["trace"])
        assert not all_ids.intersection(rows)
        all_ids.update(rows)
        for detail in source["detailed_steps"]:
            assert detail["step"] in rows
            assert detail["action"] == rows[detail["step"]]["action"]
        for row in source["run"]["trace"]:
            assert row["step"].startswith(key + ":")
            row["step"] = row["step"].split("/", 1)[1]
    result = validate_v2(restored, original, v1, aliases)
    return {**result, "same_facts_as_v2_after_id_normalization": True,
            "unique_qualified_trace_ids": len(all_ids)}
