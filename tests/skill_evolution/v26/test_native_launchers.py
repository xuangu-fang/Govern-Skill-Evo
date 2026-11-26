"""Actual native loops + public Actor, with scripted responses and blocked network."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from skilladam.execution.contracts import GenerationResult
from skilladam.methods.skilladam import SkillAdamRunner

from src.adapters.officeqa import launchers as l
from .conftest import response


def recipe(office, method, monkeypatch, *, provider=None):
    root, dataset, runtime, _ = office
    from src.adapters.officeqa.transport import ChatTransport
    calls = []
    def scripted(**body):
        calls.append(body)
        return provider(**body) if provider else response('<answer>1000</answer>')
    transport = ChatTransport(model='offline-fixture', max_completion_tokens=1234, offline_create=scripted)
    actor = root / 'actor.json'; actor.write_text(json.dumps(transport.metadata()))
    # Small synthetic data replaces only the inventory; production enforces the fixed 74 IDs.
    monkeypatch.setattr(l, 'OptimizationDataset', lambda _: dataset)
    native = ({'num_epochs': 1, 'batch_size': 2, 'use_slow_update': False, 'use_meta_skill': False}
              if method == 'skillopt' else {'train_size': 1, 'validation_size': 1,
              'validation_mode': 'same_batch', 'sampling_strategy': 'sequential',
              'feedback_loop': {'max_iterations': 2}})
    optimizer = ({'model': 'different-optimizer', 'api_key_env': 'UNUSED', 'base_url': 'https://invalid/v1',
                  'max_tokens': 4321, 'temperature': 0.5, 'timeout_seconds': 111}
                 if method == 'skillopt' else {'model': 'different-optimizer', 'base_url': 'https://invalid/v1',
                 'reasoning_effort': 'none',
                 'backend_config': {'max_completion_tokens': 4321, 'max_retries': 2}})
    cfg = {'method': method, 'prepared_root': str(dataset.root), 'parsed_root': str(runtime.parsed_root),
           'actor_config': str(actor), 'native': native, 'optimizer': optimizer, 'workers': 10 if method == 'skilladam' else 4}
    return cfg, transport, calls


class AdamGenerator:
    def __init__(self, interrupt_momentum=False):
        self.requests = []; self.interrupt_momentum = interrupt_momentum

    def generate(self, request):
        self.requests.append(request)
        assert request.context.model == 'different-optimizer'
        if request.stage == 'momentum_update':
            if self.interrupt_momentum:
                raise RuntimeError('offline interruption at Momentum')
            return GenerationResult('No tracker update required.')
        assert request.stage == 'iteration_patch'
        patch = '--- a/skill.md\n+++ b/skill.md\n@@ -1,1 +1,2 @@\n # OfficeQA Skill\n+Offline candidate instruction.\n'
        return GenerationResult(json.dumps({'reasoning': 'Synthetic fixture only.', 'patch': patch}))


def test_native_adam_loop_stage_routing_and_completed_resume(office, monkeypatch):
    cfg, transport, calls = recipe(office, 'skilladam', monkeypatch)
    generator = AdamGenerator(); root = office[0] / 'adam'
    result = l.train(cfg, root, transport=transport, optimizer_backend=generator)
    assert result['test_executed'] is False
    assert len(calls) == 6  # Same task/Skill still executes independently at each stage/iteration.
    assert len(list((root / 'actor').glob('iter_*/training/results.jsonl'))) == 2
    assert len(list((root / 'actor').glob('iter_*/validation_parent/results.jsonl'))) == 2
    assert len(list((root / 'actor').glob('iter_*/validation_candidate/results.jsonl'))) == 2
    for p in (root / 'actor').rglob('run.json'):
        assert l.read(p)['identity']['execution']['workers'] == 10
    assert [r.stage for r in generator.requests] == ['iteration_patch', 'momentum_update'] * 2
    assert l.train(cfg, root, resume=True, transport=transport) == result
    assert len(calls) == 6
    with pytest.raises(ValueError, match='requires --resume'):
        l.train(cfg, root, transport=transport)
    changed = deepcopy(cfg); changed['native']['feedback_loop']['max_iterations'] = 3
    with pytest.raises(ValueError, match='changed on resume'):
        l.train(changed, root, resume=True, transport=transport)


def test_native_adam_checkpoint_pending_momentum(office, monkeypatch):
    cfg, transport, calls = recipe(office, 'skilladam', monkeypatch)
    root = office[0] / 'momentum'
    with pytest.raises(RuntimeError, match='offline interruption'):
        l.train(cfg, root, transport=transport, optimizer_backend=AdamGenerator(True))
    assert (root / 'native/checkpoint.json').is_file()
    before = len(calls); generator = AdamGenerator()
    l.train(cfg, root, resume=True, transport=transport, optimizer_backend=generator)
    assert len(calls) - before == 3
    assert generator.requests[0].stage == 'momentum_update'


def test_adam_first_iteration_interrupt_preserves_actor_allowance(office, monkeypatch):
    count = 0
    def interrupted(**body):
        nonlocal count
        count += 1
        if count == 1:
            raise KeyboardInterrupt('offline request interruption')
        return response('<answer>1000</answer>')
    cfg, transport, calls = recipe(office, 'skilladam', monkeypatch, provider=interrupted)
    cfg['native']['feedback_loop']['max_iterations'] = 1
    root = office[0] / 'interrupted'
    with pytest.raises(KeyboardInterrupt):
        l.train(cfg, root, transport=transport, optimizer_backend=AdamGenerator())
    assert not (root / 'native/checkpoint.json').exists()
    state_path = next((root / 'actor').rglob('actor_state.json'))
    assert len(l.read(state_path)['rounds'][0]['attempts']) == 1
    l.train(cfg, root, resume=True, transport=transport, optimizer_backend=AdamGenerator())
    assert len(l.read(state_path)['rounds'][0]['attempts']) == 2
    assert (root / 'bootstrap_archives/native_000').is_dir()
    assert len(calls) == 4


def test_native_skillopt_loop_uses_native_officeqa_prompts(office, monkeypatch):
    cfg, transport, calls = recipe(office, 'skillopt', monkeypatch)
    from skillopt.gradient import reflect
    from skillopt.prompts import load_prompt
    seen = []
    def optimizer(**kwargs):
        seen.append(kwargs)
        return json.dumps({'patch': {'edits': []}}), {}
    monkeypatch.setattr(reflect, 'chat_optimizer', optimizer)
    monkeypatch.setattr(l, '_optimizer', lambda *args: None)
    root = office[0] / 'opt'
    result = l.train(cfg, root, transport=transport)
    assert result['selection'] == 'native_best_selection'
    assert len(calls) == 3  # One Selection + two Train, no native Test.
    assert seen and seen[0]['system'] == load_prompt('analyst_success', env='officeqa')
    assert (root / 'native/selection_eval_baseline/results.jsonl').exists()
    assert (root / 'native/steps/step_0001/rollout/results.jsonl').exists()
    assert l.read(root / 'native/config.json')['eval_test'] is False
    assert l.read(root / 'native/history.json')[0]['action'] == 'skip_no_patches'
    # Exercise actual native resume, not just the launcher's completion receipt.
    (root / 'result.json').unlink()
    l.train(cfg, root, resume=True, transport=transport)
    assert len(calls) == 3


@pytest.mark.parametrize('method', ['skillopt', 'skilladam'])
def test_prepare_rejects_workers_and_preserves_optimizer_config(office, monkeypatch, method):
    cfg, transport, _ = recipe(office, method, monkeypatch)
    root = office[0] / method
    plan = l.prepare(cfg, root, transport=transport)[0]
    assert not root.exists()
    assert plan['actor']['max_completion_tokens'] == 1234
    assert plan['config']['optimizer'] == cfg['optimizer']
    cfg['workers'] = 8
    with pytest.raises(ValueError, match='workers'):
        l.prepare(cfg, root, transport=transport)


@pytest.mark.parametrize('arm', l.ARMS)
def test_five_arms_forward_same_evaluate_engine(monkeypatch, tmp_path, arm):
    from scripts.runs.run_officeqa_baselines import main
    from src.skill_evolution.v26 import cli
    received = []
    monkeypatch.setattr(cli, 'main', lambda argv: received.append(argv))
    args = ['evaluate', str(tmp_path / arm), '--arm', arm, '--actor-config', 'actor.json',
            '--prepared-root', 'prepared', '--parsed-root', 'parsed', '--actor-key-env', 'ACTOR_KEY']
    if arm in ('v26', 'skillopt', 'skilladam'):
        args += ['--skill', 'chosen.md']
    main(args)
    assert len(received) == 1 and received[0][0] == 'evaluate'
    if arm in ('skillopt', 'skilladam'):
        assert received[0][received[0].index('--workers') + 1] == '20'
    else:
        assert '--workers' not in received[0]
    assert ('--no-skill' in received[0]) == (arm == 'no_skill')
    assert received[0][2:8] == ['--actor-config', 'actor.json', '--prepared-root', 'prepared', '--parsed-root', 'parsed']


def test_training_cli_requires_explicit_start(monkeypatch, tmp_path):
    from scripts.runs.run_officeqa_baselines import main
    config = tmp_path / 'config.json'; config.write_text('{}')
    monkeypatch.setattr(l, 'train', lambda *a, **k: pytest.fail('Training must not run'))
    with pytest.raises(ValueError, match='requires --start'):
        main(['train', str(tmp_path / 'run'), '--config', str(config)])


def test_optimizer_methods_stay_inherited():
    for name in ('_propose_patch', '_generate_momentum', '_condense', '_evaluate_validation'):
        assert getattr(l.TrainingSkillAdamRunner, name) is getattr(SkillAdamRunner, name)


def test_officeqa_summary_receives_actor_pages_and_complete_tool_calls(office, monkeypatch):
    first = '  ' + 'A' * 900 + '\n表格中段\n' + 'B' * 400 + '\n'
    second = '  second observation  '
    pattern = '目录/' * 80 + '"page 19"'
    raw_args = json.dumps({'pattern': pattern}, ensure_ascii=False, indent=2)

    def provider(**body):
        if body['messages'][-1]['role'] == 'user':
            reply = response(calls=[('glob', {'pattern': pattern}), ('glob', {'pattern': 'b'})])
            reply['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = raw_args
            return reply
        return response('<answer>1000</answer>')

    monkeypatch.setattr('src.adapters.officeqa.runtime.native._run_officeqa_tool',
                        lambda call, **kwargs: first if call.call_id == 'call_0' else second)
    cfg, transport, calls = recipe(office, 'skilladam', monkeypatch, provider=provider)
    cfg['native'].update(trajectory_compression='llm', prompt_profile='officeqa-main-result')
    generator = AdamGenerator()
    summaries = []
    native_generate = generator.generate

    def generate(request):
        if request.stage == 'trajectory_compression':
            summaries.append(request.messages[1]['content'])
            return GenerationResult('Offline summary of the training trajectory.')
        return native_generate(request)

    monkeypatch.setattr(generator, 'generate', generate)
    l.train(cfg, office[0] / 'aligned', transport=transport, optimizer_backend=generator)
    assert len(summaries) == 2
    for summary in summaries:
        actor_inputs = {call['messages'][1]['content'] for call in calls}
        assert any(summary.startswith('## Query\n\n' + text + '\n\n## Execution Trace') for text in actor_inputs)
        assert 'Visible source page 2' in summary
        assert summary.index(raw_args) < summary.index(first) < summary.index('{"pattern": "b"}') < summary.index(second)
        assert 'GOLD_ONLY_SENTINEL' not in summary and 'UNOBSERVED_PAGE_SENTINEL' not in summary
    assert all('Offline summary of the training trajectory.' in request.messages[-1]['content']
               for request in generator.requests if request.stage == 'iteration_patch')


def test_skillopt_final_selection_promotes_and_recovers(office, monkeypatch):
    cfg, transport, calls = recipe(office, 'skillopt', monkeypatch)
    from skillopt.gradient import reflect
    monkeypatch.setattr(reflect, 'chat_optimizer', lambda **kw: ('{"patch":{"edits":[]}}', {}))
    monkeypatch.setattr(l, '_optimizer', lambda *args: None)
    root = office[0] / 'promotion'
    l.train(cfg, root, transport=transport)
    native = root / 'native'
    state = l.read(native / 'runtime_state.json')
    current_path = Path(state['current_skill_path'])
    current_path.write_text(current_path.read_text() + '\nSynthetic epoch-end slow update.\n')
    state['best_score'] = 0.0
    l.atomic_json(native / 'runtime_state.json', state)
    (native / 'final_selection_promotion.json').unlink()
    plan, dataset, runtime, _, _ = l.prepare(cfg, root, transport=transport)
    adapter = l.TrainingSkillOptAdapter(dataset, runtime, transport, native_root=native, cfg=plan['native_config'])
    adapter.setup(plan['native_config'])
    before = len(calls)
    l.finish_skillopt_selection(adapter, plan['native_config'], native)
    assert len(calls) == before + 1
    assert l.read(native / 'final_selection_promotion.json')['promoted'] is True
    assert (native / 'best_skill.md').read_text() == current_path.read_text()
    assert l.read(native / 'runtime_state.json')['best_score'] == 1.0
    assert l.read(native / 'summary.json')['best_selection_hard'] == 1.0
    assert l.read(native / 'summary.json')['best_origin'] == state['current_origin']
    # Crash during publication: replay the stored decision, without another Actor call.
    (native / 'best_skill.md').write_text('incomplete publication')
    l.finish_skillopt_selection(adapter, plan['native_config'], native)
    assert len(calls) == before + 1
    assert (native / 'best_skill.md').read_text() == current_path.read_text()


def test_stage_guards_and_prompt_selection(office, monkeypatch):
    cfg, transport, _ = recipe(office, 'skillopt', monkeypatch)
    root = office[0] / 'guard'
    plan, dataset, runtime, _, _ = l.prepare(cfg, root, transport=transport)
    adapter = l.TrainingSkillOptAdapter(dataset, runtime, transport, native_root=root/'native', cfg=plan['native_config'])
    with pytest.raises(ValueError, match='step/stage'):
        adapter.rollout([], 'skill', root/'wrong')
    with pytest.raises(ValueError, match='Final Test must use evaluate'):
        adapter.rollout([dataset.rows['t']], 'skill', root/'native/test')
    assert adapter._env_name == 'officeqa' and adapter.workers == 4


def test_evaluation_receipt_checks_actor_and_skill(office, monkeypatch):
    cfg, transport, _ = recipe(office, 'skilladam', monkeypatch)
    cfg['native']['feedback_loop']['max_iterations'] = 1
    root = office[0] / 'receipt'
    result = l.train(cfg, root, transport=transport, optimizer_backend=AdamGenerator())
    kw = {'actor_config': cfg['actor_config'], 'prepared_root': cfg['prepared_root'],
          'parsed_root': cfg['parsed_root'], 'training_run': root}
    args = l.evaluation_args('skilladam', office[0]/'test', **kw)
    assert args[args.index('--skill')+1] == result['skill_file']
    Path(result['skill_file']).write_text('changed')
    with pytest.raises(ValueError, match='receipt or selected Skill mismatch'):
        l.evaluation_args('skilladam', office[0]/'test', **kw)


def test_exhausted_actor_is_not_reissued_after_bootstrap_resume(office, monkeypatch):
    cfg, transport, calls = recipe(office, 'skilladam', monkeypatch, provider=lambda **kw: {'choices': []})
    from src.adapters.officeqa.retry import GenerationExhausted
    root = office[0] / 'exhausted'
    with pytest.raises(GenerationExhausted):
        l.train(cfg, root, transport=transport, optimizer_backend=AdamGenerator())
    assert len(calls) == 6
    with pytest.raises(GenerationExhausted):
        l.train(cfg, root, resume=True, transport=transport, optimizer_backend=AdamGenerator())
    assert len(calls) == 6


def test_skillopt_candidate_selection_is_separate_from_training(office, monkeypatch):
    cfg, transport, calls = recipe(office, 'skillopt', monkeypatch)
    from skillopt.gradient import reflect
    monkeypatch.setattr(reflect, 'chat_optimizer', lambda **kw: (json.dumps({'patch': {
        'reasoning': 'Offline fixture', 'edits': [{'op': 'append', 'content': 'Synthetic instruction.'}]}}), {}))
    monkeypatch.setattr(l, '_optimizer', lambda *args: None)
    root = office[0] / 'opt-candidate'
    l.train(cfg, root, transport=transport)
    assert len(calls) >= 4
    assert (root / 'native/steps/step_0001/selection_eval/results.jsonl').is_file()
    assert (root / 'native/steps/step_0001/rollout/results.jsonl').is_file()
    assert (root / 'native/steps/step_0001/candidate_skill.md').read_text().endswith('Synthetic instruction.\n')
