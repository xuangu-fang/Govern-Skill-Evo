"""Migration checks for frozen identity and filesystem location separation."""
import hashlib
import json
from pathlib import Path

import pytest

from src.skill_evolution.shared.experiment_paths import ROOT, resolve_experiment_path
from src.skill_evolution.v20.benchmark_adapter_v20 import load_frozen_pilot_config


def test_historical_identity_is_unchanged_and_resolves_from_other_cwd(tmp_path, monkeypatch):
    identity = 'experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md'
    monkeypatch.chdir(tmp_path)
    expected = ROOT / 'experiments/methods/v14/autonomous_gse_v14/config/skills/S0_empty_skill.md'
    assert resolve_experiment_path(identity) == expected
    assert resolve_experiment_path(ROOT / identity) == expected
    assert expected.is_file()
    config = json.loads((expected.parents[1] / 'campaign_manifest.json').read_text())
    assert config['initial_parent']['path'] == expected.relative_to(ROOT).as_posix()
    assert not (ROOT / identity).exists()


def test_version_prefixes_do_not_match_other_campaigns():
    identity = 'experiments/campaigns/autonomous_gse_v140/skills/S0.md'
    assert resolve_experiment_path(identity) == ROOT / identity


def test_current_paths_are_idempotent():
    path = ROOT / 'experiments/methods/v20/v20_pilot_001/config/config.json'
    assert resolve_experiment_path(path) == path


def test_paths_outside_checkout_remain_unchanged(tmp_path):
    path = tmp_path / 'experiments/configs/v20_pilot_001/config.json'
    assert resolve_experiment_path(path) == path


def test_raw_runtime_path_resolves_to_canonical_location():
    path = ROOT / 'experiments/v19/formal/v19_memory_formal_003'
    expected = ROOT / 'artifacts/methods/v19/formal/v19_memory_formal_003'
    assert resolve_experiment_path(path) == expected
    assert expected.exists()
    assert not path.exists()


def test_v20_keeps_v18_dependency_identity_and_hashes():
    config = load_frozen_pilot_config('experiments/methods/v20/v20_pilot_001/config/config.json')
    assert config['benchmark_freeze'] == 'experiments/methods/v18/v18_formal_003/config'
    freeze = resolve_experiment_path(config['benchmark_freeze'])
    assert freeze == ROOT / 'experiments/methods/v18/v18_formal_003/config'
    assert hashlib.sha256((freeze / 'config.json').read_bytes()).hexdigest() == config['benchmark_config_sha256']


def test_v20_still_rejects_changed_hash(tmp_path):
    config = load_frozen_pilot_config()
    config['benchmark_config_sha256'] = '0' * 64
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match='frozen benchmark file changed'):
        load_frozen_pilot_config(path)
