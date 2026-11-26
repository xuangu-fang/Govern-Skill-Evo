"""Explicit v28 validation/run/Test commands; importing never reads credentials."""
import argparse
import json
import os
from pathlib import Path
import sys


def main(argv=None):
    from . import profiles
    parser = argparse.ArgumentParser(description='v28 SearchQA; explicit execution only')
    parser.add_argument('--data-root')
    sub = parser.add_subparsers(dest='command', required=True)
    configure = sub.add_parser('configure', help='Build configuration without starting a campaign')
    configure.add_argument('--initial-skill', required=True)
    configure.add_argument('--output', required=True)
    configure.add_argument('--batch-size', type=int, choices=(15, 30), default=15)
    configure.add_argument('--profile', choices=profiles.SUPPORTED, default=profiles.V28)
    configure.add_argument('--context-window-tokens', type=int)
    validate = sub.add_parser('validate', help='Validate configuration with no credentials or requests')
    validate.add_argument('--config', required=True)
    run = sub.add_parser('run')
    run.add_argument('directory'); run.add_argument('--config', required=True)
    run.add_argument('--resume', action='store_true'); run.add_argument('--archive-only', action='store_true')
    run.add_argument('--max-rounds', type=int)
    evaluate = sub.add_parser('evaluate')
    evaluate.add_argument('directory'); evaluate.add_argument('--skill', required=True)
    evaluate.add_argument('--resume', action='store_true')
    evaluate.add_argument('--config', help='Training configuration defining the Actor and data profile')
    for command in (run, evaluate):
        command.add_argument('--api-key-env', default='OPENAI_API_KEY')
    report = sub.add_parser('report'); report.add_argument('directory')
    report.add_argument('--config', help='Training configuration defining the Actor and data profile')
    audit = sub.add_parser('audit'); audit.add_argument('directory')
    args = parser.parse_args(argv)
    if Path(sys.prefix).name != 'SearchQA':
        parser.error('Use conda environment SearchQA')
    from .benchmarks.searchqa.dataset import SearchQADataset
    from .benchmarks.searchqa.adapter import SearchQAActorAdapter
    from .benchmarks.searchqa.actor import ChatTransport
    from .benchmarks.searchqa import protocol as p
    from .campaign import CampaignAdapter
    from .config import campaign_config, validate_config
    from .stages import read, freeze
    from .evolution import run_campaign, final_parent
    from .evaluation import run_evaluation, report_evaluation
    from src.skill_evolution.v27.transport import HTTPGenerator
    live = args.command in ('run', 'evaluate') and not getattr(args, 'archive_only', False)
    key = os.environ.get(args.api_key_env) if live else None
    if live:
        p.nonempty_text(key, 'Explicit API key environment variable')
    selected = read(args.config) if getattr(args, 'config', None) else None
    if selected is None and args.command == 'audit':
        selected = read(Path(args.directory) / 'config.json')
    batch_size = len(selected['batches'][0]) if selected else getattr(args, 'batch_size', 15)
    profile = selected['method']['version'] if selected else getattr(args, 'profile', profiles.V28)
    if selected is None and (args.command == 'report' or
                             args.command == 'evaluate' and args.resume):
        archived_plan = read(Path(args.directory) / 'plan.json')
        archived_actor = archived_plan['actor']
        profile = archived_plan.get('method_profile', profiles.V28)
        p.background(archived_actor)
        batch_size = 30 if archived_actor['max_tokens'] == 32768 else 15
    profiles.check(profile)
    dataset_options = {'verify_hashes': False} if profile == profiles.V28_1 else {}
    dataset = SearchQADataset(args.data_root, batch_size=batch_size, **dataset_options)
    actor = SearchQAActorAdapter(dataset, ChatTransport(key, metadata=p.actor_config(batch_size),
                                 retry_http_520=profile == profiles.V28_1) if live else None,
                                 profile=profile)
    adapter = CampaignAdapter(actor)
    with adapter.using():
        if selected is not None:
            validate_config(selected)
        if args.command == 'configure':
            skill = Path(args.initial_skill).resolve()
            config = campaign_config(adapter, initial_skill={'source': str(skill), 'text': skill.read_bytes().decode('utf-8')},
                                     context_window_tokens=args.context_window_tokens)
            validate_config(config); freeze(args.output, config)
            result = {'config': str(Path(args.output).resolve()), 'campaign_created': False, 'model_requests': 0}
        elif args.command == 'validate':
            validate_config(read(args.config))
            result = {'valid': True, 'campaign_created': False, 'model_requests': 0}
        elif args.command == 'run':
            if args.archive_only:
                p.require(args.resume and (Path(args.directory) / 'state.json').exists(), 'Archive-only requires existing campaign and resume')
            result = run_campaign(args.directory, config=read(args.config), generate=HTTPGenerator(key) if live else None,
                                  resume=args.resume, max_rounds=args.max_rounds)
        elif args.command == 'audit':
            result = {'final_parent': str(final_parent(args.directory)), 'model_requests': 0}
        elif args.command == 'evaluate':
            result = run_evaluation(args.directory, adapter=actor, skill_file=args.skill, resume=args.resume)
        else:
            result = report_evaluation(args.directory, adapter=actor)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
