"""Explicit full-training and final-Test entrypoints for the fixed DocVQA split."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from scripts.runs.run_v29_pilot import read_credentials
from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.transport import HTTPGenerator
from src.skill_evolution.v29 import evolution as ev
from src.skill_evolution.v29.config import validate_config
from src.skill_evolution.v29.campaign import CampaignAdapter
from src.skill_evolution.v29.benchmarks.docvqa.actor import ChatTransport, locked
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from src.skill_evolution.v29.benchmarks.docvqa.scoring import summarize_scores
from src.skill_evolution.v29.benchmarks.docvqa import prompting


def run_training(directory, config, *, generate, resume=False):
    root = Path(directory).resolve()
    ev.require(resume == (root / 'state.json').exists(),
               'Use --resume only for an existing Campaign')
    validate_config(config, executable=True)
    result = ev.run_campaign(root, config=config, generate=generate, resume=resume,
        hook=lambda stage: print(f'{ev.now()} R{ev.read(root / "state.json")["next_round"]:02} {stage}', flush=True))
    ev.require(result['status'] == 'complete', 'Training did not complete')
    final = ev.final_parent(root)
    ev.require(final is not None, 'Completed DocVQA Campaign has no final Skill')
    ev.freeze_text(root / 'final_skill.md', final.read_text(encoding='utf-8'))
    summary = {'status': 'complete', 'rounds_completed': len(config['batches']),
               'optimization_count': sum(map(len, config['batches'])),
               'state': result['state'], 'selected_skill': str(final.relative_to(root)),
               'exported_skill': str(root / 'final_skill.md'), 'test_started': False}
    ev.freeze(root / 'training_summary.json', summary)
    return summary


def run_test(campaign, directory, *, resume=False):
    campaign = Path(campaign).resolve(); root = Path(directory).resolve()
    protected = Path(current().dataset.root).resolve()
    ev.require(not root.is_relative_to(campaign) and not campaign.is_relative_to(root)
               and not root.is_relative_to(protected) and not protected.is_relative_to(root),
               'Test output must be separate from Campaign and source data')
    # A completed, revalidated final Parent is required before any Test request.
    final = ev.final_parent(campaign)
    ev.require(final is not None, 'Missing final Skill')
    tasks = list(current().dataset.splits['test'])
    actor = current().actor_adapter
    with locked(root):
        ev.require(resume == (root / 'evaluation.json').exists(),
                   'Use --resume only for an existing Test evaluation')
        ev.freeze(root / 'evaluation.json', {
            'campaign': str(campaign), 'selected_skill': str(final),
            'skill': final.read_text(encoding='utf-8'), 'tasks': tasks,
            'actor': actor.transport.metadata(), 'workers': actor.test_workers})
        ev.freeze_text(root / 'skill.md', final.read_text(encoding='utf-8'))
        records = actor.actor_batch(tasks, root / 'skill.md', root / 'runs',
                                   {'split': 'test', 'role': 'evaluation'}, final=True)
        metrics = summarize_scores([
            {'task_id': r['task_id'], 'metrics': r['execution']['metrics']} for r in records], tasks)
        summary = {'status': 'complete', 'campaign': str(campaign), 'skill': str(root / 'skill.md'),
                   **metrics, 'api_requests': sum(r['execution']['api_requests'] for r in records)}
        ev.freeze(root / 'summary.json', summary)
        return summary


def main(argv=None, *, adapter_type=None, default_config=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('train', 'test'))
    parser.add_argument('campaign')
    parser.add_argument('--config', default=str(default_config or ROOT / 'experiments/configs/v29_docvqa_optimization160.json'))
    parser.add_argument('--output', help='Separate Test output directory')
    parser.add_argument('--env-file', default=str(ROOT / '.env'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    config = ev.read(args.config if args.command == 'train' else Path(args.campaign) / 'config.json')
    actor = DocVQAActorAdapter(DocVQADataset())
    actor.workers = 15  # Test retains the agreed upper bound of 60 workers.
    with (adapter_type or CampaignAdapter)(actor).using():
        validate_config(config, executable=True)
        # Validate every selected prompt before credentials or any Actor request.
        for name in prompting.PROMPT_VERSIONS:
            prompting.render(name, config['actor'])
        if args.command == 'test':
            ev.require(bool(args.output), 'Test requires --output')
        if args.validate_only:
            print(json.dumps({'status': 'valid', 'batch_sizes': list(map(len, config['batches'])),
                              'method': config['method']['version'], 'prompts': config['method']['prompts'],
                              'train_workers': actor.workers, 'test_workers': actor.test_workers,
                              'actor_max_tokens': config['actor']['max_tokens'],
                              'method_max_tokens': {k: v['max_tokens'] for k, v in config['module_calls'].items()}}))
            return
        credentials = read_credentials(args.env_file, config)
        actor.transport = ChatTransport(credentials['OPENAI_API_KEY'])
        if args.command == 'train':
            result = run_training(args.campaign, config,
                generate=HTTPGenerator(credentials['OPENAI_API_KEY']), resume=args.resume)
        else:
            result = run_test(args.campaign, args.output, resume=args.resume)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
