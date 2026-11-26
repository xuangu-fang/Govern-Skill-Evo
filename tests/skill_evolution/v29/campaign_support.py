"""Explicit synthetic schedules and responses; the numbers below are test-only."""
from copy import deepcopy
import json
import re
from PIL import Image
from src.skill_evolution.v27.unnumbered_patch import actual_diff
from src.skill_evolution.v29.campaign import CampaignAdapter
from src.skill_evolution.v29.config import campaign_config, pending_calls
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from .test_actor import Dataset, Transport, response, HIDDEN


def diagnosis():
    return {'decision': 'revise', 'reason': 'The amount response differs from its reference in P1:outcome.',
            'plan': {'goal': 'Test amount-role guidance.', 'updates': [{'id': 'u1',
                     'text': 'Compare the requested amount role.\n', 'basis': ['P1:0', 'P1:1', 'P1:outcome']}],
                     'checks': [{'id': 'c1', 'update_ids': ['u1'], 'question': 'Compare hard and ANLS; causality remains unresolved.'}]}}


def keep():
    return {'adjustments': [{'target': 'u1', 'focus': [], 'change': 'KEEP',
                            'reason': 'Keep `Update:u1` for comparison using `Evidence:P1:1`.', 'to': None}], 'checks': None}


class CampaignDataset(Dataset):
    optimization_pool = 'synthetic_docvqa_test_fixture'

    def __init__(self, root, sizes):
        super().__init__(root)
        (root / 'images').mkdir(parents=True)
        Image.new('RGB', (2, 2), 'white').save(root / 'images/amount.png')
        self.rows = {f'synthetic:{i:03}': (f'What is amount {i}?', ['1,320'], 'train') for i in range(sum(sizes))}
        self.splits = {'train': list(self.rows), 'test': ['synthetic:test']}
        self.rows['synthetic:test'] = ('Held-out question?', ['secret'], 'test')
        self.batches = []; offset = 0
        for size in sizes:
            self.batches.append(self.splits['train'][offset:offset + size]); offset += size


def bind(root, *, rounds=2, batch_size=2, sizes=None, accept=True, transport=True):
    dataset = CampaignDataset(root / 'dataset', sizes or [batch_size] * rounds)
    actor = Transport(lambda messages, slot: response('<answer>1,320</answer>'
        if accept and 'Compare the requested amount role.' in messages[0]['content']
        else '<answer>1,200</answer>')) if transport else None
    adapter = CampaignAdapter(DocVQAActorAdapter(dataset, actor))
    calls = pending_calls()
    # These never become production defaults or formal budget decisions.
    for value in calls.values(): value.update(max_tokens=1000, timeout_seconds=1)
    return dataset, actor, adapter, campaign_config(adapter, module_calls=calls)


class Generator:
    def __init__(self, *, no_change=None, semantic_stop=False, invalid_replay=False):
        self.no_change, self.semantic_stop, self.invalid_replay = no_change, semantic_stop, invalid_replay
        self.calls, self.messages = [], []

    def __call__(self, name, messages, directory, config):
        assert HIDDEN not in json.dumps(messages)
        self.calls.append(name); self.messages.append(deepcopy(messages))
        value = json.loads(messages[1]['content'])
        if name == 'grouping':
            out = {'groups': [{'group_id': 'G1', 'members': [r['ref'] for r in value['runs']],
                              'decision_problem': 'Answer the requested amount.',
                              'shared_basis': ' '.join(r['ref'] + ':1' for r in value['runs']),
                              'important_differences': []}]}
        elif name == 'diagnosis':
            out = {'decision': 'no_change', 'reason': 'No justified update.', 'plan': None} if self.no_change == name else diagnosis()
        elif name == 'preconditioner':
            out = keep()
            if self.no_change == name:
                out['adjustments'][0].update(focus=['C'], change='Withdraw duplicate instruction.', to=[])
                out['checks'] = []
        elif name == 'editor':
            candidate = value['parent'] + '\nCompare the requested amount role. ' + directory.parents[2].name + '\n'
            delta = re.sub(r'^@@[^\n]*@@$', '@@', actual_diff(value['parent'], candidate), flags=re.MULTILINE)
            out = {'patch': None if self.semantic_stop else '' if self.no_change == name else delta,
                   'reason': 'Implement the conditional guidance for this synthetic comparison.'}
        elif name == 'replay':
            assert 'gate' not in value and 'raw_content' not in json.dumps(value)
            assert set(value['memory']) == {'format', 'entries'}
            out = {'entries': [{'revises': [], 'knowledge': [] if self.invalid_replay else [
                {'text': 'The observed amount responses permit comparison; causal interpretation remains uncertain.',
                 'evidence': ['diff', 'P1:outcome', 'Q1:outcome']}]}]}
        else:
            raise AssertionError('Unexpected module')
        return {'content': json.dumps(out), 'finish_reason': 'stop'}
