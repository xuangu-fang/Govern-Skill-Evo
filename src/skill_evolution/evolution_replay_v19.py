"""Full Evolution Parent/Candidate replay, private checkpoints and safe pairs.

No selection or attribution. Backend preparation must not call models; only
PreparedEvolution.run executes a trajectory. A complete Parent set is mandatory
before Candidate execution. Runtime authenticity belongs to the trusted backend.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from .edit_tracking_v19 import encode, parse, digest, skill_ref, validate_edit_ledger
from .information_boundary_v15 import (
    Envelope, capture_agent_visible_view, capture_experience, project_oracle_supervision, unpack,
)
from .autonomous_gse_v15_benchmark_runtime import normalize_stored_simulation


class ReplayRejected(ValueError):
    pass


@dataclass(frozen=True)
class PreparedEvolution:
    visible_view: Envelope
    initial_db: dict
    user_prompt: dict
    execution_config: dict
    run: Callable  # returns (serialized simulation, final database)


@dataclass(frozen=True)
class ReplayBatch:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)


RAW_FILES = ('binding.json', 'initial_db.json', 'visible_view.json', 'user_prompt.json',
             'execution_config.json', 'simulation.json', 'final_db.json')


def _require(condition, reason):
    if not condition:
        raise ReplayRejected(reason)


def _load(path):
    return parse(Path(path).read_bytes().decode('utf-8'))


def _save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes((encode(value) + '\n').encode('utf-8'))
    temporary.replace(path)


def _file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def _lock(directory):
    directory = Path(directory)
    directory.parent.mkdir(parents=True, exist_ok=True)
    with (directory.parent / ('.' + directory.name + '.replay.lock')).open('a+') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ReplayRejected('Evolution directory is already running') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _manifest(backend):
    # Freeze a defensive JSON snapshot. task_ids is the whole authoritative train
    # split, never a caller-selected subset of failures.
    value = parse(encode(backend.manifest()))
    _require(type(value) is dict and set(value) == {'schema_version', 'task_ids', 'seed', 'runtime'},
             'invalid Evolution manifest fields')
    _require(value['schema_version'] == 'evolution_manifest_v19.1', 'invalid manifest version')
    tasks = value['task_ids']
    _require(type(tasks) is list and bool(tasks) and all(type(t) is str and t.strip() for t in tasks)
             and len(set(tasks)) == len(tasks), 'unique nonempty train task manifest required')
    _require(type(value['seed']) is int and value['seed'] >= 0, 'invalid seed')
    _require(type(value['runtime']) is dict and bool(value['runtime']), 'runtime binding required')
    return value


def _public_view(value):
    _require(type(value) is dict and set(value) == {'domain', 'visible_policy', 'public_tools'},
             'visible context contains unexpected fields')
    # Revalidate public schemas after disk reload, without passing private fields.
    agent = SimpleNamespace(domain_policy=value['visible_policy'], tools=[
        SimpleNamespace(openai_schema=tool) for tool in value['public_tools']])
    return capture_agent_visible_view(agent, value['domain'])


def _input(run_id, round_id, role, skill, manifest, *, ledger=None, parent_set=None):
    _require(all(type(s) is str and s.strip() for s in (run_id, round_id)), 'run/round required')
    _require(type(skill) is str, 'exact Skill text required')
    return {'schema_version': 'evolution_input_v19.1', 'run_id': run_id, 'round_id': round_id,
            'role': role, 'skill': skill, 'skill_ref': skill_ref(skill), 'manifest': manifest,
            'ledger_sha256': digest(ledger.output_json) if ledger is not None else None,
            'parent_set_sha256': parent_set}


def _binding(value, index):
    return {'schema_version': 'evolution_binding_v19.1',
            'run_id': value['run_id'], 'round_id': value['round_id'], 'role': value['role'],
            'task_id': value['manifest']['task_ids'][index], 'task_ref': f'T{index+1:03d}',
            'rollout_index': 1, 'seed': value['manifest']['seed'],
            'skill_ref': value['skill_ref'], 'input_sha256': digest(encode(value))}


def _check_files(directory, marker, expected_names):
    checkpoint = _load(directory / marker)
    _require(type(checkpoint) is dict and set(checkpoint) == {'status', 'files'}
             and checkpoint['status'] == 'COMPLETE'
             and type(checkpoint['files']) is dict and set(checkpoint['files']) == set(expected_names),
             'invalid checkpoint coverage: ' + marker)
    for name, sha in checkpoint['files'].items():
        _require(_file_digest(directory / name) == sha, 'checkpoint digest mismatch: ' + name)


def _write_checkpoint(directory, marker, names):
    _save(directory / marker, {'status': 'COMPLETE', 'files': {
        name: _file_digest(directory / name) for name in names}})


def _raw(directory, binding):
    _check_files(directory, 'raw_complete.json', RAW_FILES)
    _require(encode(_load(directory / 'binding.json')) == encode(binding), 'checkpoint input binding mismatch')
    raw = {name[:-5]: _load(directory / name) for name in RAW_FILES}
    sim = raw['simulation']
    _require(type(sim) is dict and sim.get('task_id') == binding['task_id']
             and type(sim.get('seed')) is int and sim['seed'] == binding['seed'],
             'simulation task/seed mismatch')
    _public_view(raw['visible_view'])
    _require(type(raw['initial_db']) is dict and type(raw['final_db']) is dict,
             'database snapshots required')
    return raw


def _complete(directory, binding):
    _check_files(directory, 'checkpoint.json', (*RAW_FILES, 'raw_complete.json', 'evaluation.json'))
    raw = _raw(directory, binding)
    raw['evaluation'] = _load(directory / 'evaluation.json')
    # False is a completed label, not an execution error. Missing labels fail.
    project_oracle_supervision(raw['evaluation'], raw['evaluation'])
    capture_experience(_public_view(raw['visible_view']), normalize_stored_simulation(raw['simulation']),
                       project_oracle_supervision(raw['evaluation'], raw['evaluation']), 1)
    return raw


def _pair_binding(parent, candidate):
    for name in ('initial_db', 'visible_view', 'user_prompt', 'execution_config'):
        _require(encode(parent[name]) == encode(candidate[name]), 'paired ' + name + ' mismatch')


def _archive_partial(directory):
    index = 1
    while directory.with_name(directory.name + f'.partial-{index}').exists():
        index += 1
    directory.rename(directory.with_name(directory.name + f'.partial-{index}'))


def _observe(backend, value, index, directory, parent=None):
    binding = _binding(value, index)
    if (directory / 'checkpoint.json').exists():
        raw = _complete(directory, binding)
        if parent is not None:
            _pair_binding(parent, raw)
        return raw
    if (directory / 'raw_complete.json').exists():
        raw = _raw(directory, binding)
        if parent is not None:
            _pair_binding(parent, raw)
    else:
        if directory.exists():
            # Never turn a wrong version or corrupted completed checkpoint into
            # a new trajectory. Only truly incomplete attempts can restart.
            if (directory / 'binding.json').exists():
                _require(encode(_load(directory / 'binding.json')) == encode(binding), 'partial input binding mismatch')
            _archive_partial(directory)
        directory.mkdir(parents=True)
        _save(directory / 'binding.json', binding)
        prepared = backend.prepare(binding['task_id'], value['skill'], directory)
        _require(isinstance(prepared, PreparedEvolution), 'PreparedEvolution required')
        raw = {'binding': binding, 'initial_db': parse(encode(prepared.initial_db)),
               'visible_view': unpack(prepared.visible_view, 'AGENT_VISIBLE_VIEW'),
               'user_prompt': parse(encode(prepared.user_prompt)),
               'execution_config': parse(encode(prepared.execution_config))}
        _public_view(raw['visible_view'])
        _require(type(raw['initial_db']) is dict and type(raw['user_prompt']) is dict
                 and bool(raw['user_prompt']) and type(raw['execution_config']) is dict
                 and bool(raw['execution_config']), 'incomplete prepared runtime binding')
        if parent is not None:
            _pair_binding(parent, raw)  # fail before spending a Candidate rollout
        for name, record in raw.items():
            _save(directory / (name + '.json'), record)
        simulation, final_db = prepared.run()
        raw.update(simulation=simulation, final_db=final_db)
        _require(type(simulation) is dict and simulation.get('task_id') == binding['task_id']
                 and type(simulation.get('seed')) is int and simulation['seed'] == binding['seed'],
                 'simulation task/seed mismatch')
        _require(type(final_db) is dict, 'final database required')
        # Validate observable events before marking a trajectory reusable.
        normalize_stored_simulation(simulation)
        _save(directory / 'simulation.json', simulation)
        _save(directory / 'final_db.json', final_db)
        _write_checkpoint(directory, 'raw_complete.json', RAW_FILES)
    # Evaluation is checkpointed separately: an evaluator failure never requires
    # rerunning an already completed trajectory on explicit resume.
    evaluation = backend.evaluate(binding['task_id'], initial_db=raw['initial_db'],
                                  final_db=raw['final_db'], simulation=raw['simulation'])
    project_oracle_supervision(evaluation, evaluation)
    _save(directory / 'evaluation.json', evaluation)
    _write_checkpoint(directory, 'checkpoint.json', (*RAW_FILES, 'raw_complete.json', 'evaluation.json'))
    return _complete(directory, binding)


def _load_set(directory, expected_input):
    directory = Path(directory)
    _require(encode(_load(directory / 'input.json')) == encode(expected_input), 'Evolution input mismatch')
    state = _load(directory / 'state.json')
    _require(state.get('status') == 'COMPLETE', 'Evolution set is incomplete')
    rows = [_complete(directory / 'tasks' / f'T{i+1:03d}', _binding(expected_input, i))
            for i in range(len(expected_input['manifest']['task_ids']))]
    expected_checks = {f'T{i+1:03d}': _file_digest(directory / 'tasks' / f'T{i+1:03d}' / 'checkpoint.json')
                       for i in range(len(rows))}
    _require(state == {'status': 'COMPLETE', 'input_sha256': digest(encode(expected_input)),
                       'task_checkpoints': expected_checks}, 'Evolution set manifest mismatch')
    return rows


def _run_set(backend, value, directory, *, resume, max_workers, parents=None):
    _require(type(max_workers) is int and max_workers > 0, 'positive worker count required')
    _require(type(resume) is bool, 'resume must be boolean')
    directory = Path(directory)
    with _lock(directory):
        if directory.exists():
            _require(resume, 'existing Evolution output requires explicit resume')
            _require((directory / 'input.json').is_file(), 'existing output has no bound input')
            _require(encode(_load(directory / 'input.json')) == encode(value), 'resume input mismatch')
            if (directory / 'state.json').exists() and _load(directory / 'state.json').get('status') == 'COMPLETE':
                return _load_set(directory, value)
        else:
            _require(not resume, 'resume requires an existing Evolution output')
            directory.mkdir(parents=True)
            _save(directory / 'input.json', value)
        _save(directory / 'state.json', {'status': 'RUNNING'})

        def execute(index):
            task_dir = directory / 'tasks' / f'T{index+1:03d}'
            try:
                row = _observe(backend, value, index, task_dir,
                               parents[index] if parents is not None else None)
                return row, None
            except Exception as exc:
                # Only exception type is recorded; no private provider message.
                return None, {'task_ref': f'T{index+1:03d}', 'error_type': type(exc).__name__}

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                results = list(pool.map(execute, range(len(value['manifest']['task_ids']))))
        except BaseException as exc:
            _save(directory / 'state.json', {'status': 'INCOMPLETE', 'error_type': type(exc).__name__})
            raise
        errors = [error for _, error in results if error is not None]
        if errors:
            _save(directory / 'state.json', {'status': 'INCOMPLETE', 'errors': errors})
            raise ReplayRejected('Evolution set incomplete; inspect private state and explicitly resume')
        _save(directory / 'state.json', {
            'status': 'COMPLETE', 'input_sha256': digest(encode(value)),
            'task_checkpoints': {f'T{i+1:03d}': _file_digest(directory / 'tasks' / f'T{i+1:03d}' / 'checkpoint.json')
                                 for i in range(len(results))}})
        return _load_set(directory, value)


def _observation(raw, pair_id, role, contexts):
    view = _public_view(raw['visible_view'])
    public = unpack(view, 'AGENT_VISIBLE_VIEW')
    context_ref = 'CONTEXT/' + digest(encode(public))
    contexts[context_ref] = {'context_ref': context_ref, **public}
    observed = unpack(capture_experience(view, normalize_stored_simulation(raw['simulation']),
                      project_oracle_supervision(raw['evaluation'], raw['evaluation']), 1), 'TRAJECTORY_DERIVED')
    trajectory_ref = pair_id + '/' + role
    events = [{**event, 'evidence_ref': trajectory_ref + f"/E{event['step']:04d}"}
              for event in observed['trajectory']]
    return {'role': role, 'skill_ref': raw['binding']['skill_ref'], 'context_ref': context_ref,
            'trajectory_ref': trajectory_ref, 'events': events,
            'supervision': {'success': observed['supervision']['success'],
                            'compliant': observed['supervision']['compliant'], 'level': 0,
                            'supervision_ref': trajectory_ref + '/S'}}


def _state(labels):
    return ('C' if labels['compliant'] else 'V') + ('S' if labels['success'] else 'F')


def _project(value, parents, candidates):
    _require(len(parents) == len(candidates) == len(value['manifest']['task_ids']), 'incomplete pair coverage')
    contexts, pairs = {}, []
    quadrants = {role: {q: 0 for q in ('CS', 'CF', 'VS', 'VF')} for role in ('PARENT', 'CANDIDATE')}
    transitions = {a: {b: 0 for b in ('CS', 'CF', 'VS', 'VF')} for a in ('CS', 'CF', 'VS', 'VF')}
    for index, (parent, candidate) in enumerate(zip(parents, candidates)):
        _pair_binding(parent, candidate)
        pair_id = 'PAIR/' + digest(encode({'input': digest(encode(value)), 'task_ref': f'T{index+1:03d}'}))
        p, c = (_observation(raw, pair_id, role, contexts)
                for raw, role in ((parent, 'PARENT'), (candidate, 'CANDIDATE')))
        ps, cs = p['supervision'], c['supervision']
        pq, cq = _state(ps), _state(cs)
        quadrants['PARENT'][pq] += 1; quadrants['CANDIDATE'][cq] += 1
        transitions[pq][cq] += 1
        pairs.append({'schema_version': 'replay_pair_v19.1', 'pair_id': pair_id,
                      'run_id': value['run_id'], 'round_id': value['round_id'],
                      'task_ref': f'T{index+1:03d}', 'rollout_index': 1,
                      'parent': p, 'candidate': c,
                      'outcome_transition': {'success_delta': int(cs['success']) - int(ps['success']),
                                             'compliant_delta': int(cs['compliant']) - int(ps['compliant']),
                                             'parent_state': pq, 'candidate_state': cq}})
    metrics = {role: {'S': q['CS'] + q['VS'], 'C': q['CS'] + q['CF'], 'CS': q['CS'], 'VF': q['VF']}
               for role, q in quadrants.items()}
    return ReplayBatch(encode({'schema_version': 'replay_batch_v19.1', 'run_id': value['run_id'],
        'round_id': value['round_id'], 'ledger_sha256': value['ledger_sha256'],
        'contexts': [contexts[k] for k in sorted(contexts)], 'pairs': pairs,
        'summary': {'matched_samples': len(pairs), 'quadrant_counts': quadrants,
                    'transition_counts': transitions, 'metric_counts': metrics,
                    'delta_counts': {k: metrics['CANDIDATE'][k] - metrics['PARENT'][k] for k in ('S', 'C', 'CS', 'VF')}}}))


def run_parent_evolution(*, run_id, round_id, parent_skill, backend, artifact_dir,
                         resume=False, max_workers=8):
    """Capture the Parent used to generate Candidate, once, including failures."""
    value = _input(run_id, round_id, 'PARENT', parent_skill, _manifest(backend))
    _run_set(backend, value, artifact_dir, resume=resume, max_workers=max_workers)
    return {'status': 'COMPLETE', 'task_count': len(value['manifest']['task_ids'])}


def load_parent_experiences(*, run_id, round_id, parent_skill, backend, artifact_dir):
    """Reuse the same completed Parent observations in Grouping/Diagnosis.

    No task IDs, private states or evaluator explanations enter these existing
    capture DTOs. This is an input adapter, not an invocation of the learner.
    """
    from .experience_cards_v17 import CapturedGroupingExperience
    from .experience_grouping_contract_v17 import EvolutionExperienceRef, GroupingScope
    value = _input(run_id, round_id, 'PARENT', parent_skill, _manifest(backend))
    rows = _load_set(Path(artifact_dir), value)
    contexts, sources = {}, []
    for index, raw in enumerate(rows, 1):
        view = _public_view(raw['visible_view'])
        context_ref = contexts.setdefault(view.payload, f'C{len(contexts)+1:03d}')
        ref = EvolutionExperienceRef(f'T{index:03d}', context_ref, f'R{index:03d}')
        observed = capture_experience(view, normalize_stored_simulation(raw['simulation']),
                                     project_oracle_supervision(raw['evaluation'], raw['evaluation']), 1)
        sources.append(CapturedGroupingExperience(round_id, digest(parent_skill), ref, view, observed))
    return tuple(sources), GroupingScope(round_id, digest(parent_skill), tuple(s.ref for s in sources))


def _replay_inputs(ledger, history, backend, parent_dir):
    payload = validate_edit_ledger(ledger, history=history)
    manifest = _manifest(backend)
    parent_input = _input(payload['run_id'], payload['round_id'], 'PARENT',
                          ledger.source['editor']['parent_skill'], manifest)
    parents = _load_set(Path(parent_dir), parent_input)
    value = _input(payload['run_id'], payload['round_id'], 'CANDIDATE', ledger.source['candidate_skill'],
                   manifest, ledger=ledger, parent_set=digest(encode(_load(Path(parent_dir) / 'state.json'))))
    return value, parents


def run_candidate_replay(ledger, *, backend, parent_dir, artifact_dir, history=(),
                         resume=False, max_workers=8):
    """Return pairs only after all Candidate tasks complete; never run Gate."""
    value, parents = _replay_inputs(ledger, history, backend, parent_dir)
    candidates = _run_set(backend, value, artifact_dir, resume=resume, max_workers=max_workers, parents=parents)
    batch = _project(value, parents, candidates)
    path = Path(artifact_dir) / 'learner' / 'pairs.json'
    with _lock(artifact_dir):
        if path.exists():
            _require(encode(_load(path)) == batch.payload_json, 'saved learner pairs differ from checkpoint projection')
        else:
            _require(not (path.parent / 'validation.json').exists(), 'published learner pairs missing')
            _save(path, batch.payload)
        manifest = {'status': 'COMPLETE', 'pairs_sha256': _file_digest(path),
                    'input_sha256': digest(encode(value))}
        marker = path.parent / 'validation.json'
        if marker.exists():
            _require(_load(marker) == manifest, 'saved learner manifest mismatch')
        else:
            _save(marker, manifest)
    return batch


def load_candidate_replay(ledger, *, backend, parent_dir, artifact_dir, history=()):
    """No execution; reproject private artifacts and compare the learner export."""
    value, parents = _replay_inputs(ledger, history, backend, parent_dir)
    candidates = _load_set(Path(artifact_dir), value)
    expected = _project(value, parents, candidates)
    path = Path(artifact_dir) / 'learner' / 'pairs.json'
    _require(_load(path.parent / 'validation.json') == {
        'status': 'COMPLETE', 'pairs_sha256': _file_digest(path), 'input_sha256': digest(encode(value))},
        'invalid learner export manifest')
    _require(encode(_load(path)) == expected.payload_json, 'learner pairs differ from private evidence')
    return expected
