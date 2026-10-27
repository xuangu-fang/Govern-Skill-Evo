"""Behavior comparison excludes only the removed runtime bookkeeping."""
import json


def behavior(value):
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            return value
        return behavior(decoded) if isinstance(decoded, (dict, list)) else value
    if isinstance(value, (list, tuple)):
        return [behavior(v) for v in value]
    if not isinstance(value, dict):
        return value
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
