"""Verify the prepared and formal SpreadsheetBench SkillOpt bundles."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.runs.spreadsheetbench.legacy_archive import read_records
from scripts.runs.spreadsheetbench.native_archive import check_copies, verify_native
from scripts.runs.spreadsheetbench.verify_archive import read, require

PUBLISHED = ROOT / 'experiments/methods/skillopt/spreadsheetbench'


@read_records
def verify(archive=False):
    prepared = PUBLISHED / 'skillopt_spreadsheetbench_official_actor48k_20261029'
    record = read(prepared / 'record.json')
    require(record['run_id'] == prepared.name and record['status'] == 'prepared', 'Prepared record differs')
    check_copies(prepared, record['configs'], Path if archive else None)
    require(not (ROOT / record['source'] / 'campaign').exists() if archive else True,
            'Historical preparation contains a completed campaign')
    results = verify_native(PUBLISHED / 'spreadsheetbench_v25_8', 9, Path if archive else None)
    return {'prepared_records': 1, 'formal_trainings': 1, 'evaluations': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', action='store_true', help='verify original Selection and Test receipts')
    print(json.dumps(verify(parser.parse_args().archive), indent=2))
