#!/usr/bin/env python3
"""Run the shared Actor in its original Python environment, not SkillOpt's."""
import argparse
from copy import deepcopy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench import actor, facts, scoring
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from repair_spreadsheetbench_output_submission import execute_checked


def convert(record):
    """Adapt audited execution evidence to native SkillOpt reflection files."""
    run = facts.build_facts([record])['facts']['runs'][0]
    conversation = deepcopy(record['initial_messages'])
    for event in run['attempts']:
        conversation.append({'role': 'assistant', 'content': event['response']})
        conversation.append({'role': 'tool', 'content': json.dumps({
            'executed_code': event['executed_code'], 'execution': event['execution'],
            'executed': event['executed'], 'request_context': event['request_context']}, ensure_ascii=False)})
        if event['feedback_to_actor'] is not None:
            conversation.append(event['feedback_to_actor'])
    conversation.append({'role': 'system', 'content': json.dumps({
        'post_execution_outcome_not_actor_feedback': run['outcome']}, ensure_ascii=False)})
    task, score = record['task'], record['score']
    row = {'id': task['dataset_id'], 'hard': score['hard'], 'soft': score['per_cell_pass_rate'],
           'per_cell_pass_rate': score['per_cell_pass_rate'], 'task_description': task['instruction'],
           'task_type': 'cell_level' if task['instruction_type'].startswith('Cell') else 'sheet_level',
           'instruction_type': task['instruction_type'], 'n_turns': record['code_attempts'],
           'fail_reason': '' if score['hard'] else record['termination'],
           'n_cells_total': score['total_cells'], 'n_cells_match': score['correct_cells'],
           'target_system_prompt': record['initial_messages'][0]['content'],
           'target_user_prompt': record['initial_messages'][-1]['content']}
    return row, conversation


def run_task(directory, *, generate=None):
    request = ev.read(directory / 'input.json')
    cfg, key, skill = request['shared'], request['task'], request['skill']
    adapter = SpreadsheetBenchAdapter()
    path = actor.run(cfg['task_items'][key], skill, directory / 'actor', cfg,
                     generate=generate, execute=execute_checked)
    record = adapter.check_record(ev.read(path), key, skill, cfg)
    row, conversation = convert(record)
    ev.save(directory / 'conversation.json', conversation)
    ev.save(directory / 'native_result.json', row)
    ev.save(directory / 'usage.json', ev.cost_summary(directory / 'actor'))
    return row


def check(experiment):
    cfg = ev.read(experiment / 'shared_config.json')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    with using_benchmark(SpreadsheetBenchAdapter()):
        ev.validate_config(cfg)
        ev.check_live_environment(cfg)  # Checks local route/key presence only; no API call.
        runtime = ev.runtime_snapshot(cfg)
    reference = ev.read(experiment / 'references.json')
    if runtime != ev.read(Path(reference['v25_test']) / 'runtime.json'):
        raise ValueError('Docker runtime differs from completed Test')
    import importlib.metadata as metadata
    checks = []
    for task in cfg['task_items'].values():
        if not Path(task['input_path']).is_file():
            raise ValueError('Missing input: ' + task['id'])
        result = scoring.score(task['answer_path'], task['answer_path'], task['answer_region'], cfg['actor_profile'])
        if result['hard'] != 1 or result['total_cells'] <= 0:
            raise ValueError('Invalid scoring metadata: ' + task['id'])
        checks.append({'task': task['id'], 'cells': result['total_cells']})
    return {'status': 'passed', 'python': sys.executable, 'runtime': runtime,
            'packages': {n: metadata.version(n) for n in ('openpyxl', 'pandas', 'numpy', 'requests', 'python-dotenv')},
            'scoring_self_checks': checks, 'model_requests': 0, 'benchmark_rollouts': 0,
            'credential_presence_and_route': 'passed', 'live_api_connectivity': 'not_tested'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'actor', 'cost'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.action == 'check':
        print(json.dumps(check(args.directory), ensure_ascii=False))
    elif args.action == 'cost':
        print(json.dumps(ev.cost_summary(args.directory), ensure_ascii=False))
    else:
        run_task(args.directory)
