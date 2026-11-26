"""Synthetic SearchQA cases and authored outputs; never experimental results."""
from copy import deepcopy
from contextlib import contextmanager, ExitStack
import json
import re
from unittest.mock import patch
from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
from src.skill_evolution.v28_3.actor_io import ActorAdapter
from src.skill_evolution.v28_3.campaign import CampaignAdapter
from src.skill_evolution.v28_3.config import campaign_config
from tests.skill_evolution.v28.runtime_support import Transport as BaseTransport, response, HIDDEN
from tests.skill_evolution.v28.campaign_support import CampaignDataset

class Transport(BaseTransport):
    @property
    def generate(self): return self.fn
    @generate.setter
    def generate(self, fn): self.fn = fn

class PlainDataset(CampaignDataset):
    verify_hashes = False
    batch_size = 30
    optimization_pool = 'synthetic-only'
    def snapshot(self):
        return {'dataset_id': 'synthetic-v28.3', 'splits': deepcopy(self.splits), 'batches': deepcopy(self.batches)}

def fresh(data, transport=None):
    return CampaignAdapter(ActorAdapter(data, transport))

def bind(root, *, rounds=2, size=2, test_size=1, mode='mixed', sizes=None):
    if sizes is not None:
        assert len(set(sizes)) == 1
        rounds, size = len(sizes), sizes[0]
    data = PlainDataset(rounds, size, test_size)
    data.root = root / 'dataset'
    data.root.mkdir(parents=True, exist_ok=True)
    def answer(messages, slot):
        skill = messages[0]['content']
        number = int(re.search(r'(?:Question|question) (\d+)', messages[1]['content'])[1])
        if mode == 'gain': good = 'rule u1' in skill
        elif mode == 'loss': good = 'candidate_runs' not in slot.parts
        elif mode in ('none', 'f1'): good = False
        else: good = ('rule u1' in skill) if number % 2 == 0 else ('rule u2' not in skill)
        content = 'New York City' if good else ('New' if mode == 'f1' and 'rule u1' in skill else 'New York')
        return response('<answer>' + content + '</answer>')
    transport = Transport(answer); transport.config = p.actor_config(30)
    adapter = fresh(data, transport)
    return data, transport, adapter, campaign_config(adapter)

@contextmanager
def no_hashes():
    with ExitStack() as stack:
        for target in ('hashlib.sha256', 'src.skill_evolution.v28.benchmarks.searchqa.protocol.digest',
                       'src.skill_evolution.v28.benchmarks.searchqa.protocol.file_digest'):
            stack.enter_context(patch(target, side_effect=AssertionError('v28.3 must not hash')))
        yield

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
            out = {'decision': 'revise', 'reason': 'Compare the entity response using P1:1.',
                   'plan': {'goal': 'Scoped synthetic entity guidance.', 'updates': [
                       {'id': f'u{i}', 'text': f'Apply {round_name} entity rule {i}.', 'basis': ['P1:1']}
                       for i in range(1, self.count + 1)]}}
            if self.no_change == name: out = {'decision': 'no_change', 'reason': 'No justified update.', 'plan': None}
        elif name == 'preconditioner':
            out = {'adjustments': [{'target': u['id'], 'action': 'WITHDRAW' if self.no_change == name else 'KEEP',
                                    'text': None, 'reason': 'Current evidence supports this decision.'}
                                   for u in value['plan']['updates']]}
        elif name == 'editor':
            edits = []
            for u in value['plan']['updates']:
                candidate = value['parent'] + f"\n- Round {round_name} rule {u['id']}: scoped entity guidance.\n"
                delta = re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(value['parent'], candidate), flags=re.MULTILINE)
                edits.append({'update_id': u['id'], 'patch': None if self.null else '' if self.no_change == name else delta,
                              'reason': 'Implement the corresponding rule.'})
            out = {'edits': edits}
        elif name == 'replay':
            assert 'memory' not in value and 'gate' not in value
            items = []
            for pair in value['pairs']:
                uid = ('u1' if self.count == 1 or pair['candidate_result']['em'] == 1 else 'u2')
                if self.attribution == 'unresolved': uid = None
                if self.attribution == 'conflict': uid = 'u1'
                items.append({'task_id': pair['task_id'], 'update_id': uid,
                              'text': 'The observed answer change corresponds to the scoped rule; joint evidence only.'})
            out = {'entries': [] if self.invalid_replay else [{'knowledge': items}]}
        else: raise AssertionError('Unexpected model module')
        return {'content': json.dumps(out), 'finish_reason': 'stop'}
