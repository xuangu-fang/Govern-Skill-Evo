"""Three frozen Evolution inputs, one Diagnosis each; --run enables model calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_001/config/sources.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def replay_sources():
    """Trusted, explicitly hash-pinned local replay, not an arbitrary JSON loader."""
    from src.skill_evolution.v17.group_diagnosis_input_v17 import GroupDiagnosisInput
    from src.skill_evolution.v15.information_boundary_v15 import _seal, unpack
    from src.skill_evolution.v17.diagnosis_prompt_v17 import build_diagnosis_request as old_request
    from src.skill_evolution.v17.diagnosis_validation_v17 import validate_diagnosis_response as old_validate
    rows = load(MANIFEST)
    requests = []
    for row in rows:
        directory = ROOT / row['path']
        for name, expected in row['files_sha256'].items():
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Historical source changed: {row["id"]}/{name}')
        prepared = load(directory / 'request.json')
        provenance = load(directory / 'provenance.json')
        request = GroupDiagnosisInput(
            _seal('V17_GROUP_DIAGNOSIS_INPUT', json.loads(prepared['user_prompt'])),
            json.dumps(provenance))
        if any(prepared.get(k) != v for k, v in old_request(request).items()):
            raise ValueError('Historical request identity mismatch')
        response = load(directory / 'response.json')
        if response.get('refusal') or response['finish_reason'] != 'stop':
            raise ValueError('Incomplete historical response')
        checked = old_validate(response['raw_response'], request=request)
        if unpack(checked, 'V17_VALIDATED_DIAGNOSIS') != load(directory / 'validated_diagnosis.json'):
            raise ValueError('Historical diagnosis revalidation mismatch')
        requests.append((row['id'], request))
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
    requests = replay_sources()
    prepared = {key: build_diagnosis_request(request) for key, request in requests}
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'source_manifest.json', load(MANIFEST))
    save(args.output / 'preflight.json', {
        'status': 'PREFLIGHT', 'planned_model_calls': len(requests),
        'manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        'inputs': {key: {'input_sha256': value['input_sha256'],
                         'prompt_sha256': value['prompt_sha256'],
                         'prompt_version': value['prompt_version']}
                   for key, value in prepared.items()},
    })
    if not args.run:
        print('PREFLIGHT: three historical Evolution inputs verified; zero model calls.')
        return
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env', override=True)
    def run(item):
        key, request = item
        return key, run_group_diagnosis(request, artifact_dir=args.output / key)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(run, requests))
    save(args.output / 'summary.json', results)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
