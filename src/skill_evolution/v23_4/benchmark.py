"""Prepare/verify an isolated V23.4 benchmark without model or Actor execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

from . import evolution as ev
from src.skill_evolution.v23 import evolution as baseline
from src.adapters.alfworld.run_task import SPLIT_ROOT

BASE_EXPERIMENT = ev.ROOT/'experiments/methods/v23/v23_alfworld_formal_001'
BASE_CAMPAIGN = ev.ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
EXPERIMENT = ev.ROOT/'experiments/methods/v23_4/v23_4_alfworld_formal_001'
CAMPAIGN = ev.ROOT/'artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1'


BASE_URL = 'http://llm-proxy.intra.xiaojukeji.com'
MODEL = 'deepseek-v4.1-flash'


def comparable_configuration(config):
    value = deepcopy(config)
    for key in ('method', 'budget', 'actor_model', 'actor_base_url'):
        value.pop(key, None)
    for key in ('endpoint', 'model'):
        value['call_config'].pop(key)
    return value


def configuration(original):
    cfg = deepcopy(original)
    cfg['method'] = deepcopy(ev.METHOD)
    cfg['actor_model'], cfg['actor_base_url'] = MODEL, BASE_URL
    cfg['call_config'].update(endpoint=BASE_URL+'/chat/completions', model=MODEL)
    # Correct the old stale pilot budget using the formal benchmark bounds.
    cfg['budget'] = deepcopy(ev.read(BASE_EXPERIMENT/'config/budget.json')['optimization'])
    return cfg


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(path, value):
    if path.exists():
        ev.require(ev.read(path) == value, f'Frozen preparation differs: {path}')
    else:
        ev.save(path, value)


def runtime_versions(python):
    # Read package metadata only; never construct/reset an environment.
    code = 'import importlib.metadata as m,json; print(json.dumps({n:m.version(n) for n in ["alfworld","textworld","numpy","requests"]}))'
    return json.loads(subprocess.check_output([python, '-c', code], text=True))


def prepare(experiment=EXPERIMENT, campaign=CAMPAIGN):
    experiment, campaign = Path(experiment).resolve(), Path(campaign).resolve()
    ev.require(not campaign.is_relative_to(BASE_CAMPAIGN) and not experiment.is_relative_to(BASE_EXPERIMENT),
               'Cannot overwrite baseline')
    original = baseline._config(BASE_CAMPAIGN)
    cfg = configuration(original)
    budget = ev.read(BASE_EXPERIMENT/'config/budget.json')
    pool = ev.read(BASE_EXPERIMENT/'data/optimization_pool.json')
    tasks = ev.read(BASE_EXPERIMENT/'data/test.json')
    ordering = ev.read(BASE_EXPERIMENT/'data/batches.json')
    env = ev.read(BASE_EXPERIMENT/'config/protocol.json')['environment']
    ids = [t for batch in cfg['batches'] for t in batch]
    ev.require(len(ids) == 57 and ids == [t['id'] for t in pool] and
               [len(b) for b in cfg['batches']] == [10,10,10,10,10,7], 'Optimization pool/order differs')
    ev.require(cfg['task_items'] == {t['id']: t for t in pool}, 'Optimization task identity differs')
    ev.require(len(tasks) == 134 and len({t['id'] for t in tasks}) == len({t['gamefile'] for t in tasks}) == 134,
               'Invalid Test identities')
    ev.require(not set(ids) & {t['id'] for t in tasks} and
               not {t['gamefile'] for t in pool} & {t['gamefile'] for t in tasks}, 'Optimization/Test overlap')
    for split in ('train', 'val', 'test'):
        expected = [t for t in pool+tasks if t['id'].startswith(split+':')]
        ev.require(expected == ev.read(SPLIT_ROOT/split/'items.json'), 'Current task mapping differs from baseline')
    ev.require(runtime_versions(cfg['actor_python']) == env['versions'], 'Actor package versions differ')
    ev.check_environment_route(cfg)
    for path, content in cfg['environment_files'].items():
        ev.require(Path(path).read_bytes().decode('utf-8') == content, 'Optimization environment drift')
    test_files = {}
    for t in tasks:
        game = Path(env['data_root'])/t['gamefile']
        for path in (game, game.parent/'initial_state.pddl'):
            test_files[str(path)] = sha(path)
    baseline_files = [BASE_CAMPAIGN/'config.json', BASE_CAMPAIGN/'initial_config.json',
                      *sorted((BASE_CAMPAIGN/'recoveries').glob('*.json')),
                      BASE_EXPERIMENT/'config/budget.json', BASE_EXPERIMENT/'config/protocol.json',
                      *[BASE_EXPERIMENT/'data'/n for n in ('optimization_pool.json','test.json','batches.json')]]
    freeze(experiment/'config/campaign.json', cfg)
    freeze(experiment/'config/evaluation.json', {'campaign':str(campaign), 'campaign_config':cfg,
        'tasks':tasks, 'expected_tasks':134, 'environment':env, 'test_environment_sha256':test_files})
    for name, value in [('optimization_pool.json',pool),('test.json',tasks),('batches.json',ordering)]:
        freeze(experiment/'data'/name, value)
    freeze(experiment/'config/method.json', ev.METHOD)
    freeze(experiment/'config/budget.json', {'optimization': budget['optimization'],
        'test_S1':budget['test_per_group'], 'default_test_groups':['S1'],
        'attempts_per_request':3, 'max_output_tokens':16384,
        'note':'Initial invocation bounds. Explicit resume adds a bounded attempt budget. No automatic token escalation; no semantic resampling. S0 is optional and not executed by default.'})
    ev.initialize(campaign, cfg)
    freeze(experiment/'config/provenance.json', {
        'baseline_campaign':str(BASE_CAMPAIGN), 'baseline_effective_config':original,
        'baseline_files':{str(p):sha(p) for p in baseline_files},
        'allowed_configuration_differences':['method','budget','actor_model','actor_base_url','call_config.model','call_config.endpoint'],
        'configuration_parity':comparable_configuration(cfg) == comparable_configuration(original),
        'routing_override':'User explicitly selected internal proxy deepseek-v4.1-flash for all V23.4 modules and Actor, 2026-10-22.',
        'budget_correction':'Replace stale pilot budget metadata with frozen formal optimization bounds.',
        'contract_files_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in ev.frozen_contract().items()}})
    return verify(experiment)


def verify(experiment=EXPERIMENT):
    experiment = Path(experiment)
    cfg = ev.read(experiment/'config/campaign.json')
    spec = ev.read(experiment/'config/evaluation.json')
    campaign = Path(spec['campaign'])
    ev._check_contract(campaign)
    ev.require(ev._config(campaign) == cfg == spec['campaign_config'], 'Frozen configuration differs')
    provenance = ev.read(experiment/'config/provenance.json')
    ev.require(provenance['configuration_parity'] and comparable_configuration(cfg) ==
               comparable_configuration(provenance['baseline_effective_config']), 'Configuration parity failed')
    ev.require(cfg['actor_model'] == cfg['call_config']['model'] == MODEL and
               cfg['actor_base_url'] == BASE_URL and cfg['call_config']['endpoint'] == BASE_URL+'/chat/completions',
               'Authorized proxy route changed')
    for name, digest in {**provenance['baseline_files'], **spec['test_environment_sha256']}.items():
        ev.require(sha(name) == digest, f'Frozen source changed: {name}')
    ev.require(runtime_versions(cfg['actor_python']) == spec['environment']['versions'], 'Runtime versions changed')
    ev.require(ev.read(experiment/'data/test.json') == spec['tasks'], 'Test manifest changed')
    ev.require(ev.read(experiment/'data/optimization_pool.json') == list(cfg['task_items'].values()), 'Pool manifest changed')
    return {'status':'ready_offline', 'campaign':str(campaign), 'method':cfg['method'],
        'optimization_tasks':sum(map(len,cfg['batches'])), 'rounds':len(cfg['batches']),
        'test_tasks':len(spec['tasks']), 'actor_max_workers':cfg['actor_max_workers'],
        'call_config':cfg['call_config'], 'state':ev.read(campaign/'state.json'),
        'output_budget_policy': ev.output_budget.POLICY if ev.output_budget.amendment(campaign) else None,
        'model_calls_started':bool(list(campaign.rglob('request.json'))),
        'actor_episodes_started':bool(list(campaign.rglob('trajectory.json')))}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','verify'])
    args = p.parse_args()
    print(json.dumps(prepare() if args.action=='prepare' else verify(), ensure_ascii=False, indent=2))
