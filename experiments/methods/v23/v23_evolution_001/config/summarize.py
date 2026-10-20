"""Read-only analysis of actual Campaign artifacts; no model/environment calls."""
from pathlib import Path
import json
from src.skill_evolution.v23.evolution import read, save, cost_summary
ROOT = Path('artifacts/methods/v23/v23_evolution_001')
EXP = Path('experiments/methods/v23/v23_evolution_001')


def summarize():
    result = {'state': read(ROOT/'state.json'), 'cost': cost_summary(ROOT), 'rounds': {}}
    if (ROOT/'stop.json').exists(): result['stop'] = read(ROOT/'stop.json')
    for rd in sorted((ROOT/'rounds').glob('R*')):
        frozen = read(rd/'round_input.json')
        row = {'tasks': frozen['tasks'], 'initial_parent': frozen['parent'],
               'initial_memory': frozen['memory']['entries'], 'progress': read(rd/'progress.json'),
               'executions': [], 'modules': {}}
        for side in ('parent_runs', 'candidate_runs'):
            for task in frozen['tasks']:
                folder = rd/side/task.replace(':', '_')
                if (folder/'result.json').exists():
                    path = read(folder/'result.json')['trajectory']; raw = read(path)
                    row['executions'].append({'side': side, 'task': task, 'path': path,
                        'run_id': raw['run_id'], 'status': raw['status'], 'won': raw['won'],
                        'steps': len([s for s in raw['steps'] if s['phase']=='executed'])})
        for name in ('grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'):
            if (rd/name/'result.json').exists():
                folder = rd/name/read(rd/name/'result.json')['path']
                output = read(folder/f'{name}.json')
                row['modules'][name] = {'path': str(folder), 'output': output}
                if name == 'preconditioner': row['effective_plan'] = read(folder/'effective_plan.json')
                if name == 'editor' and (folder/'candidate.md').exists():
                    row['candidate'] = (folder/'candidate.md').read_text()
                row['modules'][name]['usage'] = read(folder/'response.json').get('usage')
        if (rd/'gate/result.json').exists():
            gate = read(rd/'gate/result.json'); row['gate'] = gate['result']
            pairs = gate['input']['input']['pairs']
            row['repairs'] = sum(not p['parent']['success'] and p['candidate']['success'] for p in pairs)
            row['regressions'] = sum(p['parent']['success'] and not p['candidate']['success'] for p in pairs)
        if (rd/'memory/view.json').exists(): row['prepared_memory'] = read(rd/'memory/view.json')['entries']
        if (rd/'result.json').exists(): row['publication'] = read(rd/'result.json')
        row['cost'] = cost_summary(rd)
        result['rounds'][rd.name] = row
    save(EXP/'results/summary.json', result)
    print(json.dumps({'state':result['state'], 'cost':result['cost'],
        'rounds':{k:{'progress':v['progress']['stage'], 'executions':len(v['executions']), 'gate':v.get('gate')} for k,v in result['rounds'].items()}},indent=2))


if __name__ == '__main__': summarize()
