"""Unified v20 Pilot runner. ``run`` creates; ``resume`` reuses frozen config."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('run', 'resume'):
        command = commands.add_parser(name)
        command.add_argument('--output', type=Path, required=True)
        command.add_argument('--config', type=Path,
                             default=ROOT / 'experiments/configs/v20_pilot_001/config.json')
        command.add_argument('--round-limit', type=int,
                             help='continuation limit for an explicitly migrated Pilot')
    args = parser.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    from src.skill_evolution.benchmark_adapter_v20 import BenchmarkAdapterV20
    from src.skill_evolution.campaign_v20 import campaign_config_v20, run_campaign_v20
    from src.skill_evolution.runtime_v20 import (V20RuntimeTransports,
                                                  build_v20_round_factory,
                                                  build_v20_post_generation)
    from src.skill_evolution.edit_tracking_v19 import encode
    from src.skill_evolution.evolution_replay_v19 import _load
    from src.skill_evolution.run_control_v19 import recovery_scope

    output = args.output.resolve()
    adapter = BenchmarkAdapterV20.from_config(args.config)
    round_limit = args.round_limit if args.round_limit is not None else adapter.config['round_limit']
    config = campaign_config_v20(round_limit=round_limit,
                                 model=adapter.config['model'])
    if args.command == 'run':
        if output.exists():
            raise SystemExit('run requires a new output directory; use resume for an existing Pilot')
        run_id = output.name
        resume = False
    else:
        binding = _load(output / 'binding.json')
        run_id = binding['run_id']
        if binding['config'] != config:
            raise SystemExit('frozen v20 campaign config changed')
        resume = True
    transports = V20RuntimeTransports()
    with recovery_scope(output, resume):
        result = run_campaign_v20(
            output=output, run_id=run_id, initial_skill=adapter.initial_skill,
            round_factory=build_v20_round_factory(benchmark=adapter, transports=transports),
            post_generation=build_v20_post_generation(benchmark=adapter),
            config=config, resume=resume)
    print(encode(result), flush=True)


if __name__ == '__main__':
    main()
