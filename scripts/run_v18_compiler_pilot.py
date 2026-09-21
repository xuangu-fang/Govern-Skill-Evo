"""Offline compilation of all five v2 pilot diagnoses; no models or Skill edits."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / 'experiments/configs/v18_compiler_pilot_001/sources.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def replay_inputs():
    """Rebuild trusted local development inputs, not a general artifact loader.

    Each case is compiled separately: these are slices from different rounds and
    Parents, not a complete formal round. No semantic score filters the sources.
    """
    from scripts.run_v18_diagnosis_v2_pilot import fixed_requests
    from src.skill_evolution.compiler_contract_v18 import CompilerInput, CompilerDiagnosisSource
    from src.skill_evolution.diagnosis_prompt_v18 import build_diagnosis_request
    from src.skill_evolution.diagnosis_validation_v18 import validate_diagnosis_response
    from src.skill_evolution.information_boundary_v15 import unpack
    requests = dict(fixed_requests())
    rows = load(MANIFEST)
    if len(rows) != len(requests) or {row['id'] for row in rows} != set(requests):
        raise ValueError('Expected all five fixed pilot cases exactly once')
    result = []
    for row in rows:
        directory = ROOT / row['path']
        for name, expected in row['files_sha256'].items():
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f'Pilot source changed: {row["id"]}/{name}')
        request = requests[row['id']]
        prepared = load(directory / 'request.json')
        current = build_diagnosis_request(request)
        if (prepared.get('prompt_version') != 'v18-group-diagnosis-2'
                or prepared.get('user_prompt') != current['user_prompt']
                or prepared.get('input_sha256') != current['input_sha256']
                or prepared.get('response_format') != current['response_format']):
            raise ValueError('Pilot request differs from reconstructed v2 input')
        if request.provenance != load(directory / 'provenance.json'):
            raise ValueError('Pilot provenance differs from reconstructed input')
        response = load(directory / 'response.json')
        if (load(directory / 'validation.json')['status'] != 'VALID'
                or response.get('refusal') or response.get('finish_reason') != 'stop'):
            raise ValueError('Incomplete or invalid pilot diagnosis')
        validated = validate_diagnosis_response(response['raw_response'], request=request)
        if unpack(validated, 'V18_VALIDATED_DIAGNOSIS') != load(directory / 'validated_diagnosis.json'):
            raise ValueError('Pilot diagnosis revalidation mismatch')
        parent = request.learner_payload['current_skill']
        digest = hashlib.sha256(parent.encode('utf-8')).hexdigest()
        provenance = request.provenance
        if 'parent_skill_digest' not in provenance:
            if provenance.get('origin') != 'CONSTRUCTED_DEVELOPMENT_SAMPLE_NOT_FORMAL_LEARNING':
                raise ValueError('Missing Parent binding on historical input')
            # Trusted caller supplies missing runtime metadata for the development
            # fixture only. Learner payload, response and historical files stay exact.
            provenance['parent_skill_digest'] = digest
            request = replace(request, provenance_json=json.dumps(provenance, sort_keys=True))
        ref = 'DIAGNOSIS/' + hashlib.sha256(validated.payload.encode('utf-8')).hexdigest()
        data = CompilerInput(provenance['round_id'], parent, digest,
                             (CompilerDiagnosisSource(ref, request, validated),))
        result.append((row['id'], data))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('New output directory required')
    from src.skill_evolution.compiler_audit_v18 import run_compiler
    values = replay_inputs()
    args.output.mkdir(parents=True, exist_ok=False)
    results = {key: run_compiler(value, artifact_dir=args.output / key) for key, value in values}
    summary = {'scope': 'FIVE_INDEPENDENT_DEVELOPMENT_CASES_NOT_FORMAL_ROUND',
               'model_calls': 0, 'candidate_created': False,
               'source_manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
               'results': results}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
