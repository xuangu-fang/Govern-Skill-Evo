#!/usr/bin/env python3
"""Offline representation measurements, never an Actor or optimization experiment.

Real 74-case initial contexts + explicitly synthetic accepted turns/outcomes.
Optional cached local tokenizer runs in a separate Python, with networking blocked.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import statistics
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapters.officeqa.runtime import Runtime
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.training import OptimizationDataset
from src.skill_evolution.v26.contracts.editor import actual_diff
from src.skill_evolution.v26.benchmarks.officeqa import input_view as iv, prompting as pr, protocol as p, evidence
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.adapters.officeqa.transport import ChatTransport


TOKENIZER_WORKER = r'''
import json,socket,sys
def deny(*a,**k): raise RuntimeError('Offline tokenizer cannot download assets')
socket.socket.connect=deny
socket.getaddrinfo=deny
import tiktoken
enc=tiktoken.get_encoding(sys.argv[1])
print(json.dumps({'library':'tiktoken','version':tiktoken.__version__,'encoding':enc.name}),flush=True)
for line in sys.stdin:
    messages=json.loads(line)
    count=sum(len(enc.encode(m['content'],disallowed_special=())) for m in messages)
    print(json.dumps({'content_tokens':count}),flush=True)
'''


class TokenCounter:
    def __init__(self, python, encoding):
        self.process = None; self.metadata = None
        if python:
            self.process = subprocess.Popen([python, '-c', TOKENIZER_WORKER, encoding],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            line = self.process.stdout.readline()
            if not line:
                self.close()
                raise RuntimeError('Local tokenizer unavailable; no network download attempted')
            self.metadata = json.loads(line)

    def count(self, messages):
        if self.process is None:
            return None
        self.process.stdin.write(json.dumps(messages, ensure_ascii=False)+'\n'); self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('Local tokenizer worker failed')
        return json.loads(line)['content_tokens']

    def close(self):
        if self.process is not None:
            self.process.stdin.close()
            self.process.wait(timeout=30)
            self.process.stdout.close()


def synthetic_run(case, initial, ref, rounds, observation):
    """Synthetic structural fixture: no real answer, scoring, tool or model call."""
    task = p.public_task(case); messages = deepcopy(initial); attempts = []
    for n in range(1, rounds+1):
        tools = []
        assistant = {'role': 'assistant', 'content': '<answer>OFFLINE_SYNTHETIC</answer>'}
        if n < rounds:
            call = {'id': f'offline_{n}', 'type': 'function', 'function': {'name': 'read',
                    'arguments': json.dumps({'path': task['source_files'][0], 'start': 1, 'limit': 80})}}
            assistant = {'role': 'assistant', 'content': 'Synthetic structural fixture; not a model decision.',
                         'tool_calls': [call]}
            tools = [{'ref': f'{ref}:{n}_t1', 'call': deepcopy(call), 'observation': {
                'role': 'tool', 'tool_call_id': call['id'], 'name': 'read',
                'content': 'SYNTHETIC OBSERVATION FROM LOCAL DOCUMENT BYTES\n'+observation}}]
        attempts.append({'request_context': p.FORMAL_CONTEXT, 'request_messages': deepcopy(messages),
                         'assistant': assistant, 'tools': tools, 'ref': f'{ref}:{n}'})
        messages.append(deepcopy(assistant)); messages.extend(deepcopy(t['observation']) for t in tools)
    run = {'ref': ref, 'task_id': case.case_id, 'run_id': f'offline_measurement/{case.case_id}/{ref}/{rounds}',
           'initial': {'ref': ref+':0', 'task': task, 'declared_source_pages': p.source_pages(task),
                       'messages': deepcopy(initial)}, 'attempts': attempts,
           'outcome': {'ref': ref+':outcome', 'status': 'completed', 'termination': 'answer',
                       'answer': 'OFFLINE_SYNTHETIC', 'model_rounds': rounds, 'tool_calls': rounds-1,
                       'api_requests': rounds, 'score': {'em': 0.0, 'f1': 0.0}}}
    evidence.validate_run(run)
    return run


def payloads(cases, runtime, parent, rounds, background):
    candidate = parent + '\nSynthetic candidate for representation measurement only.\n'
    parents, runs, pairs = [], [], []
    for i, case in enumerate(cases, 1):
        initial, _ = runtime.prepare(case, parent); qinitial, _ = runtime.prepare(case, candidate)
        # Bounded byte-derived text; no tool execution, no reference answers.
        observation = (runtime.text_root / case.payload['source_files'][0]).read_text()[:4000]
        a = synthetic_run(case, initial, f'P{i}', rounds, observation)
        b = synthetic_run(case, qinitial, f'Q{i}', rounds, observation)
        parents.append(a); runs.extend([a, b])
        pairs.append({'parent': a['ref'], 'candidate': b['ref'], 'task_id': case.case_id,
                      'parent_result': evidence.pair_result(a), 'candidate_result': evidence.pair_result(b)})
    facts = {'parent': parent, 'runs': parents}
    groups = {'groups': [{'group_id': 'G1', 'members': [r['ref'] for r in parents],
              'decision_problem': 'Synthetic measurement grouping.',
              'shared_basis': ' '.join(r['ref']+':1' for r in parents), 'important_differences': []}]}
    plan = {'goal': 'Synthetic representation measurement.', 'updates': [{'id': 'U1',
            'text': 'Synthetic update for measuring the existing schema.',
            'basis': ['G1', *[r['ref']+':1' for r in parents]]}], 'checks': []}
    saved = {'facts': facts, 'grouping': groups,
             'diagnosis': {'decision': 'revise', 'reason': 'Synthetic fixture.', 'plan': plan}}
    diff = actual_diff(parent, candidate)
    replay_plan = {**plan, 'updates': [{k: u[k] for k in ('id', 'text')} for u in plan['updates']]}
    replay = {'parent': parent, 'diff': diff, 'plan': replay_plan, 'pairs': pairs, 'runs': runs,
              'memory': {'format': 'memory_knowledge_only_v1', 'entries': []}}
    # Deliberately scoped review fixture: first Parent full run + its Candidate outcome.
    targets = [{'target': {'entry_index': 0, 'knowledge_index': 0}, 'knowledge': {
        'text': 'Synthetic measurement Knowledge; no experimental claim.',
        'evidence': ['diff', 'P1', 'Q1:outcome']}}]
    execution_context = {'background': background, 'description': p.execution_context(background)}
    review = {'context': {'parent': parent, 'diff': diff, 'execution_context': execution_context,
                         'pairs': [{k: pairs[0][k] for k in ('parent', 'candidate', 'task_id')}]}, 'targets': targets,
              'source_records': {'diff': {'parent': parent, 'diff': diff, 'execution_context': execution_context},
                'P1': {'task_id': parents[0]['task_id'], 'run_id': parents[0]['run_id'],
                       'role': 'parent', 'record': parents[0]},
                'Q1:outcome': {'task_id': runs[1]['task_id'], 'run_id': runs[1]['run_id'],
                              'role': 'candidate', 'record': runs[1]['outcome']}}}
    repair = deepcopy(review)
    repair['targets'][0]['issues'] = [{'statement': 'no experimental claim',
                                      'reason': 'Synthetic review fixture.', 'evidence': ['Q1:outcome']}]
    return {'grouping': facts, 'diagnosis': evidence.diagnosis_input(saved),
            'preconditioner': evidence.preconditioner_model_input(saved),
            'editor': {'parent': parent, 'plan': plan}, 'replay': replay, 'verifier': review, 'repair': repair}


def sizes(messages, counter):
    return {'content_chars': sum(len(m['content']) for m in messages),
            'content_utf8_bytes': sum(len(m['content'].encode('utf-8')) for m in messages),
            'serialized_chars': len(iv.exact(messages)), 'content_tokens': counter.count(messages)}


def measure(module, value, background, counter):
    before = pr._messages(module, value, background, input_view=iv.LEGACY)
    after = pr._messages(module, value, background)
    assert iv.equal(iv.restore(json.loads(after[1]['content'])), value)
    old, new = sizes(before, counter), sizes(after, counter)
    return {'before': old, 'after': new, 'reduction_percent': {
        key: None if old[key] is None else round(100*(old[key]-new[key])/old[key], 3) for key in old},
        'roundtrip_equal': True, 'encoded': iv.HEADER in json.loads(after[1]['content'])}


def deny(*args, **kwargs):
    raise AssertionError('Offline input measurement forbids Actor, model clients and network')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--prepared-root', default=str(ROOT/'data/officeqa/prepared_v2'))
    parser.add_argument('--parsed-root', default=str(ROOT/'data/officeqa/raw/treasury_bulletins_parsed'))
    parser.add_argument('--tokenizer-python')
    parser.add_argument('--encoding', default='cl100k_base')
    args = parser.parse_args(argv)
    directory = Path(args.directory); directory.mkdir(parents=True, exist_ok=True)
    if (directory/'input_lengths.json').exists():
        raise ValueError('Refuse to overwrite an existing measurement')
    with ExitStack() as stack:
        for target in ('socket.socket.connect', 'socket.getaddrinfo', 'requests.Session.request',
                       'openai.OpenAI', 'openai.AzureOpenAI'):
            stack.enter_context(patch(target, deny))
        stack.enter_context(patch.object(Runtime, 'run', deny))
        counter = TokenCounter(args.tokenizer_python, args.encoding); stack.callback(counter.close)
        dataset = OptimizationDataset(args.prepared_root); runtime = Runtime(args.parsed_root)
        parent = (ROOT/'experiments/configs/v26_officeqa_initial_skill.md').read_text()
        transport = ChatTransport(model='OFFLINE_INPUT_MEASUREMENT', max_completion_tokens=1, offline_create=deny)
        adapter = OfficeQAEvidenceAdapter(dataset, runtime, transport)
        background = p.background(transport.metadata())
        single, contexts, scenarios = [], [], []
        with using_benchmark(adapter):
            for case in dataset.cases('train'):
                initial, _ = runtime.prepare(case, parent)
                contexts.append((len(iv.exact(initial)), case.case_id))
                values = payloads([case], runtime, parent, 1, background)
                single.append({'task_id': case.case_id, 'initial_chars': len(iv.exact(initial)),
                    'initial_sha256': hashlib.sha256(iv.exact(initial).encode()).hexdigest(),
                    'source_identity': adapter._source_identity(case),
                    **{module: measure(module, values[module], background, counter) for module in ('diagnosis', 'replay')}})
            descending = sorted(contexts, reverse=True)
            for batch, rounds in ((1, 2), (4, 2), (4, 8), (8, 8), (1, 24)):
                cases = [dataset.case(uid) for _, uid in descending[:batch]]
                values = payloads(cases, runtime, parent, rounds, background)
                scenarios.append({'tasks': [c.case_id for c in cases], 'batch': batch, 'rounds': rounds,
                    'selection': 'largest initial contexts; synthetic rounds, not experimental trajectories',
                    'modules': {module: measure(module, values[module], background, counter) for module in pr.PROMPT_VERSIONS}})
        totals = {}
        for module in ('diagnosis', 'replay'):
            totals[module] = {}
            for metric in ('content_chars', 'content_utf8_bytes', 'content_tokens'):
                before = [row[module]['before'][metric] for row in single]
                after = [row[module]['after'][metric] for row in single]
                totals[module][metric] = None if before[0] is None else {
                    'before_sum': sum(before), 'after_sum': sum(after),
                    'reduction_percent': round(100*(sum(before)-sum(after))/sum(before), 3)}
        lengths = [n for n, _ in contexts]
        report = {'schema': 'v26_officeqa_input_measurement_v1', 'input_view': iv.FORMAT,
            'tokenizer': counter.metadata, 'token_note': 'Counts encode each system/user content with the named local reference tokenizer; include decoder instructions. Exclude provider chat framing. Not actual production model usage or a token budget.',
            'real_task_initial_contexts': len(single), 'initial_chars': {'min': min(lengths),
                'median': statistics.median(lengths), 'max': max(lengths)},
            'synthetic_round_note': 'All assistant outputs, tool events and scores are synthetic. Observation strings use bounded local TXT slices; no tool/Actor execution or model-generated trajectories. Review fixtures select only first pair.',
            'real_model_calls': 0, 'real_case_rollouts': 0, 'experiments_started': 0,
            'formal_token_budget_selected': False, 'single_case_totals': totals,
            'single_cases': single, 'stress_scenarios': scenarios,
            'sources': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in (ROOT/'scripts/runs/verify_v26_input_view.py',
                                     Path(iv.__file__), Path(pr.__file__), pr.resource_path('lossless_input_view.md'))}}
        (directory/'input_lengths.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({'cases': len(single), 'tokenizer': counter.metadata, 'totals': totals}, indent=2))


if __name__ == '__main__':
    main()
