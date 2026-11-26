"""Domain evidence adapter for the unchanged version-local method contracts."""
from copy import deepcopy
from pathlib import Path
import re
import json
from ...facts import require, text
from ...contracts.diagnosis import fields, links
from ...contracts import memory as mem
from ...contracts.grouping import references
from .facts import build_facts
from .protocol import execution_context, EXECUTION_HISTORY
from .timeline import model_messages


def run_references(run):
    return {run['ref'],run['initial']['ref'],run['outcome']['ref'],*[a['ref'] for a in run['attempts']]}


def validate_run(run):
    fields(run,('ref','task_id','run_id','initial','attempts','outcome'),'Run')
    require(re.fullmatch(r'[PQ][1-9]\d*',run['ref']) is not None,'Invalid run reference')
    require(run['initial']['ref']==run['ref']+':0' and run['outcome']['ref']==run['ref']+':outcome','Invalid run references')
    filtered=any(a.get('request_context')==EXECUTION_HISTORY for a in run['attempts'])
    previous=0
    for i,a in enumerate(run['attempts'],1):
        if filtered:
            match=re.fullmatch(re.escape(run['ref'])+r':([1-9]\d*)',a['ref'])
            require(match is not None and int(match[1])>previous,'Invalid attempt reference')
            previous=int(match[1])
            require(a.get('request_context')==EXECUTION_HISTORY and a['executed'] is True,'Mixed execution evidence views')
        else:require(a['ref']==f"{run['ref']}:{i}",'Invalid attempt reference')
        require(type(a['executed']) is bool,'Invalid executed flag')
    if filtered:
        require(not {'api_requests','generation_responses'}&set(run['outcome']),'Generation counters in execution evidence')
        require(run['outcome']['submitted_attempt'] in (None,*[a['ref'] for a in run['attempts']]),'Invalid submission reference')
    require(run['outcome']['status']=='completed','Incomplete execution evidence')
    return run


def validate_grouping(result,facts):
    fields(result,('groups',),'Grouping');require(isinstance(result['groups'],list) and result['groups'],'Missing groups')
    runs={r['ref']:r for r in facts['runs']};allowed=set().union(*(run_references(r) for r in runs.values()));assigned=[];ids=set()
    for group in result['groups']:
        fields(group,('group_id','members','decision_problem','shared_basis','important_differences'),'Group')
        gid=text(group['group_id'],'Group ID');require(gid not in ids,'Duplicate Group ID');ids.add(gid)
        links(group['members'],set(runs),'Members');assigned+=group['members']
        text(group['decision_problem'],'Decision problem');text(group['shared_basis'],'Shared basis')
        require(isinstance(group['important_differences'],list),'Invalid differences')
        for item in [group['decision_problem'],group['shared_basis'],*group['important_differences']]:
            require(references(text(item,'group text'))<=allowed,'Unknown execution reference')
        for member in group['members']:
            r=runs[member];steps={a['ref'] for a in r['attempts']} or {r['initial']['ref']}
            require(bool(steps & references(group['shared_basis'])),'Group lacks decision evidence')
    require(len(assigned)==len(set(assigned)) and set(assigned)==set(runs),'Grouping must cover each run exactly once')
    return result


def diagnosis_input(saved):
    fields(saved['facts'],('parent','runs'),'Facts');validate_grouping(saved['grouping'],saved['facts'])
    return deepcopy({**saved['facts'],'grouping':saved['grouping']})


def preconditioner_input(saved,*,memory=None,memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    from ...contracts.diagnosis import validate_diagnosis
    facts=diagnosis_input(saved);validate_diagnosis(saved['diagnosis'],facts)
    require(saved['diagnosis']['decision']=='revise','Preconditioner needs revise')
    plan=saved['diagnosis']['plan'];encoded=json.dumps(plan);ids={r.split(':')[0] for r in references(encoded)}
    gids=set(re.findall(r'\bG\d+\b',encoded));memory=deepcopy(saved.get('memory',mem.empty_memory()) if memory is None else memory)
    mem.validate_memory(memory,memory_contract=memory_contract)
    return dict(parent=facts['parent'],plan=deepcopy(plan),runs=[deepcopy(r) for r in facts['runs'] if r['ref'] in ids],
        grouping={'groups':[deepcopy(g) for g in facts['grouping']['groups'] if g['group_id'] in gids or ids.intersection(g['members'])]},memory=memory)


def memory_view(archive,contexts,active_ids,memory_contract):
    view=mem.empty_memory()
    for mid in active_ids:
        entry=archive[mid];view['entries'].append({k:deepcopy(entry[k]) for k in ('id',*mem._entry_fields(memory_contract))})
        for ref in mem.entry_evidence(entry,memory_contract=memory_contract):
            cid,local=ref.rsplit('/',1);context=contexts[cid];payload=context['payload']
            view['sources'][cid+'/diff']={'parent':payload['parent'],'diff':payload['diff'],'execution_context':deepcopy(context['execution_context'])}
            if local!='diff':
                rid=local.split(':')[0];run=next(r for r in payload['runs'] if r['ref']==rid)
                require(local in run_references(run),'Historical source missing')
                view['sources'][cid+'/'+rid]={'run':deepcopy(run)}
    mem.validate_memory(view,memory_contract=memory_contract);return view


def verify_pair(parent,candidate,*,implementation_review=None):
    require(implementation_review is None,'No runtime implementation amendments')
    for key in ('task','model','protocol','executor'):require(parent[key]==candidate[key],f'Pair {key} differs')
    require(parent['run_id']!=candidate['run_id'],'Pair reuses execution identity')
    require(Path(parent['input_snapshot']).read_bytes()==Path(candidate['input_snapshot']).read_bytes(),'Paired original inputs differ')
    require(parent['initial_messages'][1:]==candidate['initial_messages'][1:],'Paired task messages differ')


def pair_result(run):
    o=run['outcome'];return {k:o[k] for k in ('status','code_attempts','program_executions','api_requests') if k in o}|{k:o['score'][k] for k in ('hard','per_cell_pass_rate')}


def relabel(run,ref):
    run=deepcopy(run);run['ref']=ref;run['initial']['ref']=ref+':0';run['outcome']['ref']=ref+':outcome'
    for a in run['attempts']:a['ref']=ref+':'+a['ref'].split(':')[-1]
    if run['outcome']['submitted_attempt']:run['outcome']['submitted_attempt']=ref+':'+run['outcome']['submitted_attempt'].split(':')[-1]
    return run


def build_replay_from_editor(saved,editor_directory,parent_records,candidate_records,*,memory=None,implementation_review=None,memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT,facts_builder=build_facts,pair_verifier=verify_pair):
    from ...contracts.editor import apply_patch
    require(saved['editor_status']=='candidate','Replay needs real Candidate')
    require(apply_patch(saved['facts']['parent'],saved['actual_diff'])==saved['candidate_text'],'Actual Diff differs')
    p,q=facts_builder(parent_records),facts_builder(candidate_records)
    require(p['facts']==saved['facts'] and p['background']==q['background']==saved['background'],'Frozen Parent lineage differs')
    require(q['facts']['parent']==saved['candidate_text'],'Executed Candidate differs')
    require(len(parent_records)==len(candidate_records),'Incomplete pairs')
    candidates={r['task']['id']:(r,run) for r,run in zip(candidate_records,q['facts']['runs'])}
    runs=deepcopy(p['facts']['runs']);pairs=[];audits=[]
    for i,(record,prun) in enumerate(zip(parent_records,p['facts']['runs']),1):
        require(record['task']['id'] in candidates,'Missing Candidate task')
        qr,qrun=candidates[record['task']['id']];pair_verifier(record,qr,implementation_review=implementation_review)
        qrun=relabel(qrun,f'Q{i}');runs.append(qrun)
        pair=dict(parent=prun['ref'],candidate=qrun['ref'],task_id=prun['task_id'],parent_result=pair_result(prun),candidate_result=pair_result(qrun));pairs.append(pair)
        audits.append({'pair':{'parent':prun['ref'],'candidate':qrun['ref']},'task_id':prun['task_id'],'parent_run_id':record['run_id'],'candidate_run_id':qr['run_id'],'verified':True})
    plan=saved['effective_plan'];plan={'goal':plan['goal'],'updates':[{k:u[k] for k in ('id','text')} for u in plan['updates']],'checks':deepcopy(plan['checks'])}
    payload=dict(parent=p['facts']['parent'],diff=saved['actual_diff'],plan=plan,runs=runs,pairs=pairs,memory=deepcopy(memory if memory is not None else mem.empty_memory()))
    validate_payload(payload,memory_contract=memory_contract)
    return dict(payload=payload,background=p['background'],pair_audit=audits,editor_directory=str(Path(editor_directory).resolve()),candidate=saved['candidate_text'],
                execution_context={'background':p['background'],'description':execution_context(p['background']),'actor_model':parent_records[0]['model'],'protocol':parent_records[0]['protocol']})


def validate_payload(payload,*,memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    from ...contracts.editor import apply_patch
    fields(payload,('parent','diff','plan','runs','pairs','memory'),'Replay input');apply_patch(payload['parent'],payload['diff'])
    plan=payload['plan'];fields(plan,('goal','updates','checks'),'Plan');text(plan['goal'],'goal');require(bool(plan['updates']),'Missing Updates')
    ids=set()
    for u in plan['updates']:
        fields(u,('id','text'),'Update');text(u['id'],'ID');text(u['text'],'text');require(u['id'] not in ids,'Duplicate Update');ids.add(u['id'])
    cids=set()
    for c in plan['checks']:
        fields(c,('id','update_ids','question'),'Check');require(c['id'] not in ids|cids,'Duplicate Check');cids.add(c['id']);text(c['question'],'Question');links(c['update_ids'],ids,'Check updates')
    runs={r['ref']:validate_run(r) for r in payload['runs']};require(len(runs)==len(payload['runs']) and runs,'Duplicate/missing runs')
    paired=[];tasks=set()
    for pair in payload['pairs']:
        fields(pair,('parent','candidate','task_id','parent_result','candidate_result'),'Pair')
        require(pair['task_id'] not in tasks,'Duplicate paired task');tasks.add(pair['task_id'])
        for side,prefix in [('parent','P'),('candidate','Q')]:
            ref=pair[side];require(ref in runs and ref.startswith(prefix),'Invalid pair role')
            require(runs[ref]['task_id']==pair['task_id'] and pair[side+'_result']==pair_result(runs[ref]),'Pair task/result differs');paired.append(ref)
    require(len(paired)==len(set(paired)) and set(paired)==set(runs),'Pair coverage differs')
    mem.validate_memory(payload['memory'],memory_contract=memory_contract);return payload


def current_pairs(bundle):
    payload=validate_payload(bundle['payload']);audits=bundle['pair_audit'];require(len(audits)==len(payload['pairs']),'Pair audit missing')
    runs={r['ref']:r for r in payload['runs']}
    for pair,a in zip(payload['pairs'],audits):
        require(a['verified'] and a['task_id']==pair['task_id'] and a['pair']=={k:pair[k] for k in ('parent','candidate')},'Pair audit differs')
        require(a['parent_run_id']==runs[pair['parent']]['run_id'] and a['candidate_run_id']==runs[pair['candidate']]['run_id'],'Execution identity differs')
    return deepcopy(payload['pairs']),deepcopy(payload['runs'])


def model_input(bundle,*,memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    from ...memory_view import knowledge_only
    payload=validate_payload(bundle['payload'],memory_contract=memory_contract);current_pairs(bundle)
    return {k:deepcopy(v) for k,v in payload.items() if k!='memory'}|{'memory':knowledge_only(payload['memory'],memory_contract=memory_contract)}


def validate_bundle(bundle,*,memory_contract=mem.MULTI_KNOWLEDGE_CONTRACT):
    from ...editor import load_editor
    validate_payload(bundle['payload'],memory_contract=memory_contract);current_pairs(bundle);saved=load_editor(bundle['editor_directory']);p=bundle['payload']
    require(saved['editor_status']=='candidate' and bundle['candidate']==saved['candidate_text'] and p['diff']==saved['actual_diff'],'Replay edit lineage differs')
    require(p['parent']==saved['facts']['parent'] and bundle['background']==saved['background'],'Replay background differs')
    require([r for r in p['runs'] if r['ref'].startswith('P')]==saved['facts']['runs'],'Parent replay records differ')
    plan=saved['effective_plan'];expected={'goal':plan['goal'],'updates':[{k:u[k] for k in ('id','text')} for u in plan['updates']],'checks':plan['checks']}
    require(p['plan']==expected,'Replay Plan differs');return bundle


def extract(ref,bundle,historical):
    source=bundle;local=ref;history=None
    if '/' in ref:history,local=ref.rsplit('/',1);source=historical[history]
    current_pairs(source);p=source['payload']
    if local=='diff':return {'parent':p['parent'],'diff':p['diff'],'execution_context':deepcopy(source['execution_context'])}
    rid,_,suffix=local.partition(':');run=next(r for r in p['runs'] if r['ref']==rid)
    if not suffix:record=run
    elif suffix=='0':record=run['initial']
    elif suffix=='outcome':record=run['outcome']
    else:record=next(a for a in run['attempts'] if a['ref']==local)
    value={'task_id':run['task_id'],'run_id':run['run_id'],'role':'parent' if rid.startswith('P') else 'candidate','record':deepcopy(record)}
    if history:value['execution_context']=deepcopy(source['execution_context'])
    return value


def build_input(bundle,candidate,historical=None):
    from ...knowledge_evidence import select_targets
    from ...replay import validate_result
    historical=historical or {};p=validate_payload(bundle['payload']);validate_result(candidate,p)
    targets,inventory=select_targets(candidate,p['memory']);refs=list(dict.fromkeys(ref for t in targets for ref in t['knowledge']['evidence']))
    for cid in {ref.rsplit('/',1)[0] for ref in refs if '/' in ref}:
        prior=historical[cid];current_pairs(prior)
        for key,original in p['memory']['sources'].items():
            if key.rsplit('/',1)[0]!=cid:continue
            local=key.rsplit('/',1)[1]
            expected=extract(key,bundle,historical) if local=='diff' else {'run':next(r for r in prior['payload']['runs'] if r['ref']==local)}
            require(original==expected,'Historical source differs')
    cited={x.split(':')[0] for x in refs if '/' not in x and x!='diff'}
    pairs=[{k:pair[k] for k in ('parent','candidate','task_id')} for pair in p['pairs'] if pair['parent'] in cited or pair['candidate'] in cited]
    value={'context':{'parent':p['parent'],'diff':p['diff'],'execution_context':deepcopy(bundle['execution_context']),'pairs':pairs},'targets':targets,'source_records':{ref:extract(ref,bundle,historical) for ref in refs}}
    return value,inventory


def compact(value):
    fields(value,('context','targets','source_records'),'Knowledge input');return deepcopy(value)


def build_repair_input(value,verdicts,candidate):
    from ... import knowledge_verifier as v,knowledge_repair as repair
    v.validate_result(verdicts,value);original={v.position(t['target'],'target'):t for t in value['targets']};targets=[];refs=set()
    for row in verdicts['results']:
        if row['verdict']!='CONFLICT':continue
        ei,ki=key=v.position(row['target'],'target');t=deepcopy(original[key]);require(t['knowledge']==candidate['entries'][ei]['knowledge'][ki],'Target differs')
        t['issues']=deepcopy(row['issues']);targets.append(t);refs.update(t['knowledge']['evidence'])
        for issue in row['issues']:refs.update(issue['evidence'])
    context=deepcopy(value['context']);rids={r.split(':')[0] for r in refs if '/' not in r and r!='diff'}
    context['pairs']=[p for p in context['pairs'] if p['parent'] in rids or p['candidate'] in rids]
    return {'context':context,'targets':targets,'source_records':{r:deepcopy(value['source_records'][r]) for r in sorted(refs)}}


OPERATIONS={
'model_input.timeline_messages':model_messages,
'contracts.grouping.validate_grouping':validate_grouping,'contracts.diagnosis.diagnosis_input':diagnosis_input,
'contracts.preconditioner.preconditioner_input':preconditioner_input,
'contracts.memory.run_references':run_references,'contracts.memory.validate_run':validate_run,'contracts.memory._view':memory_view,
'contracts.replay.verify_pair':verify_pair,'contracts.replay.build_replay_from_editor':build_replay_from_editor,'contracts.replay.validate_payload':validate_payload,
'contracts.replay_view._current_pairs':current_pairs,'replay_view.model_input':model_input,'replay.validate_bundle':validate_bundle,
'knowledge_evidence.extract':extract,'knowledge_evidence.build_input':build_input,
'knowledge_evidence.compact':compact,'knowledge_evidence.restore':compact,'knowledge_evidence.build_repair_input':build_repair_input}
