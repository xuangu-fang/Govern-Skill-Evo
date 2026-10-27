"""Offline paired results, descriptive efficiency counts and mechanism evidence."""
from collections import Counter
import csv
import json
import re
from pathlib import Path
from unittest.mock import patch

from src.adapters.alfworld.verify_skill_run import verify_record, compare_records
from src.adapters.alfworld import verify_skill_run as legacy_audit
from src.adapters.alfworld.response_archive import verify_response_archive
from . import run as study

TARGETS = dict(zip([f'val:{n:04}' for n in range(11, 18)],
                   ['plate', 'tomato', 'apple', 'tomato', 'tomato', 'book', 'creditcard']))


def save_result(path, value):
    if path.exists():
        previous = study.read(path)
        if 'at' in value:
            value['at'] = previous['at']
        assert previous == value, f'Derived result changed: {path}'
    else:
        study.save(path, value)


def audit_record(record, path):
    """Retain all legacy checks; audit strict-response retries from raw evidence.

    The runner already retries incomplete HTTP 200 responses. The older auditor
    only recognizes HTTP failure codes. Authorize that one check only after every
    preceding request at the affected step has been independently checked here.
    Never change a response, status, hash, or production source to pass the audit.
    """
    path = study.resolve(path)
    allowed, extensions = set(), []
    for step in record['steps']:
        for attempt in step.get('transport_attempts', [])[:-1]:
            verify_response_archive(path, attempt)
            code = attempt.get('http_status')
            if code in {429, 500, 502, 503, 504}:
                continue
            assert record['request_policy']['strict_response']
            if code is None:
                assert attempt.get('error_type') in {'Timeout', 'ConnectTimeout', 'ReadTimeout', 'ConnectionError', 'ChunkedEncodingError'}
                reason = attempt['error_type']
            else:
                assert 200 <= code < 300
                try:
                    raw = json.loads((path.parent / attempt['raw_response']['path']).read_bytes())
                    choice = raw['choices'][0]; content = choice['message'].get('content') or ''
                    assert not isinstance(content, str) or not content.strip() or choice.get('finish_reason') != 'stop', 'Completed valid response was resampled'
                    reason = {'finish_reason': choice.get('finish_reason'), 'content_empty': not content}
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    reason = type(exc).__name__
            allowed.add(f"Unexpected transport retry at step {step['step']}.")
            extensions.append({'step': step['step'], 'attempt': attempt['attempt'], 'http_status': code, 'cause': reason})
    require = legacy_audit.require
    def compatible_require(condition, message):
        if not condition and message in allowed:
            return
        require(condition, message)
    with patch.object(legacy_audit, 'require', compatible_require):
        result = verify_record(record)
    if extensions:
        result['strict_response_retry_compatibility'] = extensions
    return result


def metrics(record):
    target = TARGETS[record['task']['id']]
    steps = [s for s in record['steps'] if s['phase'] == 'executed']
    take = re.compile(rf'^take {target} \d+ from ')
    acquire = next((s['step'] for s in steps if take.match(s['action']) and
                    s['observation'].startswith('You pick up ')), None)
    prefix = [s for s in steps if acquire is None or s['step'] < acquire]
    nav = [s for s in prefix if s['action'].startswith('go to ')]
    seen, revisit_steps = set(), []
    for s in nav:
        if s['action'] in seen:
            revisit_steps.append(s['step'])
        seen.add(s['action'])
    before = record['initial_observation']
    signatures, repeats, compact, opportunities, conditioning = set(), [], [], [], []
    verb = 'cool' if record['task']['id'] in {'val:0011', 'val:0012'} else 'heat'
    temperature = record['task']['id'] in {f'val:{n:04}' for n in range(11, 16)}
    command = re.compile(rf'^{verb} {target} \d+ with (?:fridge|microwave) \d+$')
    for s in steps:
        signature = (before, tuple(s['admissible_commands']), s['action'])
        if (acquire is None or s['step'] < acquire) and signature in signatures:
            repeats.append(s['step'])
        signatures.add(signature)
        available = [a for a in s['admissible_commands'] if temperature and command.match(a)]
        if available:
            opportunities.append({'step': s['step'], 'available': available, 'chosen': s['action'],
                                  'before': before, 'after': s['observation']})
        if temperature and command.match(s['action']) and s['action_in_admissible_commands']:
            conditioning.append(s['step'])
        compact.append({'step': s['step'], 'before': before, 'action': s['action'],
                        'after': s['observation'], 'admissible': s['action_in_admissible_commands'],
                        'temperature_actions_available': available, 'won': s['won']})
        before = s['observation']
    no_effect = [s['step'] for s in steps if s['observation'].strip().lower().startswith('nothing happens')]
    inadmissible = [s['step'] for s in steps if not s['action_in_admissible_commands']]
    first_opportunity = opportunities[0]['step'] if opportunities else None
    first_conditioning = conditioning[0] if conditioning else None
    interval = [s for s in steps if first_opportunity is not None and s['step'] >= first_opportunity
                and (first_conditioning is None or s['step'] < first_conditioning)]
    return {'task': record['task']['id'], 'goal': record['goal'], 'status': record['status'],
            'won': record['won'], 'steps': len(steps), 'first_target_acquisition_step': acquire,
            'inadmissible_steps': inadmissible, 'no_effect_steps': no_effect,
            'invalid_or_no_effect_steps': sorted(set(inadmissible + no_effect)),
            'fallback_steps': [s['step'] for s in steps if s['fallback']],
            'search_navigation_count': len(nav), 'unique_search_destinations': len(seen),
            'search_revisit_steps': revisit_steps, 'repeated_visible_state_action_steps': repeats,
            'temperature_applicable': temperature,
            'first_temperature_opportunity_step': first_opportunity,
            'first_temperature_action_step': first_conditioning,
            'temperature_delay_steps': first_conditioning-first_opportunity if first_conditioning is not None and first_opportunity is not None else None,
            'actions_before_temperature_after_available': [{'step': s['step'], 'action': s['action']} for s in interval],
            'temperature_opportunities': opportunities, 'temperature_action_steps': conditioning,
            'compact_trace': compact}


def main():
    cfg = study.verify()
    assert (study.HERE / 'completion.json').exists(), 'Live jobs not finished'
    plan = study.read(study.HERE / 'config/plan.json')
    usage, audits, records, results, all_attempts = Counter(), {}, {}, {}, []
    unknown, http_count, task_restarts = 0, 0, 0
    for arm in plan['arms']:
        for task in plan['tasks']:
            root = study.HERE / 'runs' / arm / task.replace(':', '_')
            attempts = list(study.archive_glob(root, 'attempt_*'))
            task_restarts += max(0, len(attempts)-1)
            assert len(attempts) <= 4
            for folder in attempts:
                meta = study.read(folder / 'attempt.json')
                all_attempts.append(meta)
                for path in study.archive_glob(folder, 'trajectory.json', recursive=True):
                    record = study.read(path)
                    assert record['model'] == cfg['actor_model']
                    assert record['request_policy'] == {'max_attempts': 3, 'strict_response': True}
                    for s in record['steps']:
                        assert len(s.get('transport_attempts', [])) <= 3
                        for a in s.get('transport_attempts', []):
                            verify_response_archive(path, a)
                            http_count += 1
                            u = a.get('usage')
                            if u is None:
                                unknown += 1
                            else:
                                usage.update({k: u.get(k, 0) for k in ['prompt_tokens','completion_tokens','total_tokens']})
            if not (root / 'selected.json').exists():
                results[(arm, task)] = {'status': 'technical_failure', 'won': False, 'steps': None}
                continue
            selected = study.read(root / 'selected.json')
            assert selected['attempt'] == next(a['attempt'] for a in [study.read(p/'attempt.json') for p in attempts] if a['complete'])
            path = study.resolve(selected['trajectory']); record = study.read(path)
            assert record['skill']['text'] == (study.HERE / f'config/{arm}.md').read_text()
            assert record['task'] == cfg['task_items'][task]
            audit = audit_record(record, path)
            assert audit['episode_complete']
            key = f'{arm}/{task}'
            audits[key] = audit
            records[(arm, task)] = record
            results[(arm, task)] = metrics(record)
            output = study.HERE / f'results/{arm}/{task.replace(":", "_")}.json'
            value = {'trajectory': selected['trajectory'], 'audit': audit, **results[(arm, task)]}
            if output.exists():
                assert study.read(output) == value
            else:
                study.save(output, value)
    pairs, pair_checks = [], {}
    for task in plan['tasks']:
        p, c = results[('parent', task)], results[('candidate', task)]
        if ('parent', task) in records and ('candidate', task) in records:
            verified = {records[(arm, task)]['run_id']: audits[f'{arm}/{task}'] for arm in plan['arms']}
            with patch.object(legacy_audit, 'verify_record', lambda r: verified[r['run_id']]):
                pair_checks[task] = compare_records(records[('parent', task)], records[('candidate', task)])
        state = ('technical_incomplete' if p['steps'] is None or c['steps'] is None else
                 'both_success' if p['won'] and c['won'] else
                 'repaired' if c['won'] else 'regressed' if p['won'] else 'both_failure')
        row = {'task': task, 'paired_outcome': state}
        for arm, m in [('parent', p), ('candidate', c)]:
            for name in ['status', 'won', 'steps', 'first_target_acquisition_step', 'first_temperature_opportunity_step', 'first_temperature_action_step', 'temperature_delay_steps']:
                row[f'{arm}_{name}'] = m.get(name)
            for name in ['invalid_or_no_effect_steps', 'search_revisit_steps', 'repeated_visible_state_action_steps']:
                row[f'{arm}_{name}_count'] = len(m[name]) if name in m else None
        pairs.append(row)
    totals = {}
    for arm in plan['arms']:
        ms = [results[(arm, task)] for task in plan['tasks']]
        totals[arm] = {'successes': sum(m['won'] for m in ms), 'denominator': 7,
                      'complete_tasks': sum(m['steps'] is not None for m in ms),
                      'total_selected_steps': sum(m['steps'] or 0 for m in ms),
                      'joint_success_steps': sum(row[f'{arm}_steps'] for row in pairs if row['paired_outcome']=='both_success'),
                      'joint_success_tasks': sum(row['paired_outcome']=='both_success' for row in pairs),
                      'invalid_or_no_effect_count': sum(len(m.get('invalid_or_no_effect_steps', [])) for m in ms),
                      'search_revisit_count': sum(len(m.get('search_revisit_steps', [])) for m in ms)}
    summary = {'at': study.ev.now(), 'paired_conditions_match': len(pair_checks)==7 and all(v['recorded_conditions_match'] for v in pair_checks.values()),
               'totals': totals, 'paired_outcomes': dict(Counter(p['paired_outcome'] for p in pairs)),
               'pairs': pairs, 'task_restarts': task_restarts, 'episode_attempts': len(all_attempts),
               'http_attempts': http_count, 'http_attempts_unknown_usage': unknown,
               'reported_usage_all_attempts': dict(usage), 'cost': None}
    save_result(study.HERE / 'results/summary.json', summary)
    save_result(study.HERE / 'results/audit.json', {'episodes': audits,'pairs': pair_checks,'all_attempts': all_attempts})
    import io
    csv_text = io.StringIO(newline='')
    writer = csv.DictWriter(csv_text, fieldnames=list(pairs[0])); writer.writeheader(); writer.writerows(pairs)
    csv_path = study.HERE / 'results/task_results.csv'
    if csv_path.exists():
        assert csv_path.read_bytes() == csv_text.getvalue().encode('utf-8')
    else:
        csv_path.write_bytes(csv_text.getvalue().encode('utf-8'))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
