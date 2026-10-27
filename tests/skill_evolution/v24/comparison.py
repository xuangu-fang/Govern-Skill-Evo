"""Compare unchanged behavior while accounting for declared input/Prompt changes.

Only Preconditioner template text and its Grouping field are normalized here;
the rendered Actor context, runs, command sets, Plan and Memory remain compared.
"""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def preconditioner_templates():
    root = Path(__file__).resolve().parents[3]
    relative = Path('src/skill_evolution/v24/benchmarks/alfworld/prompts/v23_5')
    frozen = root/'experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/code'
    return [(p.read_text().split('{{execution_context}}'),
             (frozen/relative/p.name).read_text().split('{{execution_context}}'))
            for p in sorted((root/relative).glob('preconditioner*.md'))]


def behavior(value):
    if isinstance(value, str):
        if value.startswith('# Preconditioner\n'):
            for (prefix, suffix), (old_prefix, old_suffix) in preconditioner_templates():
                if value.startswith(prefix) and suffix in value:
                    assert value.count(suffix) == 1
                    return old_prefix + value[len(prefix):].replace(suffix, old_suffix)
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            return value
        return behavior(decoded) if isinstance(decoded, (dict, list)) else value
    if isinstance(value, (list, tuple)):
        return [behavior(v) for v in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {'parent', 'plan', 'command_sets', 'runs', 'grouping', 'memory'}:
        value = {k: v for k, v in value.items() if k != 'grouping'}
    if 'repository' in value and 'files' in value:
        value = {k: v for k, v in value.items() if k != 'commit'}
        value['files'] = {k: {f: row[f] for f in ('source_path', 'source_url') if f in row}
                          for k, row in value['files'].items()}
    if 'mode' in value and 'text' in value and 'source' in value:
        value = {k: value[k] for k in ('mode', 'text', 'source')}
    if 'background' in value and 'actor_model' in value and 'protocol' in value:
        value = {k: v for k, v in value.items() if k != 'backend_id'}
    if 'path' in value and len(value) == 2 and all(isinstance(v, str) for v in value.values()):
        value = {'path': value['path']}
    return {k: behavior(v) for k, v in value.items()}
