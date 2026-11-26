"""Regression coverage for the five implementation-review findings."""
from copy import deepcopy
import json
from unittest.mock import patch

from . import test_offline as original
from . import capacity_fixture
from .support import Dataset, Transport, SKILL, CHOICES, config, response, keep
from src.skill_evolution.v27 import modules, stages, evolution
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.benchmarks.lmb import actor, protocol as p
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
from src.skill_evolution.v27.benchmarks.lmb.scoring import score
from src.skill_evolution.v27.capacity import account
from src.skill_evolution.v27.config import validate_config
from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v27.transport import response_value, RequestFailure, HTTPGenerator


class ReviewRegressionTests(original.Base):
    def stage_setup(self):
        _,saved=self.diagnosed()
        call=modules.preconditioner_call(saved,memory.empty_memory())
        a=LMBAdapter(Dataset(self.root/'data',1),Transport(),gate_metric=p.EM_GATE)
        cfg=config(a)['module_calls'][call.name]
        return call,{'call_config':cfg,'max_attempts':6,'max_input_chars':1000000,'max_message_utf8_bytes':1000000}

    def test_method_malformed_envelope_types_are_retryable(self):
        bad=[None,[],42,{}, {'choices':None},{'choices':{}},{'choices':[]},
             {'choices':[None]},{'choices':[[]]}]
        bad += [{'choices':[{'message':v}]} for v in (None,[],42,'text',{}, {'content':None})]
        for value in bad:
            with self.subTest(value=value),self.assertRaises(RequestFailure) as caught:response_value(value)
            self.assertTrue(caught.exception.retryable)
        self.assertEqual(response_value(response(''))['content'],'')

    def test_method_structure_retry_exhaustion_and_resume(self):
        call,kw=self.stage_setup()
        for recover in (True,False):
            sends=[]
            def payload():
                sends.append(1)
                return response(json.dumps(keep())) if recover and len(sends)==2 else {'choices':[{'message':None}]}
            class Session:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def mount(self,*args):pass
                def post(self,*args,**kwargs):
                    value=payload()
                    class Reply:
                        status_code=200
                        content=json.dumps(value).encode()
                        text=content.decode()
                        def json(self):return deepcopy(value)
                    return Reply()
            gen=HTTPGenerator('SYNTHETIC_KEY',session_factory=Session)
            folder=self.root/f'structure_{recover}'
            if recover:stages.run_stage(folder,call,generate=gen,**kw)
            else:self.reject(stages.run_stage,folder,call,generate=gen,**kw)
            self.assertEqual(len(sends),2 if recover else 6)
            error=stages.read(folder/'attempts/001/error.json')
            self.assertEqual(error['kind'],'technical');self.assertTrue(error['retryable'])
            before=len(sends)
            if recover:stages.run_stage(folder,call,generate=gen,resume=True,**kw)
            else:self.reject(stages.run_stage,folder,call,generate=gen,resume=True,**kw)
            self.assertEqual(len(sends),before)
            self.assertEqual(len(stages.read(folder/'attempts/002/messages.json')),2)

    def test_method_interrupted_http_structure_recovery(self):
        call,kw=self.stage_setup();folder=self.root/'interrupted';sends=[]
        def interrupted(name,msg,d,c):
            sends.append(1)
            stages.save(d/'http_status.json',{'status_code':200})
            (d/'http_response.txt').write_text(json.dumps({'choices':[{'message':[]}]}))
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):stages.run_stage(folder,call,generate=interrupted,**kw)
        def good(*args):
            sends.append(1);return response_value(response(json.dumps(keep())))
        stages.run_stage(folder,call,generate=good,resume=True,**kw)
        self.assertEqual(len(sends),2)
        self.assertTrue(stages.read(folder/'attempts/001/error.json')['retryable'])
        self.assertEqual(stages.read(folder/'result.json')['path'],'attempts/002')

    def test_campaign_cached_actor_archive_before_and_after_publication(self):
        for point in ('before_publish','after_publish'):
            for side in ('parent_runs','candidate_runs'):
                data=Dataset(self.root/'data',1);t=Transport();a=LMBAdapter(data,t,gate_metric=p.EM_GATE)
                gen,_=original.CampaignTests.generator(self);folder=self.root/(point+'_'+side)
                def hook(stage):
                    if stage==point:raise KeyboardInterrupt()
                with using_benchmark(a):
                    with self.assertRaises(KeyboardInterrupt):evolution.run_campaign(folder,config=config(a),generate=gen,hook=hook)
                    raw=folder/'rounds/R01'/side/'actor'/p.digest('synthetic:000')/'attempts/001/response.json'
                    saved=raw.read_bytes();before=t.calls
                    for mutation in ('missing','content','usage'):
                        if mutation=='missing':raw.unlink()
                        else:
                            value=json.loads(saved)
                            if mutation=='content':value['choices'][0]['message']['content']='<answer>B</answer>'
                            else:value['usage']['prompt_tokens']+=1
                            stages.save(raw,value)
                        snapshot={str(q):q.read_bytes() for q in folder.rglob('*') if q.is_file()}
                        self.reject(evolution.final_parent,folder)
                        self.assertEqual(snapshot,{str(q):q.read_bytes() for q in folder.rglob('*') if q.is_file()})
                        self.reject(evolution.run_campaign,folder,generate=gen,resume=True)
                        self.assertEqual(t.calls,before)
                        raw.write_bytes(saved)
                    evolution.run_campaign(folder,generate=gen,resume=True)
                    evolution.final_parent(folder);self.assertEqual(t.calls,before)

    def test_completed_actor_http_fallback_is_read_only(self):
        data=Dataset(self.root/'data',1);case=data.case('synthetic:000');t=Transport();folder=self.root/'actor'
        expected=actor.execute(case,SKILL,folder,t);slot=folder/'attempts/001'
        raw=(slot/'response.json').read_bytes()
        stages.save(slot/'http_status.json',{'status_code':200});(slot/'http_response.txt').write_bytes(raw)
        (slot/'response.json').unlink()
        snapshot={str(q):q.read_bytes() for q in folder.rglob('*') if q.is_file()}
        self.assertEqual(actor.execute(case,SKILL,folder,t),expected)
        self.assertEqual(snapshot,{str(q):q.read_bytes() for q in folder.rglob('*') if q.is_file()})
        self.assertEqual(t.calls,1)
        (slot/'http_response.txt').unlink();self.reject(actor.read_completed,case,SKILL,folder,t.metadata())

    def test_skill_newlines_survive_actor_gate_publication_and_resume(self):
        for i,skill in enumerate(('First condition.\r\nSecond condition.\r\n','First.\r\nSecond.\nThird.\rLast.')):
            data=Dataset(self.root/'data',1)
            t=Transport(fn=lambda m,d:response('<answer>A</answer>' if 'required equality' in m[0]['content'] else '<answer>B</answer>'))
            a=LMBAdapter(data,t,gate_metric=p.EM_GATE);cfg=config(a);cfg['initial_skill']['text']=skill
            folder=self.root/f'newlines_{i}';gen,_=original.CampaignTests.generator(self)
            with using_benchmark(a):
                evolution.run_campaign(folder,config=cfg,generate=gen)
                parent=stages.read(folder/'rounds/R01/parent_runs/records.json')[0]['execution']
                candidate=stages.read(folder/'rounds/R01/candidate_runs/records.json')[0]['execution']
                self.assertEqual(parent['skill'],skill)
                self.assertEqual(candidate['skill'],skill+'Check the required equality condition.\n')
                self.assertEqual(parent['initial_messages'],p.messages(data.case('synthetic:000').payload,skill))
                final=evolution.final_parent(folder);self.assertEqual(final.read_bytes(),candidate['skill'].encode())
                self.assertEqual(stages.read(folder/'rounds/R01/gate/result.json')['result']['decision'],'ACCEPT')
                evolution.run_campaign(folder,generate=gen,resume=True);self.assertEqual(t.calls,2)

    def test_dangling_answer_tags_change_format_only(self):
        from skilladam.benchmarks.lmb.evaluation import extract_answer,parse_choice_label
        data=Dataset(self.root/'data',1)
        for i,suffix in enumerate(('<answer','</answer','<answer ','</answer ','<ANSWER','</ANSWER','<answer x','</answer x')):
            content='<answer>A</answer>'+suffix
            native=parse_choice_label(extract_answer({'response':content})[0],CHOICES)[0]
            for finish in ('stop',):
                t=Transport(fn=lambda m,d,c=content,f=finish:response(c,f))
                out=actor.execute(data.case('synthetic:000'),SKILL,self.root/f'tag_{i}_{finish}',t)
                self.assertFalse(out['answer']['format_compliant'])
                self.assertEqual(out['metrics']['em'],int(native=='A'));self.assertEqual(t.calls,1)
                self.assertEqual(out['content'],content)
        for content in ('<answer>A</answer>','Proof about the answer. <answer>A</answer>'):
            self.assertTrue(score(content,CHOICES,'A')[0]['format_compliant'])

    def test_c01_complete_messages_feedback_and_pre_send_rejection(self):
        fixture=capacity_fixture.build(self.root/'c01');profile=fixture['report']['profile']
        self.assertEqual(fixture['report']['parent_runs'],10);self.assertEqual(fixture['report']['candidate_runs'],10)
        for name,count in (('grouping',10),('diagnosis',10),('preconditioner',10),('replay',20)):
            payload=json.loads(fixture['calls'][name].messages[1]['content'])
            self.assertEqual(len(payload['runs']),count)
            for run in payload['runs']:
                self.assertEqual(len(run['attempts'][0]['assistant']['content']),profile['content_chars_per_run'])
            if name in ('preconditioner','replay'):
                self.assertEqual(len(payload['memory']['entries']),profile['memory_entries'])
        self.assertEqual(len(json.loads(fixture['calls']['replay'].messages[1]['content'])['pairs']),10)
        self.assertEqual(set(json.loads(fixture['calls']['editor'].messages[1]['content'])),{'parent','plan'})
        a=LMBAdapter(Dataset(self.root/'data',1),Transport(),gate_metric=p.EM_GATE)
        for name,call in fixture['calls'].items():
            with self.subTest(module=name):
                cfg=config(a)['module_calls'][name];cfg['context_window_tokens']=profile['context_window_tokens']
                kw={'call_config':cfg,'max_attempts':6,**{k:profile[k] for k in ('max_input_chars','max_message_utf8_bytes')}}
                sends=[]
                def gen(n,msg,d,c):
                    sends.append(msg)
                    content=fixture['invalid'] if len(sends)==1 else json.dumps(fixture['outputs'][name])
                    return {'content':content,'finish_reason':'stop'}
                folder=self.root/name
                stages.run_stage(folder,call,generate=gen,**kw)
                self.assertEqual(len(sends),2);self.assertEqual(sends[1][-2]['content'],fixture['invalid'])
                self.assertEqual(sends[1][:2],call.messages)
                metrics=stages.read(folder/'attempts/002/capacity.json')
                self.assertEqual(metrics,fixture['report']['modules'][name]['with_feedback'])
                self.assertEqual(metrics['reserved_output_tokens'],cfg['max_tokens'])
                self.assertLess(metrics['context_token_upper_estimate'],cfg['context_window_tokens'])
                # A lower frozen budget fits the base, but rejects the complete retry BEFORE sending it.
                constrained=deepcopy(kw)
                constrained['call_config']['context_window_tokens']=metrics['context_token_upper_estimate']-1
                blocked=self.root/(name+'_over');sends.clear()
                self.reject(stages.run_stage,blocked,call,generate=gen,**constrained)
                self.assertEqual(len(sends),1)
                self.assertFalse((blocked/'attempts/002/request_started.json').exists())
                self.assertEqual(stages.read(blocked/'attempts/001/response.json')['content'],fixture['invalid'])
                self.reject(stages.run_stage,blocked,call,generate=gen,resume=True,**constrained)
                self.assertEqual(len(sends),1)

    def test_campaign_context_capacity_is_optional_and_validated(self):
        a=LMBAdapter(Dataset(self.root/'data',1),Transport(),gate_metric=p.EM_GATE)
        with using_benchmark(a):
            cfg=config(a);validate_config(cfg)
            for name in cfg['module_calls']:
                bad=deepcopy(cfg);bad['module_calls'][name].pop('context_window_tokens')
                validate_config(bad)
                for invalid in (None,True,0,bad['module_calls'][name]['max_tokens']):
                    bad['module_calls'][name]['context_window_tokens']=invalid
                    self.reject(validate_config,bad)

    def test_c01_larger_complete_replay_is_rejected_without_clipping(self):
        fixture=capacity_fixture.build(self.root/'stress',stress=True)
        report=fixture['report'];self.assertFalse(report['modules']['replay']['fits_frozen_limits'])
        self.assertLess(report['modules']['replay']['context_estimate_headroom'],0)
        a=LMBAdapter(Dataset(self.root/'data',1),Transport(),gate_metric=p.EM_GATE)
        cfg=config(a)['module_calls']['replay'];profile=report['profile']
        sends=[]
        def gen(*args):sends.append(1);raise AssertionError('Over capacity must not send')
        self.reject(stages.run_stage,self.root/'over',fixture['calls']['replay'],generate=gen,
                    call_config=cfg,max_attempts=6,
                    **{k:profile[k] for k in ('max_input_chars','max_message_utf8_bytes')})
        self.assertEqual(sends,[])
        self.assertEqual(len(json.loads(fixture['calls']['replay'].messages[1]['content'])['runs']),20)
