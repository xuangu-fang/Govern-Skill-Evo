"""Check the fresh worker profile and archived campaign without executing the Actor."""
import json
from pathlib import Path

from experiments.benchmark_record_refs.restore import Archive
from scripts.runs import run_v26_9_campaign as campaign
from tests.skill_evolution.v26_1.conftest import offline_only


def restore_test_checkpoint(root, archived, destination):
    """Materialize the published checkpoint required by final Test preparation."""
    state = campaign.ev.read(archived / 'state.json')
    last_result = f"rounds/R{state['next_round'] - 1:02}/result.json"
    files = [archived / name for name in (
        'config.json', 'initial_config.json', 'initial_memory.json', 'initial_skill.md',
        'implementation.json', 'runtime.json', 'state.json', 'final_skill.md',
        'memory/HEAD.json', last_result, state['parent'],
    )]
    files.extend((archived / 'memory/commits').glob('*.json'))
    archive = Archive('officeqa')
    try:
        for path in files:
            target = destination / path.relative_to(archived)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read_bytes(path.relative_to(root).as_posix()))
    finally:
        archive.close()


def test_current_config_and_archived_config_can_both_be_validated(tmp_path):
    root = Path(campaign.ROOT)
    archived = root / 'experiments/campaigns/v26_9_officeqa_train74_20261118_180409'
    restored = tmp_path / archived.name
    restore_test_checkpoint(root, archived, restored)
    old = json.loads((restored / 'config.json').read_text())
    new = json.loads((root / 'experiments/configs/v26_9_officeqa_train74.json').read_text())
    assert new == {**old, 'test_workers': 20} and old['test_workers'] == 4
    fresh = campaign.bind(new)
    with fresh.using():
        campaign.settings.validate_config(new, executable=True)
        assert campaign.settings.campaign_config(fresh)['test_workers'] == 20
        assert fresh.runtime_snapshot(new)['test_workers'] == 20 and fresh.workers == 10
        historic = campaign.bind(old)
        with historic.using():
            campaign.settings.validate_config(old, executable=True)
            assert historic.runtime_snapshot(old) == campaign.ev.read(restored / 'runtime.json')
            # The archived config says four, while its independent Test used twenty.
            manifest = campaign.prepare_test(restored, tmp_path / 'archive-check')
            assert len(manifest['tasks']) == 172 and manifest['workers'] == 20
        assert campaign.settings.campaign_config(fresh)['test_workers'] == 20
    assert not (tmp_path / 'archive-check').exists()
