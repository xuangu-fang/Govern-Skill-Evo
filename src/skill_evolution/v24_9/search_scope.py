"""Limit actual Skill text edits to the body of General Principle 2."""
from src.skill_evolution.v24_2 import method
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v28_5.editor import construct_selected


def protected_text(skill):
    start = '\n2. **Systematic exploration**:'
    end = '\n3. **Grab immediately**:'
    require(skill.count(start) == 1 and skill.count(end) == 1,
            'Preserve both original headings of principles 2 and 3')
    prefix, _, rest = skill.partition(start)
    body, boundary, suffix = rest.partition(end)
    require(boundary and body.strip(), 'Keep a nonempty search passage before principle 3')
    return prefix + start, end + suffix


def check_scope(parent, skill):
    require(protected_text(skill) == protected_text(parent),
            'Edit only the body of principle 2 (Systematic exploration)')


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
