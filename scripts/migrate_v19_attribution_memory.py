"""Archive an old run and migrate committed Attribution/Memory semantics; no model calls."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'external/tau2-bench/src')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    from src.skill_evolution.semantics_migration_v19 import prepare_semantics_migration
    from src.skill_evolution.evolution_benchmark_v19 import BenchmarkEvolutionV19
    from src.skill_evolution.monitor_campaign_v19 import BenchmarkMonitorV19
    from src.skill_evolution.edit_tracking_v19 import encode
    print(encode(prepare_semantics_migration(source=args.source, archive=args.archive, output=args.output,
          evolution=BenchmarkEvolutionV19(), monitor=BenchmarkMonitorV19())), flush=True)


if __name__=='__main__':main()
