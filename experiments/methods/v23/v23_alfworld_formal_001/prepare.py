"""Rebuild/verify preparation from saved public manifests; never execute tasks or models.

Run from the repository root with PYTHONPATH=. No network access is needed.
Existing prepared files are compared, never silently replaced after a pool change.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path

from src.adapters.alfworld.run_task import SPLIT_ROOT
from src.adapters.alfworld.skill_runtime import execution_protocol
from src.skill_evolution.v23.evolution import validate_config

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DATA_ROOT = Path('/Users/didi/.cache/alfworld')
LIVE = ROOT/'experiments/methods/v23/v23_evolution_001'
CAMPAIGN = ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'


def read(path):
    return json.loads(Path(path).read_text())


def frozen(path, data):
    path = Path(path)
    if path.exists():
        if read(path) != data:
            raise ValueError(f'Prepared contents changed: {path}; do not reuse the old preparation')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def batches(pool):
    # Official ALFWorld profile: sequential, shuffle=false. User confirmed 2026-10-19.
    ids = [x['id'] for x in pool]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate optimization ID')
    return [ids[i:i+10] for i in range(0, len(ids), 10)]


def load_and_verify():
    source = HERE/'data/source/SkillOpt/data/alfworld_path_split'
    adam = read(HERE/'data/source/SkillAdam/skilladam/data/profiles/alfworld_main_results.json')
    items, audit = {}, []
    paths, ids = set(), set()
    for split, count in [('train', 39), ('val', 18), ('test', 134)]:
        rows = read(source/split/'items.json')
        assert len(rows) == count
        assert rows == read(SPLIT_ROOT/split/'items.json') == adam['splits'][split]
        for item in rows:
            assert item['id'].split(':')[0] == split
            path = (DATA_ROOT/item['gamefile']).resolve()
            assert path.is_relative_to(DATA_ROOT) and path.is_file()
            assert item['id'] not in ids and path not in paths
            ids.add(item['id']); paths.add(path)
            game = read(path)
            metadata = read(path.parent/'traj_data.json')
            assert metadata['task_type'] == item['task_type']
            assert path.parent.parent.name.startswith(item['task_type']+'-')
            assert path.parent.name == metadata['task_id']
            assert all(isinstance(game[k], str) and game[k] for k in ['pddl_domain', 'pddl_problem', 'grammar'])
            assert (path.parent/'initial_state.pddl').is_file()
            audit.append({**item, 'source_split': split, 'local_gamefile': str(path),
                          'environment_task_id': metadata['task_id'], 'metadata_type_matches': True})
        items[split] = rows
    return items, audit


def exposure(pool):
    by_game = {x['gamefile']: x for x in pool}
    observed = defaultdict(list)
    count = 0
    for version in ['v22', 'v23']:
        for path in sorted((ROOT/'artifacts/methods'/version).rglob('trajectory.json')):
            # Preparation measures prior development exposure, not this formal run.
            if path.is_relative_to(CAMPAIGN.parent):
                continue
            raw = read(path); count += 1
            game = raw.get('task', {}).get('gamefile')
            # Count an actual attempted Actor request, including interrupted attempts.
            steps = raw.get('steps', [])
            if game in by_game and any(s.get('transport_attempts') or s.get('model_response') for s in steps):
                observed[game].append({'version': version, 'run_id': raw.get('run_id'),
                    'status': raw.get('status'), 'trajectory': str(path.relative_to(ROOT))})
    return {'scope': 'Actual archived trajectories under artifacts/methods/v22 and v23; matched by gamefile, not numeric ID. Copied records are listed; distinct games counted once.',
        'records_inspected': count, 'distinct_optimization_games_exposed': len(observed),
        'tasks': [{**item, 'records': observed[item['gamefile']]} for item in pool if item['gamefile'] in observed]}


def build():
    items, audit = load_and_verify()
    pool = items['train'] + items['val']; ordered = batches(pool)
    assert list(map(len, ordered)) == [10, 10, 10, 10, 10, 7]
    for name, value in [('train', items['train']), ('selection', items['val']),
                        ('optimization_pool', pool), ('test', items['test'])]:
        frozen(HERE/f'data/{name}.json', value)
    frozen(HERE/'data/batches.json', {'seed': 42, 'shuffle': False, 'order': 'SkillAdam official sequential: train then val; user-confirmed',
        'epochs': 1, 'batch_size': 10, 'ordered_task_ids': sum(ordered, []),
        'rounds': [{'round_id': f'R{i+1:02}', 'tasks': batch} for i, batch in enumerate(ordered)]})
    frozen(HERE/'data/local_mapping.json', audit)
    frozen(HERE/'data/development_overlap.json', exposure(pool))
    cfg = deepcopy(read(LIVE/'config/campaign.json'))
    cfg.update(batches=ordered, actor_max_workers=8, optimization_splits=['train', 'val'],
               environment_root=str(DATA_ROOT), actor_base_url='https://api.deepseek.com',
               task_items={x['id']: x for x in pool})
    cfg['environment_files'] = {str(DATA_ROOT/x['gamefile']): (DATA_ROOT/x['gamefile']).read_bytes().decode('utf-8') for x in pool}
    validate_config(cfg)
    frozen(HERE/'config/campaign.json', cfg)
    protocol = {'benchmark': 'ALFWorld', 'seed': 42, 'epochs': 1, 'batch_size': 10, 'rounds': 6,
        'ordering': 'official_sequential_no_shuffle', 'initial_parent': None,
        'initial_memory': {'entries': [], 'sources': {}}, 'independent_validation': False,
        'gate': 'ACCEPT iff Candidate success count > Parent success count; otherwise RETAIN',
        'gate_and_replay_tasks': 'same frozen optimization batch',
        'memory_timing': 'Preconditioner and Replay both read round-start Memory; new Memory starts next round',
        'state_publication': 'atomic Parent + Active Memory; no partial promotion',
        'actor': {'python': cfg['actor_python'], 'model': cfg['actor_model'],
                  'base_url': cfg['actor_base_url'], 'request_parameters': cfg['call_config'],
                  'execution_protocol': execution_protocol(50), 'request_attempts': 3, 'strict_response': True},
        'environment': {'data_root': str(DATA_ROOT), 'dataset': 'json_2.1.1',
                        'versions': {'alfworld': '0.4.2', 'textworld': '1.7.0', 'numpy': '1.26.4', 'requests': '2.32.5'}},
        'module_input_limits': {'chars': cfg['max_input_chars'], 'utf8_bytes': cfg['max_input_bytes']},
        'llm_seed': None, 'note': 'seed=42 seeds the environment; official sequential batching uses no shuffle. LLM responses are not guaranteed reproducible.'}
    frozen(HERE/'config/protocol.json', protocol)
    # Evaluations use the same existing fixed-Skill runner, not legacy eval_test.py.
    common = {'tasks': items['test'], 'split': 'test', 'purpose': 'final',
        'actor': protocol['actor'], 'environment': protocol['environment'],
        'max_steps': 50, 'max_attempts_per_step': 3, 'strict_response': True,
        'success': 'environment won; technical/unknown outcomes invalidate complete evaluation',
        'expected_tasks': 134, 'protocol_file': str(HERE/'config/protocol.json')}
    for group in ['S0', 'S1']:
        ev = deepcopy(common)
        ev.update(group=group, skill_source={'kind': 'none'} if group == 'S0' else
                  {'kind': 'campaign_final_parent', 'campaign': str(CAMPAIGN)},
                  output_root=str(CAMPAIGN.parent/f'{group}_test'))
        frozen(HERE/f'config/{"no_skill" if group == "S0" else "v23"}_eval.json', ev)
    # No initializer, state.json, episode runner, network call or model call here.
    stats = {'counts': {'train': 39, 'selection': 18, 'optimization': 57, 'test': 134},
        'task_types': {k: dict(Counter(x['task_type'] for x in rows)) for k, rows in
                       [('train', items['train']), ('selection', items['val']), ('optimization', pool), ('test', items['test'])]},
        'duplicate_ids': 0, 'duplicate_games': 0, 'optimization_test_overlap': 0,
        'missing_games': [], 'public_skilladam_skillopt_local_equal': True}
    frozen(HERE/'data/verification.json', stats)
    completion = read(LIVE/'results/completion.json')['cost']
    summary = read(LIVE/'results/summary.json')
    totals = [summary['rounds'][r]['cost']['total_tokens_known'] for r in ['R01','R02']]
    # Actor totals computed from every actual transport attempt, never double-count final response.
    actor_rounds = []
    for rn in ['R01', 'R02']:
        total = 0
        for record in summary['rounds'][rn]['executions']:
            raw = read(record['path'])
            total += sum(a['usage']['total_tokens'] for s in raw['steps'] for a in s['transport_attempts'])
        actor_rounds.append(total)
    budget = {'optimization': {'unique_tasks': 57, 'parent_episodes_max': 57, 'candidate_episodes_max': 57,
        'episodes_max': 114, 'steps_per_episode_max': 50, 'actor_logical_requests_max': 5700,
        'actor_http_requests_max': 17100, 'llm_stages_per_full_round': 5, 'module_logical_requests_max': 30,
        'module_http_requests_max': 90, 'gate_llm_requests': 0, 'http_requests_max': 17190,
        'generated_tokens_max': 17190*16384},
        'test_per_group': {'tasks': 134, 'episodes_max': 134, 'actor_logical_requests_max': 6700,
                           'http_requests_max': 20100, 'generated_tokens_max': 20100*16384},
        'combined': {'episodes_max': 382, 'actor_steps_max': 19100, 'http_requests_max': 57390,
                    'generated_tokens_max': 57390*16384},
        'attempts_per_request': 3, 'max_output_tokens': 16384, 'timeout_seconds': 300,
        'historical_reference': {'source': str(LIVE/'results/completion.json'), 'actual_total_tokens': completion['total_tokens_known'],
            'optimization_linear_total_token_scenarios': [round(t/4*57) for t in totals],
            'test_per_group_linear_total_token_scenarios': [round(t/8*134) for t in actor_rounds],
            'method': 'Scale each historical 4-task round to 57 optimization cases; scale its 8 Actor episodes to each 134-task test. Includes recorded failures. Scenarios, not confidence intervals or upper bounds.'},
        'limits': ['Applies to initial run only. Explicit user resume permits a new bounded budget and may rerun partial episodes.',
                   'Output upper bound includes reasoning; prompt tokens are additional and have no single frozen total-token bound.',
                   'Historical linear estimates do not bound six-round Memory growth, longer Skills, changed batch size or stochastic reasoning.',
                   'Full Memory sources may exceed 300000 input characters or 400000 message bytes; stop without truncation or automatic budget increase.',
                   'No currency estimate; cache hits and provider billing are not equivalent to total-token counts.']}
    frozen(HERE/'config/budget.json', budget)
    return stats


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
