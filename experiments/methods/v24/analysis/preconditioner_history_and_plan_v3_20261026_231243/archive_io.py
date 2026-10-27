"""Locate this replay's complete archive without loading experiment code."""
import json
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parent
ROOT = EXPERIMENT.parents[4]
ARCHIVE = ROOT / 'artifacts/methods/v24/analysis' / EXPERIMENT.name


def resolve_path(path):
    """Accept an absolute or repository-relative path; map old replay paths."""
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    try:
        relative = path.relative_to(EXPERIMENT)
    except ValueError:
        return path
    return ARCHIVE / relative


def read_json(path):
    return json.loads(resolve_path(path).read_text(encoding='utf-8'))


def selected_attempt(case):
    """Return the complete attempt selected by the original result record."""
    stage = ARCHIVE / case / 'preconditioner'
    selected = read_json(stage / 'result.json')['path']
    return resolve_path(stage / selected)
