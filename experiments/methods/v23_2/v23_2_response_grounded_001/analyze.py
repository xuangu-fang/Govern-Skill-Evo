"""Read preserved responses and compare six versions; no model calls."""
import json
from pathlib import Path
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_response_grounded_001 import run as r
from src.skill_evolution.v23 import evolution as ev
from src.skill_evolution.v23_2 import local_validation as local


def main():
    history=r.base.history
    comparison=ev.read(r.EXP/'results/historical_comparison.json');attempts=[];verification={}
    index=['# 原始证据索引\n\n只链接有效档案；失败尝试见OUTPUTS与attempts.json。',
           '[历史动作与Diff核查](../../v23_2_response_inference_analysis_001/reports/EVIDENCE_INDEX.md)']
    versions={'alignment':'v23_2_response_alignment_001','construction':'v23_2_response_construction_001',
              'symmetric':'v23_2_response_symmetric_001','calibration':'v23_2_evidence_calibration_001',
              'grounded':'v23_2_response_grounded_001'}
    lines=['# 相同Original与六版本实际输出\n\n各版从正式Original独立开始。无效技术尝试仅归档，不当作有效Plan。']
    for rnd,row in comparison.items():
        _,saved,formal,cfg,paths=history.material(rnd)
        assert row['original_plan']==saved['diagnosis']['plan'] and row['V23']['effective_plan']==formal['effective_plan']
        stage=r.OUTPUT/rnd;selected=None
        if (stage/'result.json').exists():
            selected=local.load_attempt(history.selected(r.OUTPUT,rnd),prompt_path=r.PROMPT)
        row['grounded']=None if selected is None else {k:selected[k] for k in ('preconditioner','effective_plan')}
        index.append(f'\n## {rnd}\n\n[当轮Original、Parent、Memory与sources]({paths["preconditioner"]}/input.json)\n\n| 版本 | 实际输出与编译结果 |\n|---|---|')
        for version in ('V23',*versions):
            if row[version] is None:
                index.append(f'| {version} | 合法或技术停点，无有效Plan |');continue
            directory=Path(paths['preconditioner']) if version=='V23' else history.selected(history.ROOT/f'artifacts/methods/v23_2/{versions[version]}',rnd)
            index.append(f'| {version} | [原始响应]({directory}/raw_output.txt) · [Adjustment]({directory}/preconditioner.json) · [Effective]({directory}/effective_plan.json) · [实际Prompt]({directory}/prompt.md) |')
        verification[rnd]={'selected_valid':selected is not None,'attempts':[]}
        lines.append(f'\n## {rnd}\n\n### Original\n\n```json\n'+json.dumps(row['original_plan'],indent=2)+'\n```')
        for v in ('V23','alignment','construction','symmetric','calibration','grounded'):
            lines.append(f'\n### {v}\n\n```json\n'+json.dumps(row[v],indent=2)+'\n```')
        for a in sorted((stage/'attempts').glob('*')):
            assert ev.read(a/'input.json')==saved
            messages=ev.read(a/'messages.json');assert messages==local.messages_for('preconditioner',saved,prompt_path=r.PROMPT)
            old=ev.read(Path(paths['preconditioner'])/'messages.json');assert messages[1:]==old[1:]
            original=(r.EXP/'config/original_passage.txt').read_text().rstrip('\n')
            assert messages[0]['content']==old[0]['content'].replace(original,(r.EXP/'config/replacement.txt').read_text().rstrip('\n'))
            request=ev.read(a/'request.json') if (a/'request.json').exists() else None
            if request:
                assert request['body']['messages']==messages
                actual={**{k:v for k,v in request['body'].items() if k!='messages'},'endpoint':request['endpoint'],'timeout_seconds':request['timeout_seconds']}
                assert actual==cfg.get('stage_configs',{}).get('preconditioner',cfg['call_config'])
            meta=ev.read(a/'run.json');response=ev.read(a/'response.json') if (a/'response.json').exists() else {}
            attempts.append({'round':rnd,'attempt':a.name,'path':str(a),**{k:meta.get(k) for k in ('status','started_at','finished_at','elapsed_seconds')},
                             'usage':response.get('usage'),'finish_reason':response.get('finish_reason'),
                             'error':ev.read(a/'error.json') if (a/'error.json').exists() else None})
            verification[rnd]['attempts'].append({'attempt':a.name,'input_equal':True,'single_system_replacement':True,'request_config_equal':request is not None})
            raw=(a/'raw_output.txt').read_text() if (a/'raw_output.txt').exists() else '(no completed output)'
            lines.append(f'\n### 本次attempt {a.name}\n\n[完整档案]({a})\n\n```text\n'+raw+'\n```')
    ev.save(r.EXP/'results/comparison.json',comparison);ev.save(r.EXP/'results/attempts.json',attempts)
    ev.save(r.EXP/'results/verification.json',verification);(r.EXP/'reports/OUTPUTS.md').write_text('\n'.join(lines))
    (r.EXP/'reports/EVIDENCE_INDEX.md').write_text('\n'.join(index)+'\n')
    with patch.multiple(r.base,EXP=r.EXP,OUTPUT=r.OUTPUT,PROMPT=r.PROMPT,implementation=r.implementation,protected_files=r.protected_files):
        r.base.check_baseline()
        assert r.base.protected_files()==ev.read(r.EXP/'config/protected_before.json')
        assert r.implementation()==ev.read(r.EXP/'config/implementation.json')
        assert r.freeze_hashes()==ev.read(r.EXP/'config/freeze.json')['sha256']
    for name in ('summary.json','protection.json'):ev.save(r.EXP/'results'/name,ev.read(r.OUTPUT/name))
    print(json.dumps(ev.read(r.OUTPUT/'summary.json')))


if __name__=='__main__':main()
