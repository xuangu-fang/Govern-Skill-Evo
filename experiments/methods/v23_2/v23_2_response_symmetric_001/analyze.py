"""Read-only four-version comparison of preserved fixed-material calls."""
import json
from pathlib import Path
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_response_symmetric_001 import run as r
from src.skill_evolution.v23 import evolution as ev
from src.skill_evolution.v23_2 import local_validation as local


def main():
    history=r.base.history
    result={};checks={};attempts=[]
    output=['# 共享 Original Plan 与四版本真实输出\n','每轮三次候选实验均从正式 Original Plan 独立开始，不以前版 Effective Plan 作输入。\n']
    for rnd in ('R04','R05','R06'):
        _,saved,formal,cfg,paths=history.material(rnd)
        versions={'V23':formal}
        for revision in ('alignment','construction'):
            directory=history.selected(history.ROOT/f'artifacts/methods/v23_2/v23_2_response_{revision}_001',rnd)
            prompt=history.ROOT/f'experiments/methods/v23_2/v23_2_response_{revision}_001/config/preconditioner_prompt.md'
            previous=local.load_attempt(directory,prompt_path=prompt)
            assert ev.read(directory/'input.json')==saved
            versions[revision]=previous
        stage=r.OUTPUT/rnd
        latest=local.load_attempt(history.selected(r.OUTPUT,rnd),prompt_path=r.PROMPT) if (stage/'result.json').exists() else None
        versions['symmetric']=latest
        row={'original_plan':saved['diagnosis']['plan'],'memory_ids':[m['id'] for m in saved['memory']['entries']]}
        output.append(f'\n## {rnd}\n\n### Original Plan\n\n```json\n'+json.dumps(row['original_plan'],ensure_ascii=False,indent=2)+'\n```\n')
        checks[rnd]={'historical_inputs_identical':True,'valid_current_result':latest is not None,'all_attempts':[]}
        for label,v in versions.items():
            row[label]=None if v is None else {key:v[key] for key in ('preconditioner','effective_plan')}
            output.append(f'\n### {label}\n\n```json\n'+json.dumps(row[label],ensure_ascii=False,indent=2)+'\n```\n')
        result[rnd]=row
        for attempt in sorted((stage/'attempts').glob('*')):
            inp=ev.read(attempt/'input.json');meta=ev.read(attempt/'run.json');messages=ev.read(attempt/'messages.json')
            assert inp==saved and messages==local.messages_for('preconditioner',saved,prompt_path=r.PROMPT)
            old=ev.read(Path(paths['preconditioner'])/'messages.json');assert old[1:]==messages[1:]
            original=local.PROMPTS['preconditioner'].read_text();start=original.index('Examine whether each Update is appropriate relative');end=original.index('\n\nExecution records',start)
            assert messages[0]['content']==old[0]['content'].replace(original[start:end],(r.EXP/'config/replacement.txt').read_text().rstrip('\n'))
            response=ev.read(attempt/'response.json') if (attempt/'response.json').exists() else {}
            request=ev.read(attempt/'request.json') if (attempt/'request.json').exists() else None
            if request:
                assert request['body']['messages']==messages
                actual={**{k:v for k,v in request['body'].items() if k!='messages'},'endpoint':request['endpoint'],'timeout_seconds':request['timeout_seconds']}
                assert actual==cfg.get('stage_configs',{}).get('preconditioner',cfg['call_config'])
            attempts.append({'round':rnd,'attempt':attempt.name,'status':meta['status'],'elapsed_seconds':meta.get('elapsed_seconds'),
                             'started_at':meta['started_at'],'finished_at':meta.get('finished_at'),'finish_reason':response.get('finish_reason'),
                             'usage':response.get('usage'),'error':ev.read(attempt/'error.json') if (attempt/'error.json').exists() else None,'path':str(attempt)})
            checks[rnd]['all_attempts'].append({'attempt':attempt.name,'input_memory_unchanged':True,'single_system_replacement':True,'request_config_exact':request is not None})
            raw=(attempt/'raw_output.txt').read_text() if (attempt/'raw_output.txt').exists() else '(no completed model output)'
            output.append(f'\n### 本次 attempt {attempt.name} 原始输出\n\n[完整档案]({attempt})\n\n```text\n'+raw+'\n```\n')
    ev.save(r.EXP/'results/comparison.json',result);ev.save(r.EXP/'results/verification.json',checks);ev.save(r.EXP/'results/attempts.json',attempts)
    (r.EXP/'reports/OUTPUTS.md').write_text('\n'.join(output))
    for file in ('summary.json','protection.json'):ev.save(r.EXP/'results'/file,ev.read(r.OUTPUT/file))
    with patch.multiple(r.base,EXP=r.EXP,OUTPUT=r.OUTPUT,PROMPT=r.PROMPT,implementation=r.implementation):
        r.base.check_baseline()
        assert r.base.protected_files()==ev.read(r.EXP/'config/protected_before.json')
        assert r.implementation()==ev.read(r.EXP/'config/implementation.json')
    print(json.dumps(ev.read(r.OUTPUT/'summary.json'),ensure_ascii=False))


if __name__=='__main__':main()
