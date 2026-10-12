"""Run v3 Diagnosis on six frozen end-to-end Pilot inputs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
FREEZE = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_003/config'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + '\n', encoding='utf-8')


def frozen_requests():
    from src.skill_evolution.v17.group_diagnosis_input_v17 import GroupDiagnosisInput
    from src.skill_evolution.v15.information_boundary_v15 import _seal
    manifest = load(FREEZE / 'manifest.json')
    if digest((FREEZE / 'cases.json').read_bytes()) != manifest['cases_sha256']:
        raise ValueError('Frozen v3 cases changed')
    if digest((FREEZE / 'semantic_rubric.json').read_bytes()) != manifest['semantic_rubric_sha256']:
        raise ValueError('Frozen v3 semantic rubric changed')
    requests = []
    for case in load(FREEZE / 'cases.json'):
        request = GroupDiagnosisInput(
            _seal('V17_GROUP_DIAGNOSIS_INPUT', case['learner_payload']),
            json.dumps(case['provenance'], ensure_ascii=False, sort_keys=True),
        )
        requests.append((case['group_id'], request, case['v2_request_identity']))
    return requests


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
    for group_id, request, v2_identity in requests:
        current = build_diagnosis_request(request)
        if current['input_sha256'] != v2_identity['input_sha256']:
            raise ValueError(f'v3 input differs from frozen v2 input: {group_id}')
        if current['prompt_version'] != 'v18-group-diagnosis-3':
            raise ValueError('Expected v3 Diagnosis prompt')
        prepared[group_id] = current
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'preflight.json', {
        'status': 'PREFLIGHT', 'planned_model_calls': 6, 'monitor_data_used': False,
        'frozen_manifest_sha256': digest((FREEZE / 'manifest.json').read_bytes()),
        'semantic_rubric_sha256': digest((FREEZE / 'semantic_rubric.json').read_bytes()),
        'inputs': {group_id: {
            key: prepared[group_id][key]
            for key in ('input_sha256', 'prompt_sha256', 'prompt_version')
        } for group_id, _, _ in requests},
    })
    if not args.run:
        print('PREFLIGHT: six frozen v2 inputs bound to Prompt v3; zero model calls.')
        return
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    def run(item):
        group_id, request, _ = item
        return group_id, run_group_diagnosis(request, artifact_dir=args.output / group_id)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(run, requests))
    save(args.output / 'summary.json', results)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
