"""Read-only final-test handoff: print commands, never execute an episode.

S1 refuses incomplete campaigns and resolves only the officially retained Parent.
The printed commands are for later explicit authorization, not preparation.
"""
import argparse
import json
from pathlib import Path
import shlex

from src.adapters.alfworld.run_task import SPLIT_ROOT
from src.adapters.alfworld.skill_runtime import execution_protocol
from src.skill_evolution.v23.evolution import final_parent, read

HERE = Path(__file__).resolve().parent


def commands(config, campaign=None):
    if config['actor']['execution_protocol'] != execution_protocol(config['max_steps']):
        raise ValueError('Frozen Actor execution protocol changed')
    if config['tasks'] != read(SPLIT_ROOT/'test/items.json'):
        raise ValueError('Frozen final Test mapping changed')
    if config['skill_source']['kind'] == 'none':
        skill = None
    elif config['skill_source']['kind'] == 'campaign_final_parent':
        root = Path(campaign or config['skill_source']['campaign'])
        if read(root/'initial_config.json') != read(HERE/'config/campaign.json'):
            raise ValueError('Final Skill comes from a different campaign configuration')
        skill = final_parent(root)
    else:
        raise ValueError('Unknown Skill source')
    result = []
    for item in config['tasks']:
        if not (Path(config['environment']['data_root'])/item['gamefile']).is_file():
            raise ValueError('Missing final Test gamefile')
        cmd = ['env', 'ALFWORLD_DATA='+config['environment']['data_root'],
               'OPENAI_BASE_URL='+config['actor']['base_url'], config['actor']['python'],
               '-m', 'src.adapters.alfworld.run_task_skill', '--split', 'test', '--purpose', 'final',
               '--task-id', item['id'], '--model', config['actor']['model'],
               '--max-steps', str(config['max_steps']), '--request-attempts', str(config['max_attempts_per_step']),
               '--strict-response', '--archive-responses', '--output-root',
               str(Path(config['output_root'])/item['id'].replace(':', '_'))]
        if skill is not None:
            cmd += ['--skill-file', str(skill)]
        result.append(cmd)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', required=True, choices=['S0', 'S1'])
    parser.add_argument('--shell', action='store_true', help='Print a stop-on-error shell script, without running it')
    args = parser.parse_args()
    cfg = read(HERE/'config'/('no_skill_eval.json' if args.group == 'S0' else 'v23_eval.json'))
    rows = commands(cfg)
    if args.shell:
        print('# NOT EXECUTED: requires explicit authorization to run final Test.\nset -e')
        print('cd '+shlex.quote(str(HERE.parents[3])))
        print('\n'.join(shlex.join(row) for row in rows))
    else:
        print(json.dumps(rows, indent=2))
