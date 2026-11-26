"""Explicit independent OfficeQA v26.2 train/test; no automatic Test or restart."""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam'), str(ROOT / 'external/SkillOpt')]

from src.skill_evolution.v26.evaluation import ArchiveTransport
from src.skill_evolution.v26.transport import HTTPGenerator
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26_2.campaign import CampaignAdapter
from src.skill_evolution.v26_2.dataset import OfficeQADataset
from src.skill_evolution.v26_2 import config as settings, evolution as ev, protocol as p
from src.skill_evolution.v26_2.actor_io import read_skill
from src.skill_evolution.v26_2.evaluation import prepare_test, run_test
from src.skill_evolution.v26_2 import reporting


def bind(config, *, actor_key=None):
    def transport(metadata):
        if actor_key is None: return ArchiveTransport(metadata)
        result = ChatTransport(endpoint=metadata['endpoint'], api_key=actor_key,
            **{k: metadata[k] for k in ('model', 'max_completion_tokens', 'temperature',
                                      'reasoning_effort', 'reasoning_mode', 'token_limit_field')})
        p.require(result.metadata() == metadata, 'Actor configuration differs')
        return result
    return CampaignAdapter(OfficeQADataset(ROOT / config['prepared_root']), Runtime(ROOT / config['parsed_root']),
        transport(config['actor']), task_transports={task: transport({**config['actor'],
        'max_completion_tokens': limit}) for task, limit in config['actor_task_output_limits'].items()})


def run_training(directory, config, *, generate=None, resume=False):
    root = Path(directory).resolve()
    settings.validate_config(config, executable=True)
    from src.skill_evolution.v26_2.telemetry import invocation
    with invocation(root, 'training'):
        result = ev.run_campaign(root, config=config, generate=generate, resume=resume)
    ev.require(result['status'] == 'complete', 'Training did not complete')
    final = ev.final_parent(root)
    ev.freeze_text(root / 'final_skill.md', read_skill(final))
    rounds = reporting.training_rounds(root)
    new_combinations = sum(r.get('selected_execution_source') is None for r in rounds)
    summary = {'status': 'complete', 'method': settings.METHOD_VERSION,
               'rounds_completed': len(config['batches']), 'optimization_count': sum(map(len, config['batches'])),
               'state': result['state'], 'selected_skill': str(final.relative_to(root)),
               'test_started': False, 'rounds': rounds, 'new_combinations': new_combinations,
               'new_combination_fraction': new_combinations / len(rounds), 'cost': reporting.costs(root)}
    ev.freeze(root / 'training_summary.json', summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('train', 'test'))
    parser.add_argument('campaign')
    parser.add_argument('--config')
    parser.add_argument('--output')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--archive-only', action='store_true')
    parser.add_argument('--actor-key-env')
    parser.add_argument('--method-key-env')
    args = parser.parse_args(argv)
    if args.command == 'train':
        ev.require(args.config is not None or args.resume, 'Fresh training requires --config')
        ev.require(args.output is None, '--output is Test-only')
    else:
        ev.require(args.config is None and bool(args.output), 'Test uses saved config and requires --output')
    if args.validate_only or args.archive_only:
        ev.require(not args.actor_key_env and not args.method_key_env, 'Offline mode accepts no credential options')
        ev.require(not args.archive_only or args.resume, 'Archive recovery requires --resume')
    else:
        ev.require(bool(args.actor_key_env) and (args.command == 'test' or bool(args.method_key_env)),
                   'Live execution requires explicit credential environment variable names')
    config = ev.read(args.config or Path(args.campaign) / 'config.json')
    # Read-only preflight precedes all credential access and execution.
    method = bind(config)
    with method.using():
        settings.validate_config(config, executable=True)
        for tid in method.dataset.splits['train'] + method.dataset.splits['test']:
            method.runtime.prepare(method.dataset.case(tid), None)
        test = prepare_test(args.campaign, args.output) if args.command == 'test' else None
        if args.validate_only:
            print(json.dumps({'status': 'valid', 'method': settings.METHOD_VERSION,
                  'optimization_count': len(method.dataset.splits['train']), 'test_count': len(method.dataset.splits['test']),
                  'batch_sizes': list(map(len, config['batches'])), 'model_requests': 0,
                  'training_started': False, 'test_started': False}))
            return
    if args.archive_only:
        ev.require((Path(args.campaign) / 'state.json').is_file(), 'Archive recovery needs an existing Campaign')
        generator = None
    else:
        key = os.environ.get(args.actor_key_env)
        ev.require(bool(key), 'Missing Actor credential')
        method = bind(config, actor_key=key)
        generator = HTTPGenerator(os.environ.get(args.method_key_env)) if args.command == 'train' else None
    with method.using():
        result = (run_training(args.campaign, config, generate=generator, resume=args.resume)
                  if args.command == 'train' else run_test(args.campaign, args.output, resume=args.resume))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
