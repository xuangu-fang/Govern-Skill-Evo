from copy import deepcopy
import json
import re
from src.skill_evolution.v24.contracts.diagnosis import diagnosis_input, validate_diagnosis
from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.grouping import references
from src.skill_evolution.v24.contracts.memory import empty_memory, validate_memory, LEGACY_CONTRACT

def preconditioner_input(saved, *, memory=None, memory_contract=LEGACY_CONTRACT):
    """Select whole referenced executions without expanding Group membership."""
    memory = deepcopy(saved.get("memory", empty_memory()) if memory is None else memory)
    validate_memory(memory, memory_contract=memory_contract)
    facts = diagnosis_input(saved)
    validate_diagnosis(saved["diagnosis"], facts)
    require(saved["diagnosis"]["decision"] == "revise", "Preconditioner requires a revise Diagnosis")
    plan = saved["diagnosis"]["plan"]
    encoded = json.dumps(plan, ensure_ascii=False)
    run_ids = {ref.split(":", 1)[0] for ref in references(encoded)}
    group_ids = set(re.findall(r"\bG\d+\b", encoded))
    runs = [run for run in facts["runs"] if run["ref"] in run_ids]
    groups = [g for g in facts["grouping"]["groups"]
              if g["group_id"] in group_ids or run_ids.intersection(g["members"])]
    menus = set()
    for run in runs:
        for state in [run["initial"], *[s[side] for s in run["steps"] for side in ("before", "after")]]:
            if state["commands_ref"] is not None:
                menus.add(state["commands_ref"])
    return deepcopy({"parent": facts["parent"], "plan": plan,
                     "command_sets": {k: v for k, v in facts["command_sets"].items() if k in menus},
                     "runs": runs, "grouping": {"groups": groups}, "memory": memory})
