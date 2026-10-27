from copy import deepcopy
import json
from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.memory import validate_memory, entry_evidence, LEGACY_CONTRACT
from src.skill_evolution.v24.contracts.memory_view import FORMAT, ranges

def compact_memory(memory, *, memory_contract=LEGACY_CONTRACT):
    """Fixed ±2 citation windows, exact menus, explicit states and qualified IDs.

    Preserve all actions and feedback. Sources without numeric citations retain
    all detailed steps. Outcome citations alone do not localize a state window.
    """
    validate_memory(memory, memory_contract=memory_contract)
    anchors = {}
    for entry in memory["entries"]:
        for ref in entry_evidence(entry, memory_contract=memory_contract):
            context, local = ref.rsplit("/", 1)
            if local == "diff":
                continue
            run, _, position = local.partition(":")
            positions = anchors.setdefault(f"{context}/{run}", set())
            if position.isdecimal():
                positions.add(int(position))
    view = {"format": FORMAT, "policy": {"radius": 2, "full": False, "shared_menus": True},
            "entries": deepcopy(memory["entries"]), "sources": {}, "command_pool": {}}
    menu_ids = {}
    for key, source in memory["sources"].items():
        if key.endswith("/diff"):
            view["sources"][key] = deepcopy(source)
            continue
        run = source["run"]
        count = len(run["steps"])
        localized = anchors.get(key, set())
        selected = set(range(1, count + 1)) if not localized else {
            n for anchor in localized
            for n in range(max(1, anchor - 2), min(count, anchor + 2) + 1)}
        states = [run["initial"]]
        for n in sorted(selected):
            states.extend(run["steps"][n - 1][side] for side in ("before", "after"))
        used = {s["commands_ref"] for s in states} - {None}
        aliases = {}
        # Preserve established pool numbering, including unused menus in full-detail sources.
        for cid, commands in source["command_sets"].items():
            if localized and cid not in used:
                continue
            encoded = json.dumps(commands, ensure_ascii=False, separators=(",", ":"))
            if encoded not in menu_ids:
                mid = f"menu_{len(menu_ids) + 1}"
                menu_ids[encoded] = mid
                view["command_pool"][mid] = deepcopy(commands)
            aliases[cid] = menu_ids[encoded]

        def state(value):
            return {"observation": value["observation"],
                    "commands_ref": None if value["commands_ref"] is None else aliases[value["commands_ref"]]}

        context = key.rsplit("/", 1)[0]
        trace, details = [], []
        for n, step in enumerate(run["steps"], 1):
            qualified = f"{context}/{step['step']}"
            require(qualified == f"{key}:{n}", "Historical step/source identity differs")
            trace.append({"step": qualified, "action": step["action"],
                          "feedback": deepcopy(step["feedback"])})
            if n in selected:
                details.append({"step": qualified, "before": state(step["before"]),
                                "action": step["action"], "after": state(step["after"])})
        view["sources"][key] = {
            "run": {"ref": run["ref"], "task": run["task"], "initial": state(run["initial"]),
                    "trace": trace, "outcome": deepcopy(run["outcome"])},
            "detail_reason": "reference_windows" if localized else "unlocalized_reference",
            "detail_coverage": "complete" if len(selected) == count else "partial",
            "windows": [{"start": start, "end": end} for start, end in ranges(selected)],
            "omitted_detail_ranges": ranges(set(range(1, count + 1)) - selected),
            "detailed_steps": details,
        }
    return view

