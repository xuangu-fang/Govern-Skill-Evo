"""Run the frozen v3.2.1 boundary-resolution controls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
FREEZE = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_006/config'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + '\n', encoding='utf-8')


def frozen_requests():
    from scripts.runs.v18.run_v18_diagnosis_v2_pilot import constructed_request
    manifest = load(FREEZE / 'manifest.json')
    for key, name in [('cases_sha256', 'cases.json'),
                      ('semantic_rubric_sha256', 'semantic_rubric.json')]:
        if digest((FREEZE / name).read_bytes()) != manifest[key]:
            raise ValueError(f'Frozen boundary resolution changed: {name}')
    return [(case['id'], constructed_request(case)) for case in load(FREEZE / 'cases.json')]


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
    prepared = {case_id: build_diagnosis_request(request) for case_id, request in requests}
    if any(value['prompt_version'] != 'v18-group-diagnosis-3.2.1'
           for value in prepared.values()):
        raise ValueError('Expected Diagnosis Prompt v3.2.1')
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'preflight.json', {
        'status': 'PREFLIGHT', 'planned_model_calls': 2, 'monitor_data_used': False,
        'semantic_rubric_sha256': digest((FREEZE / 'semantic_rubric.json').read_bytes()),
        'inputs': {key: {name: value[name] for name in
                         ('input_sha256', 'prompt_sha256', 'prompt_version')}
                   for key, value in prepared.items()},
    })
    if not args.run:
        print('PREFLIGHT: two boundary-resolution controls; zero model calls.')
        return
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(pool.map(
            lambda item: (item[0], run_group_diagnosis(item[1], artifact_dir=args.output / item[0])),
            requests))
    save(args.output / 'summary.json', results)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
