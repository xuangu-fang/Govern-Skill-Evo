"""Preserve the initial Skill's Pick Two clauses in each adoptable patch."""

from src.skill_evolution.v24_2 import method
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v28_5.editor import construct_selected


# The entire lines are rules for acquisition, counting, placement and delivery.
# Behavioral overrides elsewhere are also reviewed by Preconditioner and Editor.
PREFIXES = ('| Pick Two & Place |', '3. **Grab immediately**:', '5. **Direct delivery**:',
            '6. **Track progress**:', '- **Ignoring visible objects**:', '- **Premature termination**:')


def check_scope(parent, skill):
    for prefix in PREFIXES:
        original = [line for line in parent.splitlines() if line.startswith(prefix)]
        retained = [line for line in skill.splitlines() if line.startswith(prefix)]
        require(len(original) == 1 and original == retained,
                f'Preserve the original Pick Two rule line beginning {prefix}')


def edit(result, payload):
    built = method.edit(result, payload)
    if built['editor_status'] == 'candidate':
        parent = payload['parent']
        check_scope(parent, built['candidate_text'])
        if len(result['edits']) > 1:
            for item in result['edits']:
                if item['patch']:
                    single = construct_selected(result, payload, [item['update_id']])
                    check_scope(parent, single['selected_text'])
    return built
