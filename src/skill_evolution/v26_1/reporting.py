"""Read-only accounting; reserved unknown requests are never free or scored zero."""
from collections import Counter
from pathlib import Path
from .stages import read
from .protocol import require


def costs(root):
    root = Path(root)
    if (root / 'rounds').is_dir():
        parts = [read(rd / 'cost_summary.json') if (rd / 'cost_summary.json').exists() else costs(rd)
                 for rd in sorted((root / 'rounds').glob('R*'))]
        total = costs(root / '__empty_cost_source__')
        for part in parts:
            for key, value in part.items():
                if type(value) is int: total[key] += value
                elif key in ('actor_attempt_statuses', 'method_attempt_statuses', 'finish_reasons'):
                    total[key] = dict(Counter(total[key]) + Counter(value))
                elif key == 'tokens':
                    for token, counts in value.items():
                        for field, count in counts.items(): total[key][token][field] += count
                elif key == 'invocations': total[key].extend(value)
        total['invocations'].extend(read(path) for path in (root / 'timing_sessions').glob('*.json'))
        return total
    actor_attempts, method_attempts, usages = [], [], []
    rounds = tools = completed = 0
    actor_retries = method_retries = 0
    finishes = Counter()
    states = list(root.rglob('actor_state.json'))
    for path in states:
        state = read(path)
        completed += state.get('status') == 'completed'
        rounds += sum(r['phase'] == 'done' for r in state['rounds'])
        tools += sum(t['status'] == 'done' for r in state['rounds'] for t in r.get('tools', []))
        for rd in state['rounds']:
            actor_retries += max(0, len(rd['attempts']) - 1)
            for attempt in rd['attempts']:
                actor_attempts.append(attempt.get('status', 'unknown'))
                response = attempt.get('response') or {}
                if isinstance(response, dict) and response.get('choices'):
                    finishes['actor:' + str(response['choices'][0].get('finish_reason'))] += 1
                usages.append(attempt.get('usage', {}))
    for started in root.rglob('request_started.json'):
        path = started.parent
        if path.parent.name != 'attempts': continue
        error = read(path/'error.json') if (path/'error.json').exists() else None
        response = read(path/'response.json') if (path/'response.json').exists() else {}
        kind = error['kind'] if error else ('completed' if (path/'completed.json').exists() else 'unknown')
        method_attempts.append(kind)
        method_retries += int(path.name) > 1
        if response: finishes['method:' + str(response.get('finish_reason'))] += 1
        usage = response.get('usage') or {}
        usages.append({'input_tokens': usage.get('prompt_tokens'), 'output_tokens': usage.get('completion_tokens'),
                       'total_tokens': usage.get('total_tokens')})
    token = {}
    for key in ('input_tokens','output_tokens','total_tokens'):
        known = [u[key] for u in usages if type(u.get(key)) in (int,float)]
        token[key] = {'known_sum':sum(known),'unknown_requests':len(usages)-len(known)}
    timings = [read(path) for path in root.rglob('timing_sessions/*.json')]
    return {'actor_tasks_started':len(states),'actor_tasks_completed':completed,
            'accepted_model_rounds':rounds,'committed_tool_calls':tools,
            'actor_reserved_http_attempts':len(actor_attempts),'method_reserved_http_attempts':len(method_attempts),
            'physical_http_attempts_upper_bound':len(actor_attempts)+len(method_attempts),
            'unknown_send_states':sum(s in ('started','interrupted','unknown') for s in actor_attempts)+method_attempts.count('unknown'),
            'actor_retries':actor_retries, 'method_retries':method_retries, 'finish_reasons':dict(finishes),
            'actor_attempt_statuses':dict(Counter(actor_attempts)), 'method_attempt_statuses':dict(Counter(method_attempts)),
            'tokens':token, 'invocations':timings,
            'accounting_note':'Reserved sends include interrupted unknown outcomes; tokens unknown remain unknown. Offline fixtures are not physical network requests.'}


def training_rounds(root, *, directories=None, use_cache=True):
    rows=[]
    for rd in (directories if directories is not None else sorted((Path(root)/'rounds').glob('R*'))):
        if use_cache and (rd / 'round_summary.json').exists():
            rows.append(read(rd / 'round_summary.json'))
            continue
        result=read(rd/'result.json') if (rd/'result.json').exists() else None
        row={'round':rd.name,'status':result['status'] if result else 'incomplete',
             'outcome':result['outcome'] if result else None}
        for side in ('parent','candidate'):
            path=rd/(side+'_runs')/'records.json'
            records=read(path) if path.exists() else []
            row[side]={'count':len(records), **{metric:sum(r['execution']['metrics'][metric] for r in records)/len(records)
                        if records else None for metric in ('em','f1')}}
        row.update(gains=0, losses=0, f1_only=0, attributed_gains=0, attributed_losses=0,
                   unattributed_gains=0, unattributed_losses=0)
        if (rd/'pairs/input.json').exists():
            bundle=read(rd/'pairs/input.json')
            pairs={p['task_id']:p for p in bundle['payload']['pairs']}
            for pair in pairs.values():
                a,b=pair['parent_result'],pair['candidate_result']
                row['gains']+=a['em']==0 and b['em']==1
                row['losses']+=a['em']==1 and b['em']==0
                row['f1_only']+=a['em']==b['em'] and a['f1']!=b['f1']
            if (rd/'gate/result.json').exists():
                decision=read(rd/'gate/result.json');row['updates']=decision['decisions']
                row['attributed_gains']=sum(u['G'] for u in row['updates'])
                row['attributed_losses']=sum(u['L'] for u in row['updates'])
                row['unattributed_gains']=row['gains']-row['attributed_gains']
                row['unattributed_losses']=row['losses']-row['attributed_losses']
        for stage in ('diagnosis','preconditioner','editor'):
            marker=rd/stage/'result.json'
            if not marker.exists():continue
            pointer=read(marker)['path'];out=read(rd/stage/pointer/'result.json')
            if stage=='diagnosis':row['original_count']=len((out['diagnosis']['plan'] or {}).get('updates',[]))
            elif stage=='preconditioner':
                row['effective_count']=len((out['effective_plan'] or {}).get('updates',[]))
                row['adjustments']=dict(Counter(a['action'] for a in out['preconditioner']['adjustments']))
            else:
                row['empty_patches']=sum(e['patch']=='' for e in out['editor']['edits'])
                row['null_patches']=sum(e['patch'] is None for e in out['editor']['edits'])
        if result:
            source=result['selected_execution_source']
            row['selected_execution_source']=source
            row['selected_scores']=row[source] if source in ('parent','candidate') else None
        rows.append(row)
    return rows


def pending_test(root, tasks):
    import json
    path=Path(root)/'runs/actor/results.jsonl'
    rows=[]
    if path.exists():
        for line in path.read_bytes().splitlines(keepends=True):
            if line.endswith(b'\n'):rows.append(json.loads(line))
    completed=[row['id'] for row in rows]
    require(len(set(completed))==len(completed) and set(completed)<=set(tasks),'Invalid partial Test journal')
    return {'completed':len(completed),'pending':[t for t in tasks if t not in completed]}
