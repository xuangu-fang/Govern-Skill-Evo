"""Offline preflight by default; train and test are explicit opt-in commands."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
from src.adapters.docvqa import skilladam as m


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'train', 'test'), nargs='?', default='preflight')
    parser.add_argument('--config', default=str(m.DEFAULT_CONFIG))
    parser.add_argument('--output')
    parser.add_argument('--campaign', help='Completed training directory for Test')
    parser.add_argument('--env-file', default=str(ROOT / '.env'))
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    if Path(sys.prefix).name != 'DocVQA':
        parser.error('Use the independent DocVQA conda environment')
    prepared = m.prepare(args.config)
    cfg, dataset, _, native, context = prepared
    if args.command == 'preflight':
        print(json.dumps({'status': 'ready_offline', 'optimization_count': len(dataset.splits['train']),
            'test_count': len(dataset.splits['test']), 'batch_sizes': list(map(len, dataset.batches)),
            'actor_max_tokens': cfg['actor']['max_tokens'], 'optimizer_max_tokens': 16384,
            'gate': 'SkillAdam DocVQA v2', 'stage0': False, 'model_requests': 0}, indent=2))
        return
    if not args.output or (args.command == 'test' and not args.campaign):
        parser.error('--output is required; test also requires --campaign')
    output = Path(args.output).resolve()
    allowed = ROOT / ('experiments/baselines/docvqa_skilladam' if args.command == 'train'
                      else 'experiments/evaluations/docvqa_skilladam')
    if not output.is_relative_to(allowed) or output == allowed:
        parser.error(f'Use a dedicated output directory under {allowed}')
    # Reuse v29 credential loading and endpoint checks, without reading .env in preflight.
    from scripts.runs.run_v29_pilot import read_credentials
    credentials = read_credentials(args.env_file, {'actor': cfg['actor'], 'module_calls': {}})
    transport = m.actor.ChatTransport(credentials['OPENAI_API_KEY'])
    if args.command == 'train':
        generation = m.generation_transport(cfg, dataset, context, output / 'execution', environ=credentials)
        result = m.run_training(output, prepared, actor_transport=transport, generation=generation, resume=args.resume)
    else:
        result = m.run_test(args.campaign, output, prepared, actor_transport=transport, resume=args.resume)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
