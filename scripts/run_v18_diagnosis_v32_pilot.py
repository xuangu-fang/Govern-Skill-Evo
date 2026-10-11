"""Run Prompt v3.2 on frozen regressions, boundaries, and aggregation pair."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
V3_FREEZE = ROOT / 'experiments/configs/v18_diagnosis_pilot_003'
V31_FREEZE = ROOT / 'experiments/configs/v18_diagnosis_pilot_004'
V32_FREEZE = ROOT / 'experiments/configs/v18_diagnosis_pilot_005'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + '\n', encoding='utf-8')


def verify_freeze():
    manifest = load(V32_FREEZE / 'manifest.json')
    checks = {
        'cases_sha256': V32_FREEZE / 'cases.json',
        'semantic_rubric_sha256': V32_FREEZE / 'semantic_rubric.json',
    }
    for key, path in checks.items():
        if digest(path.read_bytes()) != manifest[key]:
            raise ValueError(f'Frozen v3.2 {key} changed')
    dependencies = {
        'v3_cases_sha256': V3_FREEZE / 'cases.json',
        'v31_boundary_cases_sha256': V31_FREEZE / 'cases.json',
        'v31_boundary_rubric_sha256': V31_FREEZE / 'semantic_rubric.json',
    }
    for key, path in dependencies.items():
        if digest(path.read_bytes()) != manifest['dependencies'][key]:
            raise ValueError(f'Frozen v3.2 dependency changed: {key}')
    return manifest


def frozen_requests():
    from scripts.run_v18_diagnosis_v2_pilot import constructed_request
    from scripts.run_v18_diagnosis_v3_pilot import frozen_requests as regressions
    verify_freeze()
    items = [(case_id, request, identity, 'REGRESSION')
             for case_id, request, identity in regressions()]
    items.extend((case['id'], constructed_request(case), None, 'BOUNDARY')
                 for case in load(V31_FREEZE / 'cases.json'))
    items.extend((case['id'], constructed_request(case), None, 'AGGREGATION')
                 for case in load(V32_FREEZE / 'cases.json'))
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('New output directory required')
    from src.skill_evolution.diagnosis_prompt_v18 import build_diagnosis_request
    from src.skill_evolution.diagnosis_v18 import run_group_diagnosis
    requests = frozen_requests()
    prepared = {}
    for case_id, request, old_identity, role in requests:
        current = build_diagnosis_request(request)
        if role == 'REGRESSION' and current['input_sha256'] != old_identity['input_sha256']:
            raise ValueError(f'Frozen regression input changed: {case_id}')
        if current['prompt_version'] != 'v18-group-diagnosis-3.2.1':
            raise ValueError('Expected Diagnosis Prompt v3.2.1')
        prepared[case_id] = current
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'preflight.json', {
        'status': 'PREFLIGHT', 'planned_model_calls': len(requests),
        'regression_cases': 6, 'boundary_cases': 5, 'aggregation_cases': 2,
        'monitor_data_used': False,
        'unified_rubric_sha256': digest((V32_FREEZE / 'semantic_rubric.json').read_bytes()),
        'inputs': {case_id: {key: prepared[case_id][key]
                            for key in ('input_sha256', 'prompt_sha256', 'prompt_version')}
                   for case_id, _, _, _ in requests},
    })
    if not args.run:
        print('PREFLIGHT: 6 regressions + 5 boundaries + 2 aggregation cases; zero model calls.')
        return
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)

    def run(item):
        case_id, request, _, _ = item
        return case_id, run_group_diagnosis(request, artifact_dir=args.output / case_id)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(run, requests))
    save(args.output / 'summary.json', results)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
