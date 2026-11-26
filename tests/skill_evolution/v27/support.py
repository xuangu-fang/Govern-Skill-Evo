from copy import deepcopy
from pathlib import Path
import json
from src.skill_evolution.v27.benchmarks.lmb import protocol as p
from src.skill_evolution.v27.benchmarks.lmb.actor import usage_view
from src.skill_evolution.v27.benchmarks.lmb.scoring import score
from src.skill_evolution.v27.training import Case
from src.skill_evolution.v27.config import method_config

HIDDEN='HIDDEN_REASONING_SENTINEL_DO_NOT_PROJECT'
CHOICES=[{'label':l,'text':f'value {i}'} for i,l in enumerate('ABCDE',1)]
SKILL='Compare hypotheses carefully.\n'

class Dataset:
    optimization_pool=None
    def __init__(self,root,count=3):
        self.root=Path(root);self.root.mkdir(exist_ok=True)
        ids=[f'synthetic:{i:03}' for i in range(count)]
        self.rows={i:{'question':'Which integer is one?','choices':CHOICES,'correct_label':'A'} for i in ids}
        self.splits={'train':ids,'validation':[],'test':[]}
    def case(self,uid):
        r=self.rows[uid]
        return Case(uid,{'question':r['question'],'choices':deepcopy(r['choices'])},{'label':r['correct_label']},{'split':'train','source_split':'train'})
    def snapshot(self):return deepcopy({'rows':self.rows,'splits':self.splits})


def response(content='<answer>A</answer>',finish='stop'):
    return {'choices':[{'finish_reason':finish,'message':{'role':'assistant','content':content,'reasoning_content':HIDDEN}}],
            'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30,'completion_tokens_details':{'reasoning_tokens':15}},
            'provider_metadata':{'nested':HIDDEN}}

class Transport:
    def __init__(self,content='<answer>A</answer>',fn=None):self.calls=0;self.content=content;self.fn=fn
    def metadata(self):return deepcopy(p.ACTOR)
    def __call__(self,messages,directory):
        self.calls+=1
        return self.fn(messages,directory) if self.fn else response(self.content)


def record(uid='synthetic:000',*,role='parent',skill=SKILL,content='<answer>B</answer>',batch=None,finish='stop',question='Which integer is one?'):
    task={'id':uid,'split':'train','question':question,'choices':deepcopy(CHOICES)}
    answer,metrics=score(content,CHOICES,'A');batch=batch or role
    execution={'skill':skill,'actor':deepcopy(p.ACTOR),'initial_messages':p.messages(task,skill),'content':content,
               'termination':finish,'answer':answer,'metrics':metrics,'api_requests':1,'usage_records':[usage_view(response(content))]}
    return {'schema':p.RECORD_VERSION,'run_id':batch+':'+p.digest(uid),'task_id':uid,'task':task,'execution':execution,
            'provenance':{'batch_id':batch,'role':role,'case_sha256':p.digest(task),'task_context_sha256':p.digest(p.messages(task,None)),
                          'scorer':p.EM_GATE,'record_sha256':p.digest(execution)}}


def grouping(runs):
    return {'groups':[{'group_id':'G1','members':[r['ref'] for r in runs], 'decision_problem':'Compare conditions',
                      'shared_basis':' '.join(r['ref']+':1' for r in runs),'important_differences':[]}]}

def diagnosis():
    return {'decision':'revise','reason':'P1:1 returned a wrong label.',
            'plan':{'goal':'Compare the relevant condition.','updates':[{'id':'u1','text':'Check the required equality condition.\n','basis':['P1:1']}],
                    'checks':[{'id':'c1','update_ids':['u1'],'question':'Does the selected option improve?'}]}}

def keep():
    return {'adjustments':[{'target':'u1','focus':[],'change':'KEEP','reason':'`Evidence:P1:0` supports the scoped comparison.','to':None}],'checks':None}

def replay():
    return {'entries':[{'revises':[],'knowledge':[{'text':'The scoped joint edit coincided with an improved submitted option; causation remains uncertain.',
                    'evidence':['diff','P1:outcome','Q1:outcome']}]}]}


def config(adapter,batches=None):
    names=('grouping','diagnosis','preconditioner','editor','replay')
    return {'method':method_config(),'benchmark':p.IDENTITY,'actor':adapter.transport.metadata(),'gate_metric':p.EM_GATE,
            'optimization_splits':['train'],'batches':batches or [list(adapter.dataset.rows)],
            'initial_skill':{'source':'synthetic','text':SKILL},'max_attempts':6,'continue_no_change':True,
            'max_input_chars':1000000,'max_message_utf8_bytes':2000000,'retry_delay_seconds':0,
            'module_calls':{n:{'endpoint':p.ACTOR['endpoint'],'model':p.ACTOR['model'],'max_tokens':16384 if n in ('grouping','editor') else 32768,
                'context_window_tokens':1048576,
                'timeout_seconds':300,'temperature':1.0,'reasoning_effort':'medium','thinking':{'type':'enabled'}} for n in names}}
