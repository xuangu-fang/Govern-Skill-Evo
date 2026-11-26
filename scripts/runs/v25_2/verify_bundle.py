"""Verify the published v25.2 run offline, optionally including local raw records."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench.legacy_archive import check_publications, read_records

from src.skill_evolution.v25_2 import evolution, preconditioner
from src.skill_evolution.v25_2.benchmark import using_benchmark
from src.skill_evolution.v25_2.benchmarks.spreadsheetbench import scoring
from src.skill_evolution.v25_2.cli import EXPERIMENT, adapter_for, read_config


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


@read_records
def verify(archive=False):
    config_dir = EXPERIMENT / 'config'
    results = EXPERIMENT / 'results'
    test_id = EXPERIMENT.name + '_test280'
    published = results / test_id
    config = read_config(config_dir / 'config.json')
    test_config = read_config(config_dir / 'evaluation/config.json')
    tasks = test_config['test_tasks']
    adapter = adapter_for(config)
    with using_benchmark(adapter):
        for cfg in (config, test_config):
            evolution.validate_config(cfg)
        from src.skill_evolution.v25_2 import diagnosis
        require(config['method']['diagnosis_version'] == diagnosis.PROMPT_VERSION, 'Wrong diagnosis version')
        require(adapter.resource('diagnosis.md').read_bytes() == (config_dir/'approved_prompts/diagnosis.md').read_bytes(),
                'Diagnosis prompt differs')
        method = config['method']
        version, prompt = preconditioner.prompt_for(method['memory_view'], method['preconditioner_contract'],
                                                   method['preconditioner_prompt'])
        require(version == preconditioner.CURRENT_UPDATE_PROMPT_VERSION, 'Wrong method version')
        require(prompt.read_bytes() == (config_dir / 'approved_prompts/preconditioner.md').read_bytes(),
                'Preconditioner prompt differs')
    require(test_config['test_tasks'] == config['test_tasks'] and len(set(tasks)) == 280, 'Test split differs')
    require((config_dir / 'evaluation/scoring.py').read_bytes() == Path(scoring.__file__).read_bytes(), 'Scorer differs')
    require(config['initial_skill']['text'] == (config_dir / 'initial_skill.md').read_text(), 'Initial Skill differs')
    final = (results / 'final_skill.md').read_bytes()
    check_publications(EXPERIMENT, final, Path if archive else None)
    require(final == (published / 'evaluated_skill.md').read_bytes(), 'Evaluated Skill differs')
    train = read(results / 'training_complete.json')
    require(train['status'] == 'complete' and train['rounds'] == len(config['batches']) == 8, 'Training receipt differs')
    receipt = read(results / 'test_complete.json')
    summary = read(published / 'summary.json')
    for key in ('status', 'completed', 'success', 'hard', 'per_cell_pass_rate'):
        require(receipt[key] == summary[key], 'Test receipt differs: ' + key)
    require(summary['status'] == 'complete' and summary['completed'] == len(tasks), 'Incomplete test')
    require(summary['success'] / len(tasks) == summary['hard'], 'Hard score differs')
    info = dict(rounds=train['rounds'], completed=summary['completed'], success=summary['success'])
    if archive:
        test = ROOT / summary['raw_summary']
        raw = read(test)
        rows = raw['tasks']
        require([r['task_id'] for r in rows] == tasks and sum(r['hard'] for r in rows) == summary['success'],
                'Raw test rows differ')
        for key in ('completed', 'success', 'hard', 'per_cell_pass_rate'):
            require(raw[key] == summary[key], 'Raw summary differs: ' + key)
        actual = read(test.parent / 'input.json')
        require([t['id'] for t in actual['tasks']] == tasks and actual['skill_text'].encode() == final,
                'Actual evaluation inputs differ')
        require(actual['actor_config'] == read(config_dir/'evaluation/config.json'), 'Raw evaluation config differs')
        campaign = ROOT / 'artifacts/methods/v25_2' / EXPERIMENT.name / 'campaign'
        state = read(campaign / 'state.json')
        require(state['next_round'] == 9 and (campaign / state['parent']).read_bytes() == final, 'Retained Skill differs')
        require(read(campaign / 'config.json') == read(config_dir / 'config.json'), 'Raw training config differs')
        for number in range(1, 9):
            result = read(campaign / 'rounds' / f'R{number:02}' / 'result.json')
            require(result['status'] == 'completed' and result['after']['next_round'] == number + 1, 'Round differs')
        for row in rows:
            old = Path(row['trajectory'])
            relative = old.relative_to(Path(actual['campaign']).parent / 'test')
            trajectory = read(test.parent / relative)
            require(trajectory['task']['id'] == row['task_id'] and trajectory['score']['hard'] == row['hard'],
                    'Trajectory differs: ' + row['task_id'])
        info['trajectories_verified'] = len(rows)
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='also read the original training and test records')
    print(json.dumps(verify(parser.parse_args().archive), indent=2))
