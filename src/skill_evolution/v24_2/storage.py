"""Immutable round artifacts and atomic replacements for publication pointers."""
import json
from pathlib import Path
from src.skill_evolution.v24_1.storage import write_record
from src.skill_evolution.v24_1.facts import require


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    write_record(path, value)


def same_contract(saved, current):
    """Allow the recorded layout-only revision when reading a pre-move campaign."""
    if saved == current:
        return True
    files = saved.get('files', {})
    old_prompts = 'docs/methods/v24_2/prompts/'
    if not any(p.startswith(old_prompts) for p in files):
        return False
    root = Path(__file__).resolve().parents[3]
    changes = read(root / 'experiments/methods/v24_2/layout-change.json')['source_revisions']
    translated = {}
    for name, revision in files.items():
        if name in changes and revision == changes[name]['before']:
            revision = changes[name]['after']
        if name.startswith(old_prompts):
            name = 'src/skill_evolution/v24_2/prompts/' + name[len(old_prompts):]
        if name in translated:
            return False
        translated[name] = revision
    return dict(saved, files=translated) == current


def freeze(path, value, *, read_only=False):
    if path.exists():
        saved = read(path)
        matches = (same_contract(saved, value) if path.name == 'contract.json' and isinstance(saved, dict)
                   else json.dumps(saved, sort_keys=True) == json.dumps(value, sort_keys=True))
        require(matches, f'Frozen artifact differs: {path}')
    else:
        require(not read_only, f'Missing artifact: {path}')
        save(path, value)


def freeze_text(path, value):
    if path.exists():
        require(path.read_bytes() == value.encode(), f'Frozen text differs: {path}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_bytes(value.encode())
        temporary.replace(path)
