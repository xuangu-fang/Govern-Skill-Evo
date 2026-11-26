import json
from pathlib import Path
import sys
from unittest.mock import patch
import zipfile

import openpyxl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/runs'))
import repair_spreadsheetbench_output_submission as repair
from src.skill_evolution.v25.benchmarks.spreadsheetbench import actor, facts
from .support import config, response, fast_execute, CODE, PARENT


def invalid_cache(path):
    w = openpyxl.Workbook(); w.active.title = 'Sheet1'; w.active['C2'] = '=1/0'; w.save(path); w.close()
    with zipfile.ZipFile(path) as z: contents = {n: z.read(n) for n in z.namelist()}
    contents['xl/worksheets/sheet1.xml'] = contents['xl/worksheets/sheet1.xml'].replace(b'<v></v>', b'<v>#DIV/0!</v>').replace(b'<v/>', b'<v>#DIV/0!</v>').replace(b'<v />', b'<v>#DIV/0!</v>')
    with zipfile.ZipFile(path, 'w') as z:
        for n, data in contents.items(): z.writestr(n, data)


def test_dual_mode_rejects_invalid_cache_but_accepts_typed_excel_error(tmp_path):
    path = tmp_path / 'bad.xlsx'; invalid_cache(path)
    w = openpyxl.load_workbook(path); w.close()
    detail = repair.validate_output(path)
    assert 'data_only=True' in detail and '#DIV/0!' in detail
    good = tmp_path / 'good.xlsx'
    w = openpyxl.Workbook(); w.active['A1'] = '#DIV/0!'; w.save(good); w.close()
    assert repair.validate_output(good) is None
    (tmp_path / 'broken.xlsx').write_text('bad')
    assert 'data_only=False' in repair.validate_output(tmp_path / 'broken.xlsx')


def test_checked_executor_turns_false_success_into_output_feedback(tmp_path):
    output = tmp_path / 'output'; output.mkdir(); invalid_cache(output / 'result.xlsx')
    old = {'status': 'success', 'exit_status': 0, 'output_openable': True}
    with patch.object(repair.executor, 'execute', return_value=old):
        result = repair.execute_checked('', '', tmp_path, 600, {})
    assert result['status'] == 'error' and result['error_category'] == 'output_file_error'
    assert not result['output_openable'] and 'data_only=True' in result['error_detail']


def test_reopen_preserves_budget_and_archive_then_resumes_next_execution(tmp_path):
    cfg = config(tmp_path / 'data', n=1); task = next(iter(cfg['task_items'].values()))
    source = tmp_path / '001'; dest = tmp_path / '002'
    def execute(code, inp, directory, timeout, config):
        path = Path(directory) / 'bad.xlsx'; invalid_cache(path)
        return dict(status='success', exit_status=0, output_openable=True,
                    output_path=str(path), stdout='', stderr='')
    def generate(*args): return response('```python\n' + CODE % ' + 1' + '```')
    with pytest.raises(ValueError): actor.run(task, PARENT, source, cfg, generate=generate, execute=execute)
    before = (source / 'actor_state.json').read_bytes()
    original = json.loads(before)
    changed = repair.prepare_recovery(source, dest)
    assert (source / 'actor_state.json').read_bytes() == before
    assert changed['requests'] == original['requests']
    assert changed['code_attempts'] == changed['program_executions'] == changed['api_requests'] == 1
    assert 'code_attempts_remaining: 29' in changed['messages'][-1]['content']
    seen = []
    def next_generation(messages, directory, *args):
        seen.append((messages, str(directory)))
        return generate()
    record = json.loads(actor.run(task, PARENT, dest, cfg, generate=next_generation, execute=fast_execute).read_text())
    assert len(seen) == 1 and seen[0][1].endswith('requests/002_01')
    assert 'output_file_error' in seen[0][0][-1]['content']
    assert task['answer_path'] not in seen[0][0][-1]['content']
    assert record['code_attempts'] == record['api_requests'] == record['program_executions'] == 2
    assert record['score']['hard'] == 1
    facts.build_facts([record])
    with pytest.raises(ValueError, match='scored|interrupted'):
        repair.prepare_recovery(dest, tmp_path / '003')
