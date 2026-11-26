#!/usr/bin/env python3
"""Explicit DeepSeek configuration over the unchanged native SkillAdam optimizer."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.runs.run_v26_pilot import read_credentials
from src.adapters.officeqa import launchers as launch
from skilladam.backends.openai_compatible import OpenAICompatibleConfig, create_generation_transport
from skilladam.execution.contracts import BackendContext, BackendInit


def prepare(config, directory):
    identity = config['launch_adapter']
    launch.require(identity == {'path': str(Path(__file__).resolve()),
                               'sha256': launch.digest(Path(__file__))}, 'Launch adapter identity changed')
    launch.require(config['method'] == 'skilladam', 'SkillAdam configuration required')
    optimizer = config['optimizer']
    launch.require(optimizer['thinking'] == {'type': 'enabled'}, 'Explicit thinking configuration required')
    launch.require(optimizer['backend_config']['reasoning_mode'] == 'top_level', 'DeepSeek requires top-level reasoning effort')
    launch.require(optimizer['backend_config']['token_limit_field'] == 'max_tokens', 'DeepSeek requires max_tokens')
    return launch.prepare(config, directory)


def generation_backend(config, directory, api_key, *, client_factory=None):
    """Add only the provider thinking flag; retain native SDK retries and generation parsing."""
    optimizer = config['optimizer']
    settings = OpenAICompatibleConfig.from_mapping(optimizer['backend_config'])
    native = launch.adam_config(launch._fixed(config['native'], {
        'benchmark': 'officeqa', 'split': 'train', 'validation_split': 'train', 'scope': None}))
    context = BackendContext('officeqa', 'skilladam', optimizer['model'],
                             optimizer['reasoning_effort'], config.get('workers', launch.SkillAdamEvidenceAdapter.train_workers), native.seed)
    if client_factory is None:
        from openai import OpenAI
        client_factory = OpenAI

    def factory(**options):
        client = client_factory(**options)
        original = client.chat.completions.create

        def create(**payload):
            extra = dict(payload.pop('extra_body', {}))
            extra['thinking'] = dict(optimizer['thinking'])
            return original(**payload, extra_body=extra)

        client.chat.completions.create = create
        return client

    return create_generation_transport(
        BackendInit(Path(config['parsed_root']), Path(directory) / 'native',
                    optimizer['backend_config'], context), config=settings,
        environ={settings.api_key_env: api_key, settings.base_url_env: optimizer['base_url']},
        client_factory=factory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'train'))
    parser.add_argument('directory'); parser.add_argument('--config', required=True)
    parser.add_argument('--env-file', default=str(ROOT / '.env'))
    parser.add_argument('--start', action='store_true'); parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    config = launch.read(args.config)
    plan = prepare(config, args.directory)[0]
    if args.command == 'preflight':
        print(json.dumps({'status': 'passed', 'train_cases': len(plan['train_ids']),
                          'native_config': plan['native_config'], 'actor': plan['actor'],
                          'optimizer': config['optimizer'], 'requests': 0}, indent=2))
        return
    launch.require(args.start, 'Training requires --start')
    credentials = read_credentials(args.env_file)
    base = credentials.get('OPENAI_BASE_URL', '').rstrip('/')
    launch.require(base == config['optimizer']['base_url'].rstrip('/') and
                   plan['actor']['endpoint'] == base + '/chat/completions', 'Endpoint differs from selected env file')
    key_name = 'OFFICEQA_SKILLADAM_ACTOR_KEY'
    previous = os.environ.get(key_name)
    os.environ[key_name] = credentials['OPENAI_API_KEY']
    try:
        backend = generation_backend(config, args.directory, credentials['OPENAI_API_KEY'])
        result = launch.train(config, args.directory, actor_key_env=key_name,
                              resume=args.resume, optimizer_backend=backend)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if previous is None:
            os.environ.pop(key_name, None)
        else:
            os.environ[key_name] = previous


if __name__ == '__main__':
    main()
