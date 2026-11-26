"""Synthetic tasks and preset responses: no dataset or model measurements."""
from copy import deepcopy
import json
from src.skill_evolution.v25_1.config import method_config
from pathlib import Path
import openpyxl
from src.skill_evolution.v25_1.baseline import configuration
from src.skill_evolution.v25_1.config import KNOWLEDGE_REVIEW
from src.skill_evolution.v25_1.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25_1.benchmarks.spreadsheetbench import executor

PARENT='# Spreadsheet manipulation\n\n## Data rows\nProcess rows from row 2 through the row before max_row.\n\n## Preservation\nPreserve unrelated cells.\n'
NEW='Identify the header row from the task-required column labels in the input; process numeric data rows after that header through the last populated row, including it, while leaving explanatory and footer rows unchanged.'
CODE='import openpyxl\nwb = openpyxl.load_workbook(INPUT_PATH)\nws = wb["Sheet1"]\nfor r in range(2, ws.max_row%s):\n    a, b = ws.cell(r, 1).value, ws.cell(r, 2).value\n    if isinstance(a, (int, float)) and isinstance(b, (int, float)):\n        ws.cell(r, 3).value = a * b\nwb.save(OUTPUT_PATH)\n'


def config(root,n=2,rounds=1,test=0):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);tasks={};batches=[];tests=[]
    for i in range(n*rounds+test):
        tid=f'syn_{i+1:03}';split='test' if i>=n*rounds else ('train' if i%2==0 else 'val')
        folder=root/tid;folder.mkdir();w=openpyxl.Workbook();s=w.active;s.title='Sheet1'
        s.append(['Qty','Price','Total']);s.append([2,3,None]);s.append([4,5,None]);w.save(folder/'input.xlsx')
        s['C2']=6;s['C3']=20;w.save(folder/'answer.xlsx');w.close()
        tasks[tid]=dict(id=tid,dataset_id=tid,split=split,instruction='In Sheet1 multiply Qty by Price into Total for all data rows; preserve unrelated cells.',instruction_type='Cell-Level Manipulation',answer_region='Sheet1!C2:C3',input_path=str((folder/'input.xlsx').resolve()),answer_path=str((folder/'answer.xlsx').resolve()))
        if split=='test':tests.append(tid)
    optimize=[t for t in tasks if t not in tests];batches=[optimize[i:i+n] for i in range(0,len(optimize),n)]
    c=configuration(tasks,batches,tests,fixture=True,knowledge_review=KNOWLEDGE_REVIEW);c['initial_skill']['text']=PARENT;c['retry_delay_seconds']=0
    # Synthetic tests may vary Skill, timing and workers independently of formal preparation.
    c.pop('comparison_profile');c['actor_max_workers']=1
    c['method']=method_config(KNOWLEDGE_REVIEW, 'v25_1_current_update_evidence_to_behavior_v1')
    return c


def response(content):return {'content':content,'finish_reason':'stop','usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}


class ActorResponses:
    def __init__(self,*,candidate_correct=True):self.calls=[];self.candidate_correct=candidate_correct
    def __call__(self,messages,directory,timeout,cfg):
        self.calls.append(deepcopy(messages));correct=self.candidate_correct and NEW in messages[0]['content']
        return response('```python\n'+CODE%(' + 1' if correct else '')+'```')


def fast_execute(code,input_path,directory,timeout,cfg):
    # Test-only predetermined behavior. Does not execute model-controlled Python.
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);(directory/'program.py').write_text(code)
    output=directory/'result.xlsx';w=openpyxl.load_workbook(input_path);s=w['Sheet1']
    for r in range(2,s.max_row+(1 if 'max_row + 1' in code else 0)):s.cell(r,3).value=s.cell(r,1).value*s.cell(r,2).value
    w.save(output);w.close()
    return {'status':'success','exit_status':0,'stdout':'','stderr':'','output_openable':True,'output_path':str(output)}


class MethodResponses:
    def __init__(self,*,decision='revise',pre='KEEP',editor_empty=False,conflict=False,withdraw=False,history=False,invalid_once=None):
        self.decision,self.pre,self.editor_empty,self.conflict,self.withdraw,self.history=decision,pre,editor_empty,conflict,withdraw,history
        self.invalid_once=invalid_once;self.calls=[];self.payloads=[]
    def __call__(self,messages,directory):
        name=next(k for k in ('grouping','diagnosis','preconditioner','editor','replay','verifier','repair') if k in Path(directory).parts)
        self.calls.append(name);p=json.loads(messages[1]['content']);self.payloads.append((name,p))
        if self.invalid_once==name:self.invalid_once=None;return response('{invalid')
        if name=='grouping':
            value={'groups':[{'group_id':'G1','members':[r['ref'] for r in p['runs']], 'decision_problem':'Process final data rows.',
                              'shared_basis':' '.join(r['ref']+':1' for r in p['runs'])+' use a row loop.', 'important_differences':[]}]}
        elif name=='diagnosis':
            value={'decision':self.decision,'reason':'P1:1 excludes the final data row.','plan':None}
            if self.decision=='revise':value['plan']={'goal':'Include all required data rows.', 'updates':[{'id':'u1','text':'Include the final data row while preserving unrelated cells.','basis':['G1','P1:1','P1:outcome']}], 'checks':[{'id':'c1','update_ids':['u1'],'question':'Does the last data row receive its result?'}]}
        elif name=='preconditioner':
            value={'adjustments':[{'target':'u1','focus':['D'] if self.pre=='DROP' else [],'change':self.pre,'reason':'`Evidence:P1:1` provides the current row boundary.','to':[] if self.pre=='DROP' else None}], 'checks':[] if self.pre=='DROP' else None}
        elif name=='editor':
            old='Process rows from row 2 through the row before max_row.' if NEW not in p['parent'] else NEW
            new=NEW if old!=NEW else NEW+' Check all required rows.'
            patch='' if self.editor_empty else '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-'+old+'\n+'+new+'\n'
            value={'patch':patch,'reason':'Apply the inclusive row boundary.'}
        elif name=='replay':
            refs=['diff','P1:1','P1:outcome','Q1:outcome'];revises=[]
            if self.history and p['memory']['entries']:
                old=p['memory']['entries'][0];revises=[old['id']];refs+=old['knowledge'][0]['evidence']
            value={'entries':[{'revises':revises,'knowledge':[{'text':'Observed paired scores describe this input; do not assume broader gains.','evidence':refs}]}]}
        elif name=='verifier':
            value={'results':[{'target':t['target'],'verdict':'CONFLICT' if self.conflict else 'SUPPORTED','issues':[{'statement':t['knowledge']['text'],'reason':'Limit the claim to the submitted result.','evidence':['P1:outcome']}] if self.conflict else []} for t in p['targets']]}
        elif name=='repair':
            value={'changes':[{'target':t['target'],'knowledge':None if self.withdraw else {'text':'The scores were computed after submission and describe only these observed runs.','evidence':t['knowledge']['evidence']}} for t in p['targets']]}
        else:raise AssertionError(name)
        return response(json.dumps(value))
