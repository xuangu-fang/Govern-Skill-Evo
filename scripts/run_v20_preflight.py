"""Run the frozen v20 Pilot benchmark preflight without model rollouts."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path,
                        default=ROOT / 'experiments/configs/v20_pilot_001/config.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    from src.skill_evolution.benchmark_adapter_v20 import BenchmarkAdapterV20
    from src.skill_evolution.edit_tracking_v19 import encode

    adapter = BenchmarkAdapterV20.from_config(args.config)
    report = adapter.preflight(output=args.output.resolve())
    print(encode(report), flush=True)


if __name__ == '__main__':
    main()
