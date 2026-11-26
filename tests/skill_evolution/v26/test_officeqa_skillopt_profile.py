"""Offline acceptance for the production recipe, using the frozen OfficeQA archives."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from skillopt.model import openai_compatible_backend as backend
from skillopt.prompts import load_prompt

from src.adapters.officeqa import launchers as launch
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26 import evaluation
from .conftest import response

ROOT = launch.ROOT
RECIPE = ROOT / 'experiments/configs/officeqa_skillopt_deepseek_flash.json'
V26 = ROOT / 'experiments/campaigns/v26_9_officeqa_train74_20261118_180409'
ADAM = ROOT / 'experiments/baselines/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937'


@pytest.fixture(scope='module')
def frozen(tmp_path_factory):
    run = tmp_path_factory.mktemp('skillopt-plan') / 'run'
    return launch.prepare(launch.read(RECIPE), run)


def adapter(frozen, root, transport):
    plan, dataset, runtime, _, _ = frozen
    result = launch.TrainingSkillOptAdapter(dataset, runtime, transport, native_root=root,
                                           cfg=plan['native_config'])
    result.setup(plan['native_config'])
    return result


def scripted_actor(actor, create):
    return ChatTransport(offline_create=create, **{k: actor[k] for k in (
        'model', 'max_completion_tokens', 'temperature', 'reasoning_effort',
        'reasoning_mode', 'token_limit_field')})


def test_profile_matches_archives_and_plans_four_disjoint_epochs(frozen, tmp_path):
    plan, dataset, _, transport, initial = frozen
    adam = launch.read(ADAM / 'plan.json')
    v26 = launch.read(V26 / 'config.json')
    assert not Path(plan['directory']).exists()
    assert initial == (V26 / 'initial_skill.md').read_text() == (ADAM / 'initial_skill.md').read_text()
    assert plan['initial_skill_sha256'] == adam['initial_skill_sha256']
    assert plan['actor'] == v26['actor'] == adam['actor']
    assert plan['workers'] == v26['train_workers'] == adam['workers'] == 10
    from src.skill_evolution.v26.training import OptimizationDataset
    from src.skill_evolution.v26.benchmarks.officeqa.protocol import digest
    merged = OptimizationDataset(dataset.root)
    for uid, skillopt_task in plan['runtime']['tasks'].items():
        # SkillAdam records its merged split label in the case hash.
        assert adam['runtime']['tasks'][uid] == {**skillopt_task, 'case_sha256': digest(merged.rows[uid])}
    assert plan['train_ids'] + plan['selection_ids'] == adam['train_ids']
    assert plan['test_during_training'] is False and plan['stage0'] is False
    cfg = plan['native_config']
    env = adapter(frozen, tmp_path, transport)
    assert cfg['eval_test'] is False and env.workers == 10 and env.analyst_workers == 16
    assert cfg['num_epochs'] == 4 and cfg['accumulation'] == 1
    assert cfg['use_gate'] and cfg['gate_metric'] == 'hard' and cfg['slow_update_gate_with_selection']
    assert cfg['use_slow_update'] and cfg['use_meta_skill'] and cfg['slow_update_samples'] == 20
    for epoch in range(1, cfg['num_epochs'] + 1):
        batches = env.dataloader.plan_train_epoch(epoch=epoch, steps_per_epoch=2, accumulation=1,
                                                   batch_size=cfg['batch_size'], seed=cfg['seed'])
        assert [b.batch_size for b in batches] == [40, 10]
        assert sorted(row['id'] for b in batches for row in b.payload) == sorted(plan['train_ids'])
    selected = env.build_eval_env(cfg['sel_env_num'], 'valid_seen', cfg['seed'])
    assert [row['id'] for row in selected] == plan['selection_ids']
    assert len(selected) == 24 and tuple(dataset.splits['test']) == evaluation.TEST_IDS


@pytest.mark.parametrize('use_receipt', [False, True], ids=['skill-only', 'training-receipt'])
def test_case_limits_on_real_actor_and_independent_test_entry(frozen, tmp_path, monkeypatch, use_receipt):
    plan, dataset, _, _, initial = frozen
    requests = []
    def create(**body):
        requests.append(body)
        reply = response('<answer>offline</answer>')
        reply['choices'][0]['message']['reasoning_content'] = 'private fixture'
        return reply

    transport = scripted_actor(plan['actor'], create)
    native = tmp_path / 'native'
    env = adapter(frozen, native, transport)
    training = ['UID0002', 'UID0007']
    rows = env.rollout([dataset.rows[uid] for uid in training], initial, native / 'rollout')
    assert {r['id'] for r in rows} == set(training)
    assert launch.read(native / 'rollout/run.json')['identity']['execution']['workers'] == 10
    with pytest.raises(ValueError, match='Final Test'):
        env.rollout([dataset.rows['UID0111']], initial, native / 'rollout')
    schedule = ['UID0003', 'UID0111']
    # Drive the receipt and CLI, but replace the full Test runner with two
    # simulated actor_batch calls. A benchmark Test report is never produced.
    best = tmp_path / 'best_skill.md'
    best.write_text('offline selected skill')
    if use_receipt:
        launch.atomic_json(tmp_path / 'plan.json', plan)
        launch.atomic_json(tmp_path / 'result.json', {'method': 'skillopt', 'skill_file': str(best),
                                                     'skill_sha256': launch.digest(best)})
    def probe(directory, *, adapter, skill_file, resume):
        assert Path(skill_file) == best and adapter.workers == 20
        assert adapter.task_output_limits == {'UID0111': 65536}
        for uid in schedule:
            actor = adapter._adapter(uid).transport
            assert actor.metadata()['max_completion_tokens'] == (65536 if uid == 'UID0111' else 32768)
            sample = adapter.actor_batch([uid], best, tmp_path / 'probe' / uid,
                                         evaluation.ROLE, final=True)
            assert sample[0]['execution']['actor'] == actor.metadata()
        return {}
    monkeypatch.setattr(evaluation, 'run_evaluation', probe)
    # Preserve the production transport constructor and intercept the HTTP boundary.
    def fake_post(session, endpoint, *, json, **kwargs):
        assert endpoint == plan['actor']['endpoint'] and kwargs['timeout'] == (10, 300)
        return SimpleNamespace(status_code=200, json=lambda: create(**json))
    monkeypatch.setattr('requests.Session.post', fake_post)
    monkeypatch.setenv('OFFLINE_PROBE_KEY', 'dummy')
    recipe = plan['config']
    from scripts.runs.run_officeqa_baselines import main
    source_args = ['--training-run', str(tmp_path)] if use_receipt else ['--skill', str(best)]
    main(['evaluate', str(tmp_path / 'test'), '--arm', 'skillopt', *source_args,
          '--actor-config', recipe['actor_config'], '--prepared-root', recipe['prepared_root'],
          '--parsed-root', recipe['parsed_root'], '--actor-key-env', 'OFFLINE_PROBE_KEY'])
    assert not (tmp_path / 'test').exists()
    assert len(requests) == 4
    for uid in training + schedule:
        bodies = [r for r in requests if dataset.rows[uid]['question'] in r['messages'][1]['content']]
        assert len(bodies) == 1
        body = bodies[0]
        assert body['max_tokens'] == (65536 if uid in ('UID0007', 'UID0111') else 32768)
        assert (body['model'], body['thinking'], body['reasoning_effort'], body['temperature']) == (
            'deepseek-flash', {'type': 'enabled'}, 'medium', 1.0)


def test_archived_failure_reaches_native_analyst_and_optimizer_wire(frozen, tmp_path, monkeypatch):
    plan, dataset, runtime, transport, initial = frozen
    uid = 'UID0007'
    record = launch.read(V26 / 'rounds/R01/parent_runs/actor/predictions' / uid / 'trajectory.json')
    assert record['metrics']['em'] == 0 and record['raw_result']['n_tool_calls'] > 0
    # Change only privileged inputs to detectable markers. The question, public
    # page, observations, answer and scores come from the actual archived failure.
    monkeypatch.setitem(dataset.rows[uid], 'answers', ['GOLD_ONLY_OFFICEQA_MARKER'])
    for msg in record['raw_result']['messages']:
        if 'reasoning_content' in msg:
            msg['reasoning_content'] = 'PRIVATE_THINKING_MARKER'
    monkeypatch.setattr(runtime, 'run', lambda *args, **kwargs: record)
    env = adapter(frozen, tmp_path, transport)
    folder = tmp_path / 'rollout'
    rows = env.rollout([dataset.rows[uid]], initial, folder)
    assert not {'ground_truth', 'reference_text', 'aligned_record'} & rows[0].keys()
    seen = []
    def fake_create(**kw):
        seen.append(kw)
        msg = SimpleNamespace(content='{"patch":{"edits":[]}}')
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=None)
    monkeypatch.setenv('OFFICEQA_OPTIMIZER_KEY', 'offline-only')
    launch._optimizer(plan, tmp_path, None)
    monkeypatch.setattr(backend, '_get_client', lambda role: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))))
    from skillopt.model import set_optimizer_backend
    set_optimizer_backend('openai_compatible')
    env.reflect(rows, initial, str(folder))
    assert len(seen) == 1
    wire = seen[0]
    system, user = [m['content'] for m in wire['messages']]
    assert system == load_prompt('analyst_error', env='officeqa')
    assert (wire['model'], wire['max_tokens'], wire['temperature']) == ('deepseek-flash', 16384, 1.0)
    assert wire['extra_body'] == {'thinking': {'type': 'enabled'}, 'reasoning_effort': 'medium'}
    assert initial in user and record['initial_messages'][1]['content'] in user and record['answer'] in user
    assert 'GOLD_ONLY_OFFICEQA_MARKER' not in user and 'PRIVATE_THINKING_MARKER' not in user
    assert '#### Hidden Reference' not in user
    calls = {}
    cursor = 0
    for msg in record['raw_result']['messages']:
        for call in msg.get('tool_calls', []):
            calls[call['id']] = call['function']
        if msg['role'] == 'tool':
            call = calls[msg['tool_call_id']]
            text = f"[action] {call['name']}({call['arguments']})\n[obs]    {msg['content']}"
            cursor = user.index(text, cursor) + len(text)


def test_native_four_epoch_selection_with_mock_models(office, monkeypatch):
    """Run the full algorithm on two synthetic train cases and a held-out fixture."""
    from skillopt.gradient import reflect
    from skillopt.optimizer import meta_skill, slow_update
    from .test_native_launchers import recipe

    marker = 'Evidence rule for synthetic gate.'
    def actor(**body):
        has_rule = marker in body['messages'][0]['content']
        return response('<answer>1000</answer>' if has_rule else '<answer>unmatched</answer>')

    cfg, transport, requests = recipe(office, 'skillopt', monkeypatch, provider=actor)
    cfg['workers'] = 10
    cfg['native'] = {**launch.read(RECIPE)['native'], 'sel_env_num': 1,
                     'batch_size': 1, 'slow_update_samples': 2}
    # Count real native stages; replace only outbound model calls.
    seen = []
    def generate(**kw):
        seen.append(kw)
        result = {'analyst': {'patch': {'edits': [{'op': 'append', 'content': marker}]}},
                  'slow_update': {'slow_update_content': 'Synthetic longitudinal rule.'},
                  'meta_skill': {'meta_skill_content': 'Synthetic optimizer guidance.'}}
        return json.dumps(result[kw['stage']]), {}

    for module in (reflect, slow_update, meta_skill):
        monkeypatch.setattr(module, 'chat_optimizer', generate)
    monkeypatch.setattr(launch, '_optimizer', lambda *args: None)
    root = office[0] / 'synthetic-run'
    result = launch.train(cfg, root, transport=transport)
    history = launch.read(root / 'native/history.json')
    assert len(history) == 8 and history[0]['action'] == 'accept_new_best'
    assert history[0]['selection_hard'] == 1.0
    assert any(row['action'] == 'reject' for row in history[1:])
    for epoch in (2, 3, 4):
        slow = launch.read(root / f'native/slow_update/epoch_{epoch:02}/slow_result.json')
        assert slow['selection_hard'] == 1.0 and slow['action'] == 'reject'
    assert {kw['stage'] for kw in seen} == {'analyst', 'slow_update', 'meta_skill'}
    assert all('GOLD_ONLY_SENTINEL' not in kw['user'] for kw in seen)
    assert not any('Question for t?' in msg['content'] for r in requests for msg in r['messages'])
    best = Path(result['skill_file'])
    assert marker in best.read_text() and 'Synthetic longitudinal rule.' not in best.read_text()
    assert result['skill_sha256'] == launch.digest(best)
    assert result['selection'] == 'native_best_selection' and result['test_executed'] is False
    assert launch.read(root / 'native/final_selection_promotion.json')['promoted'] is False
    calls = len(requests)
    assert launch.train(cfg, root, transport=transport, resume=True) == result and len(requests) == calls


@pytest.mark.parametrize('correct,promoted', [(11, False), (12, False), (13, True)])
def test_final_selection_uses_full_24_and_strict_em(frozen, tmp_path, monkeypatch, correct, promoted):
    plan, _, _, transport, _ = frozen
    cfg = plan['native_config']
    env = adapter(frozen, tmp_path, transport)
    best = tmp_path / 'best_skill.md'
    best.write_text('Previous best')
    current = tmp_path / 'skill_v0008.md'
    current.write_text('Last candidate')
    launch.atomic_json(tmp_path / 'runtime_state.json', {
        'best_skill_path': str(best), 'current_skill_path': str(current), 'best_score': 12/24,
        'best_step': 4, 'best_origin': 'step_0004', 'last_completed_step': 8, 'current_origin': 'step_0008'})
    launch.atomic_json(tmp_path / 'summary.json', {})
    evaluations = []
    def mock_scores(items, skill, directory):
        evaluations.append([item['id'] for item in items])
        assert skill == current.read_text() and directory.name == 'final_selection_eval'
        # Give incorrect cases high partial credit; it must never break a hard tie.
        return [{'id': item['id'], 'hard': int(i < correct), 'soft': 1.0 if i < correct else 0.9}
                for i, item in enumerate(items)]
    monkeypatch.setattr(env, 'rollout', mock_scores)
    launch.finish_skillopt_selection(env, cfg, tmp_path)
    launch.finish_skillopt_selection(env, cfg, tmp_path)
    assert evaluations == [plan['selection_ids']]
    assert launch.read(tmp_path / 'final_selection_promotion.json')['promoted'] is promoted
    assert best.read_text() == ('Last candidate' if promoted else 'Previous best')


def test_selection_and_reflection_reject_wrong_split_before_actor(frozen, tmp_path):
    plan, dataset, _, transport, _ = frozen
    env = adapter(frozen, tmp_path, transport)
    train = dataset.rows[plan['train_ids'][0]]
    val = dataset.rows[plan['selection_ids'][0]]
    with pytest.raises(ValueError, match='Only Train'):
        env.rollout([val], 'skill', tmp_path / 'rollout')
    for rows in ([val], [train], [val] * 24):
        with pytest.raises(ValueError, match='fixed validation IDs'):
            env.rollout(rows, 'skill', tmp_path / 'selection_eval')


@pytest.mark.parametrize('workers,limits', [(4, {}), (20, {'UID0111': 65536})])
def test_standalone_skill_resume_uses_frozen_test_settings(frozen, tmp_path, monkeypatch, workers, limits):
    from scripts.runs.run_officeqa_baselines import main
    plan, _, _, _, _ = frozen
    recipe = plan['config']
    directory = tmp_path / 'existing-test'
    runtime = {'actor': plan['actor']}
    if limits:
        runtime['actor_task_output_limits'] = limits
    launch.atomic_json(directory / 'plan.json', {'runtime': runtime, 'execution': {'workers': workers}})
    best = tmp_path / 'best_skill.md'
    best.write_text('offline resume fixture')
    def inspect(directory, *, adapter, skill_file, resume):
        assert resume and Path(skill_file) == best
        assert adapter.workers == workers and getattr(adapter, 'task_output_limits', {}) == limits
        assert isinstance(adapter.transport, evaluation.ArchiveTransport)
        return {}
    monkeypatch.setattr(evaluation, 'run_evaluation', inspect)
    main(['evaluate', str(directory), '--resume', '--arm', 'skillopt', '--skill', str(best),
          '--actor-config', recipe['actor_config'], '--prepared-root', recipe['prepared_root'],
          '--parsed-root', recipe['parsed_root']])
