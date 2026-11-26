"""Deterministic synthetic campaign dependencies, never provider calls."""
from copy import deepcopy
import json
from .runtime_support import Dataset, Transport, response, SKILL, HIDDEN
from .test_method import diagnosis, keep, knowledge, unnumbered
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.campaign import CampaignAdapter
from src.skill_evolution.v28.config import campaign_config


class CampaignDataset(Dataset):
    def __init__(self, rounds=2, batch_size=2, test_size=2):
        super().__init__(rounds * batch_size)
        self.splits = {'train': list(self.rows), 'test': []}
        self.batches = [self.splits['train'][i:i + batch_size] for i in range(0, rounds * batch_size, batch_size)]
        for i in range(test_size):
            tid = f'synthetic-test:{i:03}'
            self.rows[tid] = {'question': f'Test question {i}', 'context': f'Test context {i}',
                              'answers': ['New York City'], 'source_split': 'test'}
            self.splits['test'].append(tid)

    def snapshot(self):
        return {**super().snapshot(), 'splits': deepcopy(self.splits), 'batches': deepcopy(self.batches)}


def bind(*, rounds=2, batch_size=2, accept=True, transport=True):
    dataset = CampaignDataset(rounds, batch_size)
    actor = Transport(lambda m, _: response('<answer>New York City</answer>'
        if accept and 'Use the exact entity.' in m[0]['content'] else '<answer>New York</answer>')) if transport else None
    adapter = CampaignAdapter(SearchQAActorAdapter(dataset, actor))
    config = campaign_config(adapter, initial_skill={'source': 'synthetic fixture only', 'text': SKILL},
                             context_window_tokens=1048576)
    return dataset, actor, adapter, config


class Generator:
    def __init__(self, *, no_change=None, semantic_stop=False, invalid_replay=False):
        self.no_change = no_change
        self.semantic_stop = semantic_stop
        self.invalid_replay = invalid_replay
        self.calls = []
        self.messages = []

    def __call__(self, name, messages, directory, config):
        assert HIDDEN not in json.dumps(messages)
        self.calls.append(name); self.messages.append(deepcopy(messages))
        value = json.loads(messages[1]['content'])
        if name == 'grouping':
            runs = value['runs']
            out = {'groups': [{'group_id': 'G1', 'members': [r['ref'] for r in runs],
                    'decision_problem': 'Entity boundaries',
                    'shared_basis': ' '.join(r['ref'] + ':1' for r in runs), 'important_differences': []}]}
        elif name == 'diagnosis':
            out = {'decision': 'no_change', 'reason': 'No justified update.', 'plan': None} if self.no_change == name else diagnosis(1)
        elif name == 'preconditioner':
            out = keep(1)
            if self.no_change == name:
                out['adjustments'][0].update(focus=['D'], change='Withdraw redundant instruction.', to=[])
                out['checks'] = []
        elif name == 'editor':
            candidate = value['parent'] + '\nUse the exact entity. ' + directory.parents[2].name + '\n'
            out = {'patch': None if self.semantic_stop else '' if self.no_change == name else unnumbered(value['parent'], candidate),
                   'reason': 'Synthetic entity instruction.'}
        elif name == 'replay':
            assert 'gate' not in value
            assert set(value['memory']) == {'format', 'entries'}
            out = {'entries': [{'revises': [], 'knowledge': []}]} if self.invalid_replay else knowledge()
        else:
            raise AssertionError('Disabled method module invoked')
        return {'content': json.dumps(out), 'finish_reason': 'stop', 'usage': response()['usage']}
