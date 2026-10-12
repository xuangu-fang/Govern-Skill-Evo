import copy
import json
from pathlib import Path
import tempfile
import unittest
from benchmark_v5.calibration.runner import CONFIG, read, jobs, initial_messages, scenario, run_episode
from benchmark_v5.calibration.transport import TransportError
from benchmark_v5.session import AgentSession, build


def response(name='finish', args=None, model='glm-5.3-flash', content=None):
    msg = {'role': 'assistant', 'content': content, 'reasoning_content': 'Keep native continuity.'}
    if name:
        msg['tool_calls'] = [{'index': 0, 'id': 'call1', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args or {})}}]
    return {'model': model, 'choices': [{'message': msg, 'finish_reason': 'tool_calls' if name else 'stop'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120}}, 0.1


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.config = read(CONFIG)
        self.job = {'id':'test', 'task':'K2', 'model':'glm-5.3-flash', 'condition':'baseline', 'repetition':1}

    def run_fake(self, fn, config=None):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_episode(config or self.config, self.job, Path(tmp), fn, lambda _: None)
            return result, read(Path(tmp)/'test'/'trace.json'), read(Path(tmp)/'test'/'audit.json')

    def test_schedule_and_variants(self):
        js = jobs(self.config)
        self.assertEqual(len(js), 72)
        self.assertEqual(len({j['id'] for j in js}),72)
        self.assertEqual(js, jobs(self.config))
        self.assertEqual(sum(j['condition']=='baseline' for j in js),36)
        self.assertEqual(scenario('I1','decision_variant')['flights']['A']['arrival'],800)
        self.assertEqual(scenario('I1','baseline')['flights']['A']['arrival'],720)

    def test_interface_not_private(self):
        for task in self.config['tasks']:
            env = build(task)
            messages = initial_messages(self.config, {**self.job,'task':task,'condition':'full_documents'}, AgentSession(env))
            content = json.loads(messages[-1]['content'])
            self.assertEqual(set(content), {'request','published_documents'})
            self.assertEqual(env.events, [])
            self.assertNotIn('audit', json.dumps(content))
            self.assertNotIn('predicates',json.dumps(content))

    def test_text_stop_is_valid_failure_not_execution(self):
        r,_,a = self.run_fake(lambda *a,**k:response(name=None, content='I have finished.'))
        self.assertTrue(r['valid'])
        self.assertFalse(r['score']['S'])
        self.assertTrue(r['score']['C'])
        self.assertEqual(r['tool_calls'],0)
        self.assertEqual(a['events'][-1]['tool'],'__end__')

    def test_native_continuity_and_no_grades(self):
        seen=[]
        def fake(root,payload,**kwargs):
            seen.append(copy.deepcopy(payload))
            if len(seen)==1: return response('read_returns')
            return response('finish',{'receipt':{}})
        r,t,a = self.run_fake(fake)
        self.assertEqual(r['api_attempts'],2)
        assistant = seen[1]['messages'][-2]
        self.assertIn('reasoning_content',assistant)
        self.assertNotIn('index',assistant['tool_calls'][0])
        self.assertEqual(seen[1]['messages'][-1]['role'],'tool')
        self.assertNotIn('predicates',json.dumps(seen))
        self.assertEqual(r['usage']['total_tokens'],240)

    def test_transport_retries_record_unknown_usage(self):
        calls=[]
        def fake(*a,**kw):
            calls.append(1)
            if len(calls)==1:raise TransportError('http_error',503)
            return response('finish',{'receipt':{}})
        r,t,_=self.run_fake(fake)
        self.assertTrue(r['valid'])
        self.assertEqual(r['api_attempts'],2)
        self.assertEqual(r['unknown_usage_attempts'],1)
        self.assertEqual(len(t['rounds'][0]['attempts']),2)

    def test_exhausted_transport_is_invalid_not_S0(self):
        def fake(*a,**kw):raise TransportError('http_error',503)
        r,_,_=self.run_fake(fake)
        self.assertFalse(r['valid'])
        self.assertIsNone(r['score'])
        self.assertEqual(r['api_attempts'],2)

    def test_no_retry_auth_or_model_swap(self):
        def fake(*a,**kw):raise TransportError('http_error',401)
        r,_,_=self.run_fake(fake)
        self.assertEqual(r['api_attempts'],1)
        r,_,_=self.run_fake(lambda *a,**kw:response(model='other'))
        self.assertFalse(r['valid'])
        self.assertEqual(r['failure_kind'],'unexpected_response_model')

    def test_invalid_arguments_consume_budget(self):
        cfg=copy.deepcopy(self.config);cfg['limits']['tool_calls']=1
        def fake(*a,**kw):
            r,s=response('cancel_return',{'item':5});return r,s
        r,t,a=self.run_fake(fake,cfg)
        self.assertTrue(r['valid']);self.assertFalse(r['score']['S'])
        self.assertEqual(r['stop'],'tool_budget')
        self.assertEqual(a['events'][0]['result']['error'],'INVALID_ARGUMENT_TYPES')

    def test_token_cap_and_finish_batch(self):
        cfg=copy.deepcopy(self.config);cfg['limits']['completion_tokens']=20
        def fake(root,payload,**kw):
            self.assertEqual(payload['max_tokens'],20)
            return response('read_returns')
        r,_,_=self.run_fake(fake,cfg)
        self.assertEqual(r['stop'],'completion_budget')
        def batch(*a,**kw):
            r,s=response('finish',{'receipt':{}})
            tc=r['choices'][0]['message']['tool_calls']
            tc.append({'id':'extra','type':'function','function':{'name':'cancel_return','arguments':'{"item":"A"}'}})
            return r,s
        r,t,a=self.run_fake(batch)
        self.assertEqual(r['tool_calls'],1)
        self.assertEqual(t['rounds'][0]['tool_results'][-1]['result'],{'error':'SESSION_CLOSED'})
        self.assertEqual(a['final']['requests']['A'],'REQUESTED')

if __name__=='__main__':unittest.main()
