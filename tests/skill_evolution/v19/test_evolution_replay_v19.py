from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.skill_evolution.v19.edit_tracking_v19 import encode, digest
from src.skill_evolution.v19.evolution_replay_v19 import PreparedEvolution, ReplayRejected, _file_digest, _lock, _load, _save, load_candidate_replay, load_parent_experiences, run_candidate_replay, run_parent_evolution
from src.skill_evolution.v15.information_boundary_v15 import capture_agent_visible_view
from tests.skill_evolution.v19.test_edit_tracking_v19 import case, value_for, ledger_for


class Backend:
    def __init__(self, parent='- Parent\n'):
        self.parent = parent
        self.tasks = ['PRIVATE-TRAIN-A', 'PRIVATE-TRAIN-B', 'PRIVATE-TRAIN-C']
        self.seed = 200
        self.version = 'test-runtime'
        self.calls = Counter(); self.evaluations = Counter()
        self.fail_run = set(); self.fail_eval = set()
        self.mismatch = None
        self.simulation_mutator = None
        self.label_mutator = None

    def manifest(self):
        return {'schema_version': 'evolution_manifest_v19.1', 'task_ids': self.tasks.copy(),
                'seed': self.seed, 'runtime': {'implementation': self.version}}

    def prepare(self, task_id, skill, artifact_dir):
        role = 'PARENT' if skill == self.parent else 'CANDIDATE'
        key = (role, task_id)
        agent = SimpleNamespace(domain_policy='Follow the public policy.', tools=[SimpleNamespace(openai_schema={
            'type': 'function', 'function': {'name': 'change', 'description': 'Change requested value.',
                                            'parameters': {'type': 'object'}}})])
        initial = {'private_database': 'NOT_LEARNER_DATA', 'value': 0}
        prompt = {'system_prompt': 'PRIVATE_SIMULATOR_SCENARIO'}
        config = {'model': 'test', 'temperature': 0, 'seed': self.seed}
        if role == 'CANDIDATE':
            if self.mismatch == 'initial_db': initial['value'] = 100
            if self.mismatch == 'user_prompt': prompt['system_prompt'] = 'changed'
            if self.mismatch == 'execution_config': config['temperature'] = 1
            if self.mismatch == 'visible_view': agent.domain_policy = 'Different policy'
        view = capture_agent_visible_view(agent, 'airline')

        def run():
            self.calls[key] += 1
            if key in self.fail_run:
                raise RuntimeError('SECRET_PROVIDER_MESSAGE')
            simulation = {'task_id': task_id, 'seed': self.seed, 'private_metadata': 'HIDDEN_METADATA',
                'messages': [
                    {'role': 'user', 'content': 'Please change the value.'},
                    {'role': 'assistant', 'content': 'I will make the requested change.' if role == 'PARENT' else 'I checked and will change it.',
                     'tool_calls': [{'id': 'call1', 'name': 'change', 'arguments': {'value': 1}}]},
                    {'role': 'tool', 'id': 'call1', 'content': {'value': 1}},
                    {'role': 'assistant', 'content': 'Done.'}]}
            if self.simulation_mutator: self.simulation_mutator(simulation)
            initial['value'] = 1  # runner must have snapshotted the pre-run state
            return simulation, dict(initial)
        return PreparedEvolution(view, initial, prompt, config, run)

    def evaluate(self, task_id, *, initial_db, final_db, simulation):
        role = 'CANDIDATE' if 'checked' in simulation['messages'][1]['content'] else 'PARENT'
        key = (role, task_id)
        self.evaluations[key] += 1
        if key in self.fail_eval: raise RuntimeError('PRIVATE_EVALUATOR_FAILURE')
        outcomes = {'PARENT': [(False, True), (True, True), (True, False)],
                    'CANDIDATE': [(True, True), (False, True), (True, False)]}
        s, c = outcomes[role][self.tasks.index(task_id)]
        result = {'success': s, 'compliant': c, 'expected_action': 'HIDDEN_ANSWER',
                  'reason': 'PRIVATE_EVALUATOR_REASON'}
        if self.label_mutator: self.label_mutator(result)
        return result


@pytest.fixture
def scenario(case, tmp_path):
    backend = Backend()
    ledger = ledger_for(value_for(case, backend.parent, [('MISSING', [])]), [(0, '- Candidate')])
    parent = tmp_path / 'parent'; candidate = tmp_path / 'candidate'
    run_parent_evolution(run_id='test-run', round_id='r1', parent_skill=backend.parent,
                         backend=backend, artifact_dir=parent, max_workers=2)
    return backend, ledger, parent, candidate


def run(scenario, **kwargs):
    backend, ledger, parent, candidate = scenario
    return run_candidate_replay(ledger, backend=backend, parent_dir=parent, artifact_dir=candidate,
                                max_workers=2, **kwargs)


def test_complete_pairs_include_success_failures_and_safe_evidence(scenario):
    backend, ledger, parent, candidate = scenario
    batch = run(scenario)
    payload = batch.payload
    assert [p['task_ref'] for p in payload['pairs']] == ['T001', 'T002', 'T003']
    assert [p['outcome_transition'] for p in payload['pairs']] == [
        {'success_delta': 1, 'compliant_delta': 0, 'parent_state': 'CF', 'candidate_state': 'CS'},
        {'success_delta': -1, 'compliant_delta': 0, 'parent_state': 'CS', 'candidate_state': 'CF'},
        {'success_delta': 0, 'compliant_delta': 0, 'parent_state': 'VS', 'candidate_state': 'VS'}]
    assert all(count == 1 for count in backend.calls.values()) and sum(backend.calls.values()) == 6
    for private in ('PRIVATE-', 'HIDDEN_', 'task_id', 'seed', 'expected_action', 'gate_decision'):
        assert private not in batch.payload_json
    assert payload['summary']['matched_samples'] == 3
    assert payload['summary']['delta_counts'] == {'S': 0, 'C': 0, 'CS': 0, 'VF': 0}
    refs = []
    for pair in payload['pairs']:
        for role in ('parent', 'candidate'):
            observation = pair[role]
            assert observation['skill_ref'] == ledger.payload[role + '_skill_ref']
            assert observation['supervision']['level'] == 0
            assert len(observation['events']) == 5
            refs.extend(e['evidence_ref'] for e in observation['events'])
            refs.append(observation['supervision']['supervision_ref'])
    assert len(refs) == len(set(refs))
    assert _load(parent / 'tasks/T001/initial_db.json')['value'] == 0
    assert load_candidate_replay(ledger, backend=backend, parent_dir=parent, artifact_dir=candidate) == batch
    changed = batch.payload; changed['pairs'].clear()
    assert len(batch.payload['pairs']) == 3


def test_completed_resume_never_executes_or_scores_again(scenario):
    backend, ledger, parent, candidate = scenario
    first = run(scenario)
    before = backend.calls.copy(), backend.evaluations.copy()
    backend.fail_run = {(role, t) for role in ('PARENT', 'CANDIDATE') for t in backend.tasks}
    assert run(scenario, resume=True) == first
    run_parent_evolution(run_id='test-run', round_id='r1', parent_skill=backend.parent,
                         backend=backend, artifact_dir=parent, resume=True)
    assert before == (backend.calls, backend.evaluations)
    with pytest.raises(ReplayRejected, match='explicit resume'): run(scenario)


def test_candidate_execution_failure_retains_good_checkpoints(scenario):
    backend, _, _, candidate = scenario
    failed = ('CANDIDATE', backend.tasks[1]); backend.fail_run.add(failed)
    with pytest.raises(ReplayRejected, match='incomplete'): run(scenario)
    assert _load(candidate / 'state.json')['status'] == 'INCOMPLETE'
    assert not (candidate / 'learner/pairs.json').exists()
    assert 'SECRET_PROVIDER_MESSAGE' not in (candidate / 'state.json').read_text()
    backend.fail_run.clear()
    result = run(scenario, resume=True)
    assert backend.calls[failed] == 2
    assert backend.calls[('CANDIDATE', backend.tasks[0])] == 1
    assert backend.calls[('PARENT', backend.tasks[1])] == 1
    assert (candidate / 'tasks/T002.partial-1/binding.json').exists()
    assert len(result.payload['pairs']) == 3


def test_evaluation_failure_resumes_without_new_rollout(scenario):
    backend, _, _, candidate = scenario
    failed = ('CANDIDATE', backend.tasks[1]); backend.fail_eval.add(failed)
    with pytest.raises(ReplayRejected): run(scenario)
    assert (candidate / 'tasks/T002/raw_complete.json').exists()
    assert not (candidate / 'tasks/T002/checkpoint.json').exists()
    backend.fail_eval.clear()
    run(scenario, resume=True)
    assert backend.calls[failed] == 1 and backend.evaluations[failed] == 2
    assert backend.evaluations[('CANDIDATE', backend.tasks[0])] == 1


@pytest.mark.parametrize('field', ['initial_db', 'user_prompt', 'execution_config', 'visible_view'])
def test_pair_mismatch_fails_before_candidate_model_execution(scenario, field):
    backend, _, _, candidate = scenario
    backend.mismatch = field
    with pytest.raises(ReplayRejected): run(scenario)
    assert not any(role == 'CANDIDATE' for role, _ in backend.calls)
    assert not (candidate / 'learner/pairs.json').exists()


@pytest.mark.parametrize('change', ['seed', 'runtime', 'subset', 'reorder', 'monitor'])
def test_parent_manifest_drift_blocks_all_candidate_execution(scenario, change):
    backend, _, _, candidate = scenario
    if change == 'seed': backend.seed += 1
    elif change == 'runtime': backend.version = 'other'
    elif change == 'subset': backend.tasks.pop()
    elif change == 'reorder': backend.tasks.reverse()
    else: backend.tasks.append('PRIVATE-MONITOR')
    with pytest.raises(ReplayRejected, match='input mismatch'): run(scenario)
    assert not candidate.exists()


def test_wrong_candidate_or_parent_skill_cannot_reuse_run(case, scenario):
    backend, ledger, parent, candidate = scenario
    run(scenario)
    different = ledger_for(value_for(case, backend.parent, [('MISSING', [])]), [(0, '- Other')])
    with pytest.raises(ReplayRejected, match='input mismatch'):
        run_candidate_replay(different, backend=backend, parent_dir=parent, artifact_dir=candidate, resume=True)
    wrong_parent = ledger_for(value_for(case, '- Different parent', [('MISSING', [])]), [(0, '- Candidate')])
    with pytest.raises(ReplayRejected, match='input mismatch'):
        run_candidate_replay(wrong_parent, backend=backend, parent_dir=parent, artifact_dir=candidate, resume=True)


def test_completed_checkpoint_corruption_is_not_rerun(scenario):
    backend, _, _, candidate = scenario
    run(scenario); before = backend.calls.copy()
    simulation = candidate / 'tasks/T001/simulation.json'
    simulation.write_text('{}')
    with pytest.raises(ReplayRejected, match='digest mismatch'): run(scenario, resume=True)
    assert backend.calls == before


def test_missing_parent_pair_blocks_candidate(scenario):
    backend, _, parent, candidate = scenario
    (parent / 'tasks/T002/checkpoint.json').unlink()
    with pytest.raises((ReplayRejected, OSError)): run(scenario)
    assert not candidate.exists() and sum(backend.calls.values()) == 3


def test_changed_parent_evidence_cannot_reuse_candidate(scenario):
    _, _, parent, _ = scenario
    run(scenario)
    _save(parent / 'tasks/T001/evaluation.json', {'success': True, 'compliant': True})
    with pytest.raises(ReplayRejected, match='digest mismatch'): run(scenario, resume=True)


@pytest.mark.parametrize('change', [lambda d:d.pop('success'), lambda d:d.update(success=1), lambda d:d.update(compliant=None)])
def test_missing_or_nonboolean_score_is_not_false_label(scenario, change):
    backend, _, _, candidate = scenario
    backend.label_mutator = change
    with pytest.raises(ReplayRejected): run(scenario)
    assert not (candidate / 'learner/pairs.json').exists()
    assert all((candidate / 'tasks' / f'T{i+1:03d}/raw_complete.json').exists() for i in range(3))


@pytest.mark.parametrize('change', [lambda d:d.update(task_id='other'), lambda d:d.update(seed=True)])
def test_wrong_simulation_identity_is_rejected(scenario, change):
    backend, _, _, candidate = scenario
    backend.simulation_mutator = change
    with pytest.raises(ReplayRejected): run(scenario)
    assert not (candidate / 'learner/pairs.json').exists()


def test_forged_learner_export_rejected_even_after_rehash(scenario):
    backend, ledger, parent, candidate = scenario
    run(scenario)
    path = candidate / 'learner/pairs.json'
    payload = _load(path); payload['pairs'][0]['candidate']['supervision']['success'] = False
    _save(path, payload)
    marker = candidate / 'learner/validation.json'
    validation = _load(marker); validation['pairs_sha256'] = _file_digest(path); _save(marker, validation)
    with pytest.raises(ReplayRejected, match='private evidence'):
        load_candidate_replay(ledger, backend=backend, parent_dir=parent, artifact_dir=candidate)
    with pytest.raises(ReplayRejected, match='saved learner'): run(scenario, resume=True)


def test_export_interruption_resume_does_not_rerun(scenario, monkeypatch):
    _, _, _, candidate = scenario
    original = Path.replace
    def fail(self, target):
        if Path(target).name == 'pairs.json': raise OSError('disk')
        return original(self, target)
    monkeypatch.setattr(Path, 'replace', fail)
    with pytest.raises(OSError): run(scenario)
    assert _load(candidate / 'state.json')['status'] == 'COMPLETE'
    before = scenario[0].calls.copy()
    monkeypatch.setattr(Path, 'replace', original)
    run(scenario, resume=True)
    assert scenario[0].calls == before


def test_empty_candidate_delete_is_executed(case, tmp_path):
    backend = Backend()
    ledger = ledger_for(value_for(case, backend.parent, [('SHOULD_REMOVE', [0])]))
    run_parent_evolution(run_id='test-run', round_id='r1', parent_skill=backend.parent,
                         backend=backend, artifact_dir=tmp_path / 'parent')
    result = run_candidate_replay(ledger, backend=backend, parent_dir=tmp_path / 'parent', artifact_dir=tmp_path / 'candidate')
    assert result.payload['pairs'][0]['candidate']['skill_ref']['sha256'] == digest('')
    assert sum(backend.calls.values()) == 6


def test_directory_lock_blocks_concurrent_runs(scenario):
    with _lock(scenario[3]):
        with pytest.raises(ReplayRejected, match='already running'): run(scenario)


def test_no_outcome_or_gate_filter_argument(scenario):
    with pytest.raises(TypeError): run(scenario, accepted_only=True)


@pytest.mark.parametrize('workers', [0, True, -1])
def test_invalid_worker_count_rejected(scenario, workers):
    backend, ledger, parent, candidate = scenario
    with pytest.raises(ReplayRejected, match='worker'):
        run_candidate_replay(ledger, backend=backend, parent_dir=parent, artifact_dir=candidate, max_workers=workers)


def test_parent_generation_inputs_reuse_identical_safe_experiences(scenario):
    from src.skill_evolution.v17.experience_cards_v17 import build_experience_cards
    backend, _, parent, _ = scenario
    before = backend.calls.copy()
    sources, scope = load_parent_experiences(run_id='test-run', round_id='r1', parent_skill=backend.parent,
                                             backend=backend, artifact_dir=parent)
    cards = build_experience_cards(sources, scope=scope).payload
    replay = run(scenario).payload
    for card, pair in zip(cards['cards'], replay['pairs']):
        assert card['task_ref'] == pair['task_ref']
        assert card['events'] == [{k:v for k,v in e.items() if k != 'evidence_ref'} for e in pair['parent']['events']]
    assert all(backend.calls[k] == count for k, count in before.items())


def test_unknown_tool_observation_never_publishes_safe_pair(scenario):
    backend, _, _, candidate = scenario
    backend.simulation_mutator = lambda d: d['messages'][1]['tool_calls'][0].update(name='hidden_tool')
    with pytest.raises(ReplayRejected): run(scenario)
    assert not (candidate / 'learner/pairs.json').exists()


def test_corrupt_export_manifest_not_silently_repaired(scenario):
    run(scenario)
    marker = scenario[3] / 'learner/validation.json'
    state = _load(marker); state['input_sha256'] = '0' * 64; _save(marker, state)
    with pytest.raises(ReplayRejected, match='manifest mismatch'): run(scenario, resume=True)
    assert _load(marker) == state


def test_interruption_records_incomplete_and_reuses_other_tasks(scenario, monkeypatch):
    backend, _, _, candidate = scenario
    prepare = backend.prepare
    def interrupted(task_id, skill, directory):
        if task_id == backend.tasks[1]: raise KeyboardInterrupt()
        return prepare(task_id, skill, directory)
    monkeypatch.setattr(backend, 'prepare', interrupted)
    with pytest.raises(KeyboardInterrupt): run(scenario)
    assert _load(candidate / 'state.json')['status'] == 'INCOMPLETE'
    assert not (candidate / 'learner/pairs.json').exists()
    before = backend.calls.copy()
    monkeypatch.setattr(backend, 'prepare', prepare)
    run(scenario, resume=True)
    for key, value in before.items():
        assert backend.calls[key] == value


def test_pair_identity_is_round_scoped(case, scenario):
    backend, ledger, parent, candidate = scenario
    first = run(scenario).payload
    round2 = ledger_for(value_for(case, backend.parent, [('MISSING', [])], 'r2'), [(0, '- Candidate')])
    parent2 = parent.parent / 'parent2'; candidate2 = candidate.parent / 'candidate2'
    run_parent_evolution(run_id='test-run', round_id='r2', parent_skill=backend.parent,
                         backend=backend, artifact_dir=parent2)
    second = run_candidate_replay(round2, backend=backend, parent_dir=parent2, artifact_dir=candidate2).payload
    assert {p['pair_id'] for p in first['pairs']}.isdisjoint({p['pair_id'] for p in second['pairs']})
    assert [p['task_ref'] for p in first['pairs']] == [p['task_ref'] for p in second['pairs']]
