"""Offline replay of the nine selected v7 diagnoses; never invokes a model."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.compiler_contract_v17 import CompilerInput, CompilerDiagnosisSource
from src.skill_evolution.compiler_audit_v17 import run_compiler
from src.skill_evolution.compiler_v17 import compile_edit_plan
from src.skill_evolution.compiler_validation_v17 import validate_edit_plan
from src.skill_evolution.group_diagnosis_input_v17 import GroupDiagnosisInput
from src.skill_evolution.diagnosis_prompt_v17 import build_diagnosis_request
from src.skill_evolution.diagnosis_validation_v17 import validate_diagnosis_response
from src.skill_evolution.information_boundary_v15 import _seal, unpack
from scripts.run_v17_diagnosis_pilot import PILOT_EXPERIMENT_SCOPE


def load(path):
    return json.loads(path.read_text())


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'experiments/v17_compiler_pilot_001')
    args = parser.parse_args()
    require(not args.output.exists(), 'output directory already exists')
    manifest_path = ROOT / 'experiments/v17_diagnosis_prompt7_analysis_001/selected_results.json'
    selected = load(manifest_path)
    require(len(selected) == 9 and {r['group'] for r in selected} == {f'G{i}' for i in range(1, 10)}, 'nine unique groups required')
    sources, lineage = [], []
    for row in selected:
        directory = ROOT / row['path']
        saved = load(directory / 'validated_diagnosis.json')
        require(hashlib.sha256((directory / 'validated_diagnosis.json').read_bytes()).hexdigest() == row['sha256'], 'selected artifact changed')
        prepared = load(directory / 'request.json')
        response = load(directory / 'response.json')
        provenance = load(directory / 'provenance.json')
        require(load(directory / 'validation.json')['status'] == 'VALID', 'source not valid')
        require(prepared['prompt_version'] == 'v17-group-diagnosis-7' and prepared['experiment_scope'] == PILOT_EXPERIMENT_SCOPE, 'wrong prompt/scope')
        require(response['finish_reason'] == 'stop' and not response.get('refusal'), 'incomplete response')
        historical = load(ROOT / 'experiments/v17_diagnosis_pilot_002' / row['group'] / 'request.json')
        require(prepared['user_prompt'] == historical['user_prompt'], 'historical learner input changed')
        # Trusted local replay, not authentication of arbitrary external JSON.
        request = GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', json.loads(prepared['user_prompt'])), json.dumps(provenance))
        require(all(prepared[k] == v for k, v in build_diagnosis_request(request, experiment_scope=PILOT_EXPERIMENT_SCOPE).items()), 'request identity mismatch')
        validated = validate_diagnosis_response(response['raw_response'], request=request)
        require(unpack(validated, 'V17_VALIDATED_DIAGNOSIS') == saved, 'source revalidation differs')
        require(provenance['group_id'] == row['group'], 'group provenance mismatch')
        ref = 'DIAGNOSIS/' + hashlib.sha256(validated.payload.encode()).hexdigest()
        sources.append(CompilerDiagnosisSource(ref, request, validated))
        lineage.append({'group_id': row['group'], 'diagnosis_ref': ref, 'artifact_dir': row['path'],
                        'files_sha256': {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in ['request.json', 'response.json', 'validated_diagnosis.json', 'provenance.json', 'validation.json']}})
    first = sources[0].request
    parent = first.learner_payload['current_skill']
    data = CompilerInput(first.provenance['round_id'], parent, hashlib.sha256(parent.encode()).hexdigest(), tuple(sources))
    plan = compile_edit_plan(data)
    require(plan == compile_edit_plan(replace(data, diagnoses=tuple(reversed(sources)))), 'order-dependent plan')
    expected = {(s.diagnosis_ref, i) for s in sources for i, _ in enumerate(unpack(s.validated, 'V17_VALIDATED_DIAGNOSIS')['semantic']['parent_skill_gaps'])}
    actual = [(r.diagnosis_ref, r.gap_index) for u in plan.edit_units for r in u.supporting_gap_refs]
    require(len(actual) == len(set(actual)) and set(actual) == expected, 'gap coverage mismatch')
    require(len(plan.edit_units) == 7 and all(u.operation == 'ADD' and not u.target_rule_refs for u in plan.edit_units), 'unexpected pilot operations')
    group_for = {r['diagnosis_ref']: r['group_id'] for r in lineage}
    require({group_for[n.diagnosis_ref] for n in plan.noop_records} == {'G1', 'G9'}, 'NOOP mismatch')
    result = run_compiler(data, artifact_dir=args.output)
    require(result['status'] == 'VALID', 'audit run rejected')
    persisted = load(args.output / 'edit_plan.json')
    validate_edit_plan(persisted, compiler_input=data)
    for name, key in [('edit_plan.json', 'plan_sha256'), ('input.json', 'input_sha256')]:
        require(hashlib.sha256((args.output / name).read_bytes()).hexdigest() == result[key], 'persisted digest mismatch')
    trace = {'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
             'sources': lineage, 'gap_coverage': '7/7 exactly once', 'noop_groups': ['G1', 'G9'],
             'reversed_input_same_plan': True, 'model_calls': 0,
             'edit_units': [{'index': i, 'operation': u.operation, 'groups': [group_for[r.diagnosis_ref] for r in u.supporting_gap_refs], 'gap_indices': [r.gap_index for r in u.supporting_gap_refs]} for i,u in enumerate(plan.edit_units)]}
    (args.output / 'traceability.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
