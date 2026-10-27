"""Baseline preparation using named versions and ordinary source/config snapshots."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
from .facts import require
from .storage import write_record

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT/'experiments/methods/v24/alfworld_verified_feedback_001/config/baseline_manifest.json'


def audit(manifest=MANIFEST):
    evidence = json.loads(Path(manifest).read_text())
    campaign = ROOT/evidence['campaign']
    config = json.loads((campaign/'config.json').read_text())
    require(config == json.loads((campaign/'initial_config.json').read_text()), 'Baseline configuration differs')
    experiment = ROOT/'experiments/methods/v23_5'/evidence['baseline']
    require(config == json.loads((experiment/'config/campaign.json').read_text()), 'Experiment configuration differs')
    return evidence, config


def prepare(output, *, manifest=MANIFEST):
    evidence, original = audit(manifest)
    from .benchmarks.alfworld.adapter import ALFWorldAdapter
    from .config import baseline_config
    adapter = ALFWorldAdapter()
    config = baseline_config(original, benchmark=adapter)
    expected = deepcopy(original)
    expected['method']['version'] = config['method']['version']
    expected['method']['preconditioner_prompt'] = config['method']['preconditioner_prompt']
    expected['benchmark'] = config['benchmark']
    expected['initial_skill'] = {k: original['initial_skill'][k] for k in ('source', 'text')}
    require(config == expected, 'Unexpected migration configuration change')
    source = ROOT/'experiments/methods/v23_5'/evidence['baseline']
    output = Path(output).resolve()
    require(not output.exists(), 'Preparation requires a new directory')
    output.mkdir(parents=True)
    (output/'config').mkdir()
    shutil.copytree(source/'data', output/'data')
    reference = json.loads((source/'config/initial_baseline_reference.json').read_text())
    reference = {k: reference[k] for k in ('source', 'comparable_to_current_protocol', 'test_tasks',
                 'success_rate', 'label', 'remaining_actor_differences', 'remeasure')}
    write_record(output/'config/initial_baseline_reference.json', reference)
    write_record(output/'config/budget.json', json.loads((source/'config/budget.json').read_text()))
    write_record(output/'config/campaign.json', config)
    write_record(output/'config/baseline_manifest.json', evidence)
    result = {'baseline': evidence['baseline'], 'candidate': evidence['version'],
              'method': config['method'], 'benchmark': adapter.identity,
              'data_files': [p.name for p in sorted((output/'data').glob('*.json'))],
              'config_changes': ['method.version', 'method.preconditioner_prompt', 'benchmark', 'initial_skill metadata simplified'],
              'real_model_requests': 0, 'environment_episodes': 0}
    write_record(output/'config/preparation.json', result)
    return {'experiment': str(output), **result}
