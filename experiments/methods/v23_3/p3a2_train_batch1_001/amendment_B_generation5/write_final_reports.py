"""Offline reports only; refuses to finalize while a scheduled A run is active."""
from datetime import datetime
from .run import HERE, ROOT, read, save, now, verify, COMPLETE
from . import analyze


def main():
    verify()
    for task in read(HERE / 'tasks.json'):
        record = read(HERE / f"episodes/A/{task['ref']}/trajectory.json")
        assert record['status'] != 'running', task['ref']
    analyze.main()
    data = read(HERE / 'analysis.json')
    rows = {(r['ref'], r['arm']): r for r in data['rows']}
    totals = data['totals']
    aggregate = {}
    for arm in ['Parent', 'A']:
        rs = [rows[(f'P{i}', arm)] for i in range(1, 7)]
        aggregate[arm] = {
            'success': sum(r.get('native_success', False) for r in rs),
            'complete': sum(r['status'] in COMPLETE for r in rs),
            'steps': sum(r.get('steps_executed', 0) for r in rs),
            'repeats': sum(len(r.get('same_location_observation_repeats', [])) for r in rs),
            'invalid': sum(len(r.get('invalid_steps', [])) for r in rs),
            'nothing': sum(len(r.get('nothing_happens_steps', [])) for r in rs),
        }
    paired = sum(p['both_complete'] and p['conditions_match'] for p in data['pairs'] if p['arms'] == ['Parent', 'A'])
    save(HERE / 'final_metrics.json', {'at': now(), 'aggregate': aggregate, 'valid_parent_A_pairs': paired, 'valid_three_way_pairs': 0})
    retry = ['# 请求、重试与成本', '',
             '原协议保留；并发与追加生成授权见 PARALLEL_AMENDMENT.md、RESAMPLING_AMENDMENT.md、B_GENERATION3_AMENDMENT.md、B_GENERATION4_AMENDMENT.md。技术重试与收到输出后的追加生成分开统计。', '',
             f"实际逻辑调用 {totals['logical_calls']}：上游 {totals['upstream_logical_calls']}、Actor {totals['actor_logical_calls']}。实际 POST {totals['post_attempts']}，journal 尝试 {totals['journal_attempts']}，HTTP 429 共 {totals['http_429']}。授权后上游上限 10、Episode 上限 18、Actor 上限 900 均未超出。", '',
             'Diagnosis 首次 HTTP 401 Authentication Error，无模型内容；用户明确授权保持请求恢复，第二次 HTTP 成功，仍仅一个有效 Diagnosis。A1/B1/B2/B3/B4 都收到真实输出而后契约失败；A2、B2、B3、B4 是分别授权的新生成，不是技术重试。没有格式修补、纠错 Prompt、策略择优或失败预算重置。B4 之后停止该分支。', '',
             '| 上游调用 | HTTP 状态 | 耗时秒（请求起止） | input | completion | total |',
             '|---|---|---:|---:|---:|---:|']
    for item in read(HERE / 'upstream_cost_audit.json'):
        for a in item['attempts']:
            duration = (datetime.fromisoformat(a['finished_at']) - datetime.fromisoformat(a['started_at'])).total_seconds()
            usage = a['usage'] or {}
            retry.append(f"| {item['name']} #{a['attempt_index']} | {a['http_status']} | {duration:.2f} | {usage.get('prompt_tokens', '未知')} | {usage.get('completion_tokens', '未知')} | {usage.get('total_tokens', '未知')} |")
    retry += ['', f"已知服务 usage：input {totals['prompt_tokens']:,}、completion {totals['completion_tokens']:,}、total {totals['total_tokens']:,}。其中 reasoning {totals['reasoning_tokens']:,} 已包含在 completion，不重复相加。{totals['unknown_usage_attempts']} 次尝试缺 usage，不能假定零费用；货币单价/总价未知。缓存 tokens 是 input 子集，不另加。", '',
              f"journal 累计 wait_seconds={totals['wait_seconds']:.3f}，包含正常节流/排队，不能全部称为故障退避。实际 Actor POST 峰值并发 {totals['observed_peak_actor_post_concurrency']}；请求配置四并发、共享至少 3 秒节流、timeout=[60,300]。HTTP 尝试的响应头、正文、异常堆栈及状态均在各 call/step journal。", '',
              'A2/B2 与各自首次正文完全相同，但服务回报 prompt_tokens 各相差 36；原样记录，不能反推人为更改输入，服务内部计数原因未知。真实请求字节数、超时、finish_reason、响应模型汇总见 upstream_cost_audit.json；完整正文见各 request.json。', '',
              '没有 429 不代表恢复逻辑已被本轮真实限流验证；技术包装器的合成离线测试单列。P6 A 第 13 步动作格式错误产生无效动作，是收到模型输出后的执行问题，不重试。B 编译失败是工程契约失败，不计为 ALFWorld 策略失败。']
    (HERE / 'RETRY_REPORT.md').write_text('\n'.join(retry) + '\n')
    replay = ['# Batch-1 配对 Replay', '',
              f'六条 Parent 复用，六条 A 执行；B 无合法 Candidate，六条均未运行，不能按失败或成功填补。有效 Parent/A 配对 {paired}/6，完整 Parent/A/B 配对 0/6。', '',
              '| Task | Parent | A | B |', '|---|---|---|---|']
    for i in range(1, 7):
        p, a = rows[(f'P{i}', 'Parent')], rows[(f'P{i}', 'A')]
        replay.append(f"| P{i} | {p['status']} / {p['steps_executed']} 步 | {a['status']} / {a['steps_executed']} 步 | 未运行：无合法 Effective |")
    replay += ['', '| 条件 | 成功 | 正常结束 | 总步数 | 同位置同反馈重复代理 | 候选外动作 | Nothing happens |', '|---|---:|---:|---:|---:|---:|---:|']
    for arm, v in aggregate.items():
        replay.append(f"| {arm} | {v['success']}/6 | {v['complete']}/6 | {v['steps']} | {v['repeats']} | {v['invalid']} | {v['nothing']} |")
    replay += ['', '“同位置同反馈”仅统计 go to 后完整反馈相同的再次访问；包含有效回返，例如 P5 第 4 步带目标回灯处，不能直接当作无效动作。没有重复并不代表搜索覆盖充分；定位速度较快的成功任务可以自然覆盖更少位置。位置/类别数按 go to 统计，是导航覆盖代理，不等于全部已检查位置（例如在 countertop 可 examine coffeemachine）。', '',
               '| Task/条件 | 不同位置/类别 | 首次目标反馈步 | 必要动作 |', '|---|---:|---:|---|']
    for i in range(1, 7):
        for arm in ['Parent', 'A']:
            r = rows[(f'P{i}', arm)]
            actions = '; '.join(f"{x['step']}: {x['action']}" for x in r['key_actions']) or '未发生'
            replay.append(f"| P{i}/{arm} | {len(r['locations'])}/{len(r['classes'])} | {r['first_target_observed_feedback_step'] or '未观察到'} | {actions} |")
    replay += ['', '逐步原始动作和反馈见 TRAJECTORY_EVIDENCE.md，完整候选、请求、响应、状态见 episodes/ 下各 trajectory.json；analysis.json 保存原 verifier、配对条件校验及所有代理明细。任务实例、初始观察、模型配置、固定 Skill/最近两步协议匹配；实际时序并发有用户授权的中途改变（Parent P1–P3 串行），不能掩盖。', '',
               'A P1 在第 1 步直接到 coffeetable，2 take、4 move；Parent 直到 36 才找到。这与新增表面搜索文字一致，但单条随机轨迹无法隔离条款因果。A P2 依次检查 countertop 1/2/3，4 stoveburner 找到、7 clean、10 move；说明 Actor 没有机械遵守每次不同类别，也保留了必要处理。P4 与 P5 的成功动作链和步数保持，P5 回返是灯具共位所需。', '',
               'A P6 第 13 步原输出混入解释文字，形成候选外动作和 Nothing happens；14 examine 后 15 才 open，保留全过程，没有人工修复。它是执行输出格式问题，不能自动归因于 Preconditioner 策略。', '',
               'A P3 仍有 24 次同位置同反馈重复，导航位置 12→11，未到 diningtable/fridge；50 步无 mug、take、heat 或交付。A P6 同样有 32 次重复，导航位置 7→8，增加 sidetable 3 但仍未找到 watch，无获取或两次交付。P1/P2 的重复减少解释了总重复代理 70→57，不能称长期循环已解决。两条失败没有早停于类别覆盖完成；不能把实际 step_limit 归因成执行了类别终点。', '',
               '研究者曾仅凭动作名把 P3 cabinet 7 误判为关闭容器未打开；原反馈明确为 On the cabinet 7，已即时撤回，见 researcher_fact_correction.json。此处不把它算作漏开容器。', '',
               '目标首次观察指标来自实际反馈，不读取隐藏布局；未找到不等于环境没有目标。同类实例遗漏用完整执行位置列表与可见菜单交叉检查，不凭历史任务名称猜测。归因需区分 Effective 的风险、Editor 落实、Actor 实际遵循。']
    (HERE / 'REPLAY_REPORT.md').write_text('\n'.join(replay) + '\n')
    p, a = aggregate['Parent'], aggregate['A']
    decision = f'''# P3-A2 阶段决策

未形成完整 A/B 行为对照。B 四次真实输出全部被原契约拒绝，不能据此回答 V23.3 是否优于 V23。有效 A 与 Parent 的结果为 {a['success']}/6 对 {p['success']}/6 成功，{a['steps']} 对 {p['steps']} 步；完整结果见 REPLAY_REPORT.md。没有运行 Batch-2、Gate、Memory 更新或完整进化。

1. **六条是否按协议执行？** 六条固定 Parent 和六条 A 已执行，未替换任务；B 因门控未运行。并发改为四、401 恢复及 A2/B2/B3/B4 都有用户追加授权，原协议与变更分别保留，不能声称未经变更的一次生成实验。
2. **有效配对数？** Parent/A {paired}/6，Parent/A/B 0/6；不把 B 缺失记为任务失败。
3. **A/B 怎样更新 Skill？** A2 重构搜索首轮与近期反重复，Editor 落入 Skill；B 无合法 Skill。B3 提案只改 u2 前两行，B4 则修改 u1/u2 并提出强制容器/表面交替，均未实际执行。
4. **B 有真实 Patch 吗？** 有，四次原输出都有 Patch。B3/B4 原 Patch 引擎应用成功，但整体验证拒绝理由引用，因此无有效 Plan/Candidate。
5. **Keep 是否有依据？** B3 保留 u1 的广覆盖动机有 P1 表面找到目标等证据，但保留全局已访问条件和对所有候选打开的要求，存在未修正问题；不是全部 Keep；最新 B4 修改两项 Update。
6. **是否减少无依据承诺？** B3 提案未引入 A2 的类别一次首轮终点，局部边界较好；B1/B2/B4 仍提出阈值或强类别排序；B4 还存在 inspected→visited、按名称判断关闭容器等边界问题。生成机会不等且 B 契约失败，不能宣布方法稳定减少附带承诺。
7. **Memory 是否影响决策？** 两组理由明确使用 M3/M6 的旧编辑混合响应，支持重新考虑调度、限制旧规则有效性。但当前证据已支持减少循环；无消融，不能确认历史因果增量。
8. **Editor 是否落实？** A 有效且主要准确落实 Effective，包括其类别覆盖风险；未独立提供完整 heat/cool 流程。B 无调用，不能做两组落实比较。
9. **任务表现哪组更好？** 只有 A 对 Parent 可比：成功 {a['success']}/6 vs {p['success']}/6，总步数 {a['steps']} vs {p['steps']}。不能比较 B；单次六例不证明泛化或稳定优越性。
10. **失败性质？** Diagnosis 401 是技术故障；A1/B1/B2/B3/B4 是生成后的契约失败；正常 step_limit 是 Actor 行为结果；P6 A 第13步是 Actor 动作输出格式问题。分别统计。
11. **429 恢复了吗？** 本轮记录 {totals['http_429']} 次 429；没有观察到真实 429 时不能宣称实测恢复有效。离线包装器测试与真实数据分开。
12. **共同瓶颈？** 契约严格性与自由理由引用/多余字段冲突，当前证据理解错误，局部历史与全局覆盖要求不一致；Parent 与 A 均残留搜索循环及目标未发现；本轮不能确认两组方法共同的 Actor 瓶颈，因为 B 未执行。
13. **支持研究方向/范围/关联吗？** 支持继续检验：覆盖扩展能否避免同类实例遗漏、局部触发是否能解决长期循环、目标修改是否引入无依据终点。文本 Patch 成功不是答案。
14. **下一步 Batch-2 还是先处理问题？** 优先单独预注册并审计输出契约可靠性和引用识别边界，再冻结机制进行新对照；同时核查当前轨迹事实与全局状态条件。保留本轮全部失败，不通过修补本轮答案制造有效配对。不在本轮修改正式代码或 Prompt。

最值得做的一项后续实验：固定本轮 Original、Parent、Memory、当前证据及模型，预注册等预算的 A/B 重复生成，分别报告契约通过率和未经修补的语义质量；如果先修订引用/Schema 的工程接口，应作为明确的新版本，两组共同规则一致，不能混回本轮。通过之后再用独立保留任务检验行为，不以生成次数多带来的首个有效结果当作一次采样质量。

三个层次：更新决策存在可检验的方向/范围线索；A Editor 落实可验证，B 未到达；ALFWorld 仅有 Parent/A 配对。对 V23.3 的更新粒度、历史增量、策略质量仍须分开验证。完成本阶段后停止。
'''
    (HERE / 'P3A2_DECISION.md').write_text(decision)


if __name__ == '__main__':
    main()
