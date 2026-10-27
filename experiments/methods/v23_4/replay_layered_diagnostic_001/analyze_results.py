"""Read-only checks of sent evidence, final content references and prior Replay.
Writes only new analysis artifacts in this isolated directory. No network.
"""
import json
import re
from pathlib import Path

from experiments.methods.v23_4.archive_io import resolve

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(resolve(p).read_text())
def write(name,data): (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def main():
    sources={};checks=[];reference_checks=[]
    for case in ('R05','R06'):
        a=read(HERE/f'config/{case}_A/request.json')['body']
        b=read(HERE/f'config/{case}_B/request.json')['body']
        av=json.loads(a['messages'][1]['content']);bv=json.loads(b['messages'][1]['content'])
        assert av['questions']==bv['questions']
        assert a['messages'][0]==b['messages'][0]
        assert {k:v for k,v in a.items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'}
        old=HERE.with_name('multi_knowledge_p6_001')/f'runs/{case}_replay'
        chosen=read(old/'selected.json')['attempt']; p6path=old/f'attempt_{chosen:03}/http/request.json'
        p6=read(p6path)['body'];original=json.loads(p6['messages'][1]['content'])
        assert bv['evidence']==original
        assert p6['messages'][1]['content'] in b['messages'][1]['content']
        for key in ('model','max_tokens','temperature','reasoning_effort','thinking','stream'):
            if key in p6:assert p6[key]==b[key]
        for key in ('parent','diff','plan'):assert av['evidence'][key]==original[key]
        for r in av['evidence']['runs']:assert r==next(x for x in original['runs'] if x['ref']==r['ref'])
        for key,s in av['evidence']['memory']['sources'].items():assert s==original['memory']['sources'][key]
        for e in av['evidence']['memory']['entries']:assert e==next(x for x in original['memory']['entries'] if x['id']==e['id'])
        checks.append({'case':case,'p6_request':str(p6path.relative_to(HERE.parent)),
            'full_user_evidence_identical':True,'original_user_serialization_embedded_verbatim':True,
            'same_questions_system_parameters_between_arms':True,'local_objects_unchanged':True,
            'no_historical_state_expansion':True})
        prior=read(old/f'attempt_{chosen:03}/parsed.json')
        sources[case]={'file':str((old/f'attempt_{chosen:03}/parsed.json').relative_to(HERE.parent)),
                       'original_replay':prior}
        for arm,obj in [('A',av),('B',bv)]:
            v=obj['evidence'];known={'parent','diff','plan'};initials={};windows={};lengths={}
            for r in v['runs']:
                known.add(r['ref']);known.update(t['step'] for t in r['steps']);lengths[r['ref']]=len(r['steps'])
            for key,s in v['memory']['sources'].items():
                known.add(key)
                if not key.endswith('/diff'):
                    known.update(t['step'] for t in s['run']['trace']);lengths[key]=len(s['run']['trace'])
                    windows[key]=s.get('windows',s.get('detail_windows'))
            mids={e['id'] for e in v['memory']['entries']};known.update(mids)
            # Diagnostics permit identifiable evidence pointers, not only the
            # production Memory reference grammar. Menus and Plan IDs exist.
            known.update(v['command_sets']);known.update(v['memory']['command_pool'])
            known.update('plan:'+u['id'] for u in v['plan']['updates'])
            aliases={'parent skill':'parent','current diff':'diff'}
            aliases.update({'memory:'+x:x for x in mids})
            for pair in v['pairs']:
                aliases.update({pair['task_id']+'/'+pair[side]:pair[side] for side in ('parent','candidate')})
            for path in sorted((HERE/f'runs/{case}_{arm}').glob('attempt_*/parsed.json')):
                issues=[];n=0
                for ans in read(path)['answers']:
                    for fi,fact in enumerate(ans['facts']):
                        for ref in fact['sources']:
                            n+=1;norm=aliases.get(ref,ref)
                            if norm not in known:
                                issues.append({'question':ans['id'],'fact_index':fi,'reference':ref,
                                  'issue':'not an existing supplied source ID (manual interpretation still needed)'})
                reference_checks.append({'file':str(path.relative_to(HERE)),'reference_count':n,'unresolved':issues})
    write('INPUT_VERIFICATION.json',checks)
    write('REFERENCE_AUDIT.json',reference_checks)
    write('P6_COMPARISON_SOURCE.json',sources)
    print(json.dumps({'input_checks':len(checks),'outputs_checked':len(reference_checks),
        'unresolved_references':[{'file':x['file'],'issues':x['unresolved']} for x in reference_checks if x['unresolved']]},ensure_ascii=False))

if __name__=='__main__':main()
