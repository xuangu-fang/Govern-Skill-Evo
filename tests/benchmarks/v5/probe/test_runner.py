import json
import tempfile
import unittest
from pathlib import Path
from benchmark_v5.calibration.runner import read
from benchmark_v5.core import ROOT
from benchmark_v5.probe.runner import run_episode

class RunnerTests(unittest.TestCase):
    def test_native_tool_loop_and_saved_terminal_score(self):
        calls=iter([('ask_user',{'scope':'all'}),('book_trip',{'trip_id':'T1','certificate_cents':18800,'gift_cents':0}),
                    ('book_trip',{'trip_id':'T2','certificate_cents':0,'gift_cents':22400}),('finish',{'receipt':{}})])
        def fake(root,payload,timeout):
            self.assertEqual(payload['model'],'deepseek-v4-flash')
            self.assertEqual(payload['max_tokens'],8192)
            self.assertNotIn('evaluate',str(payload['tools']))
            name,args=next(calls)
            return {'model':'deepseek-v4-flash','usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15},
                'choices':[{'finish_reason':'tool_calls','message':{'content':None,'tool_calls':[{'id':name,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}}]},0.0
        config=read(ROOT/'experiments/benchmarks/v5/decision_probe/protocol.json')
        job=dict(id='fake',model='deepseek-v4-flash',task='D1',condition='staged',repetition=0)
        with tempfile.TemporaryDirectory() as d:
            result=run_episode(config,job,Path(d),transport=fake)
            self.assertTrue(result['valid']);self.assertTrue(result['score']['S'])
            self.assertEqual(result['api_attempts'],4)
            self.assertEqual(read(Path(d)/'fake/result.json'),result)

    def test_non_tool_text_stops_without_manufactured_success(self):
        def fake(*args,**kwargs):
            return {'model':'deepseek-v4-flash','usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15},
                'choices':[{'finish_reason':'stop','message':{'content':'Done'}}]},0
        job=dict(id='fake',model='deepseek-v4-flash',task='D2',condition='preferred_over',repetition=0)
        config=read(ROOT/'experiments/benchmarks/v5/decision_probe/protocol.json')
        with tempfile.TemporaryDirectory() as d:
            result=run_episode(config,job,Path(d),transport=fake)
            self.assertEqual(result['stop'],'model_text_stop');self.assertFalse(result['score']['S'])

if __name__=='__main__':unittest.main()
