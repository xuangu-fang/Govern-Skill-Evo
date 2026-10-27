"""Publish tables and exact prior-Replay excerpts, without changing run files."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())

def main():
    ev=read(HERE/'evaluation.json'); audit=read(HERE/'AUDIT.json')
    dims=ev['dimensions']; lines=['# 逐项评分与原始输出','',
      '人工语义核对；2=满足，1=部分/有歧义/重要遗漏，0=明确矛盾或不受支持，—=不适用。维度分数不求平均，不等同模型总体正确率。核心比较正确时，附带事实/引用错误仍单独标出。','',
      '| 条件/重复/题目 | 来源绑定 | 事实 | 适用条件 | 结论强度 | 行为比较 | 不确定性 | 具体问题 |',
      '|---|---:|---:|---:|---:|---:|---:|---|']
    for row in ev['rows']:
        key=f"{row['condition']}/{row['replicate']}/{row['question']}"
        scores=['—' if row['scores'][k] is None else str(row['scores'][k]) for k in dims]
        notes='；'.join(f['assessment'] for f in row['findings']) or row['core_observation']
        lines.append('| ['+key+']('+str(HERE/row['output_file'])+') | '+' | '.join(scores)+' | '+notes+' |')
    lines+=['','每行的完整原始回答、准确 JSON 路径、问题引文、标准事实和来源索引均保存在 [evaluation.json]('+str(HERE/'evaluation.json')+')。初始评分独立保存在 initial_evaluation.json；补充调用前的决策保存在 repeat_plan.json。']
    (HERE/'SCORES.md').write_text('\n'.join(lines)+'\n')
    lines=['| 条件 | 次数 | 输入 tokens | 输出 tokens（含 reasoning） | 总 tokens | 秒 | 结束 |','|---|---:|---:|---:|---:|---:|---|']
    for a in sorted(audit['attempts'],key=lambda a:a['http_ordinal']):
        u=a['usage'];lines.append(f"| {a['label']} | {a['replicate']} | {u['prompt_tokens']:,} | {u['completion_tokens']:,} | {u['total_tokens']:,} | {a['elapsed_seconds']} | {a['finish_reason']}; {a['status']} |")
    (HERE/'CALLS.md').write_text('\n'.join(lines)+'\n')
    source=read(HERE/'P6_COMPARISON_SOURCE.json')
    specs=[
      ('R05','T1',[(0,1)],'Q7:25 动作/轮次错配；Evidence 引用存在但不支持动作陈述。','A/B 各两次均能准确绑定两个事件。'),
      ('R05','T2',[(0,1)],'未保留 Parent P8:8 已有的合法直接开柜行为；没有可观察行为进展的否定过宽。','四次均指出 Parent 直接开柜；两次补充输出未同时保留 Candidate 后续违规，比较覆盖仍会偏移。'),
      ('R05','T3',[(0,0),(0,2)],'把全局条款并入 non-desklamp，并用 pillow 响应评价搜索。','四次事实/条件部分均读出章节边界；B 两次在结论混淆无违规和未执行/不适用。'),
      ('R05','T4',[(0,3)],'soapbar absent 无穷尽依据。','四次均保留未找到与全局未知；A2 新增 candle 3 位置混写。'),
      ('R05','T6',[(0,0),(0,2)],'保留 apple 14/11 总数，但搜索认识未纳入具体三步改善，末尾引用不覆盖该行为阶段。','四次均准确定位三步搜索差异；A1/B1 对全局合法动作要求作未执行推断。'),
      ('R06','T4',[(0,1)],'继承 M10 no exact butterknife was present，未校准解释强度。','四次均明确全球不存在未证明，但对旧解释纠正程度不一致，A1 search/absence、A2 rescue 套用仍含混。'),
      ('R06','T5',[(1,1)],'成功保留 13 成功/50 失败及机会不对称。','四次均保留；B1 条件化 savings 过强，A2 no observable effect 过宽，B2 边界较清晰。'),
      ('R06','T6',[(0,0),(1,0)],'正确区分温变相同、整体搜索差异。','四次保持核心比较；B1 出现不存在的 Q2:40/Q2:11，B2 将三步 placement 写成五步。'),
    ]
    rows=[]
    for case,q,indices,prior,current in specs:
        entries=source[case]['original_replay']['entries']
        rows.append({'case':case,'question':q,'p6_file':source[case]['file'],
          'p6_excerpts':[{'jsonpath':f'entries[{i}].knowledge[{j}]',
                         'original_knowledge':entries[i]['knowledge'][j]} for i,j in indices],
          'p6_assessment':prior,'diagnostic_comparison':current,
          'diagnostic_rows':[r['condition']+'/'+str(r['replicate'])+'/'+q for r in ev['rows'] if r['condition'].startswith(case) and r['question']==q],
          'limitation':'Directed questions and complete Replay are different tasks; not a single-variable causal contrast.'})
    (HERE/'cross_layer.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print('32 score rows, 8 calls, 8 cross-layer question groups')

if __name__=='__main__':main()
