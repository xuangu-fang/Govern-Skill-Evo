"""Offline score audit of preserved outputs. No Actor or optimizer invocation."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.skilladam.spreadsheetbench.layout import ALIGNED_CONFIG as HOME, UPSTREAM_RECORD as OLD
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.scheduled.actor_runtime.benchmarks.spreadsheetbench import scoring as old
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmarks.spreadsheetbench import scoring as new


def read(p):return json.loads(p.read_text())


def offline_boundary(event,args):
    if event in {'socket.connect','socket.connect_ex','subprocess.Popen','os.system','os.exec','os.posix_spawn'}:
        raise AssertionError('Offline score audit forbids external execution')


def audit(output):
    sys.addaudithook(offline_boundary)
    shared=read(HOME/'shared_config.json'); evaluation=read(HOME/'evaluation/config.json')
    train=[t for batch in shared['batches'] for t in batch]
    assert len(train)==120 and len(set(train))==120
    assert all(old.regions(shared['task_items'][t]['answer_region']) ==
               new.regions(shared['task_items'][t]['answer_region']) for t in train)
    test_changes=[]
    for tid in shared['test_tasks']:
        prior=shared['task_items'][tid]['answer_region'];current=evaluation['task_items'][tid]['answer_region']
        parsed=new.regions(current)
        try:before=old.regions(prior)
        except ValueError:before=None
        if before!=parsed:
            test_changes.append({'task':tid,'old_region':prior,'new_region':current,
                                 'old_parser_rejected':before is None,'new_parsed':parsed})
    # One preserved training rollout per task; recompute scores without executing programs.
    records={}
    for path in sorted((OLD/'campaign/shared_actor').glob('*/training_rollout_*/**/trajectory.json')):
        record=read(path);tid=record['task']['id']
        if tid in train and tid not in records:
            records[tid]=(path,record)
    assert set(records)==set(train)
    results=[]
    for tid in train:
        path,record=records[tid];task=record['task']
        output_path = record['output_path']
        if output_path:
            output_path = path.parent / Path(output_path).relative_to(Path(record['input_snapshot']).parent)
        args=(output_path,task['answer_path'],task['answer_region'],shared['actor_profile'])
        a=old.score(*args);b=new.score(*args)
        assert all(a[k]==b[k]==record['score'][k] for k in ['hard','correct_cells','total_cells']),tid
        assert {k:v for k,v in a.items() if k!='per_cell_pass_rate'} == {
            k:v for k,v in b.items() if k!='per_cell_pass_rate'},tid
        assert b['per_cell_pass_rate']==round(a['per_cell_pass_rate'],4),tid
        results.append({'task':tid,'trajectory':str(path),'trajectory_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'hard':b['hard'],'correct_cells':b['correct_cells'],'total_cells':b['total_cells'],
            'old_rate':a['per_cell_pass_rate'],'aligned_rate':b['per_cell_pass_rate']})
    report={'status':'passed','training_regions_equal':120,'historical_training_outputs_rescored':120,
        'hard_or_cell_count_differences':0,'non_rate_diagnostic_differences':0,
        'rates_rounded_only':sum(r['old_rate']!=r['aligned_rate'] for r in results),
        'test_regions_parsed':280,'test_region_compatibility_changes':test_changes,
        'historical_records_edited':False,'model_requests':0,'programs_executed':0,
        'scope':'Rescoring existing outputs only; not new training or test results.',
        'records':results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    audit(parser.parse_args().output)
