"""Replay accepted Compiler audit and invoke Editor once; no retries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.compiler_contract_v17 import CompilerInput, CompilerDiagnosisSource
from src.skill_evolution.compiler_v17 import compile_edit_plan
from src.skill_evolution.compiler_validation_v17 import validate_edit_plan
from src.skill_evolution.diagnosis_validation_v17 import validate_diagnosis_response
from src.skill_evolution.group_diagnosis_input_v17 import GroupDiagnosisInput
from src.skill_evolution.information_boundary_v15 import _seal, unpack
from src.skill_evolution.editor_contract_v17 import EditorInput
from src.skill_evolution.editor_v17 import run_editor


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'experiments/v17_editor_pilot_001')
    args=parser.parse_args()
    directory=ROOT/'experiments/v17_compiler_pilot_001'
    load=lambda name:json.loads((directory/name).read_text())
    audit=load('validation.json')
    if audit['status']!='VALID':raise ValueError('Compiler not valid')
    for name,key in [('input.json','input_sha256'),('edit_plan.json','plan_sha256')]:
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=audit[key]:raise ValueError('Compiler artifact changed')
    snapshot=load('input.json');sources=[]
    for source in snapshot['sources']:
        request=GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT',json.loads(source['request_payload'])),json.dumps(source['provenance']))
        saved=json.loads(source['validated_payload'])
        validated=validate_diagnosis_response(saved['raw_response'],request=request)
        if unpack(validated,'V17_VALIDATED_DIAGNOSIS')!=saved:raise ValueError('Source revalidation differs')
        sources.append(CompilerDiagnosisSource(source['diagnosis_ref'],request,validated))
    value=CompilerInput(snapshot['round_id'],snapshot['parent_skill'],snapshot['parent_skill_digest'],tuple(sources))
    validate_edit_plan(load('edit_plan.json'),compiler_input=value)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=True)
    result=run_editor(EditorInput(value,compile_edit_plan(value)),artifact_dir=args.output)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
