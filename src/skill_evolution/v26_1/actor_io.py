"""Small I/O helpers; execution uses the unchanged shared OfficeQA journal."""
import json
from pathlib import Path
from .protocol import require


def read_skill(path):
    return None if path is None else Path(path).read_bytes().decode('utf-8')


def completed_journal(folder, tasks):
    path = Path(folder) / 'actor/results.jsonl'
    if not path.exists(): return False
    done = set()
    with path.open('rb') as handle:
        for line in handle:
            if not line.endswith(b'\n'): break
            row = json.loads(line)
            require(row['id'] == row['record']['task_id'] and row['id'] not in done, 'Invalid Actor journal')
            done.add(row['id'])
    require(done <= set(tasks), 'Unexpected Actor journal task')
    return done == set(tasks)
