"""Parent facts and archive checks, independent of model analysis."""
from copy import deepcopy

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v28.benchmarks.searchqa.facts import validate_saved


def validate_parent_bundle(saved):
    """Retain full-batch archive checks; never accept a legacy Grouping handoff."""
    require(isinstance(saved, dict) and 'grouping' not in saved,
            'v28.5 Parent evidence cannot contain Grouping')
    with current().memory_operation():
        validate_saved(saved)
    return saved


def build_parent_bundle(records, round_id):
    text(round_id, 'round ID')
    with current().memory_operation():
        saved = current().build_facts(records, role='parent')
        validate_parent_bundle(saved)
    return {**deepcopy(saved), 'round_id': round_id}
