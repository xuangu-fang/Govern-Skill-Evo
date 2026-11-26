#!/usr/bin/env python3
"""Independent ALFWorld SkillOpt. Default/check/prepare are strictly offline."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.skillopt_alfworld_native.project import DEFAULT, check, prepare, read, write, require, sha


def run(root, *, resume=False):
    check(root)
    from dotenv import load_dotenv
    from src.skillopt_alfworld_native.actor import build_adapter
    from src.skillopt_alfworld_native.transport import provider, usage_summary
    from skillopt.engine.trainer import ReflACTTrainer
    cfg = read(root / 'skillopt.json')
    actor = read(root / 'actor.json')
    with (root / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        campaign = root / 'campaign'
        binding = {'manifest_sha256': sha(root / 'manifest.json'), 'test_roles': ['best']}
        if resume:
            require(read(campaign / 'run_binding.json') == binding, 'Resume binding changed')
            require(not (campaign / 'completion.json').exists(), 'Run is already complete')
            require((campaign / 'runtime_state.json').is_file(), 'No native checkpoint; no implicit restart')
        else:
            require(not campaign.exists(), 'Fresh run requires a new campaign directory')
        # Credentials are only read inside explicitly requested live execution.
        load_dotenv(ROOT / '.env', override=True)
        require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == actor['base_url'], 'Official route mismatch')
        require(bool(os.environ.get('OPENAI_API_KEY')), 'Missing API credential')
        for prefix in ('', 'OPTIMIZER_', 'TARGET_'):
            for suffix in ('MAX_ATTEMPTS', 'CONNECT_TIMEOUT_SECONDS'):
                os.environ.pop(prefix + 'OPENAI_COMPATIBLE_' + suffix, None)
        os.environ['ALFWORLD_DATA'] = actor['environment_root']
        write(campaign / 'run_binding.json', binding)
        try:
            with provider(root, api_key=os.environ['OPENAI_API_KEY']):
                summary = ReflACTTrainer(cfg, build_adapter(root)).train()
            require(summary['total_steps'] == 4 and summary['test_hard'] is not None,
                    'Training/Best Test did not complete')
            require(summary['baseline_test_hard'] is None and summary['final_test_hard'] is None,
                    'Unexpected Initial or Final Test')
            state = read(campaign / 'runtime_state.json')
            (campaign / 'final_skill.md').write_bytes(Path(state['current_skill_path']).read_bytes())
            write(campaign / 'completion.json', {'status': 'complete', 'test_roles': ['best'], 'test_count': 134})
        except BaseException as exc:
            write(campaign / 'stopped.json', {'status': 'stopped', 'error_type': type(exc).__name__})
            raise
        finally:
            write(campaign / 'request_usage.json', usage_summary(root))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'check', 'run'], nargs='?', default='check')
    parser.add_argument('--experiment', type=Path, default=DEFAULT)
    parser.add_argument('--start', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    root = args.experiment.resolve()
    require(not args.start or args.mode == 'run', '--start is only valid with run')
    require(not args.resume or (args.mode == 'run' and args.start), 'Resume requires run --start')
    if args.mode == 'prepare':
        result = prepare(root)
    elif args.mode == 'run' and args.start:
        run(root, resume=args.resume)
        result = {'status': 'complete', 'test_roles': ['best']}
    else:
        result = check(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
