"""Prepare explicit input manifests; never run tasks or read answer workbook cells."""
import json
import zipfile
from xml.etree import ElementTree
from pathlib import Path
from .facts import require
from .storage import write_record
from .config import method_config
from .benchmarks.spreadsheetbench import protocol, scoring
from .benchmarks.spreadsheetbench.adapter import IDENTITY, SpreadsheetBenchAdapter
from .grouping import call_configuration

ROOT=Path(__file__).resolve().parents[6]
CANDIDATE='v25_spreadsheetbench_verified400_rc1'
DEFAULT_DATA=ROOT/'external/Trace2Skill/data/spreadsheetbench_verified/spreadsheetbench_verified_400'
DEFAULT_SPLITS=ROOT/'external/SkillOpt/data/spreadsheetbench_id_split'
DEFAULT_BATCH_SIZE=15
COMPARISON_PROFILE='execution_only_actor48k_v1'
MODULE_BUDGETS={'diagnosis':32768,'preconditioner':49152,'replay':49152,'verifier':49152,'repair':32768}


def configuration(tasks, batches, test_tasks, *, fixture=False):
    return dict(candidate=CANDIDATE,comparison_profile=COMPARISON_PROFILE,method=method_config(),benchmark=IDENTITY.copy(),
        dataset={'kind':'synthetic_offline' if fixture else 'Verified-400','val_participates_in_optimization':True,
                 'optimization_order':'original Train order, then original Val order','epochs':1},
        task_items=tasks,batches=batches,test_tasks=test_tasks,
        initial_skill={'source':'SkillOpt SpreadsheetBench initial Skill (vendored verbatim)',
                       'text':protocol.template('initial_skill.md')},
        actor_model='deepseek-v4.1-flash',actor_base_url='http://llm-proxy.intra.xiaojukeji.com',
        call_config=call_configuration(base_url='http://llm-proxy.intra.xiaojukeji.com',model='deepseek-v4.1-flash',max_tokens=16384,timeout=300),
        actor_profile={**protocol.DEFAULTS,'actor_max_output_tokens':49152,'actor_task_timeout_seconds':0,
                       'attempt_budget_policy':'program_executions_v1','actor_history_policy':protocol.EXECUTION_HISTORY},
        actor_request_attempts=6,max_attempts=6,actor_max_workers=4,
        max_input_chars=4000000,max_message_utf8_bytes=6000000,retry_delay_seconds=2,continue_no_change=True,
        module_max_tokens=MODULE_BUDGETS.copy(),
        executor={'backend':'docker','image':'govern-skill-v25-python:rc1','memory':'2g','cpus':1})


def validate_latest_configuration(config):
    """New preparation targets are strict; unmarked frozen legacy configs stay readable."""
    require(config.get('comparison_profile')==COMPARISON_PROFILE,'Latest comparison profile required')
    expected=configuration({},[],[])  # Pure construction; no data access or model calls.
    for key in ('method','benchmark','actor_profile','actor_max_workers','actor_request_attempts',
                'max_attempts','retry_delay_seconds','call_config','actor_model','actor_base_url',
                'module_max_tokens','max_input_chars','max_message_utf8_bytes','continue_no_change','executor','initial_skill'):
        require(config.get(key)==expected[key],f'Latest comparison configuration differs: {key}')


def prepare(output, *, data_root=DEFAULT_DATA, split_root=DEFAULT_SPLITS):
    data_root,split_root=Path(data_root).resolve(),Path(split_root).resolve()
    metadata={str(t['id']):t for t in json.loads((data_root/'dataset.json').read_text())}
    tasks={};splits={};issues=[]
    for split in ('train','val','test'):
        entries=json.loads((split_root/split/'items.json').read_text());splits[split]=[]
        for item in entries:
            rawid=str(item['id']);key=f'{split}:{rawid}';row=metadata[rawid]
            directory=data_root/row['spreadsheet_path'];inputs=sorted(directory.glob('*_init.xlsx')) or list(directory.glob('initial.xlsx'));answers=sorted(directory.glob('*_golden.xlsx')) or list(directory.glob('golden.xlsx'))
            require(len(inputs)==len(answers)==1,'Expected exactly one input and answer workbook')
            with zipfile.ZipFile(answers[0]) as book:
                sheets=[e.attrib['name'] for e in ElementTree.fromstring(book.read('xl/workbook.xml')).findall('{*}sheets/{*}sheet')]
            region=row['answer_position'].strip()
            if '!' not in region:
                sheet=row.get('answer_sheet') or sheets[0]
                region=','.join("'"+sheet.replace("'","''")+"'!"+r.strip() for r in region.split(','))
            try:
                parsed=scoring.regions(region)
                require(all(sheet in sheets for sheet,_ in parsed), 'Target worksheet absent from reference metadata')
            except ValueError as exc:
                issues.append({'task_id':key,'answer_region':region,'reason':str(exc),'action':'Resolve explicitly before final Test evaluation; original task remains in split'})
            tasks[key]=dict(id=key,dataset_id=rawid,split=split,instruction=row['instruction'],instruction_type=row['instruction_type'],
                            answer_region=region,input_path=str(inputs[0]),answer_path=str(answers[0]))
            splits[split].append(key)
    optimize=splits['train']+splits['val'];config=configuration(tasks,[optimize[i:i+DEFAULT_BATCH_SIZE] for i in range(0,len(optimize),DEFAULT_BATCH_SIZE)],splits['test'])
    config['dataset']['metadata_issues']=issues
    SpreadsheetBenchAdapter().validate_config(config)
    output=Path(output).resolve();require(not output.exists(),'Preparation requires a new directory')
    (output/'config').mkdir(parents=True);(output/'data').mkdir()
    write_record(output/'config/campaign.json',config)
    write_record(output/'data/splits.json',splits|{'optimization':optimize,'val_participates_in_optimization':True})
    (output/'config/initial_skill.md').write_text(config['initial_skill']['text'])
    write_record(output/'config/preparation.json',{'candidate':CANDIDATE,'dataset_root':str(data_root),'split_source':str(split_root),
        'counts':{s:len(ids) for s,ids in splits.items()},'optimization_tasks':len(optimize),'batch_size':DEFAULT_BATCH_SIZE,
        'real_model_requests':0,'dataset_tasks_executed':0})
    return {'experiment':str(output),'candidate':CANDIDATE,'optimization_tasks':len(optimize),'test_tasks':len(splits['test'])}
