"""Offline model-input view. Does not replace V23 Memory or its validators."""
from copy import deepcopy
import json

from src.skill_evolution.v23.memory import validate_memory


FORMAT = "memory_evidence_view_v1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ranges(numbers):
    """Inclusive, sorted, disjoint ranges; adjacent windows are merged."""
    result = []
    for n in sorted(set(numbers)):
        if result and n == result[-1][1] + 1:
            result[-1][1] = n
        else:
            result.append([n, n])
    return result


def anchors_for(memory):
    anchors = {}
    for entry in memory["entries"]:
        for ref in entry["evidence"]:
            context, local = ref.rsplit("/", 1)
            if local == "diff":
                continue
            run_id, _, position = local.partition(":")
            positions = anchors.setdefault(f"{context}/{run_id}", set())
            if position.isdecimal():
                positions.add(int(position))
    return anchors


def compact_memory(memory, *, radius=2, full=False, shared_menus=True):
    """Deterministic projection, without semantic ranking or generated summaries.

    With full=True, preserve every state and original command table. The compact
    full representation can be restored exactly. Window mode intentionally omits
    detailed states/menus outside the declared windows, never actions/feedback.
    """
    validate_memory(memory)
    require(type(radius) is int and radius >= 0, "radius must be a nonnegative integer")
    view = {
        "format": FORMAT,
        "policy": {"radius": radius, "full": full, "shared_menus": shared_menus},
        "entries": deepcopy(memory["entries"]),
        "sources": {},
        "command_pool": {},
    }
    anchors = anchors_for(memory)
    menu_ids = {}

    def menu_value(commands):
        if not shared_menus:
            return deepcopy(commands)
        encoded = json.dumps(commands, ensure_ascii=False, separators=(",", ":"))
        if encoded not in menu_ids:
            mid = f"menu_{len(menu_ids) + 1}"
            menu_ids[encoded] = mid
            view["command_pool"][mid] = deepcopy(commands)
        return menu_ids[encoded]

    for key, source in memory["sources"].items():
        if key.endswith("/diff"):
            view["sources"][key] = deepcopy(source)
            continue
        run = source["run"]
        n = len(run["steps"])
        localized = anchors.get(key, set())
        complete = full or not localized
        selected = set(range(1, n + 1)) if complete else {
            step for anchor in localized
            for step in range(max(1, anchor - radius), min(n, anchor + radius) + 1)
        }
        windows, states = [], [run["initial"]]
        for start, end in ranges(selected):
            before = run["steps"][start - 1]["before"]
            after = [s["after"] for s in run["steps"][start - 1:end]]
            windows.append({"start": start, "end": end,
                            "before": deepcopy(before), "after": deepcopy(after)})
            states.extend([before, *after])
        used = {state["commands_ref"] for state in states} - {None}
        # Full mode also preserves unused original menu keys, if any.
        menus = {cid: menu_value(commands) for cid, commands in source["command_sets"].items()
                 if complete or cid in used}
        view["sources"][key] = {
            "run": {
                "ref": run["ref"], "task": run["task"],
                "initial": deepcopy(run["initial"]),
                "trace": [{k: deepcopy(s[k]) for k in ("step", "action", "feedback")}
                          for s in run["steps"]],
                "outcome": deepcopy(run["outcome"]),
            },
            "detail_reason": ("full_baseline" if full else
                              "unlocalized_reference" if not localized else "reference_windows"),
            "detail_coverage": "complete" if len(selected) == n else "partial",
            "windows": windows,
            "omitted_detail_ranges": ranges(set(range(1, n + 1)) - selected),
            # Local C IDs are scoped to this source; values refer to shared exact lists.
            "command_sets": menus,
        }
    return view


def menus_for(view, source):
    if view["policy"]["shared_menus"]:
        return {cid: view["command_pool"][mid] for cid, mid in source["command_sets"].items()}
    return source["command_sets"]


def validate_view(view, original):
    """Check raw facts, windows, references and namespaces against the archive."""
    validate_memory(original)
    require(view["format"] == FORMAT, "Unexpected view format")
    require(view["entries"] == original["entries"], "Memory entries changed")
    require(set(view["sources"]) == set(original["sources"]), "Historical sources changed")
    radius, full = view["policy"]["radius"], view["policy"]["full"]
    require(type(radius) is int and radius >= 0, "Invalid radius")
    require(type(full) is bool and type(view["policy"]["shared_menus"]) is bool, "Invalid policy")
    anchors = anchors_for(original)
    counts = {"runs": 0, "steps": 0, "detailed_steps": 0, "full_runs": 0,
              "fallback_full_runs": 0, "edit_sources": 0, "windows": 0}
    used_pool = set()
    for key, old in original["sources"].items():
        source = view["sources"][key]
        if key.endswith("/diff"):
            require(source == old, "Historical edit/context changed")
            counts["edit_sources"] += 1
            continue
        run, projected = old["run"], source["run"]
        for field in ("ref", "task", "initial", "outcome"):
            require(projected[field] == run[field], f"{key}: {field} changed")
        trace = [{k: s[k] for k in ("step", "action", "feedback")} for s in run["steps"]]
        require(projected["trace"] == trace, f"{key}: action/feedback sequence changed")
        n, detailed, last_end = len(trace), set(), 0
        states = [projected["initial"]]
        for window in source["windows"]:
            start, end = window["start"], window["end"]
            require(type(start) is int and type(end) is int and last_end < start <= end <= n,
                    f"{key}: invalid window coordinates")
            require(window["before"] == run["steps"][start - 1]["before"],
                    f"{key}: window start state changed")
            expected = [s["after"] for s in run["steps"][start - 1:end]]
            require(window["after"] == expected, f"{key}: window states changed")
            detailed.update(range(start, end + 1))
            states.extend([window["before"], *window["after"]])
            last_end = end
        localized = anchors.get(key, set())
        expected_steps = set(range(1, n + 1)) if full or not localized else {
            i for i in range(1, n + 1) if any(abs(i - anchor) <= radius for anchor in localized)
        }
        require(detailed == expected_steps, f"{key}: detail selection differs from policy")
        require([[w["start"], w["end"]] for w in source["windows"]] == ranges(detailed),
                f"{key}: windows not merged")
        require(source["omitted_detail_ranges"] == ranges(set(range(1, n + 1)) - detailed),
                f"{key}: omitted detail ranges incorrect")
        require(source["detail_coverage"] == ("complete" if len(detailed) == n else "partial"),
                f"{key}: completeness falsely declared")
        reason = "full_baseline" if full else "unlocalized_reference" if not localized else "reference_windows"
        require(source["detail_reason"] == reason, f"{key}: fallback reason incorrect")
        used = {s["commands_ref"] for s in states} - {None}
        menus = menus_for(view, source)
        expected_keys = set(old["command_sets"]) if full or not localized else used
        require(set(menus) == expected_keys, f"{key}: missing/extra visible command menus")
        require(all(menus[cid] == old["command_sets"][cid] for cid in menus),
                f"{key}: menu contents or source namespace changed")
        if view["policy"]["shared_menus"]:
            used_pool.update(source["command_sets"].values())
        counts["runs"] += 1
        counts["steps"] += n
        counts["detailed_steps"] += len(detailed)
        counts["full_runs"] += len(detailed) == n
        counts["fallback_full_runs"] += not full and not localized
        counts["windows"] += len(source["windows"])
    require(used_pool == set(view["command_pool"]), "Unused/missing global menu definitions")
    return counts


def restore_complete_memory(view):
    """Refuse to reconstruct unobserved states from a partial model-input view."""
    restored = {"entries": deepcopy(view["entries"]), "sources": {}}
    for key, source in view["sources"].items():
        if key.endswith("/diff"):
            restored["sources"][key] = deepcopy(source)
            continue
        require(source["detail_coverage"] == "complete", "Cannot restore omitted historical states")
        run = source["run"]
        states = {}
        for w in source["windows"]:
            states.update({w["start"] + i: state for i, state in enumerate(w["after"])})
        steps, previous = [], run["initial"]
        for i, item in enumerate(run["trace"], 1):
            require(i in states, "Missing state in complete view")
            steps.append({**deepcopy(item), "before": deepcopy(previous), "after": deepcopy(states[i])})
            previous = states[i]
        restored["sources"][key] = {
            "run": {k: deepcopy(run[k]) for k in ("ref", "task", "initial", "outcome")},
            "command_sets": deepcopy(menus_for(view, source)),
        }
        restored["sources"][key]["run"]["steps"] = steps
    validate_memory(restored)
    return restored
