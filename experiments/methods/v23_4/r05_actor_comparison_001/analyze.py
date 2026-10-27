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

TARGETS = dict(zip([f'val:{n:04}' for n in range(1, 11)],
                   ['bowl', 'pillow', 'mug', 'mug', 'pencil', 'butterknife', 'butterknife', 'soapbar', 'soapbar', 'apple']))


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
    light = record['task']['task_type'] == 'look_at_obj_in_light'
    steps = [s for s in record['steps'] if s['phase'] == 'executed']
    take = re.compile(rf'^take {target} \d+ from ')
    acquire = next((s['step'] for s in steps if take.match(s['action']) and
                    s['observation'].startswith('You pick up ')), None)
    prefix = [] if light else [s for s in steps if acquire is None or s['step'] < acquire]
    prefix_ids = {s['step'] for s in prefix}
    nav = [s for s in prefix if s['action'].startswith('go to ') and s['action_in_admissible_commands']]
    seen, revisits = set(), []
    for s in nav:
        if s['action'] in seen:
            revisits.append(s['step'])
        seen.add(s['action'])
    before, location = record['initial_observation'], None
    signatures, repeats, compact, non_target, direct = set(), [], [], [], []
    for s in steps:
        action, menu = s['action'], s['admissible_commands']
        signature = (before, tuple(menu), action)
        if s['step'] in prefix_ids and signature in signatures:
            repeats.append(s['step'])
        signatures.add(signature)
        obj = re.match(r'^(take|clean|cool|heat|move) ([a-z]+) (\d+) (?:from|with|to) ', action)
        if obj and obj[2] != target and not light:
            non_target.append(s['step'])
        # Only selected direct container actions outside the last known navigation
        # location. This is observable evidence, not inferred intent or correctness.
        site = re.match(r'^(?:open|close|examine) (.+ \d+)$', action)
        site_name = site[1] if site else None
        without_nav = bool(site_name and s['action_in_admissible_commands'] and
                           'go to ' + site_name not in menu and location != site_name)
        if without_nav:
            direct.append(s['step'])
        compact.append({'step': s['step'], 'before': before, 'action': action,
                        'after': s['observation'], 'admissible': s['action_in_admissible_commands'],
                        'won': s['won'], 'direct_container_action_without_navigation': without_nav,
                        'last_navigation_location': location})
        if action.startswith('go to ') and s['action_in_admissible_commands'] and s['observation'].startswith('You arrive at '):
            location = action[len('go to '):]
        before = s['observation']
    no_effect = [s['step'] for s in steps if s['observation'].strip().lower().startswith('nothing happens')]
    inadmissible = [s['step'] for s in steps if not s['action_in_admissible_commands']]
    return {'task': record['task']['id'], 'goal': record['goal'], 'status': record['status'],
            'won': record['won'], 'steps': len(steps), 'first_target_acquisition_step': acquire,
            'desklamp_task': light, 'pre_acquisition_search_proxy_applicable': not light,
            'inadmissible_steps': inadmissible, 'no_effect_steps': no_effect,
            'invalid_or_no_effect_steps': sorted(set(inadmissible + no_effect)),
            'fallback_steps': [s['step'] for s in steps if s['fallback']],
            'search_navigation_count': len(nav), 'unique_search_destinations': len(seen),
            'search_revisit_steps': revisits, 'repeated_visible_state_action_steps': repeats,
            'non_target_manipulation_steps': non_target,
            'direct_container_action_without_navigation_steps': direct,
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
            for name in ['status', 'won', 'steps', 'first_target_acquisition_step', 'desklamp_task']:
                row[f'{arm}_{name}'] = m.get(name)
            for name in ['invalid_or_no_effect_steps', 'search_revisit_steps', 'repeated_visible_state_action_steps', 'non_target_manipulation_steps', 'direct_container_action_without_navigation_steps']:
                row[f'{arm}_{name}_count'] = len(m[name]) if name in m else None
        pairs.append(row)
    totals = {}
    for arm in plan['arms']:
        ms = [results[(arm, task)] for task in plan['tasks']]
        totals[arm] = {'successes': sum(m['won'] for m in ms), 'denominator': len(plan['tasks']),
                      'complete_tasks': sum(m['steps'] is not None for m in ms),
                      'total_selected_steps': sum(m['steps'] or 0 for m in ms),
                      'joint_success_steps': sum(row[f'{arm}_steps'] for row in pairs if row['paired_outcome']=='both_success'),
                      'joint_success_tasks': sum(row['paired_outcome']=='both_success' for row in pairs),
                      'invalid_or_no_effect_count': sum(len(m.get('invalid_or_no_effect_steps', [])) for m in ms),
                      'search_revisit_count': sum(len(m.get('search_revisit_steps', [])) for m in ms)}
    summary = {'at': study.ev.now(), 'paired_conditions_match': len(pair_checks)==len(plan['tasks']) and all(v['recorded_conditions_match'] for v in pair_checks.values()),
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
