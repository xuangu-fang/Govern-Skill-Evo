"""Read-only provenance audit and precommitted choice of controlled round 2."""
from pathlib import Path
import hashlib
import json
from copy import deepcopy
from .run import HERE, ROOT, P4, core, NEW
from src.skill_evolution.v23 import replay, memory
from src.skill_evolution.v23.facts import build_facts

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

def identities(bundle):
    return {a[s]['run_id'] for a in bundle['pair_audit'] for s in ('parent','candidate')}

def main():
    first=core.read(P4/'cases/R05/replay_bundle.json')
    other=core.read(P4/'cases/R06/replay_bundle.json')
    formal=ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds'
    source=formal/'R05/pairs/input.json'
    next_bundle=core.read(source)
    prior=memory.load_memory(formal/'R04/memory', memory_contract=NEW)
    assert first['payload']['memory']==prior
    assert memory.validate_memory(next_bundle['payload']['memory'])
    # Rebuild from the real records, without reinterpreting historical Editor Prompt.
    records={s:[core.read(Path(p)) for p in next_bundle['record_paths'][s]] for s in ('parent','candidate')}
    editor=Path(next_bundle['editor_directory'])
    editor_input=core.read(editor/'input.json')
    assert editor_input['parent']==next_bundle['payload']['parent']
    assert (editor/'actual.diff').read_text()==next_bundle['payload']['diff']
    assert (editor/'candidate.md').read_text()==next_bundle['candidate']
    assert editor_input['plan']['goal']==next_bundle['payload']['plan']['goal']
    saved={'editor_status':'candidate','facts':build_facts(records['parent'])['facts'],
           'actual_diff':next_bundle['payload']['diff'],'candidate_text':next_bundle['candidate'],
           'effective_plan':editor_input['plan'],'background':next_bundle['background']}
    rebuilt=replay.build_replay_from_editor(saved,editor,records['parent'],records['candidate'],
          memory=next_bundle['payload']['memory'])
    for key in rebuilt:
        assert rebuilt[key]==next_bundle[key],key
    used=identities(first)
    history=[]
    for cid in sorted({s.split('/')[0] for s in first['payload']['memory']['sources']}):
        archive=formal/f'R04/memory/archive/{cid}.json'
        data=core.read(archive)
        used.update(identities(data['context']))
        history.append({'context':cid,'archive':str(archive.relative_to(ROOT)),'sha256':core.sha(archive)})
    new=identities(next_bundle)
    assert not used & new
    assert first['payload']['parent']==next_bundle['payload']['parent']
    assert first['candidate']!=next_bundle['candidate']
    # No formal-R05 facts are in the first model-visible historical sources.
    assert not any(k.startswith('S1_R05/') for k in first['payload']['memory']['sources'])
    inventory=[]
    for p in sorted(formal.glob('R*')):
        e=p/'editor'/core.read(p/'editor/result.json')['path']
        inventory.append({'round':p.name,'parent_sha256':core.sha(p/'parent.md') if (p/'parent.md').exists() else None,
            'candidate_sha256':core.sha(e/'candidate.md'),'gate_outcome':core.read(p/'result.json')['outcome']})
    report={'classification':'offline_controlled_sibling_edit_revision_NOT_continuous_skill_evolution',
      'selection_fixed_before_reading_V3_output':True,
      'natural_R05_to_R06_valid':False,
      'natural_failure_reasons':['R05 experimental Candidate differs from R06 Parent',
          'R06 actual executions precede R05 experimental executions',
          'R06 initial Memory descends from formal R05, not experimental R05'],
      'experimental_R05':{'parent_sha256':digest(first['payload']['parent']),'candidate_sha256':digest(first['candidate']),
          'run_ids':sorted(identities(first))},
      'experimental_R06':{'parent_sha256':digest(other['payload']['parent']),'candidate_sha256':digest(other['candidate']),
          'run_ids':sorted(identities(other))},
      'selected_second_feedback':{'source':str(source.relative_to(ROOT)),'sha256':core.sha(source),
          'parent_sha256':digest(next_bundle['payload']['parent']),'candidate_sha256':digest(next_bundle['candidate']),
          'run_ids':sorted(new),'pairs':len(next_bundle['payload']['pairs']),
          'raw_record_rebuild_equals_archive':True,'shared_exact_parent':True,
          'run_id_overlap_with_all_first_input_contexts':sorted(used & new),
          'same_task_instances_different_real_executions':True,
          'chronology':'formal feedback executed 2026-10-19; first experimental feedback executed 2026-10-22; offline ingestion reverses execution order',
          'limitations':['No Candidate-to-Parent transition','No live continual-learning claim',
              'New to this R05 Memory only; formal R05 was already historical evidence in independent R06 stage-1 arm',
              'Tests revision with another intervention at the same exact ancestor, not repeated performance of the first Candidate']},
      'first_history_archives':history,'formal_skill_inventory':inventory,
      'frozen_files':{str(Path(p).relative_to(ROOT)):core.sha(Path(p)) for s in records for p in next_bundle['record_paths'][s]}}
    core.save(HERE/'LINEAGE.json',report)
    print(json.dumps({k:report[k] for k in ('classification','natural_R05_to_R06_valid')},ensure_ascii=False))

if __name__=='__main__':main()
