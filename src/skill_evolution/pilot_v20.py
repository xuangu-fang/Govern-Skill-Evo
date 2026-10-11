"""Independent v20 Pilot wrapper.

The pilot is an engineering gate around the v20 campaign. It records matched
task identity and learner-side metrics, while keeping private Gate/Monitor
artifacts behind the campaign callback boundary.
"""
from dataclasses import dataclass
from pathlib import Path
import json

from .edit_tracking_v19 import encode, digest
from .evolution_replay_v19 import _load, _save
from .campaign_v20 import campaign_config_v20, run_campaign_v20, CampaignTransports


class PilotRejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PilotRejected(message)


def _manifest(tasks):
    require(type(tasks) in (list, tuple) and tasks, 'nonempty pilot task manifest required')
    rows = []
    for task in tasks:
        require(type(task) is dict and 'task_id' in task, 'task_id required')
        require(type(task['task_id']) is str and task['task_id'].strip(), 'nonempty task_id required')
        rows.append(dict(task))
    ids = [r['task_id'] for r in rows]
    require(len(ids) == len(set(ids)), 'duplicate pilot task_id')
    return tuple(sorted(rows, key=lambda r: r['task_id']))


def pilot_config_v20(*, round_limit=1, model='deepseek-v4-pro', seed=0):
    require(type(seed) is int and seed >= 0, 'nonnegative pilot seed required')
    require(type(round_limit) is int and 1 <= round_limit <= 2, 'Pilot is limited to one or two rounds')
    return {'schema_version': 'pilot_config_v20.1', 'mode': 'PILOT', 'round_limit': round_limit,
            'model': model, 'seed': seed, 'learner': 'v20_issue_memory_fusion_local_generation',
            'v19_reuse': 'READ_ONLY_OFFLINE_ONLY', 'private_evaluation': 'CALLER_SUPPLIED_GATE_RECEIPT'}


def _binding(config, run_id, initial_skill, tasks):
    return {'schema_version': 'pilot_binding_v20.1', 'run_id': run_id,
        'initial_skill_sha256': digest(initial_skill), 'config': config,
        'task_manifest_sha256': digest(encode(list(tasks))), 'task_manifest': list(tasks)}


def _metrics(value):
    require(type(value) is dict, 'pilot metrics must be an object')
    clean = {}
    for key, item in value.items():
        require(type(key) is str and key.strip(), 'metric name required')
        require(type(item) in (int, float) and not isinstance(item, bool), 'metrics must be numeric')
        require(item == item and item not in (float('inf'), float('-inf')), 'metric must be finite')
        clean[key] = item
    return clean


@dataclass(frozen=True)
class PilotResult:
    payload_json: str
    @property
    def payload(self): return json.loads(self.payload_json)


def run_v20_pilot(*, output, run_id, initial_skill, task_manifest, round_factory,
                  post_generation, measurement=None, config=None, transports=None,
                  resume=False, campaign_runner=run_campaign_v20):
    """Run an isolated v20 Pilot and persist a compact result.

    ``measurement`` receives the completed campaign report and returns only
    learner-facing numeric metrics. It must not return private evaluator truth,
    Monitor traces or model prompts.
    """
    config = config or pilot_config_v20(); tasks = _manifest(task_manifest)
    root = Path(output); binding = _binding(config, run_id, initial_skill, tasks)
    if root.exists():
        require(resume, 'existing v20 Pilot requires resume')
        require(_load(root / 'pilot-binding.json') == binding, 'Pilot binding changed')
    else:
        require(not resume, 'resume requires existing v20 Pilot')
        root.mkdir(parents=True)
        _save(root / 'pilot-binding.json', binding)
        _save(root / 'task-manifest.json', list(tasks))
    report = campaign_runner(output=root / 'campaign', run_id=run_id,
        initial_skill=initial_skill, round_factory=round_factory,
        post_generation=post_generation,
        config=campaign_config_v20(round_limit=config['round_limit'], model=config['model']),
        transports=transports, resume=resume)
    metrics = _metrics(measurement(report) if measurement else {'committed_rounds': report['committed_rounds']})
    result = {'schema_version': 'pilot_result_v20.1', 'status': 'COMPLETE',
        'run_id': run_id, 'config': config, 'task_manifest_sha256': binding['task_manifest_sha256'],
        'campaign_report': report, 'metrics': metrics,
        'claim_boundary': 'ENGINEERING_PILOT_OBSERVATION_NOT_MECHANISM_EFFECTIVENESS'}
    _save(root / 'pilot-result.json', result)
    return PilotResult(encode(result))


def validate_pilot_result(result, *, task_manifest, run_id=None):
    payload = result.payload if isinstance(result, PilotResult) else result
    require(type(payload) is dict and payload.get('schema_version') == 'pilot_result_v20.1', 'invalid Pilot result')
    tasks = _manifest(task_manifest)
    require(payload['task_manifest_sha256'] == digest(encode(list(tasks))), 'Pilot task manifest changed')
    require(run_id is None or payload['run_id'] == run_id, 'Pilot run mismatch')
    _metrics(payload['metrics'])
    return payload
