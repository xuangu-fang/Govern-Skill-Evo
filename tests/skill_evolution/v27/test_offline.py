"""No real tasks are sent to an Actor; production data is inspected only offline."""
from copy import deepcopy
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
from src.skill_evolution.v27.benchmarks.lmb import protocol as p, facts, evidence, prompting, actor
from src.skill_evolution.v27.benchmarks.lmb.scoring import score
from src.skill_evolution.v27 import modules, replay as replay_contract, evolution, stages
from src.skill_evolution.v27.contracts import diagnosis as dc, memory, gate
from src.skill_evolution.v27.contracts.editor import actual_diff
from src.skill_evolution.v27.unnumbered_patch import apply_patch
from src.skill_evolution.v27.update_patch import normalize_update_patches
from src.skill_evolution.v27.memory_view import knowledge_only
from src.skill_evolution.v27.transport import RequestFailure, HTTPGenerator
from src.skill_evolution.v27.training import load_dataset, POOL_IDS, RESOURCES
from src.skill_evolution.v27.config import campaign_config,validate_config
from src.skill_evolution.v27.evaluation import ArchiveTransport
from tests.skill_evolution.v27.support import *

ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/'docs/methods/v27/draft_20261030_001'

def unnumbered(old,new):
    import re
    return re.sub(r'^@@[^\n]*@@[^\n]*$', '@@', actual_diff(old,new), flags=re.M)

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.adapter=LMBAdapter(gate_metric=p.EM_GATE)
        self.binding=using_benchmark(self.adapter);self.binding.__enter__()
        self.sleep=patch('src.skill_evolution.v27.benchmarks.lmb.actor.time.sleep');self.sleep.start()
    def tearDown(self):self.sleep.stop();self.binding.__exit__(None,None,None);self.tmp.cleanup()
    def reject(self,fn,*args,**kwargs):
        with self.assertRaises((ValueError,RequestFailure,stages.Stopped)):fn(*args,**kwargs)
    def diagnosed(self,count=1):
        records=[record(f'synthetic:{i:03}') for i in range(count)]
        call=modules.grouping_call(records,'fixture_R01'); grouped=call.complete(grouping(call.input['bundle']['facts']['runs']))
        return records,modules.diagnosis_call(grouped).complete(diagnosis())
    def edited(self,count=1):
        records,saved=self.diagnosed(count)
        saved=modules.preconditioner_call(saved,memory.empty_memory()).complete(keep())
        candidate=SKILL+'Check the required equality condition.\n'
        saved=modules.editor_call(saved).complete({'patch':unnumbered(SKILL,candidate),'reason':'Implement scoped comparison.'})
        qs=[record(r['task_id'],role='candidate',skill=candidate,content='<answer>A</answer>') for r in records]
        bundle=evidence.build_replay_from_editor(saved,'fixture_editor',records,list(reversed(qs)))
        return saved,bundle

class DataTests(Base):
    def test_source_freeze_and_independence(self):
        from .source_provenance import verify
        verify(ROOT)
        m=json.loads((RESOURCES/'migration_sources.json').read_text())
        for name,h in m['v26'].items():self.assertEqual(p.file_digest(ROOT/name),h)
        for path in (ROOT/'src/skill_evolution/v27').rglob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,(ast.Import,ast.ImportFrom)):
                    for dependency in ('officeqa', '.v26', '.v25', '.v24'):
                        self.assertNotIn(dependency, ast.unparse(node).lower())
        for name in prompting.PROMPT_VERSIONS:
            self.assertEqual(prompting.resource_path(name+'.md').read_bytes(),(ROOT/'docs/methods/v27'/('replay_dedup_v2_20261102' if name=='replay' else 'actor_49152_20261031')/'prompts'/f'{name}.md').read_bytes())
        self.assertEqual((RESOURCES/'initial.md').read_bytes(),(ROOT/'artifacts/benchmarks/livemathematicianbench/environment_20261029/skillopt_source/skillopt/envs/livemathematicianbench/skills/initial.md').read_bytes())
    def test_data_membership_normalization_and_native_parity(self):
        from skilladam.benchmarks.lmb.manifest import _normalize_raw_item
        from skilladam.benchmarks.lmb.choices import shuffle_choices
        d=load_dataset(ROOT/'data/livemathematicianbench/prepared_v1')
        before=d.snapshot();self.assertEqual([len(b) for b in d.batches()],[10]*5+[3])
        self.assertEqual(len(d.splits['test']),124);self.assertIn('202512:46',d.source_splits['validation'])
        self.assertEqual(d.splits['train'],sorted(POOL_IDS['train'])+sorted(POOL_IDS['val']))
        self.assertFalse(set(d.splits['train'])&set(d.splits['test']))
        for uid,row in d.rows.items():
            native=_normalize_raw_item(row,label=uid,source_file=row['source_file'])
            choices,label=shuffle_choices(native['choices'],native['reference']['label'],seed=42,item_id=uid)
            c=d.case(uid);self.assertEqual(c.payload['choices'],choices);self.assertEqual(c.reference['label'],label)
            self.assertEqual(c.payload['question'],native['question'])
            self.assertEqual(set(row['label_mapping']),set('ABCDE'))
        d.export_view(self.root/'view');self.assertEqual(d.snapshot(),before)
        self.assertEqual(sorted([':2',':10',':11']),[':10',':11',':2'])
        adapter=LMBAdapter(d,ArchiveTransport(),gate_metric=p.EM_GATE)
        with using_benchmark(adapter):
            cfg=campaign_config(adapter,max_input_chars=500000,max_message_utf8_bytes=1000000,context_window_tokens=1048576);validate_config(cfg)
            with patch.object(p,'VENDOR_PROMPT',p.VENDOR_PROMPT+' Changed protocol.'):
                self.reject(validate_config,cfg)
            bad=deepcopy(cfg);bad['batches'][0].reverse();self.reject(validate_config,bad)
            bad=deepcopy(cfg);bad['batches'][0][0]=d.splits['test'][0];self.reject(validate_config,bad)
            bad=deepcopy(cfg);bad['method']['version']='v26_campaign_v1';self.reject(validate_config,bad)
    def test_exact_protocol_projection_and_runtime(self):
        saved,bundle=self.edited()
        inputs=[modules.grouping_call([record()],'R1').messages,modules.diagnosis_call(saved).messages,
                modules.preconditioner_call(saved,memory.empty_memory()).messages,
                modules.editor_call(saved).messages,modules.replay_call(bundle).messages]
        for msgs in inputs:
            self.assertIn(p.VENDOR_PROMPT.format(skill_section=''),msgs[0]['content'])
            self.assertIn(p.execution_context(p.background(p.ACTOR)),msgs[0]['content'])
            self.assertNotIn(HIDDEN,json.dumps(msgs))
        self.assertEqual(set(json.loads(inputs[2][1]['content'])),{'parent','plan','runs','memory'})
        self.assertEqual(set(json.loads(inputs[3][1]['content'])),{'parent','plan'})
        self.assertNotIn('basis',json.loads(inputs[4][1]['content'])['plan']['updates'][0])
        b=p.background(p.ACTOR);b['max_tokens']=32768;self.reject(prompting.render,'editor',b)
        task={**record()['task'],'theorem':HIDDEN,'sketch':HIDDEN,'paper_link':HIDDEN,'reference':HIDDEN}
        self.assertNotIn(HIDDEN,json.dumps(p.messages(task,SKILL)))

class EvidenceTests(Base):
    def test_run_whitelist_and_label_only(self):
        r=record();f=facts.build_facts([r]);run=f['facts']['runs'][0]
        self.assertEqual(run['attempts'][0]['assistant']['content'],'<answer>B</answer>')
        self.assertEqual(run['attempts'][0]['request_messages'],run['initial']['messages'])
        self.assertNotIn('correct_label',json.dumps(run['initial']))
        self.assertEqual(facts.run_references(run),{'P1','P1:0','P1:1','P1:outcome'})
        for where in ('run','round','assistant','outcome'):
            bad=deepcopy(run)
            target={'run':bad,'round':bad['attempts'][0],'assistant':bad['attempts'][0]['assistant'],'outcome':bad['outcome']}[where]
            target['reasoning_content']=HIDDEN;self.reject(facts.validate_run,bad)
        bad=deepcopy(run);bad['attempts'][0]['ref']='P1:1_t1';self.reject(facts.validate_run,bad)
        bad=deepcopy(run);bad['attempts']*=2;self.reject(facts.validate_run,bad)
        r=record(content='reasoning_content is a word in ordinary content. <answer>A</answer>')
        self.assertIn('reasoning_content is',facts.build_facts([r])['facts']['runs'][0]['attempts'][0]['assistant']['content'])
    def test_grouping_and_diagnosis_coverage(self):
        facts_=facts.build_facts([record(),record('synthetic:001')])['facts'];g=grouping(facts_['runs'])
        evidence.validate_grouping(g,facts_)
        for mutate in (lambda x:x['groups'][0]['members'].append('P1'),lambda x:x['groups'][0]['members'].pop(),
                       lambda x:x['groups'][0].update(shared_basis='P1:1'),lambda x:x['groups'][0].update(shared_basis='P1:outcome P2:outcome')):
            bad=deepcopy(g);mutate(bad);self.reject(evidence.validate_grouping,bad,facts_)
        payload={**facts_,'grouping':g};dc.validate_diagnosis(diagnosis(),payload)
        dc.validate_diagnosis({'decision':'no_change','reason':'No repair supported.','plan':None},payload)
        for mutate in (lambda x:x.update(decision='need_evidence'),lambda x:x['plan'].update(updates=[]),
                       lambda x:x['plan']['updates'][0].update(basis=['G1']),lambda x:x['plan']['checks'][0].update(update_ids=['u2']),
                       lambda x:x.update(decision='no_change')):
            bad=diagnosis();mutate(bad);self.reject(dc.validate_diagnosis,bad,payload)
    def test_preconditioner_selected_runs(self):
        _,saved=self.diagnosed(2);saved['diagnosis']['plan']['updates'][0]['basis']=['G1','P1:1']
        value=evidence.preconditioner_model_input(saved)
        self.assertEqual([r['ref'] for r in value['runs']],['P1']);self.assertNotIn('grouping',value)
        self.assertEqual(value['memory'],{'format':'memory_knowledge_only_v1','entries':[]})
    def test_pair_integrity_and_gate_discrete_counts(self):
        saved,bundle=self.edited(3);payload=bundle['payload'];self.assertEqual([x['task_id'] for x in payload['pairs']],[f'synthetic:{i:03}' for i in range(3)])
        a=record();b=record(role='candidate',skill='New.\n')
        evidence.verify_pair(a,b)
        for key in ('case_sha256','scorer','task_context_sha256'):
            bad=deepcopy(b);bad['provenance'][key]='changed';self.reject(evidence.verify_pair,a,bad)
        bad=deepcopy(b);bad['run_id']=a['run_id'];self.reject(evidence.verify_pair,a,bad)
        for n in (3,10):
            for left in range(n+1):
                for right in range(n+1):
                    pairs=[{'task_id':str(i),'parent':{'run_id':'p'+str(i),'success':i<left},'candidate':{'run_id':'q'+str(i),'success':i<right}} for i in range(n)]
                    result=gate.decide_gate({'pairs':pairs},[str(i) for i in range(n)])
                    self.assertEqual(result['decision']=='ACCEPT',right>left)
                    self.assertEqual(right>left,(right-left)/n>=0.08)

class ContractTests(Base):
    def test_preconditioner_keep_patch_withdraw(self):
        _,s=self.diagnosed();payload=evidence.preconditioner_input(s)
        normalized,effective=normalize_update_patches(keep(),payload);self.assertEqual(effective,s['diagnosis']['plan'])
        old=deepcopy(payload);out=keep();out['adjustments'][0].update(focus=['S'],change='Limit comparison to relevant options.',
            to={'patch':unnumbered(payload['plan']['updates'][0]['text'],'Check equality when relevant.\n')})
        _,effective=normalize_update_patches(out,payload)
        self.assertEqual(effective['updates'][0]['id'],'u1');self.assertEqual(effective['updates'][0]['basis'],['P1:1']);self.assertEqual(old,payload)
        out=keep();out['checks']=[];normalize_update_patches(out,payload)
        out['adjustments'][0].update(focus=['D'],change='Withdraw redundant instruction.',to=[])
        self.assertIsNone(normalize_update_patches(out,payload)[1])
        out['checks']=None;self.reject(normalize_update_patches,out,payload)
        payload['plan']['checks']=[];self.assertIsNone(normalize_update_patches(out,payload)[1])
    def test_preconditioner_malformed_outputs(self):
        _,s=self.diagnosed();payload=evidence.preconditioner_input(s)
        mutations=[lambda x:x['adjustments'].clear(),lambda x:x['adjustments'].append(deepcopy(x['adjustments'][0])),
                   lambda x:x['adjustments'][0].update(target='u2'),lambda x:x['adjustments'][0].update(focus=['D']),
                   lambda x:x['adjustments'][0].update(to=[]),lambda x:x.update(decision='ready'),
                   lambda x:x['adjustments'][0].update(reason='`Evidence:P1:1_t1` supports this.'),
                   lambda x:x['adjustments'][0].update(reason='`Evidence:R01/P1:1` supports this.'),
                   lambda x:x['adjustments'][0].update(focus=['S','S'],change='Revise.',to=[])]
        for mutate in mutations:
            out=keep();mutate(out);self.reject(normalize_update_patches,out,payload)
        out=keep();out['adjustments'][0]['reason']='Use mathematical notation `x > 0`.';normalize_update_patches(out,payload)
    def test_editor_exact_patch_and_stops(self):
        for old,new in [('one\ntwo\nthree\n','ONE\ntwo\nTHREE\n'),('one','two'),('one\n','two'),('one','two\n')]:
            patch_=unnumbered(old,new);self.assertEqual(apply_patch(old,patch_),new)
        self.assertEqual(modules.validate_editor({'patch':'','reason':'Already satisfied.'},SKILL),('no_change',None))
        self.assertEqual(modules.validate_editor({'patch':None,'reason':'Cannot implement faithfully.'},SKILL),('needs_revision',None))
        for patch_ in (' ','--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-x\n+y\n',
                       '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n+x\n'):
            self.reject(modules.validate_editor,{'patch':patch_,'reason':'Test'},SKILL)
        self.reject(apply_patch,'same\nsame\n','--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-same\n+new\n')
        self.reject(modules.validate_editor,{'patch':unnumbered(SKILL,' \n'),'reason':'Test'},SKILL)
    def test_replay_entry_union_and_revisions(self):
        _,b=self.edited();payload=b['payload'];replay_contract.validate_result(replay(),payload)
        replay_contract.validate_result({'entries':[]},payload)
        for refs in (['P1:outcome'],['diff'],['M1'],['Q9:1']):
            out=replay();out['entries'][0]['knowledge'][0]['evidence']=refs;self.reject(replay_contract.validate_result,out,payload)
        for mutate in (lambda x:x['entries'][0].update(evidence=['diff']),lambda x:x['entries'][0].update(knowledge=[]),
                       lambda x:x['entries'][0]['knowledge'][0].update(id='k1')):
            out=replay();mutate(out);self.reject(replay_contract.validate_result,out,payload)
        out={'entries':[{'revises':[],'knowledge':[{'text':'Actual change.','evidence':['diff']},{'text':'Observed label.','evidence':['Q1:1']}]}]}
        replay_contract.validate_result(out,payload)
        out['entries']=[{'revises':[],'knowledge':[k]} for k in out['entries'][0]['knowledge']];self.reject(replay_contract.validate_result,out,payload)
        memory.commit_memory(self.root/'mem',context_id='R01',context=b,result=replay(),memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        active=memory.load_memory(self.root/'mem',memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        payload=deepcopy(payload);payload['memory']=active
        old=knowledge_only(active)['entries'][0]
        result={'entries':[{'revises':['M1'],'knowledge':deepcopy(old['knowledge'])}]}
        replay_contract.validate_result(result,payload)
        self.assertTrue(all('/' in ref for k in result['entries'][0]['knowledge'] for ref in k['evidence']))
        result['entries'].append(deepcopy(result['entries'][0]));self.reject(replay_contract.validate_result,result,payload)
        result['entries'].pop();result['entries'][0]['knowledge'][0]['evidence'].append('R01/P1:0');self.reject(replay_contract.validate_result,result,payload)
        view=knowledge_only(active);self.assertNotIn('sources',view)

class ScoringTests(Base):
    def test_native_parse_and_format(self):
        cases=[('<answer>A</answer>',1,True),('<answer>B</answer>',0,True),
               ('<answer>B</answer><answer>A</answer>',1,False),('A',1,False),
               ('<answer>a.</answer>',1,False),('<answer>VALUE 1</answer>',1,False),
               ('<answer>A is correct</answer>',1,False),('',0,False),('<answer>A</answer><answer>',1,False)]
        for content,em,compliant in cases:
            a,m=score(content,CHOICES,'A');self.assertEqual(m['em'],em);self.assertEqual(a['format_compliant'],compliant)
        # External overrides are deliberately absent from the scorer API.
        raw=response('<answer>B</answer>');raw.update(answer='A',predicted_answer='A')
        content,reason=actor.parse_response(raw);self.assertEqual(score(content,CHOICES,'A')[1]['em'],0)
        r=record();r['execution']['answer']['predicted_label']='A';r['provenance']['record_sha256']=p.digest(r['execution']);self.reject(facts.validate_envelope,r)
    def test_termination_classes(self):
        for value in (None,'','<answer>A</answer>'):
            with self.assertRaises(RequestFailure) as caught: actor.parse_response(response(value,'length'))
            self.assertTrue(caught.exception.retryable)
        self.assertEqual(actor.parse_response(response(''))[0],'')
        for raw in (response(None),response(123),{'choices':[]},{'choices':[{'finish_reason':'stop','message':{}}]}):self.reject(actor.parse_response,raw)
        for finish in ('tool_calls','content_filter','other'):
            with self.assertRaises(RequestFailure) as e:actor.parse_response(response('A',finish))
            self.assertFalse(e.exception.retryable)

class TransportTests(Base):
    def test_durable_actor_and_hidden_boundary(self):
        data=Dataset(self.root/'data',1);t=Transport(fn=lambda m,d:response(''))
        result=actor.execute(data.case('synthetic:000'),SKILL,self.root/'actor',t)
        self.assertEqual(result['metrics']['em'],0);self.assertEqual(t.calls,1);self.assertNotIn(HIDDEN,json.dumps(result))
        self.assertIn(HIDDEN,(self.root/'actor/attempts/001/response.json').read_text())
        actor.execute(data.case('synthetic:000'),SKILL,self.root/'actor',t);self.assertEqual(t.calls,1)
        (self.root/'actor/result.json').unlink()
        actor.execute(data.case('synthetic:000'),SKILL,self.root/'actor',t);self.assertEqual(t.calls,1)
    def test_retry_budget_and_unknown(self):
        data=Dataset(self.root/'data',1);case=data.case('synthetic:000')
        def fail(m,d):raise RequestFailure('synthetic temporary failure')
        t=Transport(fn=fail)
        self.reject(actor.execute,case,SKILL,self.root/'exhaust',t);self.assertEqual(t.calls,6)
        self.reject(actor.execute,case,SKILL,self.root/'exhaust',t);self.assertEqual(t.calls,6)
        def interrupted(m,d):raise KeyboardInterrupt()
        t=Transport(fn=interrupted)
        with self.assertRaises(KeyboardInterrupt):actor.execute(case,SKILL,self.root/'unknown',t)
        t.fn=None;result=actor.execute(case,SKILL,self.root/'unknown',t)
        self.assertEqual(result['api_requests'],2);self.assertEqual(t.calls,2)
        self.assertEqual(stages.read(self.root/'unknown/attempts/001/error.json')['status'],'unknown')
    def test_http_mock_and_method_hidden_feedback(self):
        import httpx
        captured=[]
        def handler(request):
            captured.append(json.loads(request.content));return httpx.Response(200,json=response('{"entries":[]}'))
        class Session:
            def __enter__(self):self.client=httpx.Client(transport=httpx.MockTransport(handler));return self
            def __exit__(self,*args):self.client.close()
            def mount(self,*args):self_outer.assertEqual(args[1].max_retries.total,0)
            def post(self,url,**kwargs):
                self_outer.assertEqual(kwargs.pop('timeout'),(10,300));kwargs.pop('allow_redirects')
                return self.client.post(url,**kwargs)
        self_outer=self
        t=actor.ChatTransport('SYNTHETIC_KEY',session_factory=Session)
        folder=self.root/'http';folder.mkdir();raw=t(p.messages(record()['task'],SKILL),folder)
        self.assertIn(HIDDEN,json.dumps(raw));self.assertEqual(captured[-1]['thinking'],{'type':'enabled'});self.assertEqual(captured[-1]['max_tokens'],49152)
        callconfig=config(type('A',(),{'transport':t,'dataset':Dataset(self.root/'d',1)})())['module_calls']['replay']
        folder2=self.root/'method';folder2.mkdir()
        v=HTTPGenerator('SYNTHETIC_KEY',session_factory=Session)('replay',[{'role':'user','content':'synthetic'}],folder2,callconfig)
        self.assertNotIn(HIDDEN,json.dumps(v));self.assertEqual(captured[-1]['max_tokens'],32768)
        self.assertNotIn('SYNTHETIC_KEY',(folder/'request.json').read_text())

class CampaignTests(Base):
    def bind_data(self,count=3,fn=None):
        data=Dataset(self.root/'data',count)
        t=Transport(fn=fn or (lambda m,d:response('<answer>A</answer>' if 'required equality' in m[0]['content'] else '<answer>B</answer>')))
        adapter=LMBAdapter(data,t,gate_metric=p.EM_GATE)
        return data,t,adapter
    def generator(self,*,stop=None,no_change=None,replay_value=None):
        calls=[]
        def gen(name,messages,directory,cfg):
            calls.append(name);value=json.loads(messages[1]['content'])
            self.assertNotIn(HIDDEN,json.dumps(messages))
            if name=='grouping':out=grouping(value['runs'])
            elif name=='diagnosis':out={'decision':'no_change','reason':'No justified update.','plan':None} if no_change=='diagnosis' else diagnosis()
            elif name=='preconditioner':
                out=keep()
                if no_change=='preconditioner':out['adjustments'][0].update(focus=['D'],change='Withdraw redundant requirement.',to=[]);out['checks']=[]
            elif name=='editor':
                out={'patch':None if stop=='editor' else '' if no_change=='editor' else unnumbered(value['parent'],value['parent']+'Check the required equality condition.\n'),'reason':'Synthetic fixture implementation.'}
            elif name=='replay':out=replay() if replay_value is None else replay_value
            else:raise AssertionError('Disabled module invoked')
            return {'content':json.dumps(out),'finish_reason':'stop','usage':response()['usage']}
        return gen,calls
    def test_full_chain_accept_and_retain(self):
        for accept in (True,False):
            with self.subTest(accept=accept):
                data,t,a=self.bind_data(fn=None if accept else lambda m,d:response('<answer>B</answer>'))
                gen,calls=self.generator();folder=self.root/f'chain_{accept}'
                with using_benchmark(a):
                    result=evolution.run_campaign(folder,config=config(a),generate=gen)
                    self.assertEqual(result['status'],'complete');self.assertEqual(t.calls,6)
                    self.assertEqual(calls,['grouping','diagnosis','preconditioner','editor','replay'])
                    self.assertEqual(stages.read(folder/'rounds/R01/gate/result.json')['result']['decision'],'ACCEPT' if accept else 'RETAIN')
                    final=evolution.final_parent(folder);self.assertIn('required equality',final.read_text()) if accept else self.assertEqual(final.read_text(),SKILL)
                    active=memory.load_memory(folder/result['state']['active_memory'],memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
                    self.assertEqual(len(active['entries']),1)
                    evolution.run_campaign(folder,generate=None,resume=True);self.assertEqual(t.calls,6)
                    self.assertNotIn(HIDDEN,json.dumps(active))
    def test_three_nochange_paths_all_batches(self):
        for branch in ('diagnosis','preconditioner','editor'):
            data,t,a=self.bind_data(count=6);folder=self.root/branch
            gen,calls=self.generator(no_change=branch);cfg=config(a,[[uid] for uid in data.rows])
            with using_benchmark(a):
                result=evolution.run_campaign(folder,config=cfg,generate=gen)
                self.assertEqual(result['status'],'complete');self.assertEqual(result['state']['next_round'],7)
                self.assertEqual(result['state']['active_memory'],'initial_memory');self.assertEqual(t.calls,6)
                self.assertNotIn('replay',calls)
    def test_semantic_stop_not_resampled(self):
        _,t,a=self.bind_data();gen,calls=self.generator(stop='editor');folder=self.root/'blocked'
        with using_benchmark(a):
            self.reject(evolution.run_campaign,folder,config=config(a),generate=gen)
            self.assertEqual(calls.count('editor'),1);self.assertNotIn('replay',calls)
            self.reject(evolution.run_campaign,folder,generate=gen,resume=True);self.assertEqual(calls.count('editor'),1)
            self.reject(evolution.final_parent,folder)
    def test_replay_failure_does_not_publish(self):
        _,t,a=self.bind_data();gen,calls=self.generator(replay_value={'entries':[{'revises':[],'knowledge':[]}]});folder=self.root/'failed'
        with using_benchmark(a):
            self.reject(evolution.run_campaign,folder,config=config(a),generate=gen)
            self.assertEqual(stages.read(folder/'state.json'),{'next_round':1,'parent':'initial_skill.md','active_memory':'initial_memory'})
            self.assertEqual(calls.count('replay'),6)
            self.assertEqual(stages.read(folder/'rounds/R01/gate/result.json')['result']['decision'],'ACCEPT')
            self.reject(evolution.run_campaign,folder,generate=gen,resume=True);self.assertEqual(calls.count('replay'),6)
    def test_atomic_publish_and_resume_identity(self):
        for point in ('before_publish','after_publish'):
            _,t,a=self.bind_data();gen,calls=self.generator();folder=self.root/point
            def hook(stage):
                if stage==point:raise KeyboardInterrupt()
            with using_benchmark(a):
                with self.assertRaises(KeyboardInterrupt):evolution.run_campaign(folder,config=config(a),generate=gen,hook=hook)
                state=stages.read(folder/'state.json');self.assertEqual(state['next_round'],1 if point=='before_publish' else 2)
                before=t.calls;evolution.run_campaign(folder,generate=gen,resume=True);self.assertEqual(t.calls,before)
                frozen=stages.read(folder/'contract.json');frozen['fake']='changed';stages.save(folder/'contract.json',frozen)
                self.reject(evolution.run_campaign,folder,generate=gen,resume=True)
    def test_method_feedback_recovery_and_capacity(self):
        _,s=self.diagnosed();call=modules.preconditioner_call(s,memory.empty_memory());calls=[]
        cfg=config(type('A',(),{'transport':Transport(),'dataset':Dataset(self.root/'d',1)})())['module_calls']['preconditioner']
        def gen(n,msg,d,c):
            calls.append(msg)
            out=keep() if len(calls)>1 else {'decision':'ready'}
            return {'content':json.dumps(out),'finish_reason':'stop'}
        kwargs={'call_config':cfg,'max_attempts':6,'max_input_chars':1000000,'max_message_utf8_bytes':2000000,'generate':gen}
        folder=self.root/'method'
        stages.run_stage(folder,call,**kwargs);self.assertEqual(len(calls),2)
        self.assertEqual(len(calls[1]),4);self.assertIn('Previous Output Validation Error',calls[1][-1]['content'])
        stages.run_stage(folder,call,resume=True,**kwargs);self.assertEqual(len(calls),2)
        # Recover a saved complete response without its selected marker or parsed artifacts.
        folder2=self.root/'response_recovery'
        def interrupt_finish(*args,**kw):raise KeyboardInterrupt()
        with patch('src.skill_evolution.v27.stages._parse',side_effect=interrupt_finish):
            with self.assertRaises(KeyboardInterrupt):stages.run_stage(folder2,call,**kwargs)
        stages.run_stage(folder2,call,resume=True,**kwargs);self.assertEqual(len(calls),3)
        small={**kwargs,'max_input_chars':1}
        self.reject(stages.run_stage,self.root/'over_capacity',call,**small);self.assertEqual(len(calls),3)
        # Content survives round trip exactly; hidden token usage is not method input.
        user=json.loads(call.messages[1]['content']);self.assertEqual(json.loads(p.exact(user)),user)
        self.assertEqual(cfg['max_tokens'],32768)
    def test_worker_binding_order_and_same_task_messages(self):
        from src.skill_evolution.v27.benchmark import current
        data,t,a=self.bind_data(fn=lambda m,d:(self.assertIs(current(),a),response())[1])
        skill=self.root/'skill.md';skill.write_text(SKILL)
        with using_benchmark(a):
            records=a.actor_batch(list(data.rows),skill,self.root/'batch',{'split':'train','role':'parent'})
            self.assertEqual([r['task_id'] for r in records],list(data.rows))
            before=t.calls;a.actor_batch(list(data.rows),skill,self.root/'batch',{'split':'train','role':'parent'});self.assertEqual(t.calls,before)
            newer=self.root/'new.md';newer.write_text(SKILL+'Additional comparison.\n')
            candidates=a.actor_batch(list(data.rows),newer,self.root/'candidate',{'split':'train','role':'candidate'})
            for r,q in zip(records,candidates):
                self.assertEqual(r['execution']['initial_messages'][1],q['execution']['initial_messages'][1]);evidence.verify_pair(r,q)


class AdditionalBoundaryTests(Base):
    def test_multi_update_coordination_and_checks(self):
        _,s=self.diagnosed();s['diagnosis']['plan']['updates'].append({'id':'u2','text':'Keep scope explicit.\n','basis':['P1:1']})
        payload=evidence.preconditioner_input(s);out=keep();second=deepcopy(out['adjustments'][0]);second['target']='u2';out['adjustments'].append(second)
        normalized,plan=normalize_update_patches(out,payload);self.assertEqual(len(plan['updates']),2)
        out['adjustments'][0].update(focus=['S'],change='Narrow condition.',to={'patch':unnumbered(payload['plan']['updates'][0]['text'],'Check only relevant equality.\n')})
        _,plan=normalize_update_patches(out,payload);self.assertEqual(plan['updates'][1],payload['plan']['updates'][1])
        out['adjustments'][0].update(focus=['D'],change='Withdraw redundancy.',to=[])
        self.reject(normalize_update_patches,out,payload)
        out['checks']=[{'id':'c2','update_ids':['u2'],'question':'Does the scope remain explicit?'}]
        self.assertEqual(len(normalize_update_patches(out,payload)[1]['updates']),1)
        out['adjustments'][1]['focus']=['X'];self.reject(normalize_update_patches,out,payload)
    def test_patch_overlap_order_and_multihunk(self):
        old=''.join(f'line {i}\n' for i in range(30));new=old.replace('line 1\n','changed 1\n').replace('line 28\n','changed 28\n')
        delta=unnumbered(old,new);self.assertGreater(delta.count('@@'),1);self.assertEqual(apply_patch(old,delta),new)
        head='--- a/SKILL.md\n+++ b/SKILL.md\n';hunks=delta[len(head):].split('@@\n')[1:]
        self.reject(apply_patch,old,head+''.join('@@\n'+h for h in reversed(hunks)))
        self.reject(apply_patch,old,head+'@@\n'+hunks[0]+'@@\n'+hunks[0])
        self.reject(apply_patch,SKILL,unnumbered(SKILL,SKILL))
    def test_scoped_extract_and_historical_whole_replacement(self):
        _,bundle=self.edited()
        self.assertEqual(set(evidence.extract('P1',bundle)['record']),{'ref','task_id','run_id','initial','attempts','outcome'})
        self.reject(evidence.extract,'P1:1_t1',bundle)
        out=replay();out['entries'].append({'revises':[],'knowledge':[{'text':'A separate bounded observation.', 'evidence':['diff','P1:1']}]})
        memroot=self.root/'history';memory.commit_memory(memroot,context_id='R01',context=bundle,result=out,memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        active=memory.load_memory(memroot,memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        # Rebuild a valid next bundle with full history; model receives Knowledge Only.
        saved=deepcopy(bundle['audit']['editor']);nextbundle=evidence.build_replay_from_editor(saved,'next_editor',bundle['audit']['parent_records'],bundle['audit']['candidate_records'],memory=active)
        historical={'R01':bundle}
        self.assertIn('record',evidence.extract('R01/P1:1',nextbundle,historical))
        self.reject(evidence.extract,'R01/Q1:1',nextbundle,historical)
        knowledge=knowledge_only(active)['entries']
        replacement={'entries':[{'revises':['M1'],'knowledge':deepcopy(knowledge[0]['knowledge'])}]}
        replay_contract.validate_result(replacement,nextbundle['payload'])
        memory.commit_memory(memroot,context_id='R02',context=nextbundle,result=replacement,memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        active2=memory.load_memory(memroot,memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        self.assertEqual({e['id'] for e in active2['entries']},{'M2','M3'})
        nextbundle2=evidence.build_replay_from_editor(saved,'third_editor',bundle['audit']['parent_records'],bundle['audit']['candidate_records'],memory=active2)
        all_items=[deepcopy(k) for e in knowledge_only(active2)['entries'] for k in e['knowledge']]
        merged={'entries':[{'revises':['M2','M3'],'knowledge':all_items}]}
        replay_contract.validate_result(merged,nextbundle2['payload'])
        memory.commit_memory(memroot,context_id='R03',context=nextbundle2,result=merged,memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        active3=memory.load_memory(memroot,memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT);self.assertEqual(len(active3['entries']),1)
        nextbundle3=evidence.build_replay_from_editor(saved,'fourth_editor',bundle['audit']['parent_records'],bundle['audit']['candidate_records'],memory=active3)
        memory.commit_memory(memroot,context_id='R04',context=nextbundle3,result={'entries':[]},memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        self.assertEqual(memory.load_memory(memroot,memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT),active3)
    def test_retry_accepts_one_round_and_no_answer_resampling(self):
        data=Dataset(self.root/'data',1);attempts=[]
        def fn(messages,directory):
            attempts.append(directory)
            if len(attempts)<3:raise RequestFailure('temporary synthetic failure')
            return response('unparseable')
        t=Transport(fn=fn);a=LMBAdapter(data,t,gate_metric=p.EM_GATE);skill=self.root/'skill.md';skill.write_text(SKILL)
        with using_benchmark(a):
            records=a.actor_batch(list(data.rows),skill,self.root/'batch',{'split':'train','role':'parent'})
            run=facts.build_facts(records)['facts']['runs'][0]
            self.assertEqual(run['outcome']['api_requests'],3);self.assertEqual(len(run['attempts']),1)
            self.assertEqual(run['outcome']['score']['em'],0);self.assertEqual(len(attempts),3)
        # Wrong and format-noncompliant answers also finish after the first successful HTTP response.
        for i,content in enumerate(('<answer>B</answer>','A','')):
            tr=Transport(content=content);result=actor.execute(data.case('synthetic:000'),SKILL,self.root/f'answer_{i}',tr)
            self.assertEqual(tr.calls,1);self.assertEqual(result['api_requests'],1)
    def test_technical_failure_and_pair_conditions(self):
        a=record();b=record(role='candidate',skill='New skill.\n')
        for mutation in (
            lambda r:r['execution']['actor'].update(max_tokens=8192),
            lambda r:r['task']['choices'][0].update(text='changed option'),
            lambda r:r['task'].update(question='Different question'),
            lambda r:r['execution'].update(termination='technical_error')):
            bad=deepcopy(b);mutation(bad);bad['provenance']['record_sha256']=p.digest(bad['execution']);self.reject(evidence.verify_pair,a,bad)
        b=record(role='candidate',skill='New skill.\n',finish='length',content='');self.reject(evidence.verify_pair,a,b)
    def test_prompt_semantic_requirements_remain_explicit(self):
        pre=prompting.resource_path('preconditioner.md').read_text();rep=prompting.resource_path('replay.md').read_text()
        # Text-presence guards only; detailed human fixture judgments live in the acceptance report.
        for phrase in ('KEEP applies to the entire Original Update','Address an important relevant adverse response specifically',
                       'A scoped requirement may be reasonable','both kept and modified'):
            self.assertIn(phrase,pre)
        for phrase in ('at least one actual Diff source and at least one execution source','They may keep exclusively historical evidence',
                       "Each Knowledge's supporting sources belong in that Knowledge's own evidence"):
            self.assertIn(phrase,rep)
    def test_test_evaluation_is_separate_for_three_frozen_skills(self):
        from src.skill_evolution.v27 import evaluation
        ids=tuple(f'synthetic:test:{i:03}' for i in range(124))
        class TestData(Dataset):
            def __init__(self,root):
                super().__init__(root,0);self.rows={i:{'question':'Which integer is one?','choices':CHOICES,'correct_label':'A'} for i in ids}
                self.splits={'train':[],'validation':[],'test':list(ids)}
            def case(self,uid):
                c=super().case(uid);return Case(c.case_id,c.payload,c.reference,{'split':'test','source_split':'test'})
        data=TestData(self.root/'test_data');t=Transport();a=LMBAdapter(data,t)
        with using_benchmark(a),patch.object(evaluation,'TEST_IDS',ids):
            for arm in ('initial','v27_final','skilladam_final'):
                skill=self.root/(arm+'.md');skill.write_text('Frozen '+arm+' skill.\n')
                folder=self.root/arm
                result=evaluation.run_evaluation(folder,adapter=a,skill_file=skill)
                self.assertEqual(result['completed'],124);self.assertEqual(result['exact_matches'],124)
                self.assertFalse(result['optimization_updates']);self.assertFalse((folder/'memory').exists())
                self.assertFalse((folder/'state.json').exists())
                count=t.calls;again=evaluation.report_evaluation(folder,adapter=a);self.assertEqual(t.calls,count)
                self.assertEqual(result,again)
                evaluation.run_evaluation(folder,adapter=a,skill_file=skill,resume=True);self.assertEqual(t.calls,count)
                raw=folder/'batch/actor'/p.digest(ids[0])/'attempts/001/response.json'
                archived=raw.read_bytes();raw.unlink()
                self.reject(evaluation.report_evaluation,folder,adapter=a);self.assertEqual(t.calls,count)
                raw.write_bytes(archived)
            self.assertEqual(t.calls,372)
            self.reject(facts.build_facts,stages.read(self.root/'initial/batch/records.json'))
            # Test scores cannot silently change the fixed Skill on resume.
            skill=self.root/'initial.md';skill.write_text('Changed after test.\n')
            self.reject(evaluation.run_evaluation,self.root/'initial',adapter=a,skill_file=skill,resume=True)

class CapacityAndCorruptionTests(Base):
    def test_output_reservation_and_context_limit(self):
        from src.skill_evolution.v27.capacity import account
        messages=[{'role':'system','content':'Synthetic protocol.'},{'role':'user','content':'短题目'}]
        value=account(messages,{'max_tokens':32768},max_input_chars=1000,max_message_utf8_bytes=2000)
        self.assertEqual(value['reserved_output_tokens'],32768)
        self.assertGreater(value['context_token_upper_estimate'],32768)
        self.reject(account,messages,{'max_tokens':32768,'context_window_tokens':32769},max_input_chars=1000,max_message_utf8_bytes=2000)
        longer=deepcopy(messages);longer[1]['content']*=1000
        self.reject(account,longer,{'max_tokens':32768},max_input_chars=1000,max_message_utf8_bytes=2000)
    def test_completed_actor_missing_archive_is_not_regenerated(self):
        d=Dataset(self.root/'data',1);t=Transport();folder=self.root/'actor'
        actor.execute(d.case('synthetic:000'),SKILL,folder,t)
        (folder/'attempts/001/response.json').unlink()
        self.reject(actor.execute,d.case('synthetic:000'),SKILL,folder,t);self.assertEqual(t.calls,1)

class AccountingTests(Base):
    def test_ten_task_actor_accounting_and_native_comparison(self):
        data=Dataset(self.root/'data',10)
        t=Transport(fn=lambda m,d:response('<answer>A</answer>' if 'required equality' in m[0]['content'] else '<answer>B</answer>'))
        a=LMBAdapter(data,t,gate_metric=p.EM_GATE)
        gen,calls=CampaignTests.generator(self)
        with using_benchmark(a):
            evolution.run_campaign(self.root/'ten_tasks',config=config(a),generate=gen)
        self.assertEqual(t.calls,20);self.assertEqual(len(calls),5)
        tree=ast.parse((ROOT/'external/SkillAdam/skilladam/core/feedback_loop.py').read_text())
        evaluations=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='evaluate']
        self.assertEqual(len(evaluations),2)
        source=(ROOT/'external/SkillAdam/skilladam/methods/skilladam.py').read_text()
        self.assertIn('stage="training_rollout"',source)
        # Native source establishes separate training + Gate baseline + Gate candidate.
        self.assertEqual(10+10*len(evaluations),30)

if __name__=='__main__':unittest.main()
