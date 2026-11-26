"""Check the published Actor-aligned configuration, without model or Docker calls."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.binding import components
from src.skill_evolution.skilladam.spreadsheetbench.layout import ALIGNED_CONFIG


def verify():
    native, bridge, shared, optimizer = components()
    validation = native.validate(bridge, shared, optimizer)
    assert (ALIGNED_CONFIG/'initial_skill.md').read_text() == shared['initial_skill']['text']
    cfg = bridge.read(ALIGNED_CONFIG/'evaluation/config.json')
    bridge.SharedAdapter().validate_config(cfg)
    assert cfg['test_tasks'] == shared['test_tasks'] and len(set(cfg['test_tasks'])) == 280
    return dict(status='passed', training_tasks=sum(map(len, shared['batches'])), test_tasks=len(cfg['test_tasks']),
                policy=validation, model_requests=0)


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
