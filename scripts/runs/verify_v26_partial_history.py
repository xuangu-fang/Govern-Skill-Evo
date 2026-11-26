#!/usr/bin/env python3
"""Offline local-citation size comparison against the frozen v1 implementation."""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.runs.verify_v26_input_view import (
    Runtime, OptimizationDataset, ChatTransport, OfficeQAEvidenceAdapter, using_benchmark,
    TokenCounter, payloads, sizes, deny, iv, pr, p)


def partial_views(values, *, dense=False, historical=False, singleton=False):
    """Select only provided round/tool citations; never import a full run."""
    review = deepcopy(values['verifier']); sources = {}; refs = []
    for run in values['replay']['runs']:
        selected = run['attempts'] if dense else run['attempts'][1::2]
        if singleton:
            selected = run['attempts'][-1:]
        for attempt in selected:
            records = [attempt]
            if dense:
                records += [{**tool, 'request_context': attempt['request_context'],
                             'request_messages': attempt['request_messages']} for tool in attempt['tools']]
            for record in records:
                ref = ('history_01/' if historical else '') + record['ref']
                refs.append(ref)
                source = {'task_id': run['task_id'], 'run_id': run['run_id'],
                          'role': 'parent' if run['ref'].startswith('P') else 'candidate', 'record': deepcopy(record)}
                if historical:
                    source['execution_context'] = deepcopy(review['context']['execution_context'])
                sources[ref] = source
        if singleton:
            break
    review['source_records'] = sources
    review['context']['pairs'] = [] if historical else [
        {k: pair[k] for k in ('parent', 'candidate', 'task_id')} for pair in values['replay']['pairs']]
    review['targets'][0]['knowledge']['evidence'] = refs
    repair = deepcopy(review)
    repair['targets'][0]['issues'] = [{'statement': 'Synthetic measurement',
        'reason': 'Structural fixture only.', 'evidence': refs[:1]}]
    # Actual Repair projection sorts source keys; exercise that ordering too.
    repair['source_records'] = {ref: sources[ref] for ref in sorted(sources)}
    return {'verifier': review, 'repair': repair}


def previous_encoder(snapshot):
    name = 'src/skill_evolution/v26/benchmarks/officeqa/input_view.py'
    with tarfile.open(snapshot) as archive:
        source = archive.extractfile(name).read()
        instruction = archive.extractfile(
            'src/skill_evolution/v26/benchmarks/officeqa/prompts/lossless_input_view.md').read().decode()
    module = types.ModuleType('src.skill_evolution.v26.benchmarks.officeqa._previous_input_view')
    module.__package__ = 'src.skill_evolution.v26.benchmarks.officeqa'
    exec(compile(source, name, 'exec'), module.__dict__)
    assert module.FORMAT == iv.PREVIOUS
    return module, instruction, hashlib.sha256(source).hexdigest()


def compare(module, value, background, counter, previous, instruction):
    raw = pr._messages(module, value, background, input_view=iv.LEGACY)
    before = previous.model_messages(raw, instruction)
    # Independent frozen code establishes that 'before' really is the prior implementation.
    assert before == pr._messages(module, value, background, input_view=iv.PREVIOUS)
    after = pr._messages(module, value, background)
    decoded = json.loads(after[1]['content'])
    assert iv.equal(iv.restore(decoded), value)
    old, new = sizes(before, counter), sizes(after, counter)
    assert new['serialized_chars'] <= old['serialized_chars']
    assert new['content_utf8_bytes'] <= old['content_utf8_bytes']
    return {'raw': sizes(raw, counter), 'before_v1': old, 'after_v2_policy': new,
        'reduction_percent': {k: None if old[k] is None else round(100*(old[k]-new[k])/old[k], 3) for k in old},
        'roundtrip_equal': True, 'partial_prefixes': iv.has_history_pointers(decoded),
        'citation_count': len(value['source_records'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--snapshot', default=str(ROOT/'artifacts/methods/v26/input_view_20261029_001/source_snapshot.tar.gz'))
    parser.add_argument('--prepared-root', default=str(ROOT/'data/officeqa/prepared_v2'))
    parser.add_argument('--parsed-root', default=str(ROOT/'data/officeqa/raw/treasury_bulletins_parsed'))
    parser.add_argument('--tokenizer-python')
    parser.add_argument('--encoding', default='cl100k_base')
    args = parser.parse_args(argv)
    output = Path(args.directory)/'input_lengths.json'
    if output.exists(): raise ValueError('Refuse to overwrite previous measurement')
    output.parent.mkdir(parents=True, exist_ok=True)
    previous, instruction, previous_sha = previous_encoder(args.snapshot)
    with ExitStack() as stack:
        for target in ('socket.socket.connect', 'socket.getaddrinfo', 'requests.Session.request',
                       'openai.OpenAI', 'openai.AzureOpenAI'):
            stack.enter_context(patch(target, deny))
        stack.enter_context(patch.object(Runtime, 'run', deny))
        counter = TokenCounter(args.tokenizer_python, args.encoding); stack.callback(counter.close)
        dataset = OptimizationDataset(args.prepared_root); runtime = Runtime(args.parsed_root)
        parent = (ROOT/'experiments/configs/v26_officeqa_initial_skill.md').read_text()
        actor = ChatTransport(model='OFFLINE_INPUT_MEASUREMENT', max_completion_tokens=1, offline_create=deny)
        adapter = OfficeQAEvidenceAdapter(dataset, runtime, actor); background = p.background(actor.metadata())
        single = []; contexts = []; scenarios = []
        with using_benchmark(adapter):
            for case in dataset.cases('train'):
                initial, _ = runtime.prepare(case, parent)
                contexts.append((len(iv.exact(initial)), case.case_id))
                views = partial_views(payloads([case], runtime, parent, 8, background))
                single.append({'task_id': case.case_id, 'source_identity': adapter._source_identity(case),
                    'initial_sha256': hashlib.sha256(iv.exact(initial).encode()).hexdigest(),
                    'modules': {k: compare(k, v, background, counter, previous, instruction) for k, v in views.items()}})
            ordered = sorted(contexts, reverse=True)
            for batch, rounds, dense, historical, singleton in (
                    (1, 8, False, False, True), (1, 8, False, False, False),
                    (4, 8, True, False, False), (1, 24, True, False, False),
                    (1, 8, True, True, False)):
                cases = [dataset.case(uid) for _, uid in ordered[:batch]]
                views = partial_views(payloads(cases, runtime, parent, rounds, background),
                                      dense=dense, historical=historical, singleton=singleton)
                scenarios.append({'batch': batch, 'rounds': rounds, 'dense': dense, 'historical': historical,
                    'singleton': singleton, 'tasks': [c.case_id for c in cases],
                    'modules': {k: compare(k, v, background, counter, previous, instruction) for k, v in views.items()}})
        totals = {}
        for module in ('verifier', 'repair'):
            totals[module] = {}
            for metric in ('content_chars', 'content_utf8_bytes', 'content_tokens'):
                old = [r['modules'][module]['before_v1'][metric] for r in single]
                new = [r['modules'][module]['after_v2_policy'][metric] for r in single]
                totals[module][metric] = None if old[0] is None else {'before': sum(old), 'after': sum(new),
                    'reduction_percent': round(100*(sum(old)-sum(new))/sum(old), 3)}
        report = {'input_view': iv.FORMAT, 'previous_view': iv.PREVIOUS,
            'previous_codec_sha256': previous_sha, 'snapshot_sha256': hashlib.sha256(Path(args.snapshot).read_bytes()).hexdigest(),
            'tokenizer': counter.metadata, 'real_initial_contexts': len(single),
            'measurement_note': 'Real task initial pages/local TXT slices; all turns, tool events, results and reviews synthetic. No Actor execution. Single-case fixtures: both sides, 8 rounds, rounds 2/4/6/8 cited. Stress selects largest initial contexts. No nonempty growing Memory. Not a production upper bound.',
            'token_note': 'System/user content only, including all decoding instructions; excludes provider chat framing; not production usage or a budget.',
            'real_model_calls': 0, 'experiments_started': 0, 'real_case_rollouts': 0, 'formal_token_budget_selected': False,
            'single_case_totals': totals, 'single_cases': single, 'stress_scenarios': scenarios,
            'sources': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (Path(__file__), ROOT/'scripts/runs/verify_v26_input_view.py', Path(iv.__file__), Path(pr.__file__),
                             pr.resource_path('lossless_input_view.md'), pr.resource_path('partial_history_view.md'))}}
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({'cases': len(single), 'totals': totals}, indent=2))


if __name__ == '__main__':
    main()
