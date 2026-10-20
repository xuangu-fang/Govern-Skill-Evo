"""Read-only frozen-request checks; writes receipts only under this experiment."""
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_diagnosis_interface_audit_001 import verify_protection as protection
from src.skill_evolution.v23 import memory, preconditioner as pc, evolution as ev
E=Path(__file__).resolve().parent
ROOT=E.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    freeze=read(E/'config/freeze.json')
    for path,digest in freeze['files_sha256'].items():assert sha(E/path)==digest,path
    im=read(E/'config/input_manifest.json')
    for path,digest in im['files_sha256'].items():assert sha(E/path)==digest,path
    source_changed=[p for p,digest in read(E/'config/source_hashes.json').items() if sha(ROOT/p)!=digest]
    assert not source_changed,source_changed
    a,b=(read(E/f'requests/{x}_UNSENT.json') for x in ['A','B'])
    pa,pb=(json.loads(x['body']['messages'][1]['content']) for x in [a,b])
    assert pa.pop('memory')==memory.empty_memory()
    assert pb.pop('memory')==read(E/'config/memory_B.json')
    assert pa==pb==read(E/'config/common_payload_without_memory.json')
    a['body']['messages'][1]['content']=pa;b['body']['messages'][1]['content']=pb
    assert a==b
    for arm in ['A','B']:
        payload=json.loads(read(E/f'requests/{arm}_UNSENT.json')['body']['messages'][1]['content'])
        memory.validate_memory(payload['memory'])
        fixture={'decision':'ready','reason':'Offline contract fixture.','adjustments':[],'checks':None}
        ep=pc.compile_effective_plan(fixture,payload)
        assert ep['goal']==read(E/'config/original_plan.json')['goal']
    template=read(E/'config/evaluation_template.json')
    for u in template['updates']:
        for field in ['A_decision','B_decision','A_reason','B_reason','A_adjustments','B_adjustments','A_checks','B_checks','effective_A','effective_B','material_difference','difference_evidence','new_commitment_risk','attribution_boundary','conclusion']:
            assert u[field] is None,(u['update_id'],field)
    protection.EXP=E
    before=read(E/'config/protected_before.json');after=protection.snapshot()
    changed=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))
    receipt={'at':ev.now(),'checked_files':len(before),'after_files':len(after),'unchanged':not changed,'changed':changed,
             'source_hashes_pass':True,'input_and_protocol_freeze_pass':True,'only_memory_difference':True,
             'result_fields_all_null':True,'network_blocked':True,'model_calls':0,'tokens_consumed':0,'api_cost':0,'environment_calls':0,
             'excluded':['new P3-A directory','__pycache__','.pytest_cache'],
             'test_usage':'hash protection only, no Test trajectory used'}
    (E/'results/protection.json').write_text(json.dumps(receipt,indent=2)+'\n')
    links=[]
    for report in (E/'reports').glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',report.read_text()):
            target=re.sub(r':\d+$','',target.split('#')[0]);p=Path(target) if target.startswith('/') else report.parent/target
            assert p.exists(),(report,p);links.append(str(p))
    receipt['report_links_checked']=len(links)
    (E/'results/protection.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
    print(json.dumps(receipt,indent=2))
    assert not changed,changed
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('P3-A network prohibited')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('P3-A network prohibited')):
        verify()
