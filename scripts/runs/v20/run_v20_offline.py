"""Read-only v19 -> v20 structural validation; never commits Memory."""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.skill_evolution.v20.offline_v20 import offline_validate_v19


def load(path):
    raw = Path(path).read_bytes()
    if str(path).endswith('.gz'):
        raw = gzip.decompress(raw)
    return json.loads(raw.decode('utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', action='append', required=True)
    parser.add_argument('--run-id', default='offline-v20')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = offline_validate_v19(artifacts=[load(p) for p in args.artifact], run_id=args.run_id)
    Path(args.output).write_text(report.payload_json + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
