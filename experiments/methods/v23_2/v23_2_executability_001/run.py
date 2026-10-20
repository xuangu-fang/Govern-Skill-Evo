"""Freeze and run the authorized five-call local experiment; no Actor/Editor calls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time

from src.skill_evolution.v23 import diagnosis, grouping, preconditioner, memory, evolution
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_2 import local_validation as local


ROOT = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parent
SOURCE = ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
OUTPUT = ROOT/'artifacts/methods/v23_2/v23_2_executability_001'
ROUNDS = ('R03', 'R05', 'R06')
JOBS = ('fixed_R03', 'fixed_R05', 'fixed_R06', 'chain_R05_diagnosis', 'chain_R05_preconditioner')


def selected(rd, name):
    stage = rd/name
    return stage/evolution.read(stage/'result.json')['path']


def material(round_name):
    rd = SOURCE/'rounds'/round_name
    gp, dp, pp = (selected(rd, n) for n in ('grouping', 'diagnosis', 'preconditioner'))
    g = grouping.load_grouping(gp)
    d = diagnosis.load_diagnosis(dp, expected_grouping=g)
    saved = evolution.read(pp/'input.json')
    require({k: v for k, v in saved.items() if k != 'memory'} == d, 'Upstream input mismatch')
    frozen = evolution.read(rd/'round_input.json')
    require(saved['memory'] == frozen['memory'] == memory.load_memory(SOURCE/frozen['state']['active_memory']),
            'Not the actual incoming round Memory')
    old = preconditioner.load_preconditioner(pp, expected_diagnosis=saved)
    require(preconditioner.messages_for(saved) == evolution.read(pp/'messages.json'), 'Historical messages mismatch')
    config = evolution.read(SOURCE/'config.json')
    meta = evolution.read(pp/'run.json')
    # Only recoveries already effective at this historical call supply its limits.
    for path in sorted((SOURCE/'recoveries').glob('*.json')):
        change = evolution.read(path)
        if change['at'] <= meta['started_at']:
            if change.get('input_limits'):
                config.pop('max_input_bytes', None)
                config.update(change['input_limits'])
            if change.get('stage_config'):
                config.setdefault('stage_configs', {})[change['stage']] = change['stage_config']
    require(config['max_input_chars'] == meta['max_input_chars'], 'Historical input capacity mismatch')
    require(config.get('stage_configs', {}).get('preconditioner', config['call_config']) == meta['call_config'],
            'Historical model configuration mismatch')
    require(evolution.read(dp/'run.json')['call_config'] == config['call_config'], 'Diagnosis model mismatch')
    return g, saved, old, config, {'grouping': str(gp), 'diagnosis': str(dp), 'preconditioner': str(pp),
                                'memory': str(SOURCE/frozen['state']['active_memory'])}


def implementation():
    paths = [p for p in (ROOT/'src/skill_evolution/v23_2').iterdir() if p.suffix in ('.py', '.md')]
    paths += [Path(__file__).resolve()]
    return {str(p.relative_to(ROOT)): p.read_text() for p in sorted(paths)}


def check_v23_source():
    expected = evolution.read(SOURCE/'contract.json')
    for path in sorted((SOURCE/'recoveries').glob('*.json')):
        expected.update(evolution.read(path).get('contract_changes', {}))
    for path, content in expected.items():
        if path.startswith('src/skill_evolution/v23/'):
            require((ROOT/path).read_text() == content, f'Frozen V23 dependency changed: {path}')


def prepare():
    require(not OUTPUT.exists(), 'Experiment already started; cannot replace frozen configuration')
    check_v23_source()
    inputs = {}
    for r in ROUNDS:
        g, saved, old, cfg, paths = material(r)
        messages = local.messages_for('preconditioner', saved)
        require(messages[1] == evolution.read(Path(paths['preconditioner'])/'messages.json')[1],
                'Fixed Plan data changed')
        config = {k: deepcopy(cfg[k]) for k in ('call_config', 'max_attempts', 'retry_delay_seconds', 'max_input_chars')}
        config['max_message_utf8_bytes'] = evolution.message_byte_limit(cfg)
        if 'stage_configs' in cfg: config['stage_configs'] = cfg['stage_configs']
        encoded = json.dumps(messages, ensure_ascii=False)
        inputs[r] = {'paths': paths, 'config': config,
                     'memory_ids': [e['id'] for e in saved['memory']['entries']],
                     'input_chars': len(encoded), 'input_utf8_bytes': len(encoded.encode('utf-8')),
                     'parent_runs': len(saved['facts']['runs']),
                     'visible_runs': len(preconditioner.preconditioner_input(saved)['runs'])}
    plan = {'version': 'V23.2', 'jobs': list(JOBS), 'max_logical_calls': 5,
            'max_http_requests': 15, 'semantic_resampling': False, 'rounds': inputs,
            'chain_round': 'R05', 'created_at': evolution.now()}
    evolution.save(EXP/'config/plan.json', plan)
    evolution.save(EXP/'config/implementation.json', implementation())
    print(json.dumps({'prepared': list(inputs), 'max_logical_calls': 5,
                      'inputs': {r: {k: v for k, v in d.items() if k not in ('paths', 'config')}
                                 for r, d in inputs.items()}}, ensure_ascii=False), flush=True)


def protected_bytes():
    roots = [ROOT/'src/skill_evolution/v23', ROOT/'src/adapters/alfworld',
             ROOT/'experiments/methods/v23/v23_alfworld_formal_001', SOURCE.parent]
    return {str(p): p.read_bytes() for root in roots for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def run():
    check_v23_source()
    plan = evolution.read(EXP/'config/plan.json')
    require(plan['jobs'] == list(JOBS) and plan['max_logical_calls'] == 5, 'Call budget differs')
    require(implementation() == evolution.read(EXP/'config/implementation.json'), 'Frozen implementation changed')
    OUTPUT.mkdir(parents=True, exist_ok=False)  # One invocation cannot allocate another five-call budget.
    evolution.save(OUTPUT/'plan.json', plan)
    before = protected_bytes()
    started = time.monotonic()
    outcomes, comparisons = {}, {}

    def call(job, name, saved, cfg):
        require(job in JOBS and job not in outcomes, 'Unexpected or duplicate logical call')
        outcomes[job] = {'status': 'started', 'at': evolution.now()}
        evolution.save(OUTPUT/'status.json', outcomes)
        print(f'START {job}', flush=True)
        try:
            result = local.run_stage(name, saved, OUTPUT/job, cfg)
            outcomes[job] = {'status': 'valid', 'decision': result[name]['decision']}
            return result
        except evolution.Stopped as exc:
            outcomes[job] = {'status': 'stopped', 'error': str(exc)}
            return None
        finally:
            evolution.save(OUTPUT/'status.json', outcomes)
            print(f'END {job}: {outcomes[job]}', flush=True)

    try:
        materials = {r: material(r) for r in ROUNDS}
        for r in ROUNDS:
            g, saved, old, cfg, paths = materials[r]
            config = plan['rounds'][r]['config']
            require(paths == plan['rounds'][r]['paths'], 'Historical source selection changed')
            new = call('fixed_'+r, 'preconditioner', saved, config)
            comparisons[r] = {'source': paths, 'original_plan': saved['diagnosis']['plan'],
                              'v23': {'preconditioner': old['preconditioner'], 'effective_plan': old['effective_plan']},
                              'v23_2': None if new is None else {
                                  'preconditioner': new['preconditioner'], 'effective_plan': new['effective_plan']}}
        g, saved, old, cfg, paths = materials['R05']
        config = plan['rounds']['R05']['config']
        d = call('chain_R05_diagnosis', 'diagnosis', g, config)
        chain = {'diagnosis': None if d is None else d['diagnosis'], 'preconditioner': None, 'effective_plan': None}
        if d is not None and d['diagnosis']['decision'] == 'revise':
            pc = call('chain_R05_preconditioner', 'preconditioner',
                      {**d, 'memory': deepcopy(saved['memory'])}, config)
            if pc is not None: chain.update(preconditioner=pc['preconditioner'], effective_plan=pc['effective_plan'])
        else:
            outcomes['chain_R05_preconditioner'] = {'status': 'not_called', 'reason': 'Diagnosis did not return revise'}
        evolution.save(OUTPUT/'comparison.json', {'fixed': comparisons, 'chain_R05': chain})
    finally:
        after = protected_bytes()
        changed = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p)]
        evolution.save(OUTPUT/'protection.json', {'checked_files': len(before), 'unchanged': not changed, 'changed': changed})
        evolution.save(OUTPUT/'status.json', outcomes)
        evolution.save(OUTPUT/'summary.json', {'elapsed_seconds': time.monotonic()-started,
                       'logical_calls_started': sum(v['status'] != 'not_called' for v in outcomes.values()),
                       'outcomes': outcomes, 'cost': evolution.cost_summary(OUTPUT)})
        require(not changed, 'V23 protected files changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    args = parser.parse_args()
    prepare() if args.action == 'prepare' else run()
