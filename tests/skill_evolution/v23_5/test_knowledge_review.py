"""Production publication barrier, real input parity, retries and historical scope."""
from copy import deepcopy
import json

import pytest
import requests

from src.skill_evolution.v23_5 import evolution as ev, knowledge_review as review, knowledge_evidence as evidence
from src.skill_evolution.v23_5.config import method_config
from .test_baseline import Harness, config


class ReviewedHarness(Harness):
    def __init__(self, mode='replace', outcome='ACCEPT'):
        super().__init__(outcome)
        self.mode = mode
        self.review_inputs = []
        self.technical_once = False
        self.history_ref = False

    def generate(self, messages, dest):
        stage = next((s for s in ('verifier', 'repair') if s in dest.parts), None)
        if stage is None:
            response = super().generate(messages, dest)
            if self.history_ref and 'replay' in dest.parts:
                value, payload = json.loads(response['content']), json.loads(messages[1]['content'])
                if payload['memory']['entries']:
                    ref = payload['memory']['entries'][0]['knowledge'][0]['evidence'][0]
                    value['entries'][0]['knowledge'][-1]['evidence'].append(ref)
                    response['content'] = json.dumps(value)
            return response
        self.calls.append(stage)
        value = json.loads(messages[1]['content'])
        self.review_inputs.append((stage, deepcopy(value)))
        ev.save(dest/'request.json', {'messages': messages})
        if self.technical_once:
            self.technical_once = False
            raise requests.Timeout('offline')
        if stage == 'verifier':
            result = {'results': [{'target': t['target'],
                      'verdict': 'SUPPORTED' if self.mode == 'supported' or i else 'CONFLICT',
                      'issues': [] if self.mode == 'supported' or i else [{'statement': t['knowledge']['text'],
                                 'reason': 'Synthetic contract issue.', 'evidence': t['knowledge']['evidence']}]}
                      for i, t in enumerate(value['targets'])]}
            if self.mode == 'bad_verifier': result = {}
        else:
            result = {'changes': [{'target': t['target'], 'knowledge': {**deepcopy(t['knowledge']),
                'text': 'Repaired synthetic experience.' if self.mode != 'unchanged' else t['knowledge']['text']}}
                for t in value['targets']]}
            if self.mode == 'unauthorized': result['changes'][0]['target']['knowledge_index'] = 999
            if self.mode == 'bad_repair': result = {}
            if self.mode == 'empty_entry': result['changes'][0]['knowledge'] = None
        return {'finish_reason': 'stop', 'content': json.dumps(result), 'usage': {'total_tokens': 10}}


def cfg(rounds=1):
    value = config(rounds)
    value['method'] = method_config(knowledge_review=True)
    value['module_max_tokens'] = {'verifier': 32768, 'repair': 32768}
    return value


@pytest.mark.parametrize('outcome', ['ACCEPT', 'RETAIN'])
@pytest.mark.parametrize('mode', ['supported', 'replace', 'unchanged'])
def test_two_rounds_reviewed_memory_and_reload(tmp_path, outcome, mode):
    h = ReviewedHarness(mode, outcome)
    result = ev.run_campaign(tmp_path, config=cfg(2), generate=h.generate, actor_runner=h.actor)
    assert result['status'] == 'complete'
    assert h.calls.count('verifier') == 2
    assert h.calls.count('repair') == (0 if mode == 'supported' else 2)
    for stage, value in h.review_inputs:
        # Round-two carried-over items are excluded from re-verification.
        assert len(value['targets']) == (2 if stage == 'verifier' else 1)
    rd = tmp_path/'rounds/R01'
    raw = ev.read(rd/'replay/attempts/001/replay.json')
    checked = ev.read(rd/'knowledge_review/candidate.json')
    committed = ev.read(rd/'memory/archive'/f'{tmp_path.name}_R01.json')['result']
    assert committed == checked
    if mode == 'replace':
        assert raw != checked and h.memories[1]['entries'][0]['knowledge'][0]['text'] == 'Repaired synthetic experience.'
        assert raw['entries'][0]['knowledge'][1] == checked['entries'][0]['knowledge'][1]
    else: assert raw == checked
    before = deepcopy(h.calls), deepcopy(h.actor_calls)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    ev.final_parent(tmp_path)
    assert before == (h.calls, h.actor_calls)


@pytest.mark.parametrize('mode', ['bad_verifier', 'bad_repair', 'unauthorized'])
def test_invalid_review_exhausts_budget_without_committing(tmp_path, mode):
    h = ReviewedHarness(mode)
    with pytest.raises(ev.Stopped):
        ev.run_campaign(tmp_path, config=cfg(), generate=h.generate, actor_runner=h.actor)
    assert ev.read(tmp_path/'state.json')['next_round'] == 1
    assert not (tmp_path/'rounds/R01/memory').exists()
    before = deepcopy(h.calls)
    with pytest.raises(ev.Stopped):
        ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert before == h.calls
    assert h.calls.count('verifier') == (cfg()['max_attempts'] if mode == 'bad_verifier' else 1)
    assert h.calls.count('repair') == (0 if mode == 'bad_verifier' else cfg()['max_attempts'])


def test_technical_retry_and_crash_after_merge_reuses_results(tmp_path):
    h = ReviewedHarness()
    h.technical_once = True
    def crash(stage):
        if stage == 'memory_prepared': raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        ev.run_campaign(tmp_path, config=cfg(), generate=h.generate, actor_runner=h.actor, hook=crash)
    assert h.calls.count('verifier') == 2 and h.calls.count('repair') == 1
    before = deepcopy(h.calls), deepcopy(h.actor_calls)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert before == (h.calls, h.actor_calls)
    assert h.review_inputs[0] == h.review_inputs[1]


def test_no_targets_skips_both_calls(tmp_path):
    h = ReviewedHarness(); h.empty_memory = True
    ev.run_campaign(tmp_path, config=cfg(), generate=h.generate, actor_runner=h.actor)
    assert 'verifier' not in h.calls and 'repair' not in h.calls
    assert ev.read(tmp_path/'rounds/R01/knowledge_review/result.json')['targets'] == 0


def test_cited_history_only_and_source_identity(tmp_path):
    h = ReviewedHarness('supported'); h.history_ref = True
    ev.run_campaign(tmp_path, config=cfg(2), generate=h.generate, actor_runner=h.actor)
    value = ev.read(tmp_path/'rounds/R02/knowledge_review/input.json')
    refs = value['verifier_input']['source_records']
    historical = [ref for ref in refs if '/' in ref]
    assert historical == [f'{tmp_path.name}_R01/diff']
    assert list(value['historical_sources']) == [f'{tmp_path.name}_R01']
    original = ev.read(tmp_path/'rounds/R01/pairs/input.json')
    assert refs[historical[0]]['diff'] == original['payload']['diff']
    assert refs[historical[0]]['execution_context'] == original['execution_context']


def test_promoted_inputs_and_prompts_equal_frozen_offline_artifacts():
    base = ev.ROOT/'artifacts/methods/v23_5'
    for name in ('R01', 'R02', 'R03'):
        old = base/'verifier_input_001/cases'/name
        bundle, candidate = ev.read(old/'frozen/bundle.json'), ev.read(old/'candidate.json')
        value, _, _ = review.prepare_input(bundle, candidate, '/unused')
        assert value == ev.read(base/'verifier_fact_screen_001/cases'/name/'verifier_input.json')
        verdicts = ev.read(base/'verifier_fact_screen_run_001/runs'/name/'attempts/001/verifier_output.json')
        assert evidence.build_repair_input(value, verdicts, candidate) == ev.read(base/'repair_002/cases'/name/'repair_input.json')
    assert (review.HERE/'knowledge_verifier_prompt.md').read_bytes() == (base/'verifier_fact_screen_001/verifier_prompt.md').read_bytes()
    assert (review.HERE/'knowledge_repair_prompt.md').read_bytes() == (base/'repair_002/repair_prompt.md').read_bytes()
