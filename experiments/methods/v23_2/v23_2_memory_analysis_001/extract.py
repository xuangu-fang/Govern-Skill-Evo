"""Read frozen S1 archives; emit a small source index, never call models or environments."""
import json
import os
from pathlib import Path
import socket

from src.skill_evolution.v23 import memory, preconditioner, replay

ROOT = Path(__file__).resolve().parents[4]
S1 = ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
OUT = Path(__file__).resolve().parent/'reports'


def read(path):
    return json.loads(path.read_text())


def selected(rd, stage):
    return rd/stage/read(rd/stage/'result.json')['path']


def link(path, label):
    return f'[{label}]({os.path.relpath(path, OUT)})'


def main():
    socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError('Read-only analysis'))
    bundles = {rd.name: read(rd/'pairs/input.json') for rd in sorted((S1/'rounds').glob('R*'))}
    index, timeline = {}, []
    lines = ['# 正式 S1 证据索引', '', '仅索引正式优化池，未读取 Test。P/Q 为轮内配对引用，不能跨轮省略轮次。链接指向原始档案，没有复制整份轨迹。', '']
    raw_count = source_count = 0
    for rn, bundle in bundles.items():
        rd = S1/'rounds'/rn
        pp, dp, ep, rp = (selected(rd, s) for s in ('preconditioner', 'diagnosis', 'editor', 'replay'))
        saved = read(pp/'input.json')
        incoming = read(rd/'round_input.json')
        assert saved['memory'] == incoming['memory'] == memory.load_memory(S1/incoming['state']['active_memory'])
        validated = preconditioner.load_preconditioner(pp)
        assert validated['diagnosis'] == read(dp/'diagnosis.json')
        assert validated == read(ep/'upstream.json')
        plan = validated['effective_plan']
        # Replay deliberately projects out Update basis; preserve all behavioral text.
        projected = {**plan, 'updates': [{k:u[k] for k in ('id','text')} for u in plan['updates']]}
        assert projected == bundle['payload']['plan']
        assert bundle['payload']['diff'] == (ep/'actual.diff').read_text()
        replay.load_replay(rp, expected_bundle=bundle)
        for ref, source in saved['memory']['sources'].items():
            origin, local = ref.split('/')
            assert origin < 'S1_'+rn
            old = bundles[origin.removeprefix('S1_')]['payload']
            if local == 'diff':
                assert source['diff'] == old['diff'] and source['parent'] == old['parent']
            else:
                assert source['run'] == next(r for r in old['runs'] if r['ref'] == local)
                assert all(old['command_sets'][k] == v for k, v in source['command_sets'].items())
            source_count += 1
        runs = {r['ref']: r for r in bundle['payload']['runs']}
        records = {}
        for side in ('parent', 'candidate'):
            for ref, path in zip([p[side] for p in bundle['payload']['pairs']], bundle['record_paths'][side]):
                path = Path(path)
                assert path.is_relative_to(S1)  # Never use final Test or V23.2 experimental traces.
                raw, run = read(path), runs[ref]
                assert raw['initial_observation'] == run['initial']['observation']
                assert len(raw['steps']) == len(run['steps'])
                for rs, fs in zip(raw['steps'], run['steps']):
                    assert rs['action'] == fs['action'] and rs['observation'] == fs['after']['observation']
                    assert rs['won'] == fs['feedback']['won']
                assert raw['won'] == run['outcome']['success']
                records[ref] = path
                raw_count += 1
        gate = read(rd/'gate/result.json')['result']
        pairs = []
        for audit in bundle['pair_audit']:
            assert audit['verified']
            p, q = (runs[audit['pair'][s]] for s in ('parent', 'candidate'))
            pairs.append({'task_id': audit['task']['id'], 'task':p['task'], 'p': p['ref'], 'q':q['ref'],
                          'parent_success':p['outcome']['success'], 'candidate_success':q['outcome']['success'],
                          'parent_steps':len(p['steps']), 'candidate_steps':len(q['steps']),
                          'parent_path':str(records[p['ref']].relative_to(ROOT)),
                          'candidate_path':str(records[q['ref']].relative_to(ROOT))})
        assert sum(x['parent_success'] for x in pairs) == gate['parent_success']
        assert sum(x['candidate_success'] for x in pairs) == gate['candidate_success']
        result = read(rd/'result.json')
        before = [e['id'] for e in saved['memory']['entries']]
        after = read(rd/'memory/active.json')['active_ids']
        new = [e for e in read(rd/'memory/view.json')['entries'] if e['id'] not in before]
        revisions = read(rp/'replay.json')['entries']
        assert len(new) == len(revisions)
        change = {e['id']: v['revises'] for e,v in zip(new,revisions)}
        timeline.append({'round':rn,'parent':result['before']['parent'],'incoming_memory':before,
                         'outgoing_memory':after,'new_revises':change,'gate':gate})
        index[rn] = {'selected': {k:str(v.relative_to(ROOT)) for k,v in [('diagnosis',dp),('preconditioner',pp),('editor',ep),('replay',rp)]},
                     'pairs':pairs,'incoming_memory_source':incoming['state']['active_memory']}
        lines += [f'## {rn}', '',f"输入 Memory：{', '.join(before) or '空'}；本轮后：{', '.join(after)}。Gate：{gate}。", '',
                  ' · '.join(link(p,n) for p,n in [(rd/'round_input.json','轮次快照'),(pp/'input.json','Preconditioner 实际输入'),(dp/'diagnosis.json','Original Plan'),(pp/'preconditioner.json','reason / Adjustments'),(pp/'effective_plan.json','Effective Plan'),(ep/'actual.diff','Editor 实际 Diff'),(rd/'pairs/input.json','完整配对事实'),(rp/'replay.json','Replay 输出'),(rd/'memory/view.json','本轮后 Memory'),(rd/'gate/result.json','Gate')]),'',
                  '| 配对／任务 | Parent 成功／步数 | Candidate 成功／步数 | 原始轨迹 |','|---|---|---|---|']
        for x in pairs:
            lines.append(f"| {x['p']}/{x['q']} · {x['task_id']} · {x['task']} | {x['parent_success']} / {x['parent_steps']} | {x['candidate_success']} / {x['candidate_steps']} | {link(ROOT/x['parent_path'],'Parent')} · {link(ROOT/x['candidate_path'],'Candidate')} |")
        lines.append('')
    result = {'source_root': str(S1.relative_to(ROOT)), 'timeline':timeline,'index':index,
              'verified_raw_runs':raw_count,'verified_historical_sources':source_count,
              'model_calls':0,'environment_runs':0,'test_traces_read':0}
    OUT.mkdir(exist_ok=True)
    (OUT/'index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'SOURCES.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('index','timeline')},ensure_ascii=False))


if __name__ == '__main__':
    main()
