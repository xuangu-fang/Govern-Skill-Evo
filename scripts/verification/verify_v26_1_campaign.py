"""Offline acceptance only: denied network, synthetic cases and read-only release preflight."""
import argparse
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'external/SkillAdam'),str(ROOT/'external/SkillOpt')]


def protected_sources():
    paths=[]
    for base in ('src','tests','scripts','docs/methods','experiments/configs'):
        paths.extend(p for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                     and 'offline_acceptance' not in p.parts and p.suffix in ('.py','.md','.json'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def historical_office():
    roots=[p for base in ('experiments/campaigns','experiments/evaluations')
           for p in (ROOT/base).glob('v26_officeqa*')]
    return {str(p.relative_to(ROOT)):[p.stat().st_size,p.stat().st_mtime_ns]
            for root in roots for p in root.rglob('*') if p.is_file()}


def preflight():
    from scripts.runs import run_v26_1_campaign as cli
    from src.skill_evolution.v26_1 import config,protocol as p
    path=ROOT/'experiments/configs/v26_1_officeqa_train74.json'
    cfg=json.loads(path.read_text());method=cli.bind(cfg)
    with method.using():
        config.validate_config(cfg,executable=True)
        assert method.dataset.batches==p.PLAN['schedule']['batches']
        assert method.dataset.splits['test']==p.PLAN['schedule']['test_ids']
        assert sum(method.dataset.case(t).metadata['source_split']=='validation' for t in method.dataset.splits['train'])==24
        assert len(config.MODULES)==4
        assert len(p.initial_skill())==887
        for name,value in config.render_prompts().items():
            assert value==(p.PROMPT_ROOT/f'{name}.md').read_text()
        initial=[]
        for tid in method.dataset.splits['train']+method.dataset.splits['test']:
            case=method.dataset.case(tid)
            messages,_=method.runtime.prepare(case,p.initial_skill())
            encoded=json.dumps(messages,ensure_ascii=False)
            initial.append((len(encoded),len(encoded.encode())))
    source_map=json.loads((p.DESIGN/'baseline/source_files.json').read_text())
    for item in source_map['files']:
        assert (ROOT/item['source']).read_bytes()==(p.DESIGN/item['snapshot']).read_bytes(),item['source']
    environ_get = cli.os.environ.get
    def no_credentials(key, *args):
        assert not any(token in str(key).upper() for token in ('API_KEY','TOKEN','SECRET','PASSWORD')), 'No credentials'
        return environ_get(key, *args)
    with tempfile.TemporaryDirectory(prefix='v26_1_readonly_') as tmp:
        campaign=Path(tmp)/'must_not_exist'
        with patch.object(cli,'run_training',side_effect=AssertionError('No real training')), \
             patch.object(cli,'run_test',side_effect=AssertionError('No real Test')), \
             patch.object(cli,'ChatTransport',side_effect=AssertionError('No live transport')), \
             patch.object(cli,'HTTPGenerator',side_effect=AssertionError('No optimizer transport')), \
             patch.object(cli.os.environ,'get',side_effect=no_credentials):
            cli.main(['train',str(campaign),'--config',str(path),'--validate-only'])
        assert not campaign.exists()
    return {'status':'passed','method':config.METHOD_VERSION,'optimization_count':74,'test_count':172,
            'batch_sizes':[10]*7+[4],'source_validation_count':246,'base_skill_chars':887,
            'initial_messages_max_chars':max(v[0] for v in initial),'initial_messages_max_utf8_bytes':max(v[1] for v in initial),
            'design_prompts':'byte_equal','baseline_files_unchanged':len(source_map['files']),
            'model_requests':0,'credentials_read':False,'training_started':False,'test_started':False}


# Each acceptance row points to actual executed assertions, not a static presence check.
MAP={
 'A01':['v26_1/test_campaign.py::test_data_and_configuration_drift_rejected','preflight'],
 'A02':['v26_1/test_actor_boundary.py::test_original_messages_and_exact_crlf_skill'],
 'A03':['v26_1/test_campaign.py::test_complete_synthetic74_and172'],
 'A04':['v26_1/test_actor_boundary.py::test_native_answer_parse','v26_1/test_actor_boundary.py::test_original_scoring'],
 'A05':['officeqa/test_local.py::test_tool_scope_literal_search_and_limits','officeqa/test_aligned.py::test_tool_scope_read_truncation'],
 'A06':['v26_1/test_contracts.py::test_formal_multiturn','v26/test_facts.py::test_multiple_rounds_may_reuse'],
 'A07':['officeqa/test_aligned.py::test_24_round_exhaustion','v26_1/test_actor_boundary.py::test_exhaustion'],
 'A08':['v26_1/test_actor_boundary.py::test_actor_saved_response','officeqa/test_retry.py::test_completed_tools','officeqa/test_retry.py::test_unknown_tool'],
 'A09':['v26_1/test_campaign.py::test_published_history','v26_1/test_campaign.py::test_unobserved_source_changes'],
 'A10':['v26_1/test_contracts.py::test_formal_multiturn','v26_1/test_stages.py::test_feedback_budget'],
 'A11':['v26/test_facts.py::test_formal_tool_rounds','v26_1/test_contracts.py::test_formal_multiturn'],
 'A12':['v26_1/test_contracts.py::test_formal_multiturn','v26/test_input_view.py::test_all_round_lengths'],
 'A13':['v26/test_input_view.py::test_initial_sharing','v26/test_input_view.py::test_small_payload'],
 'A14':['v26_1/test_capacity_and_references.py::test_tool_ids_and_ranges','v26_1/test_contracts.py::test_diagnosis_reference_rejections','v26_1/test_contracts.py::test_preconditioner_actions'],
 'A15':['v26_1/test_contracts.py::test_replay_selective_gate','v26/test_evidence.py::test_pairs_use_ids'],
 'A16':['v26_1/test_contracts.py::test_formal_multiturn','v26_1/test_campaign.py::test_short_circuits'],
 'A17':['v26_1/test_contracts.py::test_formal_multiturn'],
 'A18':['v26_1/test_contracts.py::test_preconditioner_actions'],
 'A19':['v26_1/test_contracts.py::test_preconditioner_actions'],
 'A20':['v26_1/test_editor.py::PatchCompositionTests'],
 'A21':['v26_1/test_editor.py::PatchCompositionTests'],
 'A22':['v26_1/test_editor.py::PatchCompositionTests'],
 'A23':['v26_1/test_campaign.py::test_null_editor','v26_1/test_campaign.py::test_short_circuits'],
 'A24':['v26_1/test_campaign.py::test_complete_synthetic74_and172'],
 'A25':['v26_1/test_contracts.py::test_gate_branches','v26_1/test_contracts.py::test_replay_selective_gate'],
 'A26':['v26_1/test_contracts.py::test_replay_selective_gate','v26_1/test_contracts.py::test_no_modification'],
 'A27':['v26_1/test_contracts.py::test_replay_selective_gate'],
 'A28':['v26_1/test_contracts.py::test_gate_branches','v26_1/test_contracts.py::test_no_modification'],
 'A29':['v26_1/test_contracts.py::test_replay_selective_gate','v26_1/test_contracts.py::test_no_modification'],
 'A30':['v26_1/test_memory.py::test_stale_head','v26_1/test_campaign.py::test_complete_synthetic74_and172'],
 'A31':['v26_1/test_campaign.py::test_short_circuits','v26_1/test_campaign.py::test_null_editor'],
 'A32':['v26_1/test_stages.py::test_shared_six','v26_1/test_stages.py::test_method_http','officeqa/test_retry.py::test_http_classification'],
 'A33':['v26_1/test_stages.py::test_saved_response','v26/test_recovery_hardening.py::test_preparation_crash'],
 'A34':['v26_1/test_campaign.py::test_publication_interrupt','v26_1/test_memory.py::test_atomic_prepublication'],
 'A35':['v26_1/test_memory.py::test_stale_head','v26_1/test_memory.py::test_atomic_prepublication'],
 'A36':['v26_1/test_campaign.py::test_published_history','v26_1/test_memory.py::test_stale_head'],
 'A37':['v26_1/test_campaign.py::test_complete_synthetic74_and172'],
 'A38':['v26_1/test_campaign.py::test_incomplete_test'],
 'A39':['v26_1/test_capacity_and_references.py::test_actual_large_utf8','v26_1/test_capacity_and_references.py::test_large_memory','v26_1/test_stages.py::test_capacity'],
 'A40':['preflight'], 'A41':['protection','preflight'],
 'A42':['v26_1/test_actor_boundary.py::test_actor_saved_response','v26_1/test_campaign.py::test_incomplete_test']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);output=Path(args.output).resolve()
    assert output.is_relative_to(ROOT/'docs/methods/v26_1/offline_acceptance'), 'Use the dedicated acceptance directory'
    output.mkdir(parents=True,exist_ok=True)
    before=protected_sources();history=historical_office();reports=[];blocked=[];check={};error=None
    def deny(*args,**kwargs):
        blocked.append('denied')
        raise AssertionError('Network or child process forbidden during offline acceptance')
    class Results:
        def pytest_runtest_logreport(self,report):
            if report.when=='call' or report.failed:
                reports.append({'nodeid':report.nodeid,'outcome':report.outcome})
    with ExitStack() as stack:
        for obj,name in ((socket.socket,'connect'),(socket.socket,'connect_ex'),(socket,'create_connection'),(socket,'getaddrinfo')):
            stack.enter_context(patch.object(obj,name,deny))
        stack.enter_context(patch('subprocess.Popen',deny))
        with (output/'preflight.log').open('w') as log,redirect_stdout(log),redirect_stderr(log):
            try:check=preflight()
            except Exception as exc:error=f'{type(exc).__name__}: {exc}'
        import pytest
        with (output/'pytest.log').open('w') as log,redirect_stdout(log),redirect_stderr(log):
            result=pytest.main(['-q','-p','no:cacheprovider','--tb=short',
                f'--junitxml={output / "junit.xml"}',
                'tests/skill_evolution/v26_1','tests/skill_evolution/v26','tests/adapters/officeqa'],plugins=[Results()])
    after=protected_sources();changed=[p for p,value in before.items() if after.get(p)!=value]
    history_changed=history!=historical_office()
    passed={r['nodeid'] for r in reports if r['outcome']=='passed'}
    cases=[]
    design=json.loads((ROOT/'docs/methods/v26_1/acceptance_matrix.json').read_text())
    for case in design['cases']:
        evidence=[];missing=[]
        for selector in MAP[case['id']]:
            if selector=='preflight':matches=['preflight.log'] if not error else []
            elif selector=='protection':matches=['protected_files.json'] if not changed and not history_changed else []
            else:matches=sorted(n for n in passed if selector in n)
            if not matches:missing.append(selector)
            evidence.extend(matches)
        cases.append({'id':case['id'],'title':case['title'],'status':'passed' if not missing else 'failed',
                      'evidence':evidence,'missing':missing})
    import xml.etree.ElementTree as ET
    skipped=[{'test':t.attrib.get('classname','')+'::'+t.attrib['name'],
              'reason':t.find('skipped').attrib.get('message')}
             for t in ET.parse(output/'junit.xml').iter('testcase') if t.find('skipped') is not None]
    summary={'skipped_tests':skipped, 'status':'passed' if result==0 and error is None and not changed and not history_changed and
             all(c['status']=='passed' for c in cases) else 'failed',
             'scope':'Offline synthetic execution and read-only real-data preflight; no real training or Test',
             'pytest_exit_code':int(result),'passed_test_nodes':len(passed),
             'preflight':check,'preflight_error':error,'acceptance_cases':cases,
             'protected_source_files':len(before),'changed_protected_files':changed,
             'historical_office_files':len(history),'historical_office_changed':history_changed,
             'network_denied_attempts':len(blocked),'real_network_requests':0,'real_training_started':False,'real_test_started':False}
    for name,value in [('summary',summary),('test_results',reports),('protected_files',before),('historical_files',history)]:
        (output/f'{name}.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('acceptance_cases',)},ensure_ascii=False,indent=2))
    return 0 if summary['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
