"""Run the v24.5 ALFWorld prompts with the retained v24.4 campaign and Test."""
import argparse
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
import subprocess
import sys
from time import sleep

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.shared.offline_records import offline_records
from src.skill_evolution.v24_2 import storage
from src.skill_evolution.v24_2.storage import read, save
from src.skill_evolution.v24_4 import campaign, stages

PROMPTS = ROOT / 'src/skill_evolution/v24_5/prompts'
TEST = ROOT / 'scripts/runs/v24_4/run_v24_4_test.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--evaluation', type=Path, required=True)
    offline = parser.add_mutually_exclusive_group()
    offline.add_argument('--read-archive', action='store_true', help='verify all receipts of a completed Test')
    offline.add_argument('--validate-only', action='store_true', help='check the published Test inputs offline')
    args = parser.parse_args()
    training = resolve_experiment_path(args.campaign.resolve())
    evaluation = resolve_experiment_path(args.evaluation.resolve())
    if evaluation.is_relative_to(training) or training.is_relative_to(evaluation):
        parser.error('Training and Test need separate directories')
    read_finished = args.read_archive or (evaluation / 'summary.json').exists()
    context = offline_records('alfworld', storage) if args.validate_only or read_finished else nullcontext()
    with context:
        config = read(resolve_experiment_path(args.config.resolve()))
        if config.get('prompt_revision') != 'v24.5' or config.get('method') != campaign.VERSION:
            parser.error('Expected the v24.5 training configuration')
        if (training / 'config.json').exists() and config != read(training / 'config.json'):
            parser.error('Campaign configuration differs')
    command = [sys.executable, str(TEST), '--campaign', str(training), '--evaluation', str(evaluation)]
    if args.validate_only:
        subprocess.run(command + ['--validate-only'], check=True)
        return
    if read_finished:
        subprocess.run(command + ['--read-archive'], check=True)
        return

    prompts = {name: (PROMPTS / f'{name}.md').read_text()
               for name in ('diagnosis', 'preconditioner', 'editor', 'replay')}
    launch = training / 'launch'

    def status(phase, **details):
        save(launch / 'status.json', dict(phase=phase, at=datetime.now().astimezone().isoformat(), **details))

    phase = 'training'
    try:
        stages.system_prompt = prompts.__getitem__
        state = campaign.prepare(training, config)
        while state['next_round'] <= len(config['batches']):
            status(phase, round=state['next_round'])
            state = campaign.run_round(training)
        campaign.run_round(training)
        phase = 'test134'
        for attempt in range(1, 4):
            status(phase, attempt=attempt)
            resume = ['--resume'] if (evaluation / 'input.json').exists() else []
            with (launch / 'test134.log').open('a+') as log:
                start = log.tell()
                result = subprocess.run(command + resume, stdout=log, stderr=subprocess.STDOUT)
                if result.returncode == 0:
                    break
                log.seek(start)
                if attempt == 3 or 'Incomplete Actor task' not in log.read()[-2000:]:
                    raise RuntimeError('Test stopped; see test134.log')
            sleep(45)
        result = read(evaluation / 'summary.json')
        status('completed', completed=result['completed'], success=result['success'])
    except BaseException as exc:
        status('stopped', stage=phase, error_type=type(exc).__name__, message=str(exc))
        raise


if __name__ == '__main__':
    main()
