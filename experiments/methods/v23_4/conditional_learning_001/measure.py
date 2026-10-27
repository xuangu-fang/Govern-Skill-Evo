"""Offline comparison of proposals and unchanged downstream projection paths."""
from copy import deepcopy
import json
from .run import HERE,ROOT,P6,P4,core,NEW
from src.skill_evolution.v23_3.memory_view import project_messages,compact_memory
from src.skill_evolution.v23.memory import entry_evidence

def chars(x):return len(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def stats(entries):
    items=[k for e in entries for k in e['knowledge']]
    return {'entries':len(entries),'knowledge_items':len(items),'text_chars':sum(len(k['text']) for k in items),
      'longest_text_chars':max([len(k['text']) for k in items],default=0),
      'evidence_occurrences':sum(len(k['evidence']) for k in items),
      'unique_evidence':len({r for k in items for r in k['evidence']})}

def pc_messages(case,loaded):
    p=(HERE.with_name('semantic_generation_006')/'config/cases/R05.json' if case=='R05'
       else HERE.with_name('semantic_generation_004')/'handoff/preconditioner_input.json')
    source=core.read(p);payload=deepcopy(source['payload']);payload['memory']=loaded
    return project_messages([{'role':'system','content':core.render_prompt(core.preconditioner.PROMPT_PATH.read_text(),source['background'])},
       {'role':'user','content':json.dumps(payload,ensure_ascii=False,separators=(',',':'))}],memory_contract=NEW)

def coverage(view):
    current=[k for k in view['sources'] if k.startswith('v23_4_') and not k.endswith('/diff')]
    return {'retained_runs':[k.rsplit('/',1)[-1] for k in current],
       'windows':{k.rsplit('/',1)[-1]:view['sources'][k]['windows'] for k in current},
       'all_runs':sum(not k.endswith('/diff') for k in view['sources']),
       'trace_steps':sum(len(v['run']['trace']) for k,v in view['sources'].items() if not k.endswith('/diff')),
       'detailed_steps':sum(len(v['detailed_steps']) for k,v in view['sources'].items() if not k.endswith('/diff'))}

def main():
    core.verify();out={}
    for case in ('R05','R06'):
        original=core.read(P4/f'cases/{case}/replay_bundle.json')['payload']['memory']
        before=compact_memory(original,memory_contract=NEW);versions={}
        for label,root in [('p4_baseline',P6),('candidate',HERE)]:
            selected=core.read(root/f'runs/{case}_replay/selected.json')['attempt']
            proposal=core.read(root/f'runs/{case}_replay/attempt_{selected:03}/parsed.json')
            loaded=core.read(root/f'cases/{case}/results/memory_candidate.json');view=compact_memory(loaded,memory_contract=NEW)
            messages=pc_messages(case,loaded)
            assert json.loads(messages[1]['content'])['memory']==view
            marker=f'v23_4_{case}_'+('multi_knowledge_p6_001' if label=='p4_baseline' else 'conditional_learning_001')
            normalized_user=messages[1]['content'].replace(marker,'EXPERIMENT_CONTEXT')
            normalized_view=json.dumps(view,ensure_ascii=False,separators=(',',':')).replace(marker,'EXPERIMENT_CONTEXT')
            attempts=[]
            for p in core.archive_glob(root/f'runs/{case}_replay', 'attempt_*'):
                a=core.read(p/'attempt.json');r=core.read(p/'response.json') if core.resolve(p/'response.json').exists() else {}
                attempts.append({'attempt':a['attempt'],'status':a['status'],'usage':r.get('usage'),
                  'finish_reason':r.get('finish_reason'),'max_tokens':a['max_tokens'],'elapsed_seconds':a['elapsed_seconds']})
            versions[label]={'proposal':stats(proposal['entries']),'after_active':stats(loaded['entries']),
               'revises':[e['revises'] for e in proposal['entries']], 'after_active_ids':[e['id'] for e in loaded['entries']],
               'memory_v3_chars':chars(view),'normalized_memory_v3_chars':len(normalized_view),
               'pc_system_chars':len(messages[0]['content']),'pc_user_chars':len(messages[1]['content']),
               'normalized_pc_user_chars':len(normalized_user),'coverage':coverage(view),'calls':attempts,
               'selected_attempt':selected,'selected_usage':core.read(root/f'runs/{case}_replay/attempt_{selected:03}/response.json')['usage']}
        out[case]={'before':stats(before['entries']),'before_v3_chars':chars(before),'versions':versions,
           'note':'PC is a fixed offline consumption probe, not a new Diagnosis/Preconditioner call or evidence of Skill improvement. Normalization changes only experiment-ID length for cost comparison.'}
    (HERE/'COMPARISON_METRICS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({case:{v:{k:d[k] for k in ('proposal','after_active','revises','memory_v3_chars','normalized_pc_user_chars','selected_usage')} for v,d in o['versions'].items()} for case,o in out.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
