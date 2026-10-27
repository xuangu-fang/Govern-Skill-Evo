"""Offline final accounting for the first-valid A2/B7 paired continuation."""
from datetime import datetime
from .archive_io import ARCHIVE
from .run import HERE, read, save, now, COMPLETE
from . import analyze


def main():
    for arm in ['Parent', 'A', 'B']:
        for task in read(HERE/'tasks.json'):
            r=read(ARCHIVE/f"episodes/{arm}/{task['ref']}/trajectory.json")
            assert r['status']!='running', (arm,task['ref'])
    analyze.main()
    data=read(ARCHIVE/'analysis.json');tot=data['totals']
    rows={(r['ref'],r['arm']):r for r in data['rows']}
    agg={}
    for arm in ['Parent','A','B']:
        rs=[rows[(f'P{i}',arm)] for i in range(1,7)]
        agg[arm]={'success':sum(r.get('native_success',False) for r in rs),'complete':sum(r['status'] in COMPLETE for r in rs),'steps':sum(r.get('steps_executed',0) for r in rs),'repeats':sum(len(r.get('same_location_observation_repeats',[])) for r in rs),'invalid':sum(len(r.get('invalid_steps',[])) for r in rs),'nothing':sum(len(r.get('nothing_happens_steps',[])) for r in rs)}
    pair_counts={}
    for arms in [('Parent','A'),('Parent','B'),('A','B')]:
        pair_counts['/'.join(arms)]=sum(p['both_complete'] and p['conditions_match'] for p in data['pairs'] if p['arms']==list(arms))
    triples=sum(all(p['both_complete'] and p['conditions_match'] for p in data['pairs'] if p['ref']==f'P{i}') for i in range(1,7))
    save(HERE/'final_metrics.json',{'at':now(),'aggregate':agg,'valid_pairs':pair_counts,'valid_three_way_pairs':triples,'selected_generations':{'A':2,'B':7}})
    md=['# 请求、重试与成本','',
        '原协议与所有授权变更分别保留，见 PARALLEL_AMENDMENT.md、RESAMPLING_AMENDMENT.md、B_GENERATION3_AMENDMENT.md 至 B_GENERATION7_AMENDMENT.md。技术重试与收到输出后的追加生成分开统计。', '',
        f"实际逻辑调用 {tot['logical_calls']}：上游 {tot['upstream_logical_calls']}、Actor {tot['actor_logical_calls']}。实际 POST {tot['post_attempts']}，journal 尝试 {tot['journal_attempts']}，HTTP 429 共 {tot['http_429']}。授权后上游上限 13、Episode 上限 18、Actor 上限 900 均未超出。",'',
        'Diagnosis 首次 HTTP 401 无模型输出，经用户授权同请求恢复，第二次 HTTP 成功，仍只有一份有效 Diagnosis。A 首次引用格式失败，A2 首次有效；B1–B6 依次为多余 checks、多余 from_note、理由引用、理由引用、Patch 原文匹配、理由引用失败；B7 首次有效。每次语义生成追加均有用户单独授权，不是技术重试。Editor A/B 各一次有效。没有响应修补、纠错提示、策略择优或失败预算重置。', '',
        '| 上游调用 | HTTP | HTTP 发送至归档完成秒 | input | completion | total |','|---|---|---:|---:|---:|---:|']
    cost=read(HERE/'upstream_cost_audit.json')
    for item in sorted(cost,key=lambda x:x['attempts'][0]['started_at']):
        for a in item['attempts']:
            dt=(datetime.fromisoformat(a['finished_at'])-datetime.fromisoformat(a.get('request_started_at') or a['started_at'])).total_seconds();u=a['usage'] or {}
            md.append(f"| {item['name']} #{a['attempt_index']} | {a['http_status']} | {dt:.2f} | {u.get('prompt_tokens','未知')} | {u.get('completion_tokens','未知')} | {u.get('total_tokens','未知')} |")
    md+=['',f"已知服务 usage：input {tot['prompt_tokens']:,}、completion {tot['completion_tokens']:,}、total {tot['total_tokens']:,}。reasoning {tot['reasoning_tokens']:,} 已包含在 completion，不重复计算。{tot['unknown_usage_attempts']} 次尝试没有 usage，不能假定零费用；货币价格未知。缓存 input 是 input 子集，不另加。",'',
         f"累计 journal wait_seconds={tot['wait_seconds']:.3f}，包含正常节流与排队，不全是故障退避。Actor 实测峰值并发 {tot['observed_peak_actor_post_concurrency']}；配置四并发、共享至少 3 秒节流，timeout=[60,300]。Parent 前三例在更早串行阶段，其余与 Candidate 使用用户授权并行；保留时间与实际并发差异为限制。",'',
         '所有 A/B 追加实际正文与各自首次完全相同，两组 user payload 和参数完全相同。服务回报同正文 prompt_tokens 有 36 的差异，保留原 usage，不推断人为裁剪；服务端原因未知。请求字节数、模型、finish_reason、超时、耗时在 upstream_cost_audit.json 和各原始 journal。', '',
         '每次失败响应、traceback 和解析结果保留。B3/B4/B6 的 Patch 可应用但完整编译失败；B5 在 Patch 应用阶段失败，不能混同。无真实 429 时，不宣称恢复逻辑获本轮限流验证；离线合成测试单列。Actor 格式/非法动作不因策略效果不佳追加生成。']
    (HERE/'RETRY_REPORT.md').write_text('\n'.join(md)+'\n')
    md=['# Batch-1 三方配对 Replay','',
        f'固定六条任务，Parent/A 已完成结果直接复用，仅新增六条 B。有效三方配对 {triples}/6；Parent/A、Parent/B、A/B 配对分别为 {pair_counts}。初始状态、任务实例、模型参数、基础协议及实现文件由原 verifier 校验，详见 [analysis.json](../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/analysis.json)。实际请求时点及 Parent 部分串行是比较限制。','',
        '**这是 A2/B7 首个有效方案的授权恢复后行为对照，不是等预算一次生成端到端比较。** A 两次、B 七次；初次输出均无合法 Effective，所有失败和成本纳入报告。', '',
        '| Task | Parent | V23 A2 | V23.3 B7 |','|---|---|---|---|']
    for i in range(1,7):
        cells=[f"{rows[(f'P{i}',arm)]['status']} / {rows[(f'P{i}',arm)]['steps_executed']} 步" for arm in ['Parent','A','B']]
        md.append('| P'+str(i)+' | '+' | '.join(cells)+' |')
    md+=['','| 条件 | 成功 | 正常结束 | 总步数 | 同位置同反馈重复代理 | 候选外动作 | Nothing happens |','|---|---:|---:|---:|---:|---:|---:|']
    for arm,v in agg.items():md.append(f"| {arm} | {v['success']}/6 | {v['complete']}/6 | {v['steps']} | {v['repeats']} | {v['invalid']} | {v['nothing']} |")
    md+=['','“同位置同反馈”只统计 go to 后完整反馈相同的再次访问，包含带物回灯处等有效回返，不能一律当作无效。位置/类别数按 go to 统计，是导航代理，不等于全部内容检查；例如在 countertop 可 examine coffeemachine。目标首次观察来自实际反馈，不读取隐藏布局。未发现目标不等于环境缺少目标。','',
         '| Task/条件 | 不同导航位置/类别 | 首次目标反馈步 | 获取、处理、交付动作 |','|---|---:|---:|---|']
    for i in range(1,7):
        for arm in ['Parent','A','B']:
            r=rows[(f'P{i}',arm)];actions='; '.join(f"{x['step']}: {x['action']}" for x in r['key_actions']) or '未发生'
            md.append(f"| P{i}/{arm} | {len(r['locations'])}/{len(r['classes'])} | {r['first_target_observed_feedback_step'] or '未观察到'} | {actions} |")
    md+=['','原始逐步证据见 TRAJECTORY_EVIDENCE.md、[episodes/](../../../../artifacts/methods/v23_3/p3a2_train_batch1_001/episodes/) 中的 trajectory.json；完整请求、反馈、动作前菜单、非法动作及传输记录都保留。Parent/A 旧分析和所有此前阶段报告有 amendment_B_generation7/ 等快照。','',
         'A P1 第1步到 coffeetable、2 take、4 move；P2 在4 stoveburner 找到、7 clean、10 move。A P3 和 P6 仍 50 步失败、无目标获取或交付，重复代理各24/32；P6 增加 sidetable 3 导航仍未恢复成功。A P6 第13步动作混入解释文字，候选外且 Nothing happens，未重采样。P5 第4步带物回灯处属于必要回返。','',
         '研究者曾仅凭动作名把 P3 cabinet 7 误判为关闭；原反馈为 On the cabinet 7，已撤回并记录 researcher_fact_correction.json，不将其算作漏开容器。', '',
         'B 的逐例行为与归因另见下方最终人工核查。文本局部化、Patch 应用和较短轨迹都不自动证明 Memory 增量；无消融且每例每条件一次，不能将结果外推为稳定泛化优势。']
    (HERE/'REPLAY_REPORT.md').write_text('\n'.join(md)+'\n'+((HERE/'PAIRED_BEHAVIOR_ANALYSIS.md').read_text() if (HERE/'PAIRED_BEHAVIOR_ANALYSIS.md').exists() else ''))
    print('PAIRED_METRICS',agg,'three_way_pairs',triples)


if __name__=='__main__':main()
