"""Offline replay through the SDK, native reflection, merge and trainer."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import httpx as http
from skillopt.model import openai_compatible_backend as backend
from scripts.runs.skillopt.searchqa import run, step5
from src.adapters.officeqa.skillopt_budget import TrainingPaused, validate
from src.skill_evolution.v28.storage import read, save

ARCHIVE = run.ARCHIVE / 'campaign/model_calls'
ARCHIVED_ANALYST = step5.ARCHIVED_ANALYST
MERGE = '81cf0635e2514be1b403e8daf871014a'
MALFORMED = {
    'c5d759f58889401a97db2fbfdd15c1e1': ('The October Horse', 'Thorn Birds'),
    '067c784b8ea94cecba037461f65a5c47': ('Saratoga Chips',),
    '7f77a169b663417f8ae48ddc953418f9': ('of Poker Flat',),
}
check = TestCase()


def archived(key):
    folder = ARCHIVE / key
    return read(folder / 'http_001_request.json')['body'], read(folder / 'http_001_response_body.bin')


def with_content(raw, text):
    fixed = deepcopy(raw)
    choice = fixed['choices'][0]
    choice['finish_reason'] = 'stop'
    choice['message']['content'] = text
    return fixed


def check_archived_responses():
    valid = Counter()
    invalid = set()
    truncated = set()
    for folder in sorted(ARCHIVE.iterdir()):
        initial = read(folder / 'input.json')
        stage = initial['stage']
        choice = read(folder / 'http_001_response_body.bin')['choices'][0]
        if choice['finish_reason'] == 'length':
            truncated.add(folder.name)
            continue
        assert choice['finish_reason'] == 'stop'
        try:
            validate(choice['message']['content'], stage, initial['messages'])
        except ValueError:
            invalid.add(folder.name)
        else:
            valid[stage] += 1
    assert valid == dict(analyst=230, merge=86, ranking=39, slow_update=3, meta_skill=3)
    assert invalid == set(MALFORMED) and truncated == {ARCHIVED_ANALYST, MERGE}
    return dict(total=sum(valid.values()) + len(invalid) + len(truncated),
                valid_by_stage=dict(valid), invalid_json=len(invalid), truncated=len(truncated))


def invoke(body, stage):
    system, user = body['messages']
    return backend.chat_optimizer(system['content'], user['content'], body['max_tokens'], stage=stage)


def replay_corrections(tmp, settings):
    for key, quotes in MALFORMED.items():
        body, raw = archived(key)
        original = raw['choices'][0]['message']['content']
        # Test oracle only. Change precisely the unescaped quote pairs present in
        # these archives; the production policy asks the optimizer to correct them.
        fixed = original
        for phrase in quotes:
            fixed = fixed.replace('"' + phrase + '"', json.dumps('"' + phrase + '"')[1:-1])
        corrected = validate(fixed, 'analyst', body['messages'])
        expected = read(ARCHIVE / key / 'input.json')
        calls = []

        def send(req):
            sent = json.loads(req.content)
            calls.append(sent)
            return http.Response(200, json=raw if len(calls) == 1 else with_content(raw, fixed))

        root = tmp / key
        save(root / 'optimizer.json', settings)
        messages = expected['messages']
        with run.optimizer_provider(root, 'offline', http_transport=http.MockTransport(send)):
            text, _ = invoke(body, 'analyst')
        assert json.loads(text) == corrected
        assert calls[0] == body and len(calls) == 2
        assert calls[1]['messages'][:2] == messages and calls[1]['messages'][2]['content'] == original
        assert 'line' in calls[1]['messages'][3]['content']
        assert calls[1]['max_tokens'] == 16384


def check_stage_budgets(tmp, settings, stages):
    # Each stage gets one logical call. Interrupt after slot four and recreate
    # the provider to verify the journal carries both the budget and length count.
    _, length = archived(MERGE)
    result = {}
    for stage in stages:
        root = tmp / ('mixed_' + stage)
        save(root / 'optimizer.json', settings)
        source = next(p for p in sorted(ARCHIVE.iterdir()) if read(p / 'input.json')['stage'] == stage)
        body, raw = archived(source.name)
        calls = []

        def send(request):
            calls.append(json.loads(request.content))
            number = len(calls)
            if number == 2:
                return http.Response(503, json={})
            if number == 3:
                return http.Response(200, json=with_content(raw, '{}'))
            return http.Response(200, json=length)

        class Interrupted(SystemExit):
            pass

        with run.optimizer_provider(root, 'offline', http_transport=http.MockTransport(send)) as budget:
            dispatch = budget.send

            def until_four(*args):
                if len(calls) == 4:
                    raise Interrupted()
                dispatch(*args)

            with patch.object(budget, 'send', until_four), check.assertRaises(Interrupted):
                invoke(body, stage)
        with run.optimizer_provider(root, 'offline', http_transport=http.MockTransport(send)):
            with check.assertRaises(TrainingPaused):
                invoke(body, stage)
        marker = read(root / 'campaign/optimizer_paused.json')
        assert marker['stage'] == stage and marker['attempts'] == 6
        with check.assertRaises(TrainingPaused), run.optimizer_provider(root, 'offline', http_transport=http.MockTransport(send)):
            raise AssertionError('Reentered paused campaign')
        caps = [c['max_tokens'] for c in calls]
        assert caps == [16384] * 5 + [32768]
        assert calls[0] == body and calls[3]['messages'][2]['content'] == '{}'
        result[stage] = caps
    return result


def check_empty_stop(tmp, settings, stages):
    repaired = []
    for stage in stages:
        root = tmp / ('empty_stop_' + stage)
        save(root / 'optimizer.json', settings)
        source = next(folder for folder in sorted(ARCHIVE.iterdir())
                      if read(folder / 'input.json')['stage'] == stage and
                      folder.name not in {ARCHIVED_ANALYST, MERGE, *MALFORMED})
        body, raw = archived(source.name)
        calls = []

        def send(request):
            calls.append(json.loads(request.content))
            return http.Response(200, json=with_content(raw, '') if len(calls) == 1 else raw)

        with run.optimizer_provider(root, 'offline', http_transport=http.MockTransport(send)):
            text, _ = invoke(body, stage)
        valid = validate(raw['choices'][0]['message']['content'], stage, body['messages'])
        assert len(calls) == 2 and json.loads(text) == valid
        assert calls[1]['messages'][2] == {'role': 'assistant', 'content': ''}
        assert calls[1]['max_tokens'] == calls[0]['max_tokens']
        repaired.append(stage)
    return repaired


class ReachedNextStep(SystemExit):
    pass


def exercise_branch(root, cfg, adapter, identity, mode):
    original, length = archived(ARCHIVED_ANALYST)
    _, merge_length = archived(MERGE)
    _, bad_json = archived(next(iter(MALFORMED)))
    calls = []
    completed_patch = {'patch': {'edits': [{'op': 'append', 'content': 'Offline fixture rule'}]}}
    requested = []

    def send(req):
        body = json.loads(req.content)
        calls.append(body)
        system = body['messages'][0]['content']
        if system == original['messages'][0]['content']:
            if mode == 'length':
                response = length
            elif mode == 'json':
                response = bad_json
            else:
                response = with_content(length, json.dumps(completed_patch))
        elif mode == 'merge_length':
            response = merge_length
        else:
            response = with_content(length, json.dumps(completed_patch['patch']))
        return http.Response(200, json=response)

    class OfflineActor:
        def metadata(self):
            return identity['actor']
        def __call__(self, *args, **kwargs):
            raise AssertionError('Unexpected Actor inference')

    adapter.shared.transport = OfflineActor()
    real_rollout = adapter.rollout

    def rollout(items, skill, directory, **kwargs):
        directory = Path(directory)
        requested.append(directory)
        if 'step_0006' in directory.parts:
            raise ReachedNextStep()
        if directory.name == 'selection_eval':
            assert mode == 'success' and len(items) == 200
            return [dict(hard=0, soft=0)] * len(items)  # synthetic score for the new candidate
        assert directory.name == 'rollout' and directory.parent.name == 'step_0005'
        return real_rollout(items, skill, directory, **kwargs)

    with patch.object(adapter, 'rollout', rollout):
        def train(*, from_step5=True):
            return run.train_formal(root, cfg, adapter, identity, 'offline', from_step5=from_step5,
                                    http_transport=http.MockTransport(send))

        if mode == 'success':
            with check.assertRaises(ReachedNextStep):
                train()
        else:
            with check.assertRaisesRegex(TrainingPaused, 'optimizer_attempts_exhausted'):
                train()
            previous = len(calls)
            with check.assertRaisesRegex(TrainingPaused, 'Optimizer paused'):
                train(from_step5=False)
            assert len(calls) == previous

    camp = root / 'campaign'
    step = camp / step5.STEP5
    assert calls[0] == original  # direct attempt 002 on precisely the archived messages
    assert not (root / 'test').exists() and not (root / 'selection.json').exists()
    journal = camp / 'model_calls' / read(camp / 'step5_origin.json')['imported_call']
    assert read(journal / 'http_001_outcome.json') == dict(action='length', length_count=1)
    assert read(journal / 'http_002_request.json')['body'] == original
    if mode == 'success':
        assert read(camp / 'runtime_state.json')['last_completed_step'] == 5
        assert len(read(camp / 'history.json')) == 5
        assert all((step / f).exists() for f in ('merged_patch.json', 'candidate_skill.md', 'step_record.json'))
        assert len(list((step / 'patches').glob('*.json'))) == 6
        assert any(d.name == 'selection_eval' for d in requested)
    else:
        assert read(camp / 'runtime_state.json')['last_completed_step'] == 4
        assert len(read(camp / 'history.json')) == 4 and not (step / 'step_record.json').exists()
        assert not (step / 'selection_eval').exists() and not (step / 'merged_patch.json').exists()
        assert not any(d.name == 'selection_eval' for d in requested)
    caps = [c['max_tokens'] for c in calls]
    if mode == 'length':
        assert caps == [16384] * 2 + [32768] * 3 and all(c['messages'] == original['messages'] for c in calls)
    if mode == 'merge_length':
        assert caps[1:] == [16384] * 3 + [32768] * 3 and all(c['messages'] == calls[1]['messages'] for c in calls[1:])
    if mode == 'json':
        assert caps == [16384] * 5 and all(len(c['messages']) == 4 for c in calls[1:])
    return caps


def verify_archives(tmp, identity):
    classified = check_archived_responses()
    replay_corrections(tmp, identity['optimizer'])
    mixed = check_stage_budgets(tmp, identity['optimizer'], identity['optimizer_retry']['stages'])
    empty_stop = check_empty_stop(tmp, identity['optimizer'], identity['optimizer_retry']['stages'])
    runs = {}
    for mode in ('length', 'json', 'merge_length', 'success'):
        root = tmp / mode
        cfg, adapter, run_identity = run.prepare(root)
        runs[mode] = exercise_branch(root, cfg, adapter, run_identity, mode)
    return dict(archive_classification=classified, archived_json_corrections=len(MALFORMED),
                archived_step5_attempt=1, reused_step5_rollouts=40, reused_step5_sibling_patches=5,
                new_request_caps=runs, mixed_failure_caps_across_restart=mixed,
                empty_stop_retried_stages=empty_stop,
                exhausted_restart_new_requests=0, resumed_next_step=6, selection_score_in_success_replay='synthetic')
