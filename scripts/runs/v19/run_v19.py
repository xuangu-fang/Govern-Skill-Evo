"""Unified current-v19 runner. run creates; resume reuses stored configuration."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'external/tau2-bench/src')]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run', help='Start a NEW campaign; invokes real models')
    run.add_argument('--config', type=Path, required=True, help='JSON: mode (pilot/formal), max_workers (1..32)')
    run.add_argument('--output', type=Path, required=True)
    resume = commands.add_parser('resume', help='Continue a campaign created by this entrypoint')
    resume.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    from src.skill_evolution.v19.campaign_v19 import campaign_config, run_campaign_v19
    from src.skill_evolution.v19.evolution_benchmark_v19 import BenchmarkEvolutionV19
    from src.skill_evolution.v19.monitor_campaign_v19 import BenchmarkMonitorV19
    from src.skill_evolution.v19.evolution_replay_v19 import _load
    from src.skill_evolution.v19.memory_store_v19 import require
    from src.skill_evolution.v19.edit_tracking_v19 import encode
    from src.skill_evolution.v19.run_control_v19 import recovery_scope
    output = args.output.resolve()
    entrypoint = {'protocol':'unified_run_v19.1', 'generation':'local', 'attribution':'pair'}
    if args.command == 'run':
        require(not output.exists(), 'run requires a new output directory; use resume for an existing run')
        user = _load(args.config)
        require(type(user) is dict and set(user)=={'mode','max_workers'} and user['mode'] in ('pilot','formal'),
                'config must contain exactly mode: pilot/formal and max_workers: 1..32')
        config = campaign_config(pilot=user['mode']=='pilot', max_workers=user['max_workers'],
                                 generation_protocol='local', attribution_protocol='pair')
        run_id = output.name
    else:
        bound = _load(output/'binding.json')
        require(bound.get('entrypoint')==entrypoint,
                'not a unified-entry campaign; historical Pilot requires explicit migration')
        config, run_id = bound['config'], bound['run_id']
    recovery = None
    if args.command == 'resume' and (output/'migration.json').exists():
        from src.skill_evolution.v19.memory_restart_v19 import MemoryRestart
        if _load(output/'migration.json')['schema_version']=='semantics_migration_v19.1':
            from src.skill_evolution.v19.semantics_migration_v19 import SemanticsMigration
            recovery = SemanticsMigration(output/'migration.json')
        else:
            recovery = MemoryRestart(output/'migration.json')
    evolution = BenchmarkEvolutionV19(source_recovery=recovery) if recovery else BenchmarkEvolutionV19()
    monitor = BenchmarkMonitorV19(source_recovery=recovery) if recovery else BenchmarkMonitorV19()
    initial = (evolution.freeze/'S0.md').read_bytes().decode('utf-8')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env', override=True)
    from loguru import logger
    logger.remove(); logger.add(sys.stderr, level='WARNING')
    with recovery_scope(output, args.command=='resume'):
        result = run_campaign_v19(output=output, config=config, run_id=run_id, initial_skill=initial,
            evolution_backend=evolution, monitor_backend=monitor, resume=args.command=='resume', entrypoint=entrypoint, source_recovery=recovery)
    print(encode(result), flush=True)


if __name__ == '__main__':
    main()
