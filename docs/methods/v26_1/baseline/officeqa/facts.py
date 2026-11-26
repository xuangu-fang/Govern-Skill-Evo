"""Audit completed public Actor records before constructing model-visible facts."""
from copy import deepcopy
from dataclasses import asdict
import json
import re

from skilladam.backends import openai_compatible as native
from skilladam.benchmarks.officeqa.rollout import extract_answer
from src.adapters.officeqa.retry import parse_turn, request_messages, FormatError, format_repair
from src.adapters.officeqa.retry import assistant_message as wire_assistant
from src.adapters.officeqa.transport import RequestFailure
from src.adapters.officeqa.data import PROFILE
from src.adapters.officeqa.execution import RETRY_POLICY, REQUEST_ATTEMPTS
from ...facts import require, text
from . import protocol as p


def assistant_message(turn):
    value = {'role': 'assistant', 'content': turn.text}
    if turn.tool_calls:
        value['content'] = turn.text or None
        value['tool_calls'] = [{'id': c.call_id, 'type': 'function',
                               'function': {'name': c.name, 'arguments': c.raw_arguments}}
                              for c in turn.tool_calls]
    return value


def validate_actor(actor):
    p.fields(actor, ('model', 'max_completion_tokens', 'temperature', 'reasoning_effort',
                    'reasoning_mode', 'token_limit_field', 'request_timeout_seconds',
                    'connect_timeout_seconds', 'retry_policy', 'request_attempts_total',
                    'transport', 'endpoint'), 'Actor metadata')
    text(actor['model'], 'model'); p.integer(actor['max_completion_tokens'], 'output limit', minimum=1)
    require(actor['retry_policy'] == RETRY_POLICY and actor['request_attempts_total'] == REQUEST_ATTEMPTS,
            'Actor retry profile differs')
    require(actor['request_timeout_seconds'] == 300 and actor['connect_timeout_seconds'] == 10,
            'Actor timeout profile differs')
    require(actor['transport'] in ('offline_fixture', 'direct_http'), 'Unsupported transport')
    return actor


def audit_record(record):
    """Reconstruct formal history and every temporary repair, without executing tools."""
    p.fields(record, ('profile', 'method', 'task_id', 'skill', 'actor', 'initial_messages',
                      'raw_result', 'answer', 'metrics', 'request_audit'), 'Completed Actor record')
    require(record['profile'] == PROFILE and record['method'] == 'govern', 'Wrong Actor owner/profile')
    text(record['task_id'], 'task ID')
    require(record['skill'] is None or isinstance(record['skill'], str), 'Invalid Skill')
    validate_actor(record['actor']); p.score_view(record['metrics'])
    reasoning = record['actor']['reasoning_mode'] == 'deepseek_thinking'
    messages = deepcopy(record['initial_messages'])
    wire_messages = deepcopy(messages)
    require(isinstance(messages, list) and len(messages) >= 2 and isinstance(messages[0], dict)
            and messages[0].get('role') == 'system',
            'Missing initial Actor messages')
    require(all(isinstance(m, dict) and set(m) == {'role', 'content'}
                and m['role'] in ('system', 'user') and isinstance(m['content'], str) for m in messages),
            'Invalid initial messages')
    rounds = record['request_audit']
    require(isinstance(rounds, list) and 1 <= len(rounds) <= 24, 'Invalid model round count')
    visible, usages, final_text, calls = [], [], None, 0
    for number, rd in enumerate(rounds, 1):
        p.fields(rd, ('number', 'phase', 'attempts', 'repair', 'tools'), 'Round audit')
        require(type(rd['number']) is int and rd['number'] == number and rd['phase'] == 'done', 'Incomplete/out-of-order round')
        attempts = rd['attempts']; repair = None; accepted = None
        require(isinstance(attempts, list) and 1 <= len(attempts) <= REQUEST_ATTEMPTS, 'Round request budget differs')
        for index, a in enumerate(attempts, 1):
            require(type(a.get('number')) is int and a['number'] == index, 'Out-of-order request attempt')
            require(p.equal(a.get('messages'), request_messages(wire_messages, repair)), 'Archived request or temporary feedback differs')
            status = a.get('status'); response = a.get('response')
            expected_usage = asdict(native.normalize_usage(None, requests=1))
            if isinstance(response, dict):
                try:
                    expected_usage = asdict(native.normalize_usage(response.get('usage'), requests=1))
                except ValueError:
                    pass
            require(p.equal(a.get('usage'), expected_usage), 'Request usage differs')
            usages.append(expected_usage)
            if status in ('accepted', 'format_error'):
                require('response' in a, 'Missing saved response')
                try:
                    turn = parse_turn(response, require_reasoning=reasoning)
                except FormatError as exc:
                    require(status == 'format_error' and a.get('error') == str(exc), 'Format failure classification differs')
                    repair = format_repair(response, exc, reasoning=reasoning)
                else:
                    require(status == 'accepted' and index == len(attempts), 'Accepted response is not the final attempt')
                    accepted = turn; repair = None
            elif status == 'technical_error':
                text(a.get('error'), 'technical error')
                if 'response' in a:
                    try:
                        parse_turn(response, require_reasoning=reasoning)
                    except RequestFailure as exc:
                        require(exc.retryable and a['error'] == str(exc), 'Technical classification differs')
                    else:
                        raise ValueError('Valid response classified as technical failure')
            elif status == 'interrupted':
                require('response' not in a, 'Interrupted request has a saved response')
            else:
                raise ValueError('Incomplete or fatal generation cannot become execution evidence')
        require(accepted is not None and rd['repair'] is None and repair is None, 'Round has no accepted response')
        require(final_text is None, 'Execution continued after final answer')
        tools = rd['tools']
        require(isinstance(tools, list) and len(tools) == len(accepted.tool_calls), 'Tool count differs')
        assistant = assistant_message(accepted)
        step = {'request_context': p.FORMAL_CONTEXT, 'request_messages': deepcopy(messages),
                'assistant': assistant, 'tools': []}
        messages.append(deepcopy(assistant))
        wire_messages.append(wire_assistant(accepted, attempts[-1]['response'], reasoning=reasoning))
        for call, saved in zip(accepted.tool_calls, tools):
            p.fields(saved, ('status', 'observation'), 'Committed tool')
            require(saved['status'] == 'done' and isinstance(saved['observation'], str), 'Tool outcome is not committed')
            observation = {'role': 'tool', 'tool_call_id': call.call_id, 'name': call.name, 'content': saved['observation']}
            step['tools'].append({'call': deepcopy(assistant['tool_calls'][len(step['tools'])]), 'observation': observation})
            messages.append(deepcopy(observation)); calls += 1
            wire_messages.append(deepcopy(observation))
        if not accepted.tool_calls:
            final_text = accepted.text
        visible.append(step)
    raw = record['raw_result']
    p.fields(raw, ('response', 'messages', 'usage_records', 'n_turns', 'n_tool_calls',
                   'api_requests', 'termination_reason', 'fail_reason'), 'Raw result')
    require(p.equal(raw['messages'], wire_messages) and p.equal(raw['usage_records'], usages), 'API transcript or usage audit differs')
    for key, count in (('n_turns', len(rounds)), ('n_tool_calls', calls), ('api_requests', len(usages))):
        require(type(raw[key]) is int and raw[key] == count, f'{key} differs')
    if final_text is None:
        require(len(rounds) == 24 and raw['termination_reason'] == 'max_tool_turns'
                and raw['response'] == '' and raw['fail_reason'] == 'Exceeded tool-turn budget (24)', 'Invalid round-limit termination')
    else:
        require(raw['termination_reason'] == 'answer' and raw['response'] == final_text and raw['fail_reason'] == '', 'Final response differs')
    answer, _ = extract_answer(raw)
    require(record['answer'] == answer, 'Extracted answer differs')
    if final_text is None:
        require(record['metrics']['em'] == record['metrics']['f1'] == 0, 'Budget termination must have zero scores')
    return visible


def validate_envelope(record):
    p.fields(record, ('schema', 'run_id', 'task_id', 'task', 'provenance', 'execution'), 'V26 execution')
    require(record['schema'] == p.RECORD_VERSION, 'Unknown V26 execution schema')
    text(record['run_id'], 'run ID'); p.validate_task(record['task'])
    require(record['task_id'] == record['task']['id'] == record['execution']['task_id'], 'Task identity differs')
    provenance = record['provenance']
    p.fields(provenance, ('batch_id', 'role', 'source_assets', 'task_context_sha256', 'record_sha256'), 'Provenance')
    require(provenance['role'] in ('parent', 'candidate', 'evaluation'), 'Invalid execution role')
    text(provenance['batch_id'], 'batch ID')
    require(record['run_id'] == provenance['batch_id'] + ':' + p.digest(record['task_id']), 'Run identity differs')
    require(provenance['record_sha256'] == p.digest(record['execution']), 'Actor record checksum differs')
    require(re.fullmatch(r'[0-9a-f]{64}', provenance['task_context_sha256']) is not None, 'Invalid input fingerprint')
    assets = provenance['source_assets']
    require(isinstance(assets, dict) and set(assets) == set(record['task']['source_files']), 'Source assets differ')
    for hashes in assets.values():
        p.fields(hashes, ('text_sha256', 'parsed_json_sha256'), 'Source hashes')
        require(all(isinstance(h, str) and re.fullmatch(r'[0-9a-f]{64}', h) for h in hashes.values()), 'Invalid source fingerprint')
    if provenance['role'] == 'evaluation':
        require(record['task']['split'] == 'test', 'Evaluation requires Test')
    else:
        require(record['task']['split'] != 'test', 'Test execution cannot enter optimization')
    return audit_record(record['execution'])


def parent_text(record):
    return record['execution']['skill']


def build_facts(records, *, role=None):
    require(isinstance(records, list) and records, 'Missing completed executions')
    first = records[0]; skill = parent_text(first); actor = first['execution']['actor']
    role = role or first['provenance']['role']
    require(role in ('parent', 'candidate'), 'Evaluation records cannot become optimization facts')
    runs, sources, tasks, identities = [], [], set(), set()
    for i, record in enumerate(records, 1):
        visible = validate_envelope(record)
        require(record['provenance']['role'] == role and p.equal(record['execution']['actor'], actor)
                and parent_text(record) == skill, 'Mixed execution conditions/roles/Skills')
        require(record['run_id'] not in identities and record['task_id'] not in tasks, 'Duplicate run/task')
        identities.add(record['run_id']); tasks.add(record['task_id']); ref = f'P{i}'
        for n, step in enumerate(visible, 1):
            step['ref'] = f'{ref}:{n}'
            for j, tool in enumerate(step['tools'], 1):
                tool['ref'] = f'{ref}:{n}_t{j}'
        raw = record['execution']['raw_result']
        outcome = {'ref': ref + ':outcome', 'status': 'completed', 'termination': raw['termination_reason'],
                   'answer': record['execution']['answer'], 'model_rounds': raw['n_turns'],
                   'tool_calls': raw['n_tool_calls'], 'api_requests': raw['api_requests'],
                   'score': p.score_view(record['execution']['metrics'])}
        run = {'ref': ref, 'task_id': record['task_id'], 'run_id': record['run_id'],
               'initial': {'ref': ref + ':0', 'task': deepcopy(record['task']),
                           'declared_source_pages': p.source_pages(record['task']),
                           'messages': deepcopy(record['execution']['initial_messages'])},
               'attempts': visible, 'outcome': outcome}
        runs.append(run); sources.append({k: run[k] for k in ('ref', 'task_id', 'run_id')})
    return {'facts': {'parent': skill, 'runs': runs}, 'background': p.background(actor), 'sources': sources}


def cost_summary(records):
    """Count all reserved HTTP attempts, including failed/unknown requests, once."""
    ids = set(); usages = []; rounds = calls = 0
    for record in records:
        validate_envelope(record)
        require(record['run_id'] not in ids, 'Duplicate execution in cost report'); ids.add(record['run_id'])
        raw = record['execution']['raw_result']; rounds += raw['n_turns']; calls += raw['n_tool_calls']
        usages.extend(raw['usage_records'])
    result = {'model_rounds': rounds, 'tool_calls': calls, 'http_attempts': len(usages)}
    for key in ('input_tokens', 'output_tokens', 'total_tokens'):
        known = [u[key] for u in usages if u.get(key) is not None]
        result[key] = {'known_sum': sum(known), 'unknown_requests': len(usages) - len(known)}
    return result
