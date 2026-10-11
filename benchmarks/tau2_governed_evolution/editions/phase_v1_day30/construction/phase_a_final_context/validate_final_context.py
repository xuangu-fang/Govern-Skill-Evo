"""Read-only static context checks. No model, task execution or evaluator calls."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def validate():
    manifest = json.loads((HERE / 'final_context_manifest.json').read_text())
    spec = importlib.util.spec_from_file_location('unified_validator', HERE.parent / 'phase_a_context/validate_unified_phase_a_context.py')
    unified = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unified)
    prior = unified.validate()  # Static schema introspection only.
    assert prior['UNIFIED_PHASE_A_CONTEXT_VERDICT'] == 'READY_FOR_SUCCESS_V1'
    for name, expected in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    for domain, item in manifest['contexts'].items():
        final = ROOT / item['policy_path']
        assert final.read_bytes() == (ROOT / item['source_path']).read_bytes()
        assert hashlib.sha256(final.read_bytes()).hexdigest() == item['policy_sha256']
        assert hashlib.sha256((ROOT / item['tool_overrides_path']).read_bytes()).hexdigest() == item['tool_overrides_sha256']
        assert item['SUCCESS_SIDE_HIDDEN'] == sorted(unified.EXPECTED_HIDE[domain])
        original = unified.UNIFIED_POLICY_PATHS[domain].read_text()
        if domain == 'airline':
            assert item['GOVERNANCE_SIDE_HIDDEN'] == ['LGA01', 'LGA03', 'LGA04']
            for edit in manifest['approved_governance_edits']:
                assert original.count(edit['old']) == 1
                original = original.replace(edit['old'], edit['new'])
            for phrase in ['The booking was made within the last 24 hrs', 'The flight is cancelled by airline', 'It is a business flight', 'the reason for cancellation is covered by insurance', 'obtain the reason for cancellation', 'You should transfer the user', 'origin and trip type', 'Basic economy flights cannot be modified', 'obtain explicit user confirmation (yes)', 'All payment methods must already be in user profile']:
                assert phrase in original, phrase
        else:
            assert item['GOVERNANCE_SIDE_HIDDEN'] == []
        assert original == final.read_text()
        for phrase in unified.FORBIDDEN_PHRASES[domain]:
            assert phrase not in original
    assert manifest['selection_key'] == 'domain' and not manifest['task_specific_switching']
    assert manifest['judge_contract']['agent_context_must_not_be_used_as_judge_policy']
    assert manifest['FINAL_CONTEXT_STATUS'] == 'FROZEN_FOR_TASK_CONSTRUCTION'
    freeze_path = HERE / 'freeze_manifest.json'
    if freeze_path.exists():
        for name, expected in json.loads(freeze_path.read_text())['sha256'].items():
            assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    return {'validated': True, 'source_files_checked': len(manifest['source_sha256']), 'operational_hidden_ids': {d: sorted(unified.EXPECTED_HIDE[d]) for d in manifest['contexts']}, 'FINAL_CONTEXT_VERDICT': manifest['FINAL_CONTEXT_VERDICT'], 'model_calls': 0}


if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))
