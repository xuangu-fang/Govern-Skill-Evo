"""Run Prompt v3.1 on six frozen regressions and five generic boundaries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
V3_FREEZE = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_003/config'
BOUNDARY_FREEZE = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_004/config'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + '\n', encoding='utf-8')


def frozen_requests():
    from scripts.runs.v18.run_v18_diagnosis_v2_pilot import constructed_request
    from scripts.runs.v18.run_v18_diagnosis_v3_pilot import frozen_requests as v3_requests
    manifest = load(BOUNDARY_FREEZE / 'manifest.json')
    if digest((BOUNDARY_FREEZE / 'cases.json').read_bytes()) != manifest['cases_sha256']:
        raise ValueError('Frozen boundary cases changed')
    if digest((BOUNDARY_FREEZE / 'semantic_rubric.json').read_bytes()) != manifest['semantic_rubric_sha256']:
        raise ValueError('Frozen boundary rubric changed')
    regressions = [(group_id, request, identity, 'REGRESSION')
                   for group_id, request, identity in v3_requests()]
    boundaries = [(case['id'], constructed_request(case), None, 'BOUNDARY')
                  for case in load(BOUNDARY_FREEZE / 'cases.json')]
    return regressions + boundaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('New output directory required')
    from src.skill_evolution.v18.diagnosis_prompt_v18 import build_diagnosis_request
    from src.skill_evolution.v18.diagnosis_v18 import run_group_diagnosis
    requests = frozen_requests()
    prepared = {}
    for case_id, request, old_identity, role in requests:
        current = build_diagnosis_request(request)
        if role == 'REGRESSION' and current['input_sha256'] != old_identity['input_sha256']:
            raise ValueError(f'Frozen regression input changed: {case_id}')
        if current['prompt_version'] != 'v18-group-diagnosis-3.1':
            raise ValueError('Expected Diagnosis Prompt v3.1')
        prepared[case_id] = current
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'preflight.json', {
        'status': 'PREFLIGHT', 'planned_model_calls': len(requests),
        'regression_cases': 6, 'boundary_cases': 5, 'monitor_data_used': False,
        'v3_rubric_sha256': digest((V3_FREEZE / 'semantic_rubric.json').read_bytes()),
        'boundary_rubric_sha256': digest((BOUNDARY_FREEZE / 'semantic_rubric.json').read_bytes()),
        'inputs': {case_id: {key: prepared[case_id][key]
                            for key in ('input_sha256', 'prompt_sha256', 'prompt_version')}
                   for case_id, _, _, _ in requests},
    })
    if not args.run:
        print('PREFLIGHT: 6 frozen regressions + 5 generic boundaries; zero model calls.')
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
