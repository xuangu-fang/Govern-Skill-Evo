"""Matched v20 comparison protocol and paired metric analysis."""
from pathlib import Path
from copy import deepcopy
import json
import re

from .edit_tracking_v19 import encode, digest
from .evolution_replay_v19 import _load, _save
from .pilot_v20 import require, _manifest


def comparison_config_v20(*, conditions=('v20_memory', 'no_memory'), seed=0):
    require(type(conditions) in (list, tuple) and len(conditions) == 2,
            'exactly two comparison conditions required')
    require(all(type(c) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', c)
                for c in conditions), 'safe condition names required')
    require(conditions[0] != conditions[1], 'comparison conditions must differ')
    require(type(seed) is int and seed >= 0, 'nonnegative comparison seed required')
    return {'schema_version': 'comparison_config_v20.1', 'conditions': list(conditions), 'seed': seed,
            'pairing': 'SAME_TASK_MANIFEST_AND_SEED', 'analysis': 'PAIRED_PER_TASK_DELTA'}


def _task_metrics(value, tasks):
    require(type(value) is dict, 'task metrics must be an object')
    expected = {t['task_id'] for t in tasks}
    require(set(value) == expected, 'task metric coverage differs from manifest')
    rows = {}
    for task_id, metrics in value.items():
        require(type(metrics) is dict and metrics, 'each task needs numeric metrics')
        checked = {}
        for name, score in metrics.items():
            require(type(name) is str and name.strip() and type(score) in (int, float)
                    and not isinstance(score, bool) and score == score and abs(score) != float('inf'),
                    'task metric must be finite numeric')
            checked[name] = score
        rows[task_id] = checked
    names = set.intersection(*(set(v) for v in rows.values())) if rows else set()
    require(names, 'no metric is shared by every task')
    return rows, sorted(names)


def paired_metrics(condition_rows, conditions):
    left, right = conditions
    left_rows, names = _task_metrics(condition_rows[left], condition_rows['_tasks'])
    right_rows, right_names = _task_metrics(condition_rows[right], condition_rows['_tasks'])
    names = sorted(set(names) & set(right_names)); require(names, 'conditions share no metric')
    result = {}
    for name in names:
        deltas = [left_rows[t][name] - right_rows[t][name] for t in sorted(left_rows)]
        result[name] = {'mean_delta': sum(deltas) / len(deltas),
            'wins': sum(d > 0 for d in deltas), 'ties': sum(d == 0 for d in deltas),
            'losses': sum(d < 0 for d in deltas), 'deltas': deltas,
            'task_ids': sorted(left_rows)}
    return result


def run_v20_comparison(*, output, task_manifest, condition_runner,
                       config=None, run_id='comparison-v20'):
    """Run two isolated conditions and write a paired comparison report.

    ``condition_runner`` receives ``condition, output_dir, task_manifest, seed``
    and returns ``{'task_metrics': {task_id: {metric: number}}, ...}``.
    """
    config = config or comparison_config_v20(); tasks = _manifest(task_manifest)
    root = Path(output); require(not root.exists(), 'comparison output already exists')
    root.mkdir(parents=True)
    binding = {'schema_version': 'comparison_binding_v20.1', 'run_id': run_id,
        'config': config, 'task_manifest': list(tasks),
        'task_manifest_sha256': digest(encode(list(tasks)))}
    _save(root / 'comparison-binding.json', binding)
    rows = {'_tasks': list(tasks)}; condition_reports = {}
    for condition in config['conditions']:
        directory = root / condition
        directory.mkdir(parents=True, exist_ok=False)
        result = condition_runner(condition, directory, deepcopy(list(tasks)), config['seed'])
        require(type(result) is dict and 'task_metrics' in result, 'condition result requires task_metrics')
        if 'seed' in result:
            require(result['seed'] == config['seed'], 'condition seed differs from comparison seed')
        if 'task_manifest_sha256' in result:
            require(result['task_manifest_sha256'] == binding['task_manifest_sha256'],
                    'condition task manifest differs from comparison manifest')
        checked, _ = _task_metrics(result['task_metrics'], tasks)
        rows[condition] = checked
        # Persist only the public comparison surface. A runner may hold private
        # evaluator traces, prompts, or monitor state that must stay outside the
        # learner-facing comparison report.
        public_result = {'status': result.get('status', 'COMPLETE'),
                         'task_metrics': checked}
        if 'artifact_ref' in result:
            public_result['artifact_ref'] = result['artifact_ref']
        condition_reports[condition] = public_result
        _save(directory / 'condition-result.json', public_result)
    paired = paired_metrics(rows, config['conditions'])
    report = {'schema_version': 'comparison_report_v20.1', 'status': 'COMPLETE',
        'run_id': run_id, 'config': config, 'task_manifest_sha256': binding['task_manifest_sha256'],
        'conditions': list(config['conditions']), 'condition_reports': condition_reports,
        'paired_metrics': paired,
        'claim_boundary': 'MATCHED_OBSERVATIONAL_COMPARISON_NOT_CAUSAL_PROOF'}
    _save(root / 'comparison-report.json', report)
    return report


def validate_comparison(report, *, task_manifest):
    require(report.get('schema_version') == 'comparison_report_v20.1', 'invalid comparison report')
    tasks = _manifest(task_manifest)
    require(report['task_manifest_sha256'] == digest(encode(list(tasks))), 'comparison manifest changed')
    require(type(report.get('conditions')) is list and len(report['conditions']) == 2,
            'comparison conditions missing')
    reports = report.get('condition_reports')
    require(type(reports) is dict and set(reports) == set(report['conditions']),
            'condition reports incomplete')
    rows = {'_tasks': list(tasks)}
    for condition in report['conditions']:
        checked, _ = _task_metrics(reports[condition].get('task_metrics'), tasks)
        rows[condition] = checked
    expected = paired_metrics(rows, report['conditions'])
    require(report.get('paired_metrics') == expected, 'paired metrics changed')
    require(report['claim_boundary'] == 'MATCHED_OBSERVATIONAL_COMPARISON_NOT_CAUSAL_PROOF',
            'comparison claim boundary changed')
    return report
