"""Independent snapshot of the v14 parent rule layout and bounded edits."""
from .information_boundary_v15 import BoundaryError
SECTIONS = ('Planning and navigation', 'Execution patterns', 'Form entry and verification', 'Error recovery and stopping')
MAX_RULES = 18
MAX_WORDS = 900


def parse_skill(text):
    if not isinstance(text, str) or not text.strip():
        raise BoundaryError('Empty Parent Skill')
    lines = text.splitlines()
    if lines[0] not in ('# Operational Skill', '# SuiteCRM Operational Skill'):
        raise BoundaryError('Invalid Skill title')
    if [l[3:] for l in lines if l.startswith('## ')] != list(SECTIONS):
        raise BoundaryError('Invalid Skill sections')
    sections = {s: [] for s in SECTIONS}
    current, number = None, 0
    for line in lines[1:]:
        if not line.strip():
            continue
        if line.startswith('## '):
            current = line[3:]
        elif line.startswith('- ') and current:
            number += 1
            sections[current].append({'rule_id': f'rule_{number:03d}', 'clause': line[2:]})
        else:
            raise BoundaryError('Only bullet rules are supported')
    if number > MAX_RULES or len(text.split()) > MAX_WORDS:
        raise BoundaryError('Skill budget exceeded')
    return sections


def render_skill(sections, title='# Operational Skill'):
    lines = [title, '']
    for section, rules in sections.items():
        lines += ['## ' + section, ''] + ['- ' + r['clause'] for r in rules] + ['']
    result = '\n'.join(lines)
    parse_skill(result)
    return result
