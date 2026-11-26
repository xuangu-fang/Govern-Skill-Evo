from copy import deepcopy
import json
from threading import Lock
from src.adapters.officeqa.data import Dataset, PROFILE
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26.training import MERGED_POOL
from src.skill_evolution.v26_1 import protocol as p, config, facts, diagnosis, preconditioner, editor, replay
from src.skill_evolution.v26_1.campaign import CampaignAdapter
from src.skill_evolution.v26_1.execution_input_view import restore_model_input


def response(answer='1000', calls=()):
    return {'choices': [{'finish_reason': 'tool_calls' if calls else 'stop', 'message': {
        'role': 'assistant', 'content': None if calls else answer, 'reasoning_content': 'HIDDEN_REASONING_SENTINEL',
        **({'tool_calls': [{'id': f'call_{i}', 'type': 'function', 'function': {'name': name,
            'arguments': json.dumps(args)}} for i, (name, args) in enumerate(calls)]} if calls else {})}}],
        'usage': {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}}


class Provider:
    def __init__(self):
        self.requests = []; self.scripts = {}; self.lock = Lock()

    def __call__(self, **body):
        with self.lock:
            self.requests.append(deepcopy(body))
            encoded = json.dumps(body['messages'])
            task = next((t for t in self.scripts if f'Question for {t}?' in encoded), None)
            if task:
                value = self.scripts[task].pop(0)
                if not self.scripts[task]: del self.scripts[task]
                if isinstance(value, BaseException): raise value
                return value
            return response()


def make(tmp, *, full=False):
    parsed = tmp / 'parsed'; (parsed / 'transformed').mkdir(parents=True); (parsed / 'jsons').mkdir()
    name = 'treasury_bulletin_2011_03.txt'
    (parsed / 'transformed' / name).write_text('Revenue 1000\nOther line\n' * 500)
    (parsed / 'jsons' / name.replace('.txt', '.json')).write_text(json.dumps({'document': {'elements': [
        {'bbox': [{'page_id': 2}], 'content': 'Visible source page 2: revenue 1000.'},
        {'bbox': [{'page_id': 3}], 'content': 'UNOBSERVED_PAGE_SENTINEL'}]}}))
    prepared = tmp / 'prepared'
    splits = {'train': sum(p.PLAN['schedule']['batches'], []) if full else ['UID0007', 'a', 'b', 'c'],
              'val': [], 'test': p.PLAN['schedule']['test_ids'] if full else ['t', 't2']}
    for split, ids in splits.items():
        (prepared / split).mkdir(parents=True)
        rows = [{'id': uid, 'uid': uid, 'question': f'Question for {uid}?',
                 'ground_truth': 'GOLD_ONLY_SENTINEL', 'answers': ['1000', 'GOLD_ONLY_SENTINEL'],
                 'category': 'synthetic', 'task_type': 'officeqa', 'split': split,
                 'source_files': [name], 'source_docs': ['https://fraser.stlouisfed.org/title/treasury-bulletin-407/march-2011-7147?page=2']}
                for uid in ids]
        (prepared / split / 'items.json').write_text(json.dumps(rows))
    (prepared / 'manifest.json').write_text(json.dumps({'profile': PROFILE, 'splits': splits, 'synthetic': True}))
    data = Dataset(prepared); data.optimization_pool = MERGED_POOL
    data.batches = [data.splits['train'][i:i+10] for i in range(0, len(data.splits['train']), 10)]
    provider = Provider()
    def transport(limit):
        return ChatTransport(offline_create=provider, model=p.ACTOR['model'], max_completion_tokens=limit,
                             reasoning_effort='medium', reasoning_mode='deepseek_thinking', token_limit_field='max_tokens')
    method = CampaignAdapter(data, Runtime(parsed), transport(32768), task_transports={'UID0007': transport(65536)})
    return method, provider, config.campaign_config(method)


def batch(method, tmp, *, role='parent', skill='alpha\nbeta\ngamma\n', tasks=None):
    tasks = tasks or method.dataset.splits['train']
    tmp.mkdir(parents=True, exist_ok=True)
    skill_file = tmp / 'skill.md'; skill_file.write_bytes(skill.encode())
    records = method.actor_batch(tasks, skill_file, tmp / 'runs', {'split': 'train', 'role': role})
    method.register_archive(tmp / 'runs')
    return records


def diagnosed(method, tmp, *, outputs=None):
    records = batch(method, tmp)
    saved = facts.build_parent_bundle(records, 'round1')
    output = outputs or {'decision': 'revise', 'reason': 'Observed P1:1', 'plan': {
        'goal': 'Read carefully P1', 'updates': [{'id': 'u1', 'text': 'Change alpha', 'basis': ['P1:1']},
                                               {'id': 'u2', 'text': 'Change beta', 'basis': ['P1:0']}]}}
    return records, diagnosis.diagnosis_call(saved).complete(output)


def edited(method, tmp, *, patches=None, answers=None):
    records, d = diagnosed(method, tmp / 'parent')
    c = preconditioner.preconditioner_call(d, {'rounds': []})
    adjusted = c.complete({'adjustments': [{'target': u['id'], 'action': 'KEEP', 'text': None, 'reason': 'Keep'}
                                         for u in d['diagnosis']['plan']['updates']]})
    patches = patches or ['@@\n-alpha\n+ALPHA\n', '@@\n-beta\n+BETA\n']
    patches = [('--- a/SKILL.md\n+++ b/SKILL.md\n' + patch) if patch else patch for patch in patches]
    e = editor.editor_call(adjusted).complete({'edits': [{'update_id': uid, 'patch': patch, 'reason': 'Apply'}
                                            for uid, patch in zip(('u1','u2'), patches)]})
    return records, e


class MethodProvider:
    def __init__(self, mode='no_change'):
        self.mode = mode; self.calls = []

    def __call__(self, name, messages, directory, call_config):
        self.calls.append((name, deepcopy(messages)))
        view = json.loads(messages[1]['content'])
        if name != 'editor': view = restore_model_input(view, module=name)
        if name == 'diagnosis':
            value = {'decision': 'no_change', 'reason': 'No change', 'plan': None}
            if self.mode != 'no_change':
                value = {'decision': 'revise', 'reason': 'Observe P1', 'plan': {'goal': 'Improve', 'updates': [
                    {'id': 'u1', 'text': 'Add a verification instruction.', 'basis': ['P1:1']}]}}
        elif name == 'preconditioner':
            value = {'adjustments': [{'target': 'u1', 'action': 'WITHDRAW' if self.mode == 'withdraw' else 'KEEP',
                                     'text': None, 'reason': 'Review'}]}
        elif name == 'editor':
            patch = '' if self.mode == 'empty' else None if self.mode == 'null' else (
                '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n ' + view['parent'].splitlines()[-1] + f'\n+Verify the operands at round {len(self.calls)}.\n')
            value = {'edits': [{'update_id': 'u1', 'patch': patch, 'reason': 'Implement'}]}
        elif name == 'replay':
            value = {'entries': [{'knowledge': [{'task_id': pair['task_id'], 'update_id': 'u1',
                'text': f"Compare {pair['parent']}:1 and {pair['candidate']}:1"} for pair in view['pairs']]}]}
        else: raise AssertionError(name)
        return {'content': json.dumps(value), 'finish_reason': 'stop', 'response_model': 'offline', 'usage': {}}
