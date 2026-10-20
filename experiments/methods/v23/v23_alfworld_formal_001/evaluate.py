"""Fixed-Skill Test only: existing Actor workers, bounded retries, resumable episodes."""
import argparse
from copy import deepcopy
import fcntl
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import time

from src.skill_evolution.v23 import evolution as ev
from src.skill_evolution.v23.facts import require, build_facts
from src.skill_evolution.v23.gate import build_gate
from src.adapters.alfworld.response_archive import verify_response_archive

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = ev.ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/evaluation'


def recovery(root):
    """Read the explicitly reviewed transport fix; all other freezes still apply."""
    records = sorted((Path(root)/'recoveries').glob('*.json'))
    if not records:
        return None
    require(len(records) == 1, 'Unexpected evaluation recovery history')
    change = ev.read(records[0])
    name = 'src/adapters/alfworld/run_task_upstream.py'
    old = change['contract_before']
    new = change['contract_changes']
    require(set(old) == set(new) == {name}, 'Recovery must only cover the transport fix')
    needle = 'except (requests.Timeout, requests.ConnectionError):'
    replacement = 'except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError):'
    require(old[name].count(needle) == 1 and old[name].replace(needle, replacement) == new[name],
            'Recovery changes more than ChunkedEncodingError coverage')
    require(set(change['runner_before']) == set(change['runner_changes']) == {'evaluate.py'},
            'Unexpected runner recovery')
    require(change['reason'].strip(), 'Missing explicit recovery reason')
    return change


def recovered_input(root, change):
    expected = ev.read(Path(root)/'input.json')
    if change:
        for name, before in change['runner_before'].items():
            require(expected['runner_sources'][name] == before, 'Runner recovery source mismatch')
        expected['runner_sources'].update(change['runner_changes'])
    return expected


def prepare(root=DEFAULT_ROOT):
    configs = {g: ev.read(HERE/'config'/n) for g, n in
               [('S0', 'no_skill_eval.json'), ('S1', 'v23_eval.json')]}
    protocol = ev.read(HERE/'config/protocol.json')
    tasks = ev.read(HERE/'data/test.json'); pool = ev.read(HERE/'data/optimization_pool.json')
    require(len(tasks) == 134 and len({t['id'] for t in tasks}) == 134 and
            len({t['gamefile'] for t in tasks}) == 134, 'Invalid frozen Test set')
    require(not {t['gamefile'] for t in tasks} & {t['gamefile'] for t in pool}, 'Test/optimization overlap')
    campaign = Path(configs['S1']['skill_source']['campaign'])
    change = recovery(root)
    expected = ev.read(campaign/'contract.json')
    for p in sorted((campaign/'recoveries').glob('*.json')):
        expected.update(ev.read(p).get('contract_changes', {}))
    if change:
        for name, before in change['contract_before'].items():
            require(expected[name] == before, 'Training source recovery mismatch')
        expected.update(change['contract_changes'])
    require(expected == ev.frozen_contract(), 'Frozen source/Prompt changed; explicit reviewed recovery required')
    skill = ev.final_parent(campaign)
    spec = importlib.util.spec_from_file_location('formal_test_commands', HERE/'test_commands.py')
    command_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(command_module)
    commands = {}
    for group, cfg in configs.items():
        require(cfg['tasks'] == tasks and cfg['expected_tasks'] == 134, 'Test set differs')
        require(cfg['split'] == 'test' and cfg['purpose'] == 'final', 'Not final Test')
        require(cfg['max_steps'] == 50 and cfg['max_attempts_per_step'] == 3 and cfg['strict_response'], 'Actor limits differ')
        require(cfg['actor'] == protocol['actor'] and cfg['environment'] == protocol['environment'], 'Protocol differs')
        require(cfg['actor']['request_parameters'] == ev.grouping.call_configuration(
            base_url=cfg['actor']['base_url'], model=cfg['actor']['model'], max_tokens=16384, timeout=300), 'Unsupported Actor parameters')
        rows = command_module.commands(cfg)
        commands[group] = {t['id']: row for t, row in zip(tasks, rows)}
    require(configs['S0']['skill_source'] == {'kind': 'none'}, 'S0 must have no Skill')
    files = {}
    for task in tasks:
        game = Path(protocol['environment']['data_root'])/task['gamefile']
        # Actual environment files, compared directly. No new hash scheme.
        for p in [game, game.parent/'initial_state.pddl']:
            files[str(p)] = p.read_bytes().decode('utf-8')
    return {'configs': configs, 'protocol': protocol, 'tasks': tasks, 'commands': commands,
            'actor_max_workers': 8, 'parent': None if skill is None else str(skill),
            'skill_text': None if skill is None else skill.read_bytes().decode('utf-8'),
            'campaign_state': ev.read(campaign/'state.json'), 'environment_files': files,
            'runner_sources': {p.name: p.read_text() for p in [Path(__file__), HERE/'test_commands.py']}}


def actor_config(bundle):
    cfg = bundle['configs']['S0']
    return {'actor_max_workers': bundle['actor_max_workers'], 'max_steps': cfg['max_steps'],
            'actor_model': cfg['actor']['model'], 'task_items': {t['id']: t for t in bundle['tasks']}}


def check_record(path, task, group, bundle):
    raw = ev.read(path); cfg = bundle['configs'][group]
    require(raw['task'] == task and raw['split'] == 'test' and raw['purpose'] == 'final', 'Wrong Test identity')
    require(raw['skill']['text'] == (None if group == 'S0' else bundle['skill_text']), 'Wrong Test Skill')
    require(raw['model'] == cfg['actor']['model'] and raw['protocol'] == cfg['actor']['execution_protocol'], 'Actor protocol differs')
    require(raw['request_policy'] == {'max_attempts': 3, 'strict_response': True}, 'Retry policy differs')
    for name in ('alfworld', 'textworld', 'requests'):
        require(raw['versions'][name] == cfg['environment']['versions'][name], 'Environment version differs')
    params = {k:v for k,v in cfg['actor']['request_parameters'].items() if k not in ('endpoint', 'timeout_seconds')}
    for step in raw['steps']:
        for attempt in step.get('transport_attempts', []):
            require(attempt['request_parameters'] == params, 'Actual Actor generation parameters differ')
            verify_response_archive(path, attempt)
    build_facts([raw])
    require(raw['status'] in ev.COMPLETE and type(raw['won']) is bool and not raw.get('error_type'), 'Technical/unknown Test outcome')
    return raw


def execute_task(bundle, group, task, skill, dest, config):
    expected = None if group == 'S0' else bundle['parent']
    require((None if skill is None else str(skill)) == expected, 'Unexpected Skill path')
    if expected is not None:
        require(Path(expected).read_bytes().decode('utf-8') == bundle['skill_text'], 'Final Skill changed')
    game = Path(bundle['configs'][group]['environment']['data_root'])/config['task_items'][task]['gamefile']
    for p in [game, game.parent/'initial_state.pddl']:
        require(p.read_bytes().decode('utf-8') == bundle['environment_files'][str(p)], 'Test environment file changed')
    cmd = list(bundle['commands'][group][task])
    cmd[cmd.index('--output-root')+1] = str(dest)
    ev.save(dest/'command.json', cmd)
    # No outer HTTP or episode retry; the existing Actor enforces 3 attempts/step.
    with (dest/'process.log').open('w') as stream:
        proc = subprocess.run(cmd, cwd=ev.ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
    paths = list(dest.rglob('trajectory.json'))
    require(len(paths) == 1, f'Actor exit {proc.returncode}: missing/ambiguous trajectory')
    check_record(paths[0], config['task_items'][task], group, bundle)
    require(proc.returncode == 0, f'Actor process exited {proc.returncode}')
    return paths[0]


def costs(directory):
    result = {k:0 for k in ['requests','input_tokens','output_tokens','reasoning_tokens','cached_tokens',
                            'total_tokens','unknown_usage_requests','reasoning_usage_missing','cached_usage_missing',
                            'retry_requests','unsuccessful_requests','unsuccessful_tokens','technical_episode_attempts']}
    for p in Path(directory).rglob('trajectory.json'):
        raw = ev.read(p); technical = raw['status'] not in ev.COMPLETE
        result['technical_episode_attempts'] += technical
        for step in raw['steps']:
            attempts = step.get('transport_attempts', [])
            for i, attempt in enumerate(attempts):
                result['requests'] += 1; result['retry_requests'] += i > 0
                failed = i < len(attempts)-1 or step.get('phase') != 'executed'
                result['unsuccessful_requests'] += failed
                u = attempt.get('usage')
                if not isinstance(u, dict):
                    result['unknown_usage_requests'] += 1; continue
                for dest, key in [('input_tokens','prompt_tokens'),('output_tokens','completion_tokens'),('total_tokens','total_tokens')]:
                    result[dest] += u.get(key, 0) or 0
                reasoning = (u.get('completion_tokens_details') or {}).get('reasoning_tokens')
                cached = (u.get('prompt_tokens_details') or {}).get('cached_tokens', u.get('prompt_cache_hit_tokens'))
                result['reasoning_usage_missing'] += reasoning is None; result['cached_usage_missing'] += cached is None
                result['reasoning_tokens'] += reasoning or 0; result['cached_tokens'] += cached or 0
                if failed: result['unsuccessful_tokens'] += u.get('total_tokens', 0) or 0
    return result


def summarize_group(root, group, bundle):
    rows = []; records = []
    for task in bundle['tasks']:
        marker = root/group/'episodes'/task['id'].replace(':','_')/'result.json'
        path = Path(ev.read(marker)['trajectory'])
        require(path.resolve().is_relative_to((root/group).resolve()), 'Episode outside this evaluation')
        raw = check_record(path, task, group, bundle);records.append(raw)
        rows.append({'task_id':task['id'],'task_type':task['task_type'],'gamefile':task['gamefile'],
                     'run_id':raw['run_id'],'success':raw['won'],'steps':len(raw['steps']),
                     'termination':raw['status'],'trajectory':str(path)})
    success = sum(x['success'] for x in rows); steps = [x['steps'] for x in rows if x['success']]
    result = {'group':group,'completed':len(rows),'success':success,'failure':len(rows)-success,
              'success_rate':success/len(rows),'steps':sum(x['steps'] for x in rows),
              'successful_steps_mean':statistics.mean(steps) if steps else None,
              'successful_steps_median':statistics.median(steps) if steps else None,
              'cost':costs(root/group),'tasks':rows}
    ev.save(root/group/'summary.json', result)
    return result, records


def comparison(root, bundle):
    summaries = {}; records = {}
    for group in ['S0','S1']:summaries[group],records[group] = summarize_group(root,group,bundle)
    change = recovery(root)
    verified = build_gate(records['S0'],records['S1'],[t['id'] for t in bundle['tasks']],
                          parent_skill=None,candidate_skill=bundle['skill_text'],
                          implementation_review=change['implementation_review'] if change else None)
    rows = []; categories = {k:[] for k in ['fixed','regressed','both_success','both_failure']}
    types = {}
    for a,b in zip(summaries['S0']['tasks'], summaries['S1']['tasks']):
        require(a['task_id']==b['task_id'],'Comparison order differs')
        key = ('both_success' if a['success'] else 'fixed') if b['success'] else ('regressed' if a['success'] else 'both_failure')
        categories[key].append(a['task_id'])
        rows.append({'task_id':a['task_id'],'task_type':a['task_type'],'category':key,'S0':a,'S1':b})
        stat = types.setdefault(a['task_type'],{'count':0,'S0_success':0,'S1_success':0,'fixed':0,'regressed':0})
        stat['count']+=1;stat['S0_success']+=a['success'];stat['S1_success']+=b['success']
        if key in ('fixed','regressed'):stat[key]+=1
    for stat in types.values():
        for g in ['S0','S1']:stat[g+'_rate'] = stat[g+'_success']/stat['count']
    result = {'groups':summaries,'improvement_percentage_points':100*(summaries['S1']['success_rate']-summaries['S0']['success_rate']),
              'categories':categories,'task_types':types,'pairs':rows,'pair_audit':verified['audit']}
    require(sum(map(len,categories.values()))==len(bundle['tasks']), 'Incomplete categories')
    ev.save(root/'comparison/results.json',result)
    return result


def run(root, *, resume=False, runner=None, bundle=None):
    root=Path(root).resolve(); root.mkdir(parents=True,exist_ok=True)
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        bundle = prepare(root) if bundle is None else bundle
        require(not root.is_relative_to(Path(bundle['configs']['S1']['skill_source']['campaign'])), 'Cannot write into training Campaign')
        if (root/'input.json').exists():
            require(resume, 'Existing evaluation requires resume')
            require(recovered_input(root, recovery(root))==bundle,'Frozen evaluation inputs changed')
            ev._check_contract(root)
        else:
            require(not resume,'No evaluation to resume')
            require(not any(p.name!='.lock' for p in root.iterdir()),'Nonempty evaluation directory')
            ev.save(root/'input.json',bundle);ev.save(root/'contract.json',ev.frozen_contract())
        sessions=root/'sessions';sessions.mkdir(exist_ok=True)
        session=sessions/f'{len(list(sessions.glob("*.json")))+1:03}.json'
        started=time.monotonic(); entry={'started_at':ev.now(),'resume':resume,'status':'running'};ev.save(session,entry)
        try:
            cfg=actor_config(bundle);tasks=[t['id'] for t in bundle['tasks']]
            for group in ['S0','S1']:
                ev.save(root/'progress.json',{'group':group,'stage':'episodes','at':ev.now()})
                folder=root/group;folder.mkdir(exist_ok=True)
                def invoke(task,skill,dest,config):
                    try:
                        if runner is None:return execute_task(bundle,group,task,skill,dest,config)
                        return runner(group,task,skill,dest,config)
                    except BaseException as exc:
                        ev.save(dest/'error.json',{'type':type(exc).__name__,'error':str(exc),'at':ev.now()})
                        raise
                ev._actors(root,folder,'episodes',tasks,None if group=='S0' else bundle['parent'],cfg,invoke,resume)
                summarize_group(root,group,bundle)
            ev.save(root/'progress.json',{'stage':'comparison','at':ev.now()})
            comparison(root,bundle)
            ev.save(root/'result.json',{'status':'complete','groups':['S0','S1'],'tasks_per_group':len(tasks),'at':ev.now()})
            entry['status']='complete'
        except BaseException as exc:
            entry.update(status='stopped',error_type=type(exc).__name__,error=str(exc))
            ev.save(root/'stop.json',{**entry,'at':ev.now(),'progress':ev.read(root/'progress.json')})
            raise
        finally:
            entry.update(finished_at=ev.now(),elapsed_seconds=time.monotonic()-started);ev.save(session,entry)
    return ev.read(root/'result.json')


def status(root):
    root=Path(root)
    return {'result':ev.read(root/'result.json') if (root/'result.json').exists() else None,
            'progress':ev.read(root/'progress.json') if (root/'progress.json').exists() else None,
            'completed':{g:len(list((root/g/'episodes').glob('*/result.json'))) for g in ['S0','S1']}}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['run','resume','status']);parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    args=parser.parse_args()
    print(json.dumps(status(args.root) if args.action=='status' else run(args.root,resume=args.action=='resume'),indent=2))
