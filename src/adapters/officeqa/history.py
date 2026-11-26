"""Validate durable wire history before resuming; never call tools or models."""
from copy import deepcopy
from .retry import assistant_message, format_repair, parse_turn, request_messages, FormatError


def validate_history(state, *, reasoning):
    def check(ok):
        if not ok: raise ValueError('Persisted OfficeQA request/history differs from saved responses')
    messages = deepcopy(state['initial']); calls = 0
    for n, rd in enumerate(state['rounds'], 1):
        check(rd['number'] == n and rd['phase'] in ('generation', 'tools', 'done'))
        check(n == len(state['rounds']) or rd['phase'] == 'done')
        repair = None; accepted = None; accepted_response = None
        for i, attempt in enumerate(rd['attempts'], 1):
            check(attempt['number'] == i and attempt['messages'] == request_messages(messages, repair))
            status = attempt['status']
            if status == 'format_error':
                try: parse_turn(attempt['response'], require_reasoning=reasoning)
                except FormatError as exc:
                    check(attempt['error'] == str(exc))
                    repair = format_repair(attempt['response'], exc, reasoning=reasoning)
                else: check(False)
            elif status == 'accepted':
                check(i == len(rd['attempts']))
                accepted_response = attempt['response']
                accepted = parse_turn(accepted_response, require_reasoning=reasoning); repair = None
            else:
                check(status in ('requesting', 'received', 'technical_error', 'interrupted', 'fatal'))
                if status in ('requesting', 'received', 'fatal'):
                    check(i == len(rd['attempts']) and rd['phase'] == 'generation')
        check(rd['repair'] == repair)
        if rd['phase'] == 'generation':
            check(not rd['tools'])
            continue  # Accepted response may be durable before message commit.
        check(accepted is not None and len(rd['tools']) == len(accepted.tool_calls))
        messages.append(assistant_message(accepted, accepted_response, reasoning=reasoning))
        pending = False
        for call, tool in zip(accepted.tool_calls, rd['tools']):
            if tool['status'] == 'done':
                check(not pending and isinstance(tool['observation'], str))
                messages.append({'role': 'tool', 'tool_call_id': call.call_id,
                                 'name': call.name, 'content': tool['observation']}); calls += 1
            else:
                check(tool['status'] in ('pending', 'started')); pending = True
        check(rd['phase'] != 'done' or not pending)
    check(state['messages'] == messages and state['calls'] == calls)
