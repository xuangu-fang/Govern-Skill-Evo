"""Frozen benchmark adapter for the v20 Pilot.

The adapter owns only benchmark identity and execution wiring.  It reuses the
existing frozen v19 benchmark implementation read-only, exposes the train
split to the learner, keeps the monitor split private, and provides a zero
rollout preflight before any v20 campaign is started.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .edit_tracking_v19 import encode, digest
from .evolution_replay_v19 import (_load, _save, _input, _manifest, _load_set, _run_set,
                                   _pair_binding, _file_digest)
from .evolution_benchmark_v19 import BenchmarkEvolutionV19
from .monitor_campaign_v19 import BenchmarkMonitorV19, run_private_monitor


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / 'experiments/configs/v20_pilot_001/config.json'


class BenchmarkAdapterRejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise BenchmarkAdapterRejected(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_pilot_config(path=DEFAULT_CONFIG):
    """Load and verify the checked-in v20 Pilot configuration."""
    path = Path(path)
    require(path.is_file(), 'frozen v20 Pilot config is missing')
    value = _load(path)
    required = {
        'schema_version', 'status', 'benchmark_freeze', 'benchmark_config_sha256',
        'benchmark_manifest_sha256', 'initial_skill', 'initial_skill_sha256',
        'evolution_split', 'monitor_split', 'evolution_task_ids', 'monitor_task_ids',
        'seed', 'round_limit', 'max_workers', 'model', 'pilot_only', 'v19_reuse',
        'private_gate', 'claim_boundary',
    }
    require(type(value) is dict and set(value) == required, 'frozen v20 Pilot config fields changed')
    require(value['schema_version'] == 'pilot_config_v20_frozen.1' and value['status'] == 'FROZEN',
            'frozen v20 Pilot config is not frozen')
    require(value['evolution_split'] == 'train' and value['monitor_split'] == 'monitor',
            'v20 Pilot split changed')
    require(type(value['seed']) is int and value['seed'] >= 0, 'invalid frozen Pilot seed')
    require(value['round_limit'] == 2 and 1 <= value['max_workers'] <= 32,
            'v20 Pilot must remain a two-round bounded run')
    require(value['pilot_only'] is True and value['private_gate'] == 'MONITOR_SPLIT_ONLY',
            'invalid v20 Pilot boundary')
    for field in ('evolution_task_ids', 'monitor_task_ids'):
        tasks = value[field]
        require(type(tasks) is list and tasks and all(type(t) is str and t.strip() for t in tasks)
                and len(tasks) == len(set(tasks)), 'invalid frozen task list')
    freeze = ROOT / value['benchmark_freeze']
    require(freeze.is_dir(), 'frozen benchmark directory is missing')
    for relative, expected in (
        ('config.json', value['benchmark_config_sha256']),
        ('manifest.json', value['benchmark_manifest_sha256']),
        ('S0.md', value['initial_skill_sha256']),
    ):
        require(_sha256(freeze / relative) == expected, 'frozen benchmark file changed: ' + relative)
    benchmark = _load(freeze / 'config.json')
    require(benchmark['benchmark_edition'] == 'phase_v4_day36', 'v20 Pilot requires benchmark v4')
    require(benchmark['seed'] == value['seed'], 'Pilot seed differs from benchmark freeze')
    require(benchmark['tasks']['train'] == value['evolution_task_ids'], 'train task freeze changed')
    require(benchmark['tasks']['monitor'] == value['monitor_task_ids'], 'monitor task freeze changed')
    return value


@dataclass(frozen=True)
class BenchmarkAdapterV20:
    """Concrete v20 bridge over the frozen Evolution and private Monitor APIs."""

    config: dict
    evolution: object
    monitor: object

    @classmethod
    def from_config(cls, path=DEFAULT_CONFIG, *, evolution=None, monitor=None):
        config = load_frozen_pilot_config(path)
        freeze = ROOT / config['benchmark_freeze']
        evolution = evolution or BenchmarkEvolutionV19(freeze=freeze)
        monitor = monitor or BenchmarkMonitorV19(freeze=freeze)
        adapter = cls(config, evolution, monitor)
        adapter._validate_backends()
        return adapter

    @property
    def initial_skill(self):
        freeze = ROOT / self.config['benchmark_freeze']
        value = (freeze / 'S0.md').read_text(encoding='utf-8')
        require(digest(value) == self.config['initial_skill_sha256'], 'initial Skill changed')
        return value

    def _validate_backends(self):
        evolution = self.evolution.manifest()
        monitor = self.monitor.manifest()
        require(evolution['schema_version'] == 'evolution_manifest_v19.1',
                'Evolution backend manifest is not train-scoped')
        require(monitor['schema_version'] == 'monitor_manifest_v19.1',
                'Monitor backend manifest is not private-scoped')
        require(evolution['task_ids'] == self.config['evolution_task_ids'],
                'Evolution task manifest differs from frozen Pilot')
        require(monitor['task_ids'] == self.config['monitor_task_ids'],
                'Monitor task manifest differs from frozen Pilot')
        require(evolution['seed'] == monitor['seed'] == self.config['seed'],
                'Evolution/Monitor seed mismatch')
        require(not set(evolution['task_ids']) & set(monitor['task_ids']),
                'Evolution and Monitor tasks overlap')
        return evolution, monitor

    def manifest(self):
        evolution, monitor = self._validate_backends()
        value = {
            'schema_version': 'benchmark_adapter_manifest_v20.1',
            'config_sha256': digest(encode(self.config)),
            'seed': self.config['seed'],
            'evolution_task_ids': list(evolution['task_ids']),
            'monitor_task_ids': list(monitor['task_ids']),
            'evolution_manifest': evolution,
            'monitor_manifest': monitor,
            'initial_skill_sha256': self.config['initial_skill_sha256'],
            'learner_boundary': 'EVOLUTION_TRAIN_ONLY',
            'private_boundary': 'MONITOR_PRIVATE_GATE_ONLY',
        }
        return json.loads(encode(value))

    def pilot_task_manifest(self):
        """Return the learner-facing train task list used by Pilot binding."""
        return [{'task_id': task_id, 'split': self.config['evolution_split'],
                 'seed': self.config['seed']} for task_id in self.config['evolution_task_ids']]

    def preflight(self, *, output, skills=None):
        """Prepare every Evolution and private Monitor environment without rollouts."""
        root = Path(output)
        require(not root.exists(), 'v20 preflight output already exists')
        initial = self.initial_skill
        skills = tuple(skills) if skills is not None else (
            initial, '', '- v20 Pilot preflight candidate.\n')
        require(type(skills) is tuple and len(skills) == 3 and skills[0] == initial,
                'preflight requires initial, empty and candidate Skills')
        require(all(type(skill) is str for skill in skills), 'preflight Skills must be text')
        evolution = self.evolution.preflight(artifact_dir=root / 'evolution', skills=skills)
        monitor = self.monitor.preflight(artifact_dir=root / 'monitor_private', skills=skills)
        require(evolution['model_calls'] == 0 and monitor['model_calls'] == 0,
                'preflight dispatched a model call')
        manifest = self.manifest()
        report = {
            'schema_version': 'benchmark_preflight_v20.1',
            'status': 'PREFLIGHT',
            'model_calls': 0,
            'evolution': evolution,
            'monitor_private': monitor,
            'manifest': manifest,
            'skill_sha256': [digest(skill) for skill in skills],
            'claim_boundary': 'NO_MODEL_ROLLOUTS_NO_MECHANISM_RESULT',
        }
        _save(root / 'preflight.json', report)
        return report

    def prepare(self, task_id, skill, artifact_dir):
        """Prepare a train rollout; actual execution remains an explicit caller action."""
        return self.evolution.prepare(task_id, skill, artifact_dir)

    def evaluate(self, task_id, *, initial_db, final_db, simulation):
        return self.evolution.evaluate(task_id, initial_db=initial_db, final_db=final_db,
                                       simulation=simulation)

    def run_private_gate(self, ledger, *, artifact_dir, history=(), resume=False):
        """Run or resume the private monitor Gate for a completed Candidate ledger."""
        return run_private_monitor(ledger, backend=self.monitor, artifact_dir=artifact_dir,
                                   history=history, max_workers=self.config['max_workers'],
                                   resume=resume)

    def run_candidate_evolution(self, *, run_id, round_id, parent_skill, candidate_skill,
                                parent_dir, artifact_dir, resume=False):
        """Replay Candidate on the train split without requiring a v19 ledger."""
        manifest = _manifest(self.evolution)
        parent_input = _input(run_id, round_id, 'PARENT', parent_skill, manifest)
        parents = _load_set(Path(parent_dir), parent_input)
        value = _input(run_id, round_id, 'CANDIDATE', candidate_skill, manifest,
                       parent_set=_file_digest(Path(parent_dir) / 'state.json'))
        candidates = _run_set(self.evolution, value, Path(artifact_dir),
                              resume=resume or Path(artifact_dir).exists(),
                              max_workers=self.config['max_workers'], parents=parents)
        rows = []
        for parent, candidate in zip(parents, candidates):
            _pair_binding(parent, candidate)
            rows.append({'task_id': candidate['binding']['task_id'],
                         'success': candidate['evaluation']['success'],
                         'compliant': candidate['evaluation']['compliant']})
        result = {'schema_version': 'candidate_replay_v20.1', 'status': 'COMPLETE',
                  'run_id': run_id, 'round_id': round_id, 'task_count': len(rows),
                  'rows': rows, 'success_count': sum(r['success'] for r in rows),
                  'compliance_count': sum(r['compliant'] for r in rows)}
        _save(Path(artifact_dir) / 'candidate-summary.json', result)
        return result

    def build_local_attribution(self, *, generation, candidate_summary):
        """Bind each generated edit to replay scope without inferring causality."""
        records = []
        for edit in generation.get('edits', []):
            records.append({'edit_id': edit['edit_id'],
                            'current_finding_refs': list(edit.get('current_finding_refs', [])),
                            'task_count': candidate_summary['task_count'],
                            'success_count': candidate_summary['success_count'],
                            'compliance_count': candidate_summary['compliance_count'],
                            'effect': 'UNRESOLVED'})
        return {'schema_version': 'local_attribution_v20.1', 'records': records,
                'scope': 'STRUCTURAL_EDIT_TO_REPLAY_BINDING_NOT_CAUSAL_EFFECT'}

    def run_private_gate_v20(self, *, run_id, round_id, parent_skill, candidate_skill,
                             artifact_dir, resume=False):
        """Run the monitor split privately for a v20 Candidate."""
        from .evolution_replay_v19 import _input, _manifest, _load_set, _run_set
        from .monitor_v18 import MonitorInput, MonitorTask, summarize_monitor
        from .monitor_campaign_v19 import _summarize
        root = Path(artifact_dir)
        _, manifest = self._validate_backends()
        parent_input = _input(run_id, round_id, 'PARENT', parent_skill, manifest)
        parent_dir = root / 'parent'
        parents = _run_set(self.monitor, parent_input, parent_dir,
                           resume=resume or parent_dir.exists(),
                           max_workers=self.config['max_workers'])
        candidate_input = _input(run_id, round_id, 'CANDIDATE', candidate_skill, manifest,
                                 parent_set=_file_digest(parent_dir / 'state.json'))
        candidate_dir = root / 'candidate'
        candidates = _run_set(self.monitor, candidate_input, candidate_dir,
                              resume=resume or candidate_dir.exists(),
                              max_workers=self.config['max_workers'], parents=parents)
        value = MonitorInput(round_id, tuple(MonitorTask(t, manifest['seed']) for t in manifest['task_ids']),
                             parent_skill, candidate_skill, digest(encode(manifest)))
        bound = {'run_id': run_id, 'round_id': round_id,
                 'parent_skill_sha256': digest(parent_skill),
                 'candidate_skill_sha256': digest(candidate_skill)}
        summary, receipt = _summarize(value, bound, parents, candidates)
        _save(root / 'summary.json', summary)
        _save(root / 'receipt.json', receipt)
        return receipt
