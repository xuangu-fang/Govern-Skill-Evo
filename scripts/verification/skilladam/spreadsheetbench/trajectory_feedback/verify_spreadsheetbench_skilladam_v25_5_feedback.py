"""Check actual SDK request bodies against archived SpreadsheetBench training executions, offline."""
from collections import Counter
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.spreadsheetbench.layout import ALIGNED_RECORD
from scripts.runs.skilladam.spreadsheetbench.trajectory_feedback import run_spreadsheetbench_skilladam_v25_5_feedback as app
from skilladam.cost.ledger import UsageLedger
from skilladam.execution.evaluate import CaseEvaluation
from skilladam.methods.skilladam_prompts import load_benchmark_prompt_context


def verify(root):
    bridge = app.bridge
    saved = ALIGNED_RECORD / 'campaign'
    shared, cfg = app.prepare()
    cases = {case.case_id: case for case in bridge.cases_for(shared, cfg)}
    # Put a mock at the HTTP boundary. All earlier stages, including the SDK,
    # native summarizer prompt selection and the response parser, are real.
    bodies = []
    def capture(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={'model': shared['actor_model'], 'choices': [
            {'index': 0, 'message': {'role': 'assistant', 'content': 'offline summary'}, 'finish_reason': 'stop'}]})

    transport = app.native.native_transport(bridge, shared, cfg, root, api_key='offline',
                                            http_transport=httpx.MockTransport(capture))
    (root / 'shared_actor').symlink_to(saved / 'shared_actor', target_is_directory=True)
    with patch.object(app.native, 'native_transport', return_value=transport):
        backend = app.cached_native(app.native, bridge, shared, cfg, root, 'offline')
    context = bridge.context_for(shared, cfg)
    adapter = bridge.AlignedAdapter(app.BASELINE)
    runner = app.FeedbackRunner(config=bridge.native_config(cfg), adapter=adapter, backend=backend,
                                context=context, output_dir=root)
    runner._usage_ledger = UsageLedger(root / 'usage.jsonl')
    runner._prompt_context = load_benchmark_prompt_context('spreadsheetbench', trajectory_count=15,
        benchmark_domain_info_md='Training trajectories are supplied per iteration.',
        prompt_profile=cfg['native']['prompt_profile'])
    historical = {bridge.digest(body['messages']): body for p in saved.glob('model_calls/*/http_request_01.json')
                  for body in [bridge.read(p)['body']]}
    totals = Counter()
    checked = set()
    for iteration, ids in enumerate(shared['batches']):
        batch = saved / 'shared_actor' / f'iter_{iteration:03d}' / 'training_rollout_0'
        signature = bridge.read(batch / 'batch.json')
        assert signature['case_ids'] == ids
        backend.iteration = iteration
        backend.patch_context = SimpleNamespace(iteration=iteration, training_case_ids=ids,
                                                current_skill=signature['skill'])
        backend.rollout_counts[iteration, 'training_rollout'] = 1
        for index, uid in enumerate(ids):
            record = bridge.read(batch / uid.replace(':', '_') / 'trajectory.json')
            backend.queries[uid] = record['initial_messages'][-1]['content']
            case = cases[uid]
            result = adapter.parse_result(case, bridge.convert_record(record))
            evaluated = CaseEvaluation(uid, result, adapter.evaluate(result))
            summary = runner._condense(case, evaluated, allow_llm=True)
            assert summary.markdown == 'offline summary' and len(bodies) == 1
            body = bodies.pop()
            logical = saved / 'logical_calls' / f'{iteration:03d}_trajectory_compression_{index:03d}' / 'request.json'
            original = bridge.read(logical)
            assert original['metadata']['case_id'] == uid
            old_body = historical[bridge.digest(original['messages'])]
            assert bridge.read(root / logical.relative_to(saved))['messages'] == body['messages']
            system, user = body['messages']
            assert {**body, 'messages': old_body['messages']} == old_body
            assert system == old_body['messages'][0] and user['role'] == 'user'
            trace, outcome = user['content'].split('\n\n## Post-submission outcome (not visible to the Actor)\n\n')
            outcome, judgment = outcome.rsplit('\n\n## Outcome\n', 1)
            assert judgment == original['messages'][-1]['content'].rsplit('\n\n## Outcome\n', 1)[1]
            run = json.loads(trace.split('\n\n')[-1])
            run['outcome'] = json.loads(outcome)
            restored, = app.timeline.restore({'runs': [run]})['runs']
            assert restored == bridge.facts.build_facts([record])['facts']['runs'][0]
            assert restored['initial']['messages'] == record['initial_messages']
            score = dict(record['score'])
            for field, limit in [('mismatched_cells', 'score_coordinate_limit'),
                                 ('missing_sheets', 'score_missing_sheet_limit')]:
                score[field] = score[field][:shared['actor_profile'][limit]]
            assert restored['outcome']['score'] == score
            actual = [step for step in record['attempts'] if step['executed']]
            assert len(actual) == len(restored['attempts'])
            for source, step in zip(actual, restored['attempts']):
                assert all(source[key] == step[key] for key in
                           ('response', 'executed_code', 'code_attempt', 'finish_reason', 'feedback_to_actor'))
                assert step['execution'] == {k: v for k, v in source['execution'].items() if k != 'output_path'}
            assert uid not in checked
            checked.add(uid)
            totals.update(tasks=1, executions=len(actual), system_prompts=1, scores=1)
    assert checked == set(cases) and totals['executions'] == 123
    return totals


if __name__ == '__main__':
    with TemporaryDirectory() as tmp, patch.object(socket.socket, 'connect', side_effect=AssertionError('network')):
        print(json.dumps(verify(Path(tmp)), indent=2))
