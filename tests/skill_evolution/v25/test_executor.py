import json
from pathlib import Path
import pytest
from src.skill_evolution.v25.benchmarks.spreadsheetbench import executor
from .support import config,CODE


def test_real_docker_success_and_environment_isolation(tmp_path):
    cfg=config(tmp_path/'data',n=1);task=next(iter(cfg['task_items'].values()))
    extra="\nimport os\nassert 'OPENAI_API_KEY' not in os.environ\nassert not os.path.exists("+repr(task['answer_path'])+")\nassert not os.path.exists('/work/answer.xlsx')\n"
    result=executor.execute(CODE%' + 1'+extra,task['input_path'],tmp_path/'execute',20,cfg)
    assert result['output_openable'] and result['exit_status']==0


@pytest.mark.parametrize('code,category',[("print('no file')",'output_file_error'),("open(OUTPUT_PATH,'w').write('not a workbook')",'output_file_error'),("import socket\nsocket.socket()",'execution_error'),("import subprocess\nsubprocess.run(['ls'])",'execution_error'),("raise RuntimeError('synthetic failure')",'execution_error')])
def test_real_docker_errors(tmp_path,code,category):
    cfg=config(tmp_path/'data',n=1);task=next(iter(cfg['task_items'].values()))
    result=executor.execute(code,task['input_path'],tmp_path/'execute',20,cfg)
    assert not result['output_openable'] and result['error_category']==category


def test_program_timeout(tmp_path):
    cfg=config(tmp_path/'data',n=1);task=next(iter(cfg['task_items'].values()))
    result=executor.execute('while True: pass',task['input_path'],tmp_path/'execute',2,cfg)
    assert result['status']=='timeout' and not result['output_openable']
