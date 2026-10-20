"""Read and verify archived outputs; never calls a model."""
import json
from pathlib import Path
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_response_construction_001 import run as r
from experiments.methods.v23_2.v23_2_executability_001 import run as history
from src.skill_evolution.v23 import evolution as ev
from src.skill_evolution.v23_2 import local_validation as local


def main():
    comparisons={};verification={};attempts=[]
    full=['# 三版本真实输出与完整 Effective Plan\n','Original Plan 三版共享。正式 V23 与 alignment 为真实历史保存输出；construction 为本次固定材料输出。技术停止不伪造 Effective Plan。\n']
    for name in ('R04','R05','R06'):
        _,saved,old,cfg,paths=history.material(name)
        prevdir=history.selected(history.ROOT/'artifacts/methods/v23_2/v23_2_response_alignment_001',name)
        prev=local.load_attempt(prevdir,prompt_path=r.base.PROMPT)
        currentdir=r.OUTPUT/name
        latest=None
        if (currentdir/'result.json').exists():
            attempt=history.selected(r.OUTPUT,name)
            latest=local.load_attempt(attempt,prompt_path=r.PROMPT)
            assert ev.read(attempt/'input.json')==saved
            before=local.messages_for('preconditioner',saved)
            after=ev.read(attempt/'messages.json')
            template=local.PROMPTS['preconditioner'].read_text()
            first=template.index('Examine whether each Update is appropriate relative')
            last=template.index('\n\nExecution records',first)
            replacement=(r.EXP/'config/replacement.txt').read_text().rstrip('\n')
            assert after[1:]==before[1:]
            assert after[0]['content']==before[0]['content'].replace(template[first:last],replacement)
            assert ev.read(attempt/'run.json')['call_config']==cfg.get('stage_configs',{}).get('preconditioner',cfg['call_config'])
            assert latest['memory']==saved['memory']
        verification[name]={'same_frozen_inputs':latest is not None,'only_system_requirement_changed':latest is not None,
                            'model_config_equal':latest is not None,'raw_response_reparsed_and_plan_recompiled':latest is not None,
                            'active_memory_unchanged':latest is not None,'valid_output':latest is not None}
        row={'original_plan':saved['diagnosis']['plan'],'memory_ids':[m['id'] for m in saved['memory']['entries']]}
        full.append(f'\n## {name}\n\n### Original Plan\n\n```json\n'+json.dumps(row['original_plan'],ensure_ascii=False,indent=2)+'\n```\n')
        for label,value in [('V23',old),('alignment',prev),('construction',latest)]:
            row[label]=None if value is None else {k:value[k] for k in ('preconditioner','effective_plan')}
            full.append(f'\n### {label}\n\n```json\n'+json.dumps(row[label],ensure_ascii=False,indent=2)+'\n```\n')
        comparisons[name]=row
        for attempt in sorted((currentdir/'attempts').glob('*')):
            meta=ev.read(attempt/'run.json'); response=ev.read(attempt/'response.json') if (attempt/'response.json').exists() else {}
            attempts.append({'round':name,'attempt':attempt.name,'status':meta['status'],'started_at':meta['started_at'],
                             'finished_at':meta.get('finished_at'),'elapsed_seconds':meta.get('elapsed_seconds'),
                             'finish_reason':response.get('finish_reason'),'usage':response.get('usage'),
                             'error':ev.read(attempt/'error.json') if (attempt/'error.json').exists() else None,
                             'path':str(attempt)})
            full.append(f'\n### 本次原始输出 attempt {attempt.name}\n\n[完整请求与响应]({attempt})\n\n```text\n'+(attempt/'raw_output.txt').read_text()+'\n```\n' if (attempt/'raw_output.txt').exists() else f'\n技术停点见 {attempt}\n')
    ev.save(r.EXP/'results/comparison.json',comparisons);ev.save(r.EXP/'results/verification.json',verification)
    ev.save(r.EXP/'results/attempts.json',attempts)
    (r.EXP/'reports/OUTPUTS.md').write_text('\n'.join(full))
    for file in ('summary.json','protection.json'):
        ev.save(r.EXP/'results'/file,ev.read(r.OUTPUT/file))
    with patch.multiple(r.base,EXP=r.EXP,OUTPUT=r.OUTPUT,PROMPT=r.PROMPT,implementation=r.implementation):
        assert r.base.protected_files()==ev.read(r.EXP/'config/protected_before.json')
        assert r.implementation()==ev.read(r.EXP/'config/implementation.json')
        r.base.check_baseline()
    print(json.dumps({'verification':verification,'summary':ev.read(r.OUTPUT/'summary.json')},ensure_ascii=False))


if __name__=='__main__':main()
