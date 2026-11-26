"""Record the size of the selected Skill alongside each round's outcomes."""
from pathlib import Path

from ..v26_3.reporting import compare_tests, costs, pending_test, training_rounds as previous_rounds
from .actor_io import read_skill


def training_rounds(root, *, directories=None, use_cache=True):
    paths = sorted((Path(root) / 'rounds').glob('R*')) if directories is None else list(directories)
    rows = previous_rounds(root, directories=paths, use_cache=use_cache)
    for directory, row in zip(paths, rows):
        if row['status'] == 'completed':
            skill = read_skill(directory / 'selected.md')
            row['selected_skill_chars'] = len(skill)
            row['selected_skill_bullets'] = sum(line.startswith('- ') for line in skill.splitlines())
    return rows
