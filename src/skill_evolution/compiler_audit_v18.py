"""Audited deterministic compilation. No model calls, retries or overwrites."""
import hashlib
import json
from pathlib import Path

from .compiler_contract_v18 import CompilerRejected
from .compiler_v18 import compile_edit_plan
from .compiler_validation_v18 import plan_payload, validate_edit_plan


def _bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def run_compiler(compiler_input, *, artifact_dir: Path) -> dict:
    """Only a VALID validation.json makes edit_plan.json consumable.

    Invalid inputs receive a rejection record only, never a partial plan. Source
    snapshots are persisted only after source acceptance; unsafe arbitrary objects
    are not dumped. Filesystem errors propagate, leaving no VALID completion marker.
    """
    directory = Path(artifact_dir)
    directory.mkdir(parents=True, exist_ok=False)

    def save(name, data):
        target = directory / name
        temporary = directory / (name + '.tmp')
        temporary.write_bytes(_bytes(data))
        temporary.replace(target)

    save('validation.json', {'status': 'RUNNING'})
    try:
        plan = compile_edit_plan(compiler_input)
        validate_edit_plan(plan, compiler_input=compiler_input)
    except CompilerRejected as exc:
        result = {'status': 'REJECTED', 'stage': exc.stage, 'reason': exc.reason}
        save('validation.json', result)
        return result

    sources = []
    for source in sorted(compiler_input.diagnoses, key=lambda s: s.diagnosis_ref):
        sources.append({
            'diagnosis_ref': source.diagnosis_ref,
            'request_payload': source.request.learner_view.payload,
            'provenance': source.request.provenance,
            'validated_payload': source.validated.payload,
        })
    snapshot = {'schema_version': 'compiler_input_audit_v18.1',
                'round_id': compiler_input.round_id,
                'parent_skill': compiler_input.parent_skill,
                'parent_skill_digest': compiler_input.parent_skill_digest,
                'sources': sources}
    payload = plan_payload(plan)
    save('input.json', snapshot)
    save('edit_plan.json', payload)
    result = {'status': 'VALID',
              'input_sha256': hashlib.sha256(_bytes(snapshot)).hexdigest(),
              'plan_sha256': hashlib.sha256(_bytes(payload)).hexdigest(),
              'edit_unit_count': len(plan.edit_units), 'noop_count': len(plan.noop_records)}
    save('validation.json', result)
    return result
