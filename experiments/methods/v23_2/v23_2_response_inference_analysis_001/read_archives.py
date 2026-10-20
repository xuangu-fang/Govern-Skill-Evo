"""Offline JSON consistency checks and evidence links; never invokes project modules."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

EXP=Path(__file__).resolve().parent
ROOT=EXP.parents[3]
FORMAL=ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
COMPARISON=ROOT/'experiments/methods/v23_2/v23_2_evidence_calibration_001/results/comparison.json'
VERSIONS={'V23':None,'alignment':'v23_2_response_alignment_001',
          'construction':'v23_2_response_construction_001','symmetric':'v23_2_response_symmetric_001',
          'calibration':'v23_2_evidence_calibration_001'}


def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def selected(stage):return stage/read(stage/'result.json')['path']
def hashes():
    roots=('src/skill_evolution/v23','src/skill_evolution/v23_2','src/adapters/alfworld',
           'artifacts/methods/v23','artifacts/methods/v23_2','experiments/methods/v23',
           'experiments/methods/v23_2','docs/methods/v23','docs/methods/v23_2')
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for r in roots for p in (ROOT/r).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and not p.is_relative_to(EXP)}


def collect():
    before=EXP/'results/protected_before.json'
    assert not before.exists(), 'Read snapshot already exists'
    save(before,hashes())
    comparison=read(COMPARISON);records=[]
    lines=['# 证据索引与覆盖清单\n\n仅链接旧档案，不复制完整轨迹，不运行编译或自进化模块。',
           f'[原有五版本全文]({COMPARISON.parent.parent}/reports/OUTPUTS.md) · [结构化对照]({COMPARISON})']
    for rnd in ('R04','R05','R06'):
        formal=selected(FORMAL/'rounds'/rnd/'preconditioner');inp=read(formal/'input.json')
        snapshot=read(FORMAL/'rounds'/rnd/'round_input.json');assert snapshot['memory']==inp['memory']
        assert inp['facts']['parent']==snapshot['parent']
        assert comparison[rnd]['original_plan']==inp['diagnosis']['plan']
        lines.append(f'\n## {rnd}\n\n[Original、Parent、Memory与sources]({formal}/input.json) · [当轮冻结快照]({FORMAL}/rounds/{rnd}/round_input.json)\n\nMemory IDs：'+', '.join(m['id'] for m in inp['memory']['entries']))
        lines.append('\n| 版本 | 有效档案 | u1 | u2 |\n|---|---|---|---|')
        for version,experiment in VERSIONS.items():
            d=formal if experiment is None else selected(ROOT/f'artifacts/methods/v23_2/{experiment}/{rnd}')
            assert read(d/'run.json')['status']=='valid' and read(d/'validation.json')['valid']
            assert read(d/'input.json')==inp
            value=read(d/'preconditioner.json');response=read(d/'response.json')
            assert response['finish_reason']=='stop'
            assert json.loads(response['content'])==value==read(d/'parsed.json')
            assert (d/'raw_output.txt').read_text()==response['content']
            effective=read(d/'effective_plan.json');assert comparison[rnd][version]=={'preconditioner':value,'effective_plan':effective}
            changed={k for a in value['adjustments'] for k in a['from']}
            original={u['id']:u for u in inp['diagnosis']['plan']['updates']}
            final={u['id']:u for u in effective['updates']}
            for k in original.keys()-changed:assert original[k]==final[k]
            for a in value['adjustments']:
                for u in a['to']:assert final[u['id']]['text']==u['text']
            status=['Adjustment' if k in changed else 'Keep' for k in ('u1','u2')]
            lines.append(f'| {version} | [输出]({d}/preconditioner.json) · [Effective]({d}/effective_plan.json) · [冻结Prompt]({d}/prompt.md) | {status[0]} | {status[1]} |')
            records.append({'round':rnd,'version':version,'path':str(d),'same_original_and_input':True,'valid_only':True,'raw_parsed_effective_match':True,'updates':['u1','u2']})
        for source_round in (('R03',) if rnd=='R04' else ('R03','R05') if rnd=='R06' else ()):
            d=selected(FORMAL/'rounds'/source_round/'editor')
            assert inp['memory']['sources'][f'S1_{source_round}/diff']['diff']==(d/'actual.diff').read_text()
            lines.append(f'\n[历史 {source_round} 实际Diff]({d}/actual.diff)，与当时可见Memory source逐字相同。')
    (EXP/'reports/EVIDENCE_INDEX.md').write_text('\n'.join(lines)+'\n')
    save(EXP/'results/archive_checks.json',{'at':datetime.now(timezone.utc).isoformat(),'records':records,'new_model_calls':0,'project_modules_invoked':0})


def verify():
    before=read(EXP/'results/protected_before.json');after=hashes()
    changed=[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)]
    save(EXP/'results/protection.json',{'at':datetime.now(timezone.utc).isoformat(),'checked_files':len(before),
         'unchanged':not changed,'changed':changed,'method':'SHA-256 and identical file set','new_model_calls':0})
    assert not changed
    print(json.dumps({'checked_files':len(before),'unchanged':True,'new_model_calls':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('collect','verify'))
    collect() if p.parse_args().action=='collect' else verify()
