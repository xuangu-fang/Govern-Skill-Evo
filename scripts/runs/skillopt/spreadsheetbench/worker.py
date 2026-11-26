"""SpreadsheetBench actor process. Use the same Python environment as the v25.8 run."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.runs.v25_8.run_v25_8_train_test import pipeline
from src.skill_evolution.v25_3.baseline.benchmarks.spreadsheetbench import facts
from src.skill_evolution.v25_3.stages import read
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.storage import write_record


def rollout_case(task, skill, folder, config, *, generate=None):
    path = pipeline.actor.run(task, skill, folder / 'actor', config, generate=generate,
                              score=pipeline.scoring.score)
    record = read(path)
    require(record['task'] == task and record['skill'] == skill and
            record['protocol'] == config['actor_profile'] and record['model'] == config['actor_model']
            and record['executor'] == config['executor'], 'Saved Actor inputs changed')
    run, = facts.build_facts([record])['facts']['runs']
    conversation = list(run['initial']['messages'])
    for event in run['attempts']:
        conversation.append({'role': 'assistant', 'content': event['response']})
        conversation.append({'role': 'tool', 'content': json.dumps(event['execution'], ensure_ascii=False)})
        if event['feedback_to_actor']:
            conversation.append(event['feedback_to_actor'])
    conversation.append({'role': 'system', 'content': json.dumps(
        {'post_submission_outcome': run['outcome']}, ensure_ascii=False)})
    write_record(folder / 'conversation.json', conversation)
    score = record['score']
    return dict(id=task['dataset_id'], hard=score['hard'], soft=score['per_cell_pass_rate'],
                task_description=task['instruction'], instruction_type=task['instruction_type'],
                task_type='cell_level' if task['instruction_type'].startswith('Cell') else 'sheet_level',
                n_turns=record['code_attempts'], n_cells_total=score['total_cells'],
                n_cells_match=score['correct_cells'], per_cell_pass_rate=score['per_cell_pass_rate'],
                target_system_prompt=conversation[0]['content'],
                target_user_prompt=record['initial_messages'][-1]['content'])


def batch(directory, config):
    request = read(directory / 'binding.json')
    def one(key):
        task = config['task_items'][key]
        require(task['split'] in ('train', 'val'), 'Test task reached the training Actor')
        return rollout_case(task, request['skill'], directory / 'predictions' / task['dataset_id'], config)
    with ThreadPoolExecutor(max_workers=config['actor_max_workers']) as pool:
        rows = list(pool.map(one, request['tasks']))
    dest = directory / 'results.jsonl'
    tmp = dest.with_suffix('.tmp')
    tmp.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
    tmp.replace(dest)


def verify_slow_gate(campaign, epoch, val_ids):
    """Check the Gate receipt against the underlying 40 scored Selection trajectories."""
    folder = campaign / 'slow_update' / f'epoch_{epoch:02d}'
    result = read(folder / 'slow_result.json')
    candidate = folder / 'candidate_skill.md'
    if not candidate.exists():
        require(result['action'] == 'no_content', 'Missing slow-update candidate')
        return
    skill = candidate.read_text()
    selection = folder / 'selection_eval'
    if not (selection / 'results.jsonl').is_file():
        # The official trainer reuses a Selection score for an identical candidate.
        for binding in campaign.rglob('binding.json'):
            request = read(binding)
            if request['skill'] == skill and request['tasks'] == val_ids and (binding.parent / 'results.jsonl').is_file():
                selection = binding.parent
                break
    require(read(selection / 'binding.json') == {'skill': skill, 'tasks': val_ids}, 'Slow Gate inputs differ')
    rows = [json.loads(line) for line in (selection / 'results.jsonl').read_text().splitlines()]
    require([f"val:{row['id']}" for row in rows] == val_ids and len(val_ids) == 40,
            'Incomplete slow-update Selection')
    score = sum(row['hard'] for row in rows) / len(rows)
    previous = read(campaign / 'steps' / f'step_{2 * epoch:04d}' / 'step_record.json')['current_score']
    allowed = ('accept', 'accept_new_best') if score > previous else ('reject',)
    require(result['selection_hard'] == score and result['action'] in allowed,
            'Slow-update decision disagrees with Selection hard')


def test_best(root, cfg, *, generate=None):
    selected = read(root / 'selection.json')
    skill = (root / 'best_skill.md').read_text()
    from hashlib import sha256
    require(sha256(skill.encode()).hexdigest() == selected['sha256'], 'Selected Skill changed')
    folder = root / 'test'
    bundle = dict(campaign=str(root / 'campaign'), skill_text=skill, actor_config=cfg,
                  tasks=[cfg['task_items'][key] for key in cfg['test_tasks']], initial_reference=None,
                  evaluation_policy=f"SkillOpt Selection-Best, step {selected['best_step']}")
    def invoke(key, snapshot, dest, config):
        return pipeline.actor.run(config['task_items'][key], skill, dest, config,
                                  generate=generate, score=pipeline.scoring.score)
    with pipeline.using_benchmark(pipeline.SpreadsheetBenchAdapter()):
        return pipeline.evaluation.run(folder, runner=invoke, bundle=bundle,
                                       resume=(folder / 'input.json').exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['batch', 'test', 'verify'])
    parser.add_argument('root', type=Path)
    parser.add_argument('directory', type=Path, nargs='?')
    args = parser.parse_args()
    if args.action == 'verify':
        from scripts.runs.skillopt.spreadsheetbench.verify import verify_actor
        verify_actor(args.root)
    elif args.action == 'test':
        config = read(args.root / 'test_actor.json')
        val_ids = [key for key, row in config['task_items'].items() if row['split'] == 'val']
        for epoch in (2, 3, 4):
            verify_slow_gate(args.root / 'campaign', epoch, val_ids)
        test_best(args.root, config)
    else:
        config = read(args.root / 'train_actor.json')
        campaign = args.root / 'campaign'
        for epoch in (2, 3):
            if args.directory == campaign / 'steps' / f'step_{2 * epoch + 1:04d}' / 'rollout':
                val_ids = [key for key, row in config['task_items'].items() if row['split'] == 'val']
                verify_slow_gate(campaign, epoch, val_ids)
        batch(args.directory, config)
