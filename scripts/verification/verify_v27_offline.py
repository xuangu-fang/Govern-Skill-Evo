"""Run v27 synthetic acceptance in the independent LMB environment, without network."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'external/SkillAdam')]

class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.outcomes={}
    def addSuccess(self,test):
        super().addSuccess(test);self.outcomes[test.id()]='passed'
    def addFailure(self,test,err):
        super().addFailure(test,err);self.outcomes[test.id()]='failed'
    def addError(self,test,err):
        super().addError(test,err);self.outcomes[test.id()]='error'
    def addSkip(self,test,reason):
        super().addSkip(test,reason);self.outcomes[test.id()]='skipped'
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if err is not None:self.outcomes[test.id()]='failed_subtest'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    if Path(sys.prefix).name!='LiveMathematicianBench':raise RuntimeError('Use the new LiveMathematicianBench environment')
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    connections=[]
    def blocked(*args,**kwargs):
        connections.append('blocked');raise AssertionError('Offline suite attempted a network connection')
    protected=[ROOT/'data/livemathematicianbench/prepared_v1',ROOT/'data/livemathematicianbench/raw/data']
    def snapshot():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for base in protected for p in sorted(base.rglob('*.json'))}
    before=snapshot()
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket,'connect',blocked))
        stack.enter_context(patch.object(socket.socket,'connect_ex',blocked))
        stack.enter_context(patch('socket.create_connection',blocked))
        stack.enter_context(patch('subprocess.Popen',side_effect=AssertionError('Offline suite cannot spawn model processes')))
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/skill_evolution/v27'),pattern='test_*.py',top_level_dir=str(ROOT))
        def test_ids(value):
            for item in value:
                if isinstance(item,unittest.TestSuite):yield from test_ids(item)
                else:yield item.id()
        discovered=set(test_ids(suite))
        with (out/'unittest.log').open('w') as log:
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
        from tests.skill_evolution.v27 import capacity_fixture
        from src.skill_evolution.v27.benchmark import using_benchmark
        from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
        from src.skill_evolution.v27.benchmarks.lmb import protocol as p
        capacity_reports={}
        with tempfile.TemporaryDirectory() as tmp,using_benchmark(LMBAdapter(gate_metric=p.EM_GATE)):
            for scenario,stress in (('bounded_complete',False),('larger_rejection',True)):
                fixture=capacity_fixture.build(Path(tmp)/scenario,stress=stress)
                capacity_reports[scenario]=fixture['report']
                target=out/'c01_messages'/scenario;target.mkdir(parents=True,exist_ok=True)
                for name,messages in fixture['messages'].items():
                    (target/(name+'.json')).write_text(json.dumps(messages,ensure_ascii=False,indent=2)+'\n')
        (out/'capacity.json').write_text(json.dumps(capacity_reports,ensure_ascii=False,indent=2)+'\n')
    unchanged=before==snapshot()
    from tests.skill_evolution.v27.source_provenance import verify as verify_sources
    try:
        provenance = {'status': 'passed', **verify_sources(ROOT)}
    except (ValueError, KeyError, OSError) as exc:
        provenance = {'status': 'failed', 'error': str(exc)}
    (out/'source_provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
    summary={'status':'passed' if result.wasSuccessful() and unchanged and not connections and provenance['status']=='passed' else 'failed',
             'python':sys.executable,'environment':sys.prefix,'tests_run':result.testsRun,
             'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
             'real_model_requests':0,'network_connection_attempts':len(connections),
             'experiments_started':0,'data_hashes_unchanged':unchanged,'synthetic_actor_only':True,
             'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src/skill_evolution/v27').rglob('*')) if p.suffix in ('.py','.md','.json')},
             'verification_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in [Path(__file__),*sorted((ROOT/'tests/skill_evolution/v27').glob('*.py')),*sorted((ROOT/'tests/skill_evolution/v27').glob('*.json'))]}}
    import re
    mapping=json.loads((ROOT/'tests/skill_evolution/v27/acceptance_map.json').read_text())
    expected=re.findall(r'^\| ([A-Z]+\d+) \|',(ROOT/mapping['design_checklist']).read_text(),re.M)
    assert [r['id'] for r in mapping['scenarios']]==expected
    assert all(set(r['tests'])<=discovered for r in mapping['scenarios'])
    for row in mapping['scenarios']:
        row['test_results']={name:result.outcomes.get(name,'not_run') for name in row['tests']}
        row['status']='mapped_automatic_checks_passed' if all(v=='passed' for v in row['test_results'].values()) else 'mapped_automatic_checks_failed'
        row['evidence']='unittest.log'
        if 'manual_review' in row:
            row['manual_review']['status']='previous_fixture_review_not_reexecuted'
    for row in mapping.get('review_regressions',[]):
        assert set(row['tests'])<=discovered
        row['test_results']={name:result.outcomes.get(name,'not_run') for name in row['tests']}
        row['status']='passed' if all(v=='passed' for v in row['test_results'].values()) else 'failed'
    (out/'acceptance.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    summary['acceptance_scenarios']=len(expected)
    summary['manual_fixture_supplements']=sum('manual_review' in row for row in mapping['scenarios'])
    summary['real_model_semantics_verified']=False
    summary['acceptance_status_scope']='Mapped automatic checks only; historical manual fixtures are supplemental, not reexecuted judgments.'
    summary['c01_report']='capacity.json'
    summary['provider_context_capacity_verified']=False
    summary['source_provenance_report']='source_provenance.json'
    (out/'test_results.json').write_text(json.dumps(result.outcomes,indent=2)+'\n')
    (out/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('source_sha256','verification_sha256')},indent=2))
    if summary['status']!='passed':
        print((out/'unittest.log').read_text()[-12000:]);raise SystemExit(1)
if __name__=='__main__':main()
