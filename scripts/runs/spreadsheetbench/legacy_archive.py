"""Apply verified SpreadsheetBench record expansion to older bundle validators."""
from functools import wraps
from hashlib import sha256
import json
from pathlib import Path
import sys

from scripts.runs.spreadsheetbench.verify_archive import ROOT, require
from src.skill_evolution.shared.offline_records import offline_records


def check_publications(run, final_skill, path_type=None):
    rows = json.loads((run / 'results/publications.json').read_bytes())
    require([row['round'] for row in rows] == [f'R{i:02}' for i in range(9)],
            f'Publication index differs: {run}')
    for row in rows:
        expected = f'results/skills/{row["round"]}.md'
        require(row['skill'] == expected, f'Unexpected publication path: {run}')
        skill = (run / expected).read_bytes()
        require(sha256(skill).hexdigest() == row['sha256'], f'Publication differs: {run}/{expected}')
        if path_type is not None:
            source = path_type(ROOT / row['source']).read_bytes()
            if 'field' in row:
                source = json.loads(source)[row['field']].encode()
            require(skill == source, f'Original publication differs: {run}/{expected}')
    require(skill == final_skill, f'Final publication differs: {run}')


def read_records(verify):
    @wraps(verify)
    def read_bundle(*args, **kwargs):
        with offline_records('spreadsheetbench', sys.modules[verify.__module__]):
            return verify(*args, **kwargs)

    return read_bundle
