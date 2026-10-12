"""Five fixed v2 Diagnosis inputs; --run performs one model call per input."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
HISTORICAL = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_001/config/sources.json'
CONSTRUCTED = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_002/config/constructed_cases.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def constructed_request(case):
    """Build a deterministic learner-safe development input from an explicit spec."""
    from src.skill_evolution.v18.diagnosis_references_v18 import build_reference_catalogs
    from src.skill_evolution.v17.group_diagnosis_input_v17 import GroupDiagnosisInput
    from src.skill_evolution.v15.information_boundary_v15 import _seal
    context_ref = 'C001'
    experiences = []
    evidence, supervision = {}, {}
    members = []
    for index, source in enumerate(case['experiences'], 1):
        task_ref, trajectory_ref = f'T{index:03d}', f'R{index:03d}'
        members.append(task_ref)
        events = []
        for step, raw in enumerate(source['events'], 1):
            ref = f'{task_ref}/{trajectory_ref}/R1/E{step:04d}'
            events.append({**raw, 'step': step, 'evidence_ref': ref})
            evidence[ref] = {'task_ref': task_ref, 'trajectory_ref': trajectory_ref,
                             'rollout_index': 1, 'step': step}
        supervision_ref = f'{task_ref}/{trajectory_ref}/R1/S'
        experiences.append({
            'task_ref': task_ref, 'context_ref': context_ref,
            'trajectory_ref': trajectory_ref, 'rollout_index': 1, 'events': events,
            'supervision': {'success': source['success'], 'compliant': source['compliant'],
                            'level': 0, 'provenance': 'LEARNER_SAFE_SUPERVISION',
                            'supervision_ref': supervision_ref},
        })
        supervision[supervision_ref] = {'task_ref': task_ref, 'trajectory_ref': trajectory_ref,
                                        'rollout_index': 1, 'level': 0}
    payload = {
        'schema_version': 'group_diagnosis_input_v17.2',
        'current_skill': case['parent_skill'],
        'contexts': [{'context_ref': context_ref, 'visible_policy': case['visible_policy'],
                      'public_tools': case['tools']}],
        'experiences': experiences,
        'available_evidence_refs': evidence,
        'available_supervision_refs': supervision,
        'grouping_hint_authority': 'ANALYSIS_HINT_ONLY_NOT_EVIDENCE_OR_POLICY',
        'grouping_hint': {
            'group_id': case['id'], 'decision_problem': case['decision_problem'],
            'members': members, 'origin': 'LEARNER_INFERRED_GROUPING',
            'shared_basis': 'Constructed development comparison for a declared edit boundary.',
            'important_differences': [],
        },
    }
    payload.update(build_reference_catalogs(payload))
    provenance = {'round_id': 'constructed-v18-pilot', 'group_id': case['id'],
                  'origin': 'CONSTRUCTED_DEVELOPMENT_SAMPLE_NOT_FORMAL_LEARNING'}
    return GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', payload),
                               json.dumps(provenance, sort_keys=True))


def fixed_requests():
    from scripts.runs.v18.run_v18_diagnosis_pilot import replay_sources
    historical = replay_sources()
    constructed = [(case['id'], constructed_request(case)) for case in load(CONSTRUCTED)]
    return historical + constructed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('New output directory required')
    from src.skill_evolution.v18.diagnosis_prompt_v18 import build_diagnosis_request
    from src.skill_evolution.v18.diagnosis_v18 import run_group_diagnosis
    requests = fixed_requests()
    prepared = {key: build_diagnosis_request(request) for key, request in requests}
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'source_manifest.json', {
        'historical_manifest_sha256': hashlib.sha256(HISTORICAL.read_bytes()).hexdigest(),
        'constructed_cases_sha256': hashlib.sha256(CONSTRUCTED.read_bytes()).hexdigest(),
        'historical_sources': load(HISTORICAL),
        'constructed_rubrics': {case['id']: case['rubric'] for case in load(CONSTRUCTED)},
    })
    save(args.output / 'preflight.json', {
        'status': 'PREFLIGHT', 'planned_model_calls': len(requests),
        'historical_inputs': 3, 'constructed_inputs': 2,
        'inputs': {key: {'input_sha256': value['input_sha256'],
                         'prompt_sha256': value['prompt_sha256'],
                         'prompt_version': value['prompt_version']}
                   for key, value in prepared.items()},
    })
    if not args.run:
        print('PREFLIGHT: five fixed inputs verified; zero model calls.')
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
