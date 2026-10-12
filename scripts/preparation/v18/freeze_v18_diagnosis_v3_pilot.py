"""Freeze the six end-to-end Pilot Diagnosis inputs and v2 outputs; no models."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'artifacts/methods/v18/pilot/v18_pilot_001/round-01/diagnosis'
OUTPUT = ROOT / 'experiments/methods/v18/v18_diagnosis_pilot_003/config'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + '\n', encoding='utf-8')


RUBRIC = {
    'rubric_version': 'v18-diagnosis-v3-regression-rubric-1',
    'written_before_prompt_v3': True,
    'prohibited_evidence': [
        'Monitor task-level errors or outcomes',
        'Monitor transition rows',
        'Gate deltas as a source of rules',
    ],
    'global_criteria': [
        'ADDRESSABLE gaps must identify an evidence-supported behavior change that the Agent can actually execute.',
        'Knowing that an observed action is wrong is insufficient when the replacement depends on a hidden mechanism or unknown mapping that tools and lawful interaction cannot supply.',
        'Incomplete evidence must not create a new verification duty, prerequisite, prohibition, refusal, transfer, or stopping condition without independent evidence.',
        'Tentative wording does not cure an unsupported duty or negative decision.',
        'Useful local executable empirical patterns remain eligible even when their complete causal mechanism is unknown.',
        'Gap conditions, scope, limitations, and epistemic status must remain faithful to the analyses.',
    ],
    'cases': {
        'G01': {
            'role': 'NON_REGRESSION',
            'pass': [
                'Preserve the tentative partner_direct protection-conditional behavior pattern.',
                'Keep consolidated unresolved and do not generalize the partner_direct pattern.',
            ],
            'fail': ['Collapse to NOT_ADDRESSABLE solely because the complete protection mechanism is unknown.'],
        },
        'G02': {
            'role': 'NON_REGRESSION',
            'pass': [
                'Preserve cedar as a context-limited tentative execution hypothesis.',
                'Do not extend the cedar hypothesis to orbit or claim a proven universal order.',
            ],
            'fail': ['Remove the local executable hypothesis solely because its causal mechanism is incomplete.'],
        },
        'G03': {
            'role': 'TARGET',
            'pass': [
                'Retain the C002 tentative passenger-count pattern as an addressable executable gap.',
                'Do not create an executable baggage-classification gap when the free-bag mapping and resulting tool arguments cannot be determined from supplied evidence.',
                'Keep the baggage deficiency as unresolved or non-addressable within the mixed group rather than asking the Agent to guess.',
            ],
            'fail': [
                'Require classification, verification, or a tool argument without an evidence-supported mapping.',
                'Move the entire mixed group to NOT_ADDRESSABLE and lose the passenger-count pattern.',
            ],
        },
        'G04': {
            'role': 'NON_REGRESSION',
            'pass': [
                'Preserve the horizon/summit channel-conditional projected-total pattern.',
                'Keep the mapping tentative and scoped to the observed workflow.',
            ],
            'fail': ['Discard the executable channel mapping because the underlying settlement mechanism is not fully stated.'],
        },
        'G05': {
            'role': 'NON_REGRESSION',
            'pass': ['Remain NO_ISSUE with no gaps.'],
            'fail': ['Create a gap merely because the Parent Skill is sparse.'],
        },
        'G06': {
            'role': 'TARGET',
            'pass': [
                'Do not turn unavailable internal coverage knowledge into a general duty to prove coverage before acting.',
                'Do not infer a default refusal, stop, or transfer merely from inability to prove coverage.',
                'A narrow empirical rule about the directly observed work-conflict/change-of-plan class is allowed only if its negative decision is supported by the supplied compliant/noncompliant contrast, not by absence of proof.',
            ],
            'fail': [
                'Require visible policy, tool, contract, or user verification of hidden coverage and otherwise deny.',
                'Use tentative wording while retaining that unsupported proof-or-deny structure.',
            ],
        },
    },
}


def main():
    if OUTPUT.exists():
        raise ValueError('Frozen v3 Pilot config already exists')
    OUTPUT.mkdir(parents=True)
    cases = []
    files = {}
    for group_id in [f'G{i:02d}' for i in range(1, 7)]:
        directory = SOURCE / group_id
        request = load(directory / 'request.json')
        provenance = load(directory / 'provenance.json')
        validated = load(directory / 'validated_diagnosis.json')
        validation = load(directory / 'validation.json')
        if validation.get('status') != 'VALID' or request.get('prompt_version') != 'v18-group-diagnosis-2':
            raise ValueError(f'Expected VALID v2 source: {group_id}')
        learner_payload = json.loads(request['user_prompt'])
        cases.append({
            'group_id': group_id,
            'learner_payload': learner_payload,
            'provenance': provenance,
            'v2_request_identity': {
                key: request[key] for key in ('prompt_version', 'prompt_sha256', 'input_sha256')
            },
            'v2_validated_diagnosis': validated,
            'v2_validation': validation,
        })
        for name in ('request.json', 'provenance.json', 'validated_diagnosis.json', 'validation.json'):
            path = directory / name
            files[str(path.relative_to(ROOT))] = digest(path.read_bytes())
    save(OUTPUT / 'cases.json', cases)
    save(OUTPUT / 'semantic_rubric.json', RUBRIC)
    save(OUTPUT / 'manifest.json', {
        'schema_version': 'v18_diagnosis_v3_frozen_inputs.1',
        'source': 'v18 end-to-end Pilot current G01-G06 Diagnosis only',
        'monitor_data_used': False,
        'case_count': 6,
        'files': files,
        'cases_sha256': digest((OUTPUT / 'cases.json').read_bytes()),
        'semantic_rubric_sha256': digest((OUTPUT / 'semantic_rubric.json').read_bytes()),
    })
    print('Frozen 6 v2 Diagnosis inputs/outputs and prewritten semantic rubric; zero model calls.')


if __name__ == '__main__':
    main()
