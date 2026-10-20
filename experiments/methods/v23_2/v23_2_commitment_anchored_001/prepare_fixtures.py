"""Create explicitly HUMAN fixtures, never model results or approved strategies."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
from anchored import plan_hash
E=Path(__file__).resolve().parent;ROOT=E.parents[3];P=E.parent/'v23_2_preconditioner_memory_ab_001'
request=json.loads((P/'p3b_B_format_001/runs/B/request.json').read_text());payload=json.loads(request['body']['messages'][1]['content']);plan=payload['plan']
def edit(anchor,replacement,op='replace',uid='u1',role='target',deps=None):
 return dict(update_id=uid,operation=op,anchor_text=anchor,replacement_text=replacement,role=role,basis=['M6','P6:6'],reason='HUMAN offline fixture: test operation mechanics, not a verified strategy.',depends_on=deps or [])
def proposal(edits,decision='ready',checks=None):
 return dict(plan_sha256=plan_hash(plan),decision=decision,reason='HUMAN synthetic proposal for deterministic tests only.',edits=edits,checks=checks)
anchor='once that series is exhausted without the target, switch to a different receptacle type'
replace='when recent observations show repeated empty locations in that series, try a different receptacle type'
one=edit(anchor,replace)
one['reason']='HUMAN test hypothesis: change the switching trigger to recent evidence; no claim that this scheduling is superior.'
support=edit('move to a receptacle not yet inspected in this search','move to a currently listed receptacle absent from the recent observations',role='supporting',deps=[0])
support['reason']='HUMAN dependency test: coordinate the global-uninspected precondition with the local-information trigger; otherwise local choice still requires unavailable global history.'
large=edit(plan['updates'][0]['text'], 'Use the current observation to identify a useful next inspection and choose an available action. '+('Preserve task-specific acquisition and completion requirements. '*20))
risk=edit('This is coverage for finding the exact target within the step budget;', ' Stop searching after each receptacle category has been sampled once.',op='insert_after',role='independent')
risk['reason']='HUMAN deliberately unsupported semantic-risk fixture. Structural validity is not evidence that category sampling completes location coverage.'
fixtures={'single_replace':proposal([one]),'target_supporting':proposal([one,support]),'large_replace':proposal([large]),'semantic_risk':proposal([risk]),'keep':proposal([]),'need_evidence':proposal([],decision='need_evidence')}
for name,value in fixtures.items():(E/f'fixtures/{name}.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
(E/'fixtures/README.md').write_text('# HUMAN offline fixtures\n\nAll proposals here are developer-authored tests. They are not LLM output, not approved strategies, and not added to historical A/B. The deliberately bad semantic_risk proposal must pass structural checks and expose its change in the audit. Other fixtures test mechanics only and may retain existing semantic problems.\n')
refs=[P/'p3b_B_format_001/runs/B/request.json',P/'p3b_A_format_001/runs/A/request.json',P/'config/original_plan.json',P/'config/memory_B.json',ROOT/'src/skill_evolution/v23/preconditioner.py',ROOT/'src/skill_evolution/v23/editor.py',ROOT/'src/skill_evolution/v23/preconditioner_prompt.md',E.parent/'v23_2_preconditioner_commitment_analysis_001/results/commitment_matrix.json']
manifest={'source_files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in refs},'plan_canonical_sha256':plan_hash(plan),'historical_input_reference':str(refs[0]),'memory_ids':[i['id'] for i in payload['memory']['entries']],'current_runs':[r['ref'] for r in payload['runs']],'model_parameters':{k:v for k,v in request['body'].items() if k!='messages'},'fixtures':'HUMAN synthetic only','design_before_implementation_sha256':hashlib.sha256((E/'reports/P3C2_ALGORITHM_DESIGN.md').read_bytes()).hexdigest()}
(E/'config/source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
# Payload is an exact offline copy of the archived B user input, not a future sent request.
(E/'fixtures/payload.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
print('Prepared six HUMAN proposals and exact archived payload; no network or model.')
