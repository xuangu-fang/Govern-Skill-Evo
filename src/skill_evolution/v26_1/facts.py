"""Registered full-batch OfficeQA facts without Grouping or gold-answer exposure."""
from copy import deepcopy
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.facts import text
from .protocol import require, fields, equal


def validate_parent_bundle(saved):
    require(isinstance(saved, dict) and 'grouping' not in saved, 'Grouping is unavailable')
    fields(saved['facts'], ('parent', 'runs'), 'Facts')
    with current().memory_operation():
        records = [current().source_record(run['run_id']) for run in saved['facts']['runs']]
        expected = current().build_facts(records, role='parent')
        for key in ('facts', 'background'):
            require(equal(saved[key], expected[key]), 'Saved Parent evidence differs')
        if 'sources' in saved:
            require(equal(saved['sources'], expected['sources']), 'Saved sources differ')
    return saved


def build_parent_bundle(records, round_id):
    text(round_id, 'round ID')
    with current().memory_operation():
        saved = current().build_facts(records, role='parent')
        validate_parent_bundle(saved)
    return {**deepcopy(saved), 'round_id': round_id}
