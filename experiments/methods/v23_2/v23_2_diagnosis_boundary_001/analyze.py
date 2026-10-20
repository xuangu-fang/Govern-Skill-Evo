"""Read P1 archives and verify request isolation; never calls a model."""
import json
from pathlib import Path
from experiments.methods.v23_2.v23_2_diagnosis_boundary_001 import run as r


def main():
    r.verify_p0()
    assert r.frozen_files() == r.ev.read(r.EXP/'config/p1_freeze.json')['sha256']
    comparison = {}; attempts = []; verification = {}
    lines = ['# 原始与P1 Diagnosis全文\n\n仅result.json指向的合法输出参与语义比较；所有失败原文亦保留。']
    for rnd in r.ROUNDS:
        saved, entry = r.material(rnd); stage = r.OUTPUT/rnd; result = None
        if (stage/'result.json').exists():
            directory = stage/r.ev.read(stage/'result.json')['path']
            result = r.local.load_attempt(directory, prompt_path=r.PROMPT)['diagnosis']
        comparison[rnd] = {'original':entry['original_output'],'new':result}
        lines.append(f'\n## {rnd}\n\n[原始输入]({entry["diagnosis_path"]}/input.json) · [Grouping]({entry["grouping_path"]}/grouping.json) · [原始请求]({entry["diagnosis_path"]}/request.json)')
        for label,value in comparison[rnd].items():
            lines.append(f'\n### {label}\n\n```json\n'+json.dumps(value,ensure_ascii=False,indent=2)+'\n```')
        for directory in sorted((stage/'attempts').glob('*')):
            assert r.ev.read(directory/'input.json') == saved and 'memory' not in saved
            messages = r.ev.read(directory/'messages.json')
            old = r.ev.read(Path(entry['diagnosis_path'])/'messages.json')
            expected = old[0]['content']
            for change in r.ev.read(r.EXP/'config/replacements.json'):
                expected = expected.replace(change['before'],change['after'])
            assert messages[0]['content'] == expected and messages[1:] == old[1:]
            assert set(json.loads(messages[1]['content'])) == {'parent','command_sets','runs','grouping'}
            req = r.ev.read(directory/'request.json') if (directory/'request.json').exists() else None
            if req:
                assert req['body']['messages'] == messages and req['attempts'] == 1
                actual = {**{k:v for k,v in req['body'].items() if k!='messages'},
                          'endpoint':req['endpoint'],'timeout_seconds':req['timeout_seconds']}
                assert actual == entry['config']['call_config']
            meta = r.ev.read(directory/'run.json')
            assert meta['max_input_chars'] == entry['config']['max_input_chars']
            assert meta['max_message_utf8_bytes'] == entry['config']['max_message_utf8_bytes']
            response = r.ev.read(directory/'response.json') if (directory/'response.json').exists() else {}
            attempts.append({'round':rnd,'path':str(directory), 'status':meta['status'],
                 'started_at':meta['started_at'],'finished_at':meta['finished_at'],
                 'elapsed_seconds':meta['elapsed_seconds'],'usage':response.get('usage'),
                 'finish_reason':response.get('finish_reason'),
                 'error':r.ev.read(directory/'error.json') if (directory/'error.json').exists() else None})
            lines.append(f'\n### 本次真实attempt {directory.name}\n\n[请求]({directory}/request.json) · [响应]({directory}/response.json) · [校验]({directory}/validation.json)\n\n```text\n'+((directory/'raw_output.txt').read_text() if (directory/'raw_output.txt').exists() else '(no completed response)')+'\n```')
        verification[rnd] = {'same_original_upstream_input':True,'memory_absent':True,
                            'only_two_system_replacements':True,'model_config_and_capacity_unchanged':True,
                            'valid_result':result is not None}
    assert len(attempts)<=3 and all(a['started_at']>r.ev.read(r.EXP/'config/p1_freeze.json')['at'] for a in attempts)
    r.ev.save(r.EXP/'results/comparison.json',comparison)
    r.ev.save(r.EXP/'results/attempts.json',attempts)
    r.ev.save(r.EXP/'results/verification.json',verification)
    (r.EXP/'reports/OUTPUTS.md').write_text('\n'.join(lines)+'\n')
    summary=r.ev.read(r.OUTPUT/'summary.json');r.ev.save(r.EXP/'results/summary.json',summary)
    print(json.dumps(summary))


if __name__=='__main__':main()
