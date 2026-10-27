from copy import deepcopy
from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.grouping import validate_grouping

def diagnosis_input(saved):
    """Reuse the complete Grouping facts without private sources or any new summary."""
    require(set(saved["facts"]) == {"parent", "command_sets", "runs"}, "Unexpected shared fact fields")
    validate_grouping(saved["grouping"], saved["facts"])
    return deepcopy({**saved["facts"], "grouping": saved["grouping"]})
