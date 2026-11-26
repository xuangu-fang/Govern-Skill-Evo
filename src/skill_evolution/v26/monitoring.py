"""Read-only Campaign progress and request accounting, including incomplete work."""
from dataclasses import asdict
from pathlib import Path
from skilladam.backends.openai_compatible import normalize_usage

from .stages import read
from .benchmarks.officeqa.prompting import PROMPT_VERSIONS


def cost_summary(campaign):
    root = Path(campaign); actor_usage = []; method_usage = []
    rounds_allocated = rounds_accepted = tools_done = tools_started = incomplete = 0
    for path in sorted((root / 'rounds').glob('R*/**/actor_state.json')):
        state = read(path)
        incomplete += state.get('status') != 'completed'
        for rd in state['rounds']:
            rounds_allocated += 1
            rounds_accepted += any(a['status'] == 'accepted' for a in rd['attempts'])
            tools_done += sum(t['status'] == 'done' for t in rd['tools'])
            tools_started += sum(t['status'] == 'started' for t in rd['tools'])
            actor_usage.extend(a.get('usage') or {} for a in rd['attempts'])
    method_slots = 0
    for rd in sorted((root / 'rounds').glob('R*')):
        for name in PROMPT_VERSIONS:
            for path in sorted((rd / name / 'attempts').glob('[0-9][0-9][0-9]')):
                if not path.is_dir(): continue
                method_slots += 1
                if not (path / 'request_started.json').exists(): continue
                raw = None
                if (path / 'response.json').exists():
                    response = read(path / 'response.json')
                    if isinstance(response, dict): raw = response.get('usage')
                elif (path / 'http_response.txt').exists():
                    try:
                        response = read(path / 'http_response.txt')
                        if isinstance(response, dict): raw = response.get('usage')
                    except (ValueError, OSError): pass
                try: usage = asdict(normalize_usage(raw, requests=1))
                except (ValueError, TypeError): usage = {}
                method_usage.append(usage)
    usages = actor_usage + method_usage
    result = {'actor_http_requests': len(actor_usage), 'module_http_requests': len(method_usage),
              'module_request_slots': method_slots, 'model_rounds_allocated': rounds_allocated,
              'model_rounds_accepted': rounds_accepted, 'tool_calls_committed': tools_done,
              'tool_calls_outcome_unknown': tools_started, 'incomplete_actor_cases': incomplete}
    for field in ('input_tokens', 'output_tokens', 'total_tokens', 'reasoning_tokens'):
        known = [u[field] for u in usages if type(u.get(field)) is int and u[field] >= 0]
        result[field] = {'known_sum': sum(known), 'unknown_requests': len(usages)-len(known)}
    return result


def status(campaign):
    """Diagnostic snapshot, not a substitute for the Campaign integrity audit."""
    root = Path(campaign); state = read(root / 'state.json'); rounds = {}
    for rd in sorted((root / 'rounds').glob('R*')):
        rounds[rd.name] = {'progress': read(rd / 'progress.json') if (rd / 'progress.json').exists() else None,
                          'result': read(rd / 'result.json') if (rd / 'result.json').exists() else None,
                          'attempts': {name: len(list((rd / name / 'attempts').glob('[0-9][0-9][0-9]')))
                                       for name in PROMPT_VERSIONS}}
    stop = read(root / 'stop.json') if (root / 'stop.json').exists() else None
    return {'state': state, 'rounds': rounds, 'cost': cost_summary(root), 'last_stop': stop,
            'currently_stopped': bool(stop and state['next_round'] <= stop['round']),
            'integrity_verified': False}
