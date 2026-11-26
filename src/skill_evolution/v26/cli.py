"""Explicit V26 Campaign and independent Test entry points."""
import argparse
import json
import os


def main(argv=None):
    parser = argparse.ArgumentParser(description='V26 OfficeQA Campaign and independent fixed-Test evaluation')
    sub = parser.add_subparsers(dest='command', required=True)
    status = sub.add_parser('status', help='Read progress and request accounting without provider access')
    status.add_argument('campaign')
    run = sub.add_parser('run', help='Execute or explicitly resume the configured Campaign')
    run.add_argument('campaign'); run.add_argument('--config', required=True)
    run.add_argument('--prepared-root', required=True); run.add_argument('--parsed-root', required=True)
    run.add_argument('--resume', action='store_true')
    run.add_argument('--validate-only', action='store_true',
                     help='Validate configuration and source inputs without credentials, requests or Campaign creation')
    run.add_argument('--archive-only', action='store_true',
                     help='Resume saved work only; never initialize request clients or issue new requests')
    run.add_argument('--actor-key-env'); run.add_argument('--method-key-env')
    evaluate = sub.add_parser('evaluate', help='Evaluate the fixed 172 Test cases independently of optimization')
    evaluate.add_argument('directory'); evaluate.add_argument('--actor-config', required=True)
    evaluate.add_argument('--prepared-root', required=True); evaluate.add_argument('--parsed-root', required=True)
    evaluate.add_argument('--resume', action='store_true')
    evaluate.add_argument('--task-output-limits', type=json.loads, help='Per-Test-ID output limits as a JSON object')
    evaluate.add_argument('--workers', type=int, choices=(4, 20))
    evaluate.add_argument('--actor-key-env', help='Required for new requests; omit only for archive recovery')
    skill = evaluate.add_mutually_exclusive_group(required=True)
    skill.add_argument('--skill'); skill.add_argument('--no-skill', action='store_true')
    report = sub.add_parser('report', help='Validate Test archives and regenerate reports without provider access')
    report.add_argument('directory')
    args = parser.parse_args(argv)
    if args.command == 'status':
        from .monitoring import status as get_status
        print(json.dumps(get_status(args.campaign), ensure_ascii=False, indent=2)); return
    if args.command in ('evaluate', 'report'):
        result = _evaluation(args)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return
    from .stages import read
    from .facts import require
    from .transport import HTTPGenerator
    from .benchmark import using_benchmark
    from .evolution import run_campaign
    from .benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
    from src.adapters.officeqa.runtime import Runtime
    from src.adapters.officeqa.transport import ChatTransport
    from .training import load_dataset
    if args.validate_only:
        require(not args.resume and not args.archive_only and not args.actor_key_env and not args.method_key_env,
                '--validate-only cannot resume or accept request credentials')
    elif args.archive_only:
        require(args.resume, '--archive-only requires --resume')
        require(not args.actor_key_env and not args.method_key_env,
                '--archive-only must not specify request credential options')
    else:
        require(args.actor_key_env and args.method_key_env,
                'Live Campaign execution requires both key options; use --resume --archive-only for saved work')
    config = read(args.config); actor = config['actor']
    require(actor['transport'] == 'direct_http', 'CLI run requires an explicit direct-HTTP Actor configuration')
    if args.archive_only:
        from pathlib import Path
        root = Path(args.campaign)
        require((root / 'state.json').is_file() and (root / 'config.json').is_file(),
                'Archive-only resume requires an existing initialized Campaign')
        require(config == read(root / 'config.json'), 'Archive configuration differs from frozen Campaign')
    def make_transport(metadata):
        if args.archive_only or args.validate_only:
            from .evaluation import ArchiveTransport
            return ArchiveTransport(metadata)
        return ChatTransport(endpoint=metadata['endpoint'], api_key=os.environ.get(args.actor_key_env),
            **{key: metadata[key] for key in ('model', 'max_completion_tokens', 'temperature',
                                          'reasoning_effort', 'reasoning_mode', 'token_limit_field')})
    transport = make_transport(actor)
    limits = config.get('actor_task_output_limits', {})
    require(isinstance(limits, dict), 'Invalid task output limits')
    adapter_type, options = OfficeQAEvidenceAdapter, {}
    if limits:
        from .benchmarks.officeqa.task_budget import TaskOutputBudgetAdapter
        adapter_type = TaskOutputBudgetAdapter
        options['task_transports'] = {task: make_transport({**actor, 'max_completion_tokens': limit})
                                      for task, limit in limits.items()}
    adapter = adapter_type(load_dataset(args.prepared_root, config.get('optimization_pool')),
                                     Runtime(args.parsed_root), transport,
                                     gate_metric=config['gate_metric'], **options)
    with using_benchmark(adapter):
        if args.validate_only:
            from .config import validate_config, REVIEW_DISABLED
            validate_config(config)
            snapshot = adapter.runtime_snapshot(config)
            result = {'status': 'configuration_validated', 'training_started': False, 'model_requests': 0,
                      'prepared_root': snapshot['prepared_root'], 'parsed_root': snapshot['parsed_root'],
                      'optimization_tasks': len(snapshot['tasks']), 'test_tasks': len(adapter.dataset.splits['test']),
                      'rounds': len(config['batches']), 'knowledge_review': config['method']['knowledge_review'],
                      'online_review_enabled': config['method']['knowledge_review'] != REVIEW_DISABLED,
                      'actor': actor, 'actor_task_output_limits': limits,
                      'task_actors': {task: adapter._adapter(task).transport.metadata()
                                     if limits else transport.metadata() for task in snapshot['tasks']},
                      'runtime_snapshot': snapshot}
        else:
            generate = None if args.archive_only else HTTPGenerator(os.environ.get(args.method_key_env))
            result = run_campaign(args.campaign, config=None if args.archive_only else config,
                                  resume=args.resume, generate=generate)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _evaluation(args):
    from pathlib import Path
    from .stages import read
    from .facts import require
    from .evaluation import ArchiveTransport, run_evaluation, report_evaluation
    from .benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter, SkillAdamEvidenceAdapter
    from src.adapters.officeqa.data import Dataset
    from src.adapters.officeqa.runtime import Runtime
    from src.adapters.officeqa.transport import ChatTransport
    if args.command == 'report':
        plan = read(Path(args.directory) / 'plan.json')
        actor = plan['runtime']['actor']
        prepared, parsed = plan['runtime']['prepared_root'], plan['runtime']['parsed_root']
        transport = ArchiveTransport(actor)
    else:
        actor = read(args.actor_config)
        require(actor['transport'] == 'direct_http', 'CLI evaluation requires direct-HTTP Actor configuration')
        prepared, parsed = args.prepared_root, args.parsed_root
        if args.actor_key_env:
            transport = ChatTransport(endpoint=actor['endpoint'], api_key=os.environ.get(args.actor_key_env),
                **{key: actor[key] for key in ('model', 'max_completion_tokens', 'temperature',
                                              'reasoning_effort', 'reasoning_mode', 'token_limit_field')})
            require(transport.metadata() == actor, 'Actor configuration differs from common execution policy')
        else:
            require(args.resume, 'New evaluation requires an explicit Actor key environment variable')
            transport = ArchiveTransport(actor)
    workers = getattr(args, 'workers', None)
    if workers is None and (args.command == 'report' or (args.resume and (Path(args.directory) / 'plan.json').is_file())):
        workers = read(Path(args.directory) / 'plan.json')['execution']['workers']
    workers = workers or 4
    adapter_type = SkillAdamEvidenceAdapter if workers == 20 else OfficeQAEvidenceAdapter
    dataset = Dataset(prepared)
    limits = getattr(args, 'task_output_limits', None)
    if args.command == 'report' or (args.resume and (Path(args.directory) / 'plan.json').is_file()):
        saved = read(Path(args.directory) / 'plan.json')['runtime'].get('actor_task_output_limits', {})
        require(limits is None or limits == saved, 'Test task output limits differ from saved plan')
        limits = saved
    options = {}
    if limits is not None:
        require(isinstance(limits, dict) and all(uid in dataset.splits['test'] and
                type(n) is int and n > 0 for uid, n in limits.items()), 'Invalid Test task output limits')
    if limits:
        from .benchmarks.officeqa.task_budget import ParallelTaskOutputBudgetAdapter
        adapter_type = ParallelTaskOutputBudgetAdapter
        options['task_transports'] = {uid: transport.with_output_limit(n) for uid, n in limits.items()}
    adapter = adapter_type(dataset, Runtime(parsed), transport, workers=workers, **options)
    if args.command == 'report':
        return report_evaluation(args.directory, adapter=adapter)
    return run_evaluation(args.directory, adapter=adapter, skill_file=args.skill, resume=args.resume)


if __name__ == '__main__':
    main()
