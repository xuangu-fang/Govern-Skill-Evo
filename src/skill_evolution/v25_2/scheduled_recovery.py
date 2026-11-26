"""One-time extra-three request grants; original budgets remain in configuration."""
import json
from pathlib import Path

def limit(directory, base, slot=None):
    filename = 'recovery_extra3.json' if slot is None else f'recovery_slot_{slot:03}.json'
    path = Path(directory) / filename
    if not path.exists():
        return base
    grant = json.loads(path.read_text())
    expected = {'schema': 'scheduled_extra3_v1', 'target': str(Path(directory).resolve()),
                'base_limit': base, 'extra': 3, 'slot': slot}
    if grant != expected:
        raise ValueError('Invalid recovery grant')
    return base + 3
