"""Action-only messages, recorded protocol, module handoff and old-run compatibility."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from src.adapters.alfworld import skill_runtime as rt
from src.adapters.alfworld.run_task_skill import run_episode
from src.adapters.alfworld.run_task_upstream import build_messages, project_action
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23_5 import evolution as ev
from tests.adapters.alfworld.test_skill_episode import FakeEnvironment
from .test_baseline import Harness, config

INITIAL = ev.ROOT / 'src/skill_evolution/v23_5/alfworld_initial_skill.md'


def aligned(record, injection=rt.SKILLOPT_INJECTION, *, retry_invalid_actions=False, action_feedback=False):
    record.setdefault('purpose', 'optimization')
    record['protocol'] = rt.execution_protocol(record['protocol']['max_steps'], injection,
                                               output_format=rt.ACTION_ONLY_OUTPUT,
                                               retry_invalid_actions=retry_invalid_actions,
                                               action_feedback=action_feedback)
    observation, history = record['initial_observation'], []
    for event in record['steps']:
        if retry_invalid_actions:
            # The inherited offline Harness omits API responses; provide the
            # synthetic body required by the new execution-boundary audit.
            event['model_response'] = {'content': f"<action>{event['action']}</action>",
                                       'finish_reason': 'stop'}
        event['messages'] = rt.build_skill_messages(observation, event['admissible_commands'], record['goal'],
            history, record['skill'], injection, output_format=rt.ACTION_ONLY_OUTPUT)
        history.append({'observation': observation, 'action': event['action']})
        observation = event['observation']
    record['context_fingerprint'] = rt.context_fingerprint(record)
    record['execution_fingerprint'] = rt.execution_fingerprint(record)
    return record


@pytest.mark.parametrize('history_length', [0, 1, 2, 4])
@pytest.mark.parametrize('injection', [rt.LEGACY_INJECTION, rt.SKILLOPT_INJECTION])
def test_same_observations_history_menu_and_skill_only_format_changes(history_length, injection):
    history = [{'observation': f'view {i}', 'action': 'look'} for i in range(history_length)]
    skill = {'mode': 'fixed', 'text': 'Keep this exact Skill.\r\n'}
    args = ('current view', ['help', 'look', 'open cabinet 2'], 'test goal', history, skill, injection)
    old = rt.build_skill_messages(*args)
    new = rt.build_skill_messages(*args, output_format=rt.ACTION_ONLY_OUTPUT)
    assert old[0] == new[0]
    assert new[1]['content'] == old[1]['content'].replace(rt._LEGACY_OUTPUT_INSTRUCTION, rt.ACTION_ONLY_INSTRUCTION)
    assert '<think>' not in new[1]['content'] and '</think>' not in new[1]['content']
    assert '<action>' not in new[1]['content']
    assert 'open cabinet 2' in new[1]['content']
    if history_length == 4:
        assert 'view 0' not in new[1]['content'] and 'view 1' not in new[1]['content']
        assert 'view 2' in new[1]['content'] and 'view 3' in new[1]['content']


def test_initial_skill_only_changes_approved_sentence():
    old = (ev.ROOT/'external/SkillOpt/skillopt/envs/alfworld/skills/initial.md').read_bytes().decode()
    instruction = '**Output format**: Always output `<think>...</think>` for reasoning, then `<action>...</action>` for the chosen action.'
    assert old.count(instruction) == 1
    assert INITIAL.read_bytes().decode() == old.replace(instruction, '**Output format**: ' + rt.ACTION_ONLY_INSTRUCTION)


def test_old_defaults_and_decoding_stay_unchanged():
    args = ('view', ['look'], 'goal', [])
    assert rt.build_skill_messages(*args, rt.load_skill()) == build_messages(*args)
    old = rt.execution_protocol(50, rt.SKILLOPT_INJECTION)
    new = rt.execution_protocol(50, rt.SKILLOPT_INJECTION, output_format=rt.ACTION_ONLY_OUTPUT)
    assert 'output_format' not in old
    changed = {k for k in new if new[k] != old.get(k)}
    assert changed == {'initial_template', 'history_template', 'output_format'}
    assert new['thinking'] == 'enabled' and new['max_tokens'] == 16384
    # Prompt-only revision does not silently introduce a stricter parser or action fallback.
    assert project_action('<action>look</action>') == ('look', None)
    assert project_action('<action>...</action><action>look</action>') == ('...', None)


@pytest.mark.parametrize('value', ['unknown', None])
def test_unknown_output_protocol_rejected(value):
    with pytest.raises(ValueError): rt.execution_protocol(50, output_format=value)
    cfg = config(1); cfg['actor_output_format'] = value
    with pytest.raises(ValueError, match='output format'): ev.validate_config(cfg)


def test_real_episode_message_path_and_archive_reconstruction(tmp_path):
    game = tmp_path/'game'; game.write_text('offline')
    item = {'id': 'train:0000', 'gamefile': 'game'}
    manifest = tmp_path/'items.json'; manifest.write_text(json.dumps([item]))
    record = rt.make_record(item=item, split='train', purpose='learning', skill=rt.load_skill(INITIAL),
        model='offline', max_steps=3, gamefile=game, manifest_path=manifest, versions={}, backend_id='offline',
        injection=rt.SKILLOPT_INJECTION, output_format=rt.ACTION_ONLY_OUTPUT)
    messages = []
    def generate(msgs):
        messages.append(deepcopy(msgs))
        assert rt.ACTION_ONLY_INSTRUCTION in msgs[1]['content']
        assert '<think>' not in str(msgs) and '</think>' not in str(msgs)
        return {'content': '<action>look</action>', 'finish_reason': 'stop'}
    path = tmp_path/'trajectory.json'
    run_episode(FakeEnvironment(), generate, record, path)
    assert len(messages) == 3 and verify_record(record)['trace_valid']
    assert build_facts([record])['background']['history_template'] == record['protocol']['history_template']
    loaded = json.loads(path.read_text()); assert verify_record(loaded)['trace_valid']
    for mutation in ('metadata', 'template', 'messages'):
        bad = deepcopy(record)
        if mutation == 'metadata': del bad['protocol']['output_format']
        elif mutation == 'template': bad['protocol']['history_template'] += 'Changed.'
        else: bad['steps'][0]['messages'][1]['content'] += 'Changed.'
        with pytest.raises(ValueError): verify_record(bad)


@pytest.mark.parametrize('retry_invalid_actions,action_feedback', [(False, False), (True, False), (True, True)])
def test_full_evolution_handoff_and_resume_use_recorded_new_templates(tmp_path, retry_invalid_actions, action_feedback):
    cfg = config(1)
    text = INITIAL.read_bytes().decode()
    cfg.update(actor_skill_injection=rt.SKILLOPT_INJECTION, actor_output_format=rt.ACTION_ONLY_OUTPUT,
               actor_retry_invalid_actions=retry_invalid_actions,
               actor_action_feedback=action_feedback,
               initial_skill={'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()})
    h = Harness()
    def actor(task, skill, directory, conf):
        path = h.actor(task, skill, directory, conf)
        ev.save(path, aligned(ev.read(path), retry_invalid_actions=retry_invalid_actions,
                             action_feedback=action_feedback))
        return path
    ev.run_campaign(tmp_path, config=cfg, actor_runner=actor, generate=h.generate)
    assert ev.read(tmp_path/'rounds/R01/result.json')['outcome'] == 'ACCEPT'
    for module in ev.MODULES:
        system = ev.read(tmp_path/'rounds/R01'/module/'attempts/001/messages.json')[0]['content']
        assert system.count(rt.ACTION_ONLY_INSTRUCTION) == 2
        assert '<think>' not in system and '</think>' not in system
    assert ev.final_parent(tmp_path).read_text().startswith(text)
    before = len(h.calls), len(h.actor_calls)
    ev.run_campaign(tmp_path, resume=True, actor_runner=actor, generate=h.generate)
    assert before == (len(h.calls), len(h.actor_calls))


def test_train_and_final_test_commands_keep_format_and_budgets():
    cfg = config(1); cfg['actor_output_format'] = rt.ACTION_ONLY_OUTPUT
    for task, final in [('train:0000', False), ('test:0000', True)]:
        cmd = ev.actor_command(task, INITIAL, Path('offline'), cfg, final=final)
        assert cmd[cmd.index('--output-format')+1] == rt.ACTION_ONLY_OUTPUT
        assert cmd[cmd.index('--request-attempts')+1] == str(cfg['actor_request_attempts'])
    del cfg['actor_output_format']
    assert '--output-format' not in ev.actor_command('train:0000', INITIAL, Path('offline'), cfg)


def test_cli_freezes_selected_format_before_environment_setup(tmp_path, monkeypatch):
    from src.adapters.alfworld import run_task_skill as actor
    (tmp_path/'train').mkdir()
    (tmp_path/'train/items.json').write_text(json.dumps([{'id': 'train:0000', 'gamefile': 'game'}]))
    (tmp_path/'game').write_text('offline fixture')
    monkeypatch.setattr(actor, 'SPLIT_ROOT', tmp_path)
    monkeypatch.setattr(actor, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setattr(actor, 'installed_versions', lambda: {})
    def unavailable():
        raise ImportError('Offline CLI test stops before environment execution')
    monkeypatch.setattr(actor, 'environment_modules', unavailable)
    monkeypatch.setenv('ALFWORLD_DATA', str(tmp_path))
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://offline.invalid')
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-fixture')
    assert actor.main(['--output-root', str(tmp_path/'runs'), '--skill-file', str(INITIAL),
                       '--output-format', rt.ACTION_ONLY_OUTPUT, '--skill-injection', rt.SKILLOPT_INJECTION]) == 1
    path, = (tmp_path/'runs').glob('*/trajectory.json')
    record = json.loads(path.read_text())
    assert record['protocol'] == rt.execution_protocol(50, rt.SKILLOPT_INJECTION, output_format=rt.ACTION_ONLY_OUTPUT)
    assert record['steps'] == [] and record['error_stage'] == 'environment_setup'
