"""Offline replay of all 57 training records through the native summarizer and mock HTTP."""
from collections import Counter
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from scripts.runs.skilladam.alfworld.trajectory_feedback import run_alfworld_skilladam_v24_9_feedback as app
from src.skill_evolution.skilladam.alfworld.trajectory_feedback import backend as feedback
from scripts.runs.alfworld.alfworld_aligned_common import read, validate_trajectory
from skilladam.cost.ledger import UsageLedger
from skilladam.execution.contracts import BatchExecution, GenerationRequest
from skilladam.execution.evaluate import CaseEvaluation
from skilladam.methods.skilladam import _profile_gate, _gate_signature
from skilladam.methods.skilladam_prompts import load_benchmark_prompt_context
from src.skill_evolution.v24_1.benchmarks.alfworld.facts import build_facts


def verify(root):
    actor, cfg = app.prepare()
    bridge = app.bridge
    campaign = app.resolve_experiment_path(cfg['output_root'])
    context = feedback.official.context_for(bridge, actor, cfg)
    historical = {}
    for path in (campaign / 'model_calls').glob('trajectory_compression_*/http_request_01.json'):
        body = read(path)['body']
        iteration = read(path.parent / 'request.json')['iteration']
        historical[iteration, body['messages'][1]['content']] = body

    bodies = []
    def capture(request):
        assert str(request.url) == actor['call_config']['endpoint']
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={'model': actor['model'], 'choices': [
            {'index': 0, 'message': {'role': 'assistant', 'content': 'offline summary'}, 'finish_reason': 'stop'}]})

    backend = app.FeedbackBackend(actor, cfg, root, api_key='offline', http_transport=httpx.MockTransport(capture))
    adapter = bridge.ALFWorldAdapter(app.BASELINE / 'splits')
    runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=adapter, backend=backend,
                                  context=context, output_dir=root)
    runner._usage_ledger = UsageLedger(root / 'usage.jsonl')
    runner._prompt_context = load_benchmark_prompt_context('alfworld', trajectory_count=10,
        benchmark_domain_info_md='Training trajectories are supplied per iteration.', prompt_profile=cfg['native']['prompt_profile'])
    cases = {c.case_id: c for c in bridge.cases_for(cfg)}
    totals, checked = Counter(), set()
    checkpoint = read(campaign / 'checkpoint.json')
    gate = _profile_gate(adapter, 'alfworld', None, cfg['native']['gate_profile'])
    assert _gate_signature(gate, 'alfworld', None, cfg['native']['gate_profile']) == checkpoint['run_signature']['gate']
    assert runner.config.to_dict() == checkpoint['run_signature']['post_decision']['run_config']
    for iteration, entry in enumerate(checkpoint['iterations']):
        batch = campaign / 'shared_actor' / f'iter_{iteration:03d}' / 'training_rollout_0'
        ids = entry['training_case_ids']
        skill = (batch / 'actor_skill.md').read_text()
        archived = [json.loads(line) for line in (batch / 'results.jsonl').read_text().splitlines()]
        assert ids == [row['id'] for row in archived]
        requests = tuple(adapter.build_rollout_request(cases[uid], method='skilladam', split='train',
                                                       skill=skill, seed=context.seed) for uid in ids)
        backend.iteration = iteration
        with patch.object(bridge.backend, 'run_batch', return_value=archived):
            rows = backend.execute_batch(BatchExecution(requests, context, 'training_rollout'))
        for raw in rows:
            uid = raw.case_id
            path = app.resolve_experiment_path(raw.result['trajectory'])
            record = validate_trajectory(path, actor, backend.allowed[uid], skill)
            facts = build_facts([record])['facts']
            ref_run, = facts['runs']
            result = adapter.parse_result(cases[uid], raw.result)
            with patch.object(feedback, 'summary_input', wraps=feedback.summary_input) as project:
                summary = runner._condense(cases[uid], CaseEvaluation(uid, result, adapter.evaluate(result)), allow_llm=True)
            assert len(bodies) == 1 and summary.markdown == 'offline summary'
            body = bodies.pop()
            old = historical.pop((iteration, project.call_args.args[-1]))
            system, user = body['messages']
            assert {**body, 'messages': old['messages']} == old and system == old['messages'][0]
            query, data = user['content'].split('\n\n## Execution Trace\n\n', 1)
            data, native_suffix = data.rsplit('\n\n## Final Answer\n\n', 1)
            assert native_suffix == old['messages'][1]['content'].rsplit('\n\n## Final Answer\n\n', 1)[1]
            evidence = json.loads(data)
            menus = evidence['command_sets']
            assert query == '## Query\n\n' + ref_run['task'] and evidence['parent'] == facts['parent'] == skill
            assert evidence['initial'] == ref_run['initial'] and menus == facts['command_sets']
            assert evidence['environment_outcome'] == {**ref_run['outcome'], 'executed_steps': len(record['steps'])}
            for step, event, ref in zip(evidence['steps'], record['steps'], ref_run['steps'], strict=True):
                n = event['model_response']['api_attempts']
                attempt = event['transport_attempts'][n - 1]
                commands = menus[step['commands_ref']]
                # Compare the full rendered list, including order and delimiters, to the sent user turn.
                rendered = "\n ".join(f"'{cmd}'" for cmd in commands)
                suffix = 'Your admissible actions of the current situation are: [' + rendered + '].\n\nNow it'
                assert suffix in attempt['messages'][1]['content'] and commands == facts['command_sets'][ref['before']['commands_ref']]
                assert step == {'step': event['step'], 'commands_ref': ref['before']['commands_ref'],
                                'action': ref['action'], 'after_observation': ref['after']['observation'], 'feedback': ref['feedback']}
                totals.update(steps=1, retried_steps=int(n > 1), hidden_help_excluded=int(
                    'help' in event['admissible_commands'] and 'help' not in commands))
                if n > 1:
                    # Even if a retry menu were reordered, retain that request's order.
                    changed = dict(attempt, messages=list(attempt['messages']))
                    user_turn = changed['messages'][1]
                    changed['messages'][1] = dict(user_turn, content=user_turn['content'].replace(
                        suffix, suffix.replace(rendered, "\n ".join(f"'{cmd}'" for cmd in reversed(commands)))))
                    probe = dict(event, transport_attempts=[*event['transport_attempts'][:-1], changed])
                    template = record['protocol']['initial_template' if event['step'] == 1 else 'history_template']
                    assert feedback.accepted_menu(path, probe, template) == tuple(reversed(commands))
            assert uid not in checked
            checked.add(uid)
            totals.update(tasks=1, native_prompt_and_budget=1, native_final_answer_and_outcome=1)
    assert not historical and checked == set(cases)
    assert (totals['tasks'], totals['steps'], totals['retried_steps'], totals['hidden_help_excluded']) == (57, 1121, 13, 1121)
    for stage in ('iteration_patch', 'momentum_update'):
        for path in (campaign / 'model_calls').glob(stage + '_*/http_request_01.json'):
            body = read(path)['body']
            backend.iteration = read(path.parent / 'request.json')['iteration']
            metadata = {'tools': body['tools']} if 'tools' in body else {}
            backend.generate(GenerationRequest(stage, tuple(body['messages']), context, metadata))
            assert len(bodies) == 1 and bodies.pop() == body
            totals[stage] += 1
        assert totals[stage] == 6
    return totals


if __name__ == '__main__':
    with TemporaryDirectory() as tmp, patch.object(socket.socket, 'connect', side_effect=AssertionError('network')):
        print(json.dumps(verify(Path(tmp)), indent=2))
