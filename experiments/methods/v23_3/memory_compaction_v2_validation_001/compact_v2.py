"""Two representation changes only: explicit step states and direct global menus."""
from copy import deepcopy

from experiments.methods.v23_3.memory_compaction_offline_001.compact import (
    compact_memory, validate_view,
)


FORMAT = "memory_evidence_view_v2"


def explicit_view(v1):
    """Preserve v1 selection and pool IDs. Return model view and audit-only aliases."""
    assert v1["format"] == "memory_evidence_view_v1"
    assert v1["policy"]["shared_menus"] is True
    result, aliases = deepcopy(v1), {}
    result["format"] = FORMAT
    for key, source in result["sources"].items():
        if key.endswith("/diff"):
            continue
        local = source.pop("command_sets")
        aliases[key] = deepcopy(local)

        def state(value):
            value = deepcopy(value)
            cid = value["commands_ref"]
            value["commands_ref"] = None if cid is None else local[cid]
            return value

        source["run"]["initial"] = state(source["run"]["initial"])
        details, windows = [], []
        context = key.rsplit("/", 1)[0]
        for window in source["windows"]:
            windows.append({"start": window["start"], "end": window["end"]})
            previous = window["before"]
            for i, after in enumerate(window["after"], window["start"]):
                trace = source["run"]["trace"][i - 1]
                details.append({
                    "step": f"{context}/{trace['step']}",
                    "before": state(previous), "action": trace["action"], "after": state(after),
                })
                previous = after
        source["windows"] = windows
        source["detailed_steps"] = details
    return result, aliases


def make_view(original):
    v1 = compact_memory(original)
    v2, aliases = explicit_view(v1)
    validate_explicit(v2, original, v1, aliases)
    return v2, aliases


def validate_explicit(v2, original, v1, aliases):
    """Compare every delivered fact/menu with full archive and v1's visibility."""
    metrics = validate_view(v1, original)
    assert v2["format"] == FORMAT
    for field in ("policy", "entries", "command_pool"):
        assert v2[field] == v1[field], f"{field} changed"
    assert set(v2["sources"]) == set(v1["sources"])
    assert set(aliases) == {k for k in v1["sources"] if not k.endswith("/diff")}
    for key, source in v2["sources"].items():
        old, full = v1["sources"][key], original["sources"][key]
        if key.endswith("/diff"):
            assert source == old == full
            continue
        assert set(source) == (set(old) - {"command_sets"}) | {"detailed_steps"}
        assert aliases[key] == old["command_sets"]
        for field in ("detail_reason", "detail_coverage", "omitted_detail_ranges"):
            assert source[field] == old[field]
        assert source["windows"] == [{"start": w["start"], "end": w["end"]} for w in old["windows"]]
        assert set(source["run"]) == set(old["run"])
        for field in ("ref", "task", "trace", "outcome"):
            assert source["run"][field] == old["run"][field]

        def check_state(actual, archived):
            assert set(actual) == {"observation", "commands_ref"}
            assert actual["observation"] == archived["observation"]
            cid = archived["commands_ref"]
            expected = None if cid is None else aliases[key][cid]
            assert actual["commands_ref"] == expected
            if expected is not None:
                assert v2["command_pool"][expected] == full["command_sets"][cid]

        check_state(source["run"]["initial"], full["run"]["initial"])
        selected = [i for w in old["windows"] for i in range(w["start"], w["end"] + 1)]
        assert len(source["detailed_steps"]) == len(selected)
        context = key.rsplit("/", 1)[0]
        for number, detail in zip(selected, source["detailed_steps"]):
            archived = full["run"]["steps"][number - 1]
            assert set(detail) == {"step", "before", "action", "after"}
            assert detail["step"] == f"{context}/{archived['step']}"
            assert detail["action"] == archived["action"]
            check_state(detail["before"], archived["before"])
            check_state(detail["after"], archived["after"])
    return {**metrics, "same_detail_selection_as_v1": True,
            "same_raw_facts_and_resolved_menus_as_v1": True}
