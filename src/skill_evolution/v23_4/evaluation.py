"""Fixed-Skill Test only: existing Actor workers, bounded retries, resumable episodes."""
import argparse
import hashlib
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import statistics
import subprocess
import time

from . import evolution as ev
from src.skill_evolution.v23.facts import require, build_facts
from src.skill_evolution.v23.gate import build_gate
from src.adapters.alfworld.response_archive import verify_response_archive

DEFAULT_CONFIG = ev.ROOT/'experiments/methods/v23_4/v23_4_alfworld_formal_001/config/evaluation.json'
DEFAULT_ROOT = ev.ROOT/'artifacts/methods/v23_4/v23_4_alfworld_formal_001/evaluation'


def prepare(config_path=DEFAULT_CONFIG):
    """Bind final Test only to a completed Campaign's officially retained Parent."""
    from src.adapters.alfworld.run_task import SPLIT_ROOT
    spec = ev.read(config_path)
    campaign = Path(spec['campaign']).resolve()
    ev._check_contract(campaign)
    cfg = ev._config(campaign)
    budget_recovery = ev.output_budget.amendment(campaign) is not None
    require(cfg == spec['campaign_config'], 'Evaluation Campaign configuration differs')
    tasks = spec['tasks']
    require(len(tasks) == spec['expected_tasks'] == 134 and tasks == ev.read(SPLIT_ROOT/'test/items.json'),
            'Invalid frozen final Test mapping')
    require(len({t['id'] for t in tasks}) == len({t['gamefile'] for t in tasks}) == 134, 'Duplicate Test identity')
    pool = list(cfg['task_items'].values())
    require(not {t['id'] for t in tasks} & {t['id'] for t in pool} and
            not {t['gamefile'] for t in tasks} & {t['gamefile'] for t in pool}, 'Test/optimization overlap')
    skill = ev.final_parent(campaign)
    actor = {'python': cfg['actor_python'], 'model': cfg['actor_model'], 'base_url': cfg['actor_base_url'],
             'request_parameters': cfg['call_config'], 'execution_protocol': ev.execution_protocol(cfg['max_steps'])}
    configs, commands = {}, {}
    for group in ('S0', 'S1'):
        configs[group] = {'actor': actor, 'environment': spec['environment'],
            'max_steps': cfg['max_steps'], 'max_attempts_per_step': cfg['actor_request_attempts'],
            'skill_source': {'kind': 'none'} if group == 'S0' else
                {'kind': 'campaign_final_parent', 'campaign': str(campaign)}}
        if budget_recovery:
            configs[group]['output_budget_policy'] = ev.output_budget.POLICY
        rows = {}
        for task in tasks:
            cmd = ['env', 'ALFWORLD_DATA='+cfg['environment_root'], 'OPENAI_BASE_URL='+cfg['actor_base_url'],
                cfg['actor_python'], '-m', 'src.adapters.alfworld.run_task_skill', '--split', 'test',
                '--purpose', 'final', '--task-id', task['id'], '--model', cfg['actor_model'],
                '--max-steps', str(cfg['max_steps']), '--request-attempts', str(cfg['actor_request_attempts']),
                '--strict-response', '--archive-responses', '--output-root', 'SET_BY_EXECUTOR']
            if group == 'S1' and skill is not None:
                cmd += ['--skill-file', str(skill)]
            if budget_recovery:
                cmd[5] = 'src.skill_evolution.v23_4.budget_actor'
                cmd += ['--budget-campaign', str(campaign)]
            rows[task['id']] = cmd
        commands[group] = rows
    files = {}
    for path, digest in spec['test_environment_sha256'].items():
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'Frozen Test environment changed')
    for task in tasks:
        game = Path(cfg['environment_root'])/task['gamefile']
        for p in [game, game.parent/'initial_state.pddl']:
            files[str(p)] = p.read_bytes().decode('utf-8')
    require(spec['environment']['data_root'] == cfg['environment_root'], 'Evaluation environment differs')
    return {'configs': configs, 'tasks': tasks, 'commands': commands,
        'actor_max_workers': cfg['actor_max_workers'], 'parent': None if skill is None else str(skill),
        'skill_text': None if skill is None else skill.read_bytes().decode('utf-8'),
        'campaign_state': ev.read(campaign/'state.json'), 'environment_files': files,
        'method': cfg['method'], 'evaluation_spec': spec}


def actor_config(bundle):
    cfg = bundle['configs']['S0']
    result = {'actor_max_workers': bundle['actor_max_workers'], 'max_steps': cfg['max_steps'],
            'actor_model': cfg['actor']['model'], 'task_items': {t['id']: t for t in bundle['tasks']}}
    if cfg.get('output_budget_policy'):
        result['_output_budget_campaign'] = bundle['configs']['S1']['skill_source']['campaign']
    return result


def check_record(path, task, group, bundle):
    raw = ev.read(path); cfg = bundle['configs'][group]
    require(raw['task'] == task and raw['split'] == 'test' and raw['purpose'] == 'final', 'Wrong Test identity')
    require(raw['skill']['text'] == (None if group == 'S0' else bundle['skill_text']), 'Wrong Test Skill')
    require(raw['model'] == cfg['actor']['model'] and raw['protocol'] == cfg['actor']['execution_protocol'], 'Actor protocol differs')
    require(raw['request_policy'] == {'max_attempts': 3, 'strict_response': True}, 'Retry policy differs')
    for name in ('alfworld', 'textworld', 'requests'):
        require(raw['versions'][name] == cfg['environment']['versions'][name], 'Environment version differs')
    params = {k:v for k,v in cfg['actor']['request_parameters'].items() if k not in ('endpoint', 'timeout_seconds')}
    if cfg.get('output_budget_policy'):
        ev.output_budget.validate_actor(path, raw)
    for step in raw['steps']:
        for attempt in step.get('transport_attempts', []):
            expected = {**params, 'max_tokens': attempt['request_parameters']['max_tokens']} if cfg.get('output_budget_policy') else params
            require(attempt['request_parameters'] == expected, 'Actual Actor generation parameters differ')
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
    verified = build_gate(records['S0'],records['S1'],[t['id'] for t in bundle['tasks']],
                          parent_skill=None,candidate_skill=bundle['skill_text'],
                          implementation_review=None)
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


def run(root, *, config_path=DEFAULT_CONFIG, groups=('S1',), resume=False, runner=None, bundle=None):
    root=Path(root).resolve(); root.mkdir(parents=True,exist_ok=True)
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(tuple(groups) in (('S1',), ('S0',), ('S0', 'S1')), 'Unsupported evaluation groups')
        bundle = prepare(config_path) if bundle is None else deepcopy(bundle)
        bundle['groups'] = list(groups)
        if runner is None:
            ev.check_live_environment(bundle['evaluation_spec']['campaign_config'])
        require(not root.is_relative_to(Path(bundle['configs']['S1']['skill_source']['campaign'])), 'Cannot write into training Campaign')
        if (root/'input.json').exists():
            require(resume, 'Existing evaluation requires resume')
            require(ev.read(root/'input.json')==bundle,'Frozen evaluation inputs changed')
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
            for group in groups:
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
            if tuple(groups) == ('S0', 'S1'):
                comparison(root,bundle)
            ev.save(root/'result.json',{'status':'complete','groups':list(groups),'tasks_per_group':len(tasks),'at':ev.now()})
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
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--groups',nargs='+',choices=['S0','S1'],default=['S1'])
    args=parser.parse_args()
    print(json.dumps(status(args.root) if args.action=='status' else run(args.root,config_path=args.config,groups=args.groups,resume=args.action=='resume'),indent=2))
