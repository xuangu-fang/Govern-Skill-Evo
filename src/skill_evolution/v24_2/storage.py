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
    from src.skill_evolution.shared.experiment_paths import resolve_experiment_path

    if not isinstance(saved.get('files'), dict) or not isinstance(current.get('files'), dict):
        return False
    root = Path(__file__).resolve().parents[3]
    files = saved['files']
    layouts = {}
    versions = {Path(name).parts[2] for name in files if name.startswith('src/skill_evolution/v24_')}
    for version in versions:
        path = root / 'experiments/methods' / version / 'layout-change.json'
        if path.is_file():
            layouts.update(read(path)['source_revisions'])
    translated = {}
    for name, revision in files.items():
        change = layouts.get(name)
        if change and (revision == change['before'] or revision in change.get('intermediate', [])):
            revision = change['after']
        if name.startswith('docs/methods/v24_') and '/prompts/' in name:
            name = str(resolve_experiment_path(name).relative_to(root))
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
