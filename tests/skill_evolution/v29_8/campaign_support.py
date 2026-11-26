"""Authored model outputs and tiny images; no experimental results or providers."""
from copy import deepcopy
import json
import re

from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29_8.campaign import CampaignAdapter
from src.skill_evolution.v29_8.config import campaign_config, pending_calls
from tests.skill_evolution.v29.campaign_support import CampaignDataset
from tests.skill_evolution.v29.test_actor import Transport, response, HIDDEN


def bind(root, *, sizes=(2, 2), mode='mixed'):
    data = CampaignDataset(root / 'dataset', list(sizes))
    def answer(messages, slot):
        skill = messages[0]['content']
        candidate = 'candidate_runs' in slot.parts
        number = int(re.search(r'amount (\d+)\?', messages[1]['content'][0]['text'])[1])
        if mode == 'gain': good = 'rule u1' in skill
        elif mode == 'loss': good = not candidate
        elif mode == 'none': good = False
        else: good = ('rule u1' in skill) if number % 2 == 0 else ('rule u2' not in skill)
        return response('<answer>1,320</answer>' if good else '<answer>1,200</answer>')
    transport = Transport(answer)
    adapter = CampaignAdapter(DocVQAActorAdapter(data, transport))
    calls = pending_calls()
    for value in calls.values(): value.update(max_tokens=1000, timeout_seconds=1)
    return data, transport, adapter, campaign_config(adapter, module_calls=calls)


class Generator:
    def __init__(self, *, count=2, no_change=None, null=False, invalid_replay=False, attribution='separate'):
        self.count, self.no_change, self.null = count, no_change, null
        self.invalid_replay, self.attribution = invalid_replay, attribution
        self.calls, self.inputs = [], []

    def __call__(self, name, messages, directory, config):
        assert HIDDEN not in json.dumps(messages)
        value = json.loads(messages[1]['content'])
        self.calls.append(name); self.inputs.append((name, deepcopy(value)))
        round_name = directory.parents[2].name
        if name == 'diagnosis':
            out = {'decision': 'revise', 'reason': 'Compare the amount response using P1:1.',
                   'plan': {'goal': 'Scoped synthetic amount guidance.', 'updates': [
                       {'id': f'u{i}', 'text': f'Apply {round_name} amount rule {i}.', 'basis': ['P1:1']}
                       for i in range(1, self.count + 1)]}}
            if self.no_change == name: out = {'decision': 'no_change', 'reason': 'No justified update.', 'plan': None}
        elif name == 'preconditioner':
            out = {'adjustments': [{'target': u['id'], 'action': 'WITHDRAW' if self.no_change == name else 'KEEP',
                                    'text': None, 'reason': 'Current evidence supports this decision.'}
                                   for u in value['plan']['updates']]}
        elif name == 'editor':
            edits = []
            for u in value['plan']['updates']:
                candidate = value['parent'] + f"\n- Round {round_name} rule {u['id']}: scoped amount guidance.\n"
                delta = re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(value['parent'], candidate), flags=re.MULTILINE)
                edits.append({'update_id': u['id'], 'patch': None if self.null else '' if self.no_change == name else delta,
                              'reason': 'Implement the corresponding rule.'})
            out = {'edits': edits}
        elif name == 'replay':
            assert 'memory' not in value and 'gate' not in value
            items = []
            for pair in value['pairs']:
                uid = ('u1' if self.count == 1 or pair['candidate_result']['hard'] == 1 else 'u2')
                if self.attribution == 'unresolved': uid = None
                if self.attribution == 'conflict': uid = 'u1'
                items.append({'task_id': pair['task_id'], 'update_id': uid,
                              'text': 'The observed answer change corresponds to the scoped rule; joint evidence only.'})
            out = {'entries': [] if self.invalid_replay else [{'knowledge': items}]}
        else: raise AssertionError('Unexpected model module')
        return {'content': json.dumps(out), 'finish_reason': 'stop'}
