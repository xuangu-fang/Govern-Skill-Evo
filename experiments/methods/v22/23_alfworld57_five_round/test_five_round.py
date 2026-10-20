"""Synthetic full five-round lineage and stop tests; no network/environment."""
from pathlib import Path
import sys,json,unittest
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import Mock
import requests
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE/'revision'))
from src.adapters.alfworld.skill_runtime import load_skill,make_record,build_skill_messages,write_record
from src.adapters.alfworld.run_task_skill import RecordingSession
from src.skill_evolution.v22.continual_runtime import load_bundle
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_verify import verify_campaign
from src.skill_evolution.v22.model_call import semantic_call
from src.skill_evolution.v22.five_round_runtime import capacity_audit
from src.skill_evolution.v22 import p1_input

class Fixture:
    def __init__(self,root):
        self.root=root; self.game=root/'synthetic.tw-pddl';self.game.write_text('Offline synthetic, no environment.')
        self.fail=None;self.calls=[]
    def response(self,content):
        response=requests.Response();response.status_code=200
        response._content=json.dumps({'model':'deepseek-flash','choices':[{'finish_reason':'stop','message':{'content':content}}],
           'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2,'completion_tokens_details':{'reasoning_tokens':0}}}).encode()
        return response
    def execute(self,item,skill_file,out):
        out=Path(out);out.mkdir(parents=True);n=int(next(p[1:] for p in out.parts if p in ['r1','r2','r3','r4','r5']))
        candidate='candidate_runs' in out.parts
        # Alternating ACCEPT and RETAIN, including regression learning.
        won=candidate and n%2==1
        skill=load_skill(skill_file); split=item['id'].split(':')[0]
        record=make_record(item=item,split=split,purpose='development',skill=skill,model='deepseek-flash',max_steps=50,
          gamefile=self.game,manifest_path=ROOT/f'benchmarks/alfworld/editions/skillopt_39_18_134/{split}/items.json',
          versions={'offline':'synthetic'},backend_id='synthetic')
        obs='Your task is to: inspect the visible room.';messages=build_skill_messages(obs,['look'],'inspect the visible room.',[],skill)
        record.update(initial_observation=obs,initial_admissible_commands=['look'],won=won,status='success' if won else 'environment_ended',finished_at='synthetic')
        record['steps']=[{'step':1,'phase':'requesting','messages':messages,'admissible_commands':['look']}]
        path=out/'trajectory.json';session=Mock();session.post.return_value=self.response('<action>look</action>')
        recording=RecordingSession(session,record,path,archive_responses=True)
        body={'model':'deepseek-flash','messages':messages,'temperature':1.0,'max_tokens':16384,
              'reasoning_effort':'medium','thinking':{'type':'enabled'},'stream':False}
        response=recording.post('https://offline.invalid',json=body)
        record['steps'][0].update(phase='executed',model_response={'content':'<action>look</action>',
           'response_model':'deepseek-flash','finish_reason':'stop','usage':response.json()['usage'],'api_attempts':1,'transport_retries':0},
           action='look',fallback=None,action_in_admissible_commands=True,observation='Synthetic outcome.',reward=int(won),done=True,won=won)
        write_record(path,record);return path
    def generate(self,stage,messages,out):
        n=int(next(p[1:] for p in Path(out).parts if p in ['r1','r2','r3','r4','r5']))
        view=p1_input.decode(json.loads(messages[1]['content']));self.calls.append((n,stage))
        if self.fail==(n,stage): raise ValueError('Synthetic technical stop before network.')
        if stage=='classification':
            value={'groups':[{'group_id':'G1','decision_problem':'When is visible inspection useful?',
               'members':[x['task_ref'] for x in view['experiences']], 'shared_basis':'Visible decisions share an inspection question.',
               'important_differences':['Native outcomes may differ.']}]}
        elif stage=='diagnosis':
            group=next(k for k in view['sources'] if k.startswith('group:'))
            value={'decision':'revise','reason':'Synthetic observed inspection opportunity.', 'plan':{'intent':'Inspect under an unresolved visible condition.',
              'requirements':[{'id':'u1','text':'Inspect only when current evidence leaves a relevant decision unresolved.','basis':[group,'P1:1']}],
              'watch':[{'id':'w1','about':['requirement:u1'],'question':'Does inspection help or interfere?'}],'open':[]}}
        elif stage=='fusion':
            value={'decision':'ready','reason':'Keep the current bounded proposal.','changes':[],'watch_changes':[],'open':[]}
            if view['memory']:
                value.update(reason='Synthetic historical joint response motivates a scoped replacement.',
                   changes=[{'from':['requirement:u1'],'to':[{'id':'u2','text':'Inspect only unresolved visible conditions relevant to the active goal.'}],
                       'basis':[view['memory'][0]['id']],'reason':'Historical bounded observation, not independent attribution.','disposition':'replace'}],
                   watch_changes=[{'from':['watch:w1'],'to':[{'id':'w2','about':['requirement:u2'],'question':'Does the narrowed trigger interfere?'}]}])
        elif stage=='main_editor':
            text=(view['parent']['text'] or '')+f'Inspect unresolved relevant visible conditions. Synthetic round {n}.\n'
            value={'decision':'candidate','reason':'Synthetic realization.','candidate_text':text,
              'mappings':[{'requirements':['requirement:'+r['id'] for r in view['plan']['requirements']], 'side':'candidate','excerpt':text}],
              'issues':[],'watch':[]}
        else:
            group=next(k for k in view['sources'] if k.startswith('group:'))
            value={'findings':[{'id':'f1','about':['watch:'+w['id'] for w in view['plan']['watch']],
                'observation':'Synthetic paired bundle changes the observed response; individual edit contributions remain unknown.',
                'refs':['P1:1','C1:1',group]}],'open':[],'memory_delta':[{'replace':[],
                'claim':'The synthetic joint edit has a measured bounded response.','limits':['Synthetic evidence only; no independent attribution.'],
                'findings':['f1'],'retire_limits':[]}]}
        session=Mock();session.post.return_value=self.response(json.dumps(value))
        return semantic_call(stage,messages,session=session,endpoint='https://offline.invalid',key='fixture',model='deepseek-flash',
            output=out,max_tokens=65536 if stage=='post_gate_learning' else 32768,timeout_seconds=600,transport_policy='single_attempt')

class FiveRoundTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.bundle=load_bundle(HERE/'config/plan.json');self.f=Fixture(self.root)
    def test_full_five_round_accept_retain_memory_lineage(self):
        out=self.root/'campaign';r=run_campaign(self.bundle,out,self.f.generate,self.f.execute,offline=True)
        self.assertEqual(r['status'],'completed',{k:v for k,v in r.items() if k!='rounds'})
        self.assertEqual(r['published_rounds'],5);self.assertEqual(r['cost']['episodes_dispatched'],114)
        self.assertEqual(len(self.f.calls),25)
        self.assertEqual([x['gate']['decision'] for x in r['rounds']],['ACCEPT','RETAIN','ACCEPT','RETAIN','ACCEPT'])
        prev=json.loads((out/'state0.json').read_text())
        for n in range(1,6):
            d=out/f'rounds/r{n}';c=json.loads((d/'context.json').read_text());state=json.loads((d/'state.json').read_text())
            self.assertEqual(c['memory'],prev['memory']);self.assertEqual(c['parent'],prev['parent'])
            self.assertEqual(len(state['memory']),n)
            if n>1:self.assertTrue(r['rounds'][n-1]['fusion']['history_cited'])
            if n%2==0:self.assertEqual(state['parent'],prev['parent'])
            prev=state
        self.assertTrue(verify_campaign(out)['campaign_complete'])
    def test_checkpoint_technical_stop_keeps_published_pair(self):
        self.f.fail=(2,'fusion');out=self.root/'campaign'
        r=run_campaign(self.bundle,out,self.f.generate,self.f.execute,offline=True)
        self.assertEqual(r['status'],'error');self.assertEqual(r['published_rounds'],1)
        self.assertEqual(r['rounds'][-1]['active_stage'],'fusion')
        self.assertFalse((out/'rounds/r2/state.json').exists());self.assertFalse((out/'rounds/r3').exists())
        self.assertEqual(self.f.calls.count((2,'fusion')),1)
        self.assertFalse(verify_campaign(out)['campaign_complete'])
    def test_capacity_and_native_id_rejection(self):
        with self.assertRaises(ValueError):capacity_audit([{'role':'user','content':'x'*400001}],self.bundle['plan'],'diagnosis')
        with self.assertRaises(ValueError):capacity_audit([{'role':'user','content':'中'*330000}],self.bundle['plan'],'diagnosis')
        for item in self.bundle['task_items'].values():self.assertIn(item['id'].split(':')[0],['train','val'])

if __name__=='__main__':unittest.main(verbosity=2)
