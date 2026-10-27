"""Deterministic before/after evidence coverage; no automatic semantic grading."""
import json
from .round2 import HERE, FIRST, core, NEW
from src.skill_evolution.v23_3.memory_view import compact_memory
from src.skill_evolution.v23.memory import entry_evidence

def size(value):return len(json.dumps(value,ensure_ascii=False,separators=(',',':')))

def main():
    before=core.read(HERE/'config/replay_bundle.json')['payload']['memory']
    after=core.read(HERE/'cases/ROUND2/results/memory_candidate.json')
    first=core.read(FIRST/'cases/R05/results/MEMORY_AUDIT.json')['new_entries']
    first_ids={e['id'] for e in first}
    selected=core.read(HERE/'runs/ROUND2_replay/selected.json')['attempt']
    proposal=core.read(HERE/f'runs/ROUND2_replay/attempt_{selected:03}/parsed.json')
    index={e['id']:e for e in before['entries']}
    rows=[]
    for e in proposal['entries']:
        old=[index[mid] for mid in e['revises']]
        oldrefs={r for x in old for r in entry_evidence(x,memory_contract=NEW)}
        # New proposal current refs gain their context on commit; compare history refs only here.
        newrefs={r for k in e['knowledge'] for r in k['evidence']}
        rows.append({'revises':e['revises'],'revises_first_generated_ids':sorted(first_ids & set(e['revises'])),
            'before_complete_entries':old,'after_complete_knowledge':e['knowledge'],
            'old_evidence_not_repeated':sorted(oldrefs-newrefs),
            'new_evidence':sorted(newrefs-oldrefs),
            'note':'Reference loss is a retrieval fact, not automatic semantic forgetting; related claims may be synthesized or retained elsewhere.'})
    views={label:compact_memory(m,memory_contract=NEW) for label,m in [('before',before),('after',after)]}
    summary={}
    for label,m in [('before',before),('after',after)]:
        ks=[k for e in m['entries'] for k in e['knowledge']];v=views[label]
        summary[label]={'entries':len(m['entries']),'knowledge_items':len(ks),
          'knowledge_text_chars':sum(len(k['text']) for k in ks),'memory_v3_chars':size(v),
          'source_keys':sorted(v['sources']),
          'windows':{key:val['windows'] for key,val in v['sources'].items() if not key.endswith('/diff')}}
    report={'classification':'offline_controlled_sibling_edit_revision',
      'first_generated_ids':sorted(first_ids),'first_generated_ids_revised':sorted(first_ids & {x for e in proposal['entries'] for x in e['revises']}),
      'first_generated_ids_left_active':sorted(first_ids & {e['id'] for e in after['entries']}),
      'summary':summary,'revisions':rows}
    (FIRST/'ROUND2_REVISION_METRICS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('first_generated_ids','first_generated_ids_revised','first_generated_ids_left_active')},ensure_ascii=False))

if __name__=='__main__':main()
