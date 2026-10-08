import json
from pathlib import Path

import pytest

from src.skill_evolution.benchmark_adapter_v20 import (
    BenchmarkAdapterRejected,
    BenchmarkAdapterV20,
    DEFAULT_CONFIG,
    load_frozen_pilot_config,
)


def test_frozen_config_and_real_backend_manifests_are_bound():
    config = load_frozen_pilot_config(DEFAULT_CONFIG)
    adapter = BenchmarkAdapterV20.from_config(DEFAULT_CONFIG)
    manifest = adapter.manifest()
    assert config['round_limit'] == 2 and config['seed'] == 200
    assert manifest['schema_version'] == 'benchmark_adapter_manifest_v20.1'
    assert manifest['evolution_task_ids'] == config['evolution_task_ids']
    assert manifest['monitor_task_ids'] == config['monitor_task_ids']
    assert len(adapter.pilot_task_manifest()) == 36


class FakeBackend:
    def __init__(self, tasks, schema):
        self.tasks = tasks
        self.schema = schema

    def manifest(self):
        return {'schema_version': self.schema, 'task_ids': list(self.tasks), 'seed': 200,
                'runtime': {'fake': True}}

    def preflight(self, *, artifact_dir, skills):
        Path(artifact_dir).mkdir(parents=True)
        return {'status': 'PREFLIGHT', 'task_count': len(self.tasks),
                'prepared_instances': len(self.tasks) * len(skills), 'model_calls': 0}


def test_preflight_writes_zero_model_call_report_with_private_split(tmp_path):
    adapter = BenchmarkAdapterV20.from_config(
        evolution=FakeBackend(load_frozen_pilot_config(DEFAULT_CONFIG)['evolution_task_ids'],
                              'evolution_manifest_v19.1'),
        monitor=FakeBackend(load_frozen_pilot_config(DEFAULT_CONFIG)['monitor_task_ids'],
                            'monitor_manifest_v19.1'),
    )
    report = adapter.preflight(output=tmp_path / 'preflight')
    assert report['model_calls'] == 0
    assert report['claim_boundary'] == 'NO_MODEL_ROLLOUTS_NO_MECHANISM_RESULT'
    assert (tmp_path / 'preflight' / 'evolution').exists()
    assert (tmp_path / 'preflight' / 'monitor_private').exists()
    saved = json.loads((tmp_path / 'preflight' / 'preflight.json').read_text())
    assert saved['manifest']['private_boundary'] == 'MONITOR_PRIVATE_GATE_ONLY'


def test_preflight_rejects_existing_output_and_config_drift(tmp_path):
    adapter = BenchmarkAdapterV20.from_config(DEFAULT_CONFIG)
    output = tmp_path / 'preflight'
    output.mkdir()
    with pytest.raises(BenchmarkAdapterRejected, match='already exists'):
        adapter.preflight(output=output)

    config_path = tmp_path / 'config.json'
    config = load_frozen_pilot_config(DEFAULT_CONFIG)
    config['seed'] = 201
    config_path.write_text(json.dumps(config))
    with pytest.raises(BenchmarkAdapterRejected, match='frozen benchmark file changed|seed'):
        load_frozen_pilot_config(config_path)
