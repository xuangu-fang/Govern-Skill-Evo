# Batch-1 配对 Replay

六条 Parent 复用，六条 A 执行；B 无合法 Candidate，六条均未运行，不能按失败或成功填补。有效 Parent/A 配对 6/6，完整 Parent/A/B 配对 0/6。

| Task | Parent | A | B |
|---|---|---|---|
| P1 | success / 39 步 | success / 4 步 | 未运行：无合法 Effective |
| P2 | success / 12 步 | success / 10 步 | 未运行：无合法 Effective |
| P3 | step_limit / 50 步 | step_limit / 50 步 | 未运行：无合法 Effective |
| P4 | success / 8 步 | success / 8 步 | 未运行：无合法 Effective |
| P5 | success / 5 步 | success / 5 步 | 未运行：无合法 Effective |
| P6 | step_limit / 50 步 | step_limit / 50 步 | 未运行：无合法 Effective |

| 条件 | 成功 | 正常结束 | 总步数 | 同位置同反馈重复代理 | 候选外动作 | Nothing happens |
|---|---:|---:|---:|---:|---:|---:|
| Parent | 4/6 | 6/6 | 164 | 70 | 0 | 0 |
| A | 4/6 | 6/6 | 127 | 57 | 1 | 1 |

“同位置同反馈”仅统计 go to 后完整反馈相同的再次访问；包含有效回返，例如 P5 第 4 步带目标回灯处，不能直接当作无效动作。没有重复并不代表搜索覆盖充分；定位速度较快的成功任务可以自然覆盖更少位置。位置/类别数按 go to 统计，是导航覆盖代理，不等于全部已检查位置（例如在 countertop 可 examine coffeemachine）。

| Task/条件 | 不同位置/类别 | 首次目标反馈步 | 必要动作 |
|---|---:|---:|---|
| P1/Parent | 10/4 | 36 | 37: take box 1 from coffeetable 1; 39: move box 1 to armchair 1 |
| P1/A | 2/2 | 1 | 2: take box 1 from coffeetable 1; 4: move box 1 to armchair 1 |
| P2/Parent | 5/4 | 7 | 8: take kettle 1 from stoveburner 1; 10: clean kettle 1 with sinkbasin 1; 12: move kettle 1 to cabinet 1 |
| P2/A | 6/4 | 4 | 5: take kettle 1 from stoveburner 1; 7: clean kettle 1 with sinkbasin 1; 10: move kettle 1 to cabinet 1 |
| P3/Parent | 12/3 | 未观察到 | 未发生 |
| P3/A | 11/3 | 未观察到 | 未发生 |
| P4/Parent | 3/3 | 3 | 4: take apple 2 from countertop 1; 6: cool apple 2 with fridge 1; 8: move apple 2 to diningtable 1 |
| P4/A | 3/3 | 3 | 4: take apple 2 from countertop 1; 6: cool apple 2 with fridge 1; 8: move apple 2 to diningtable 1 |
| P5/Parent | 2/1 | 2 | 3: take alarmclock 2 from desk 2; 5: use desklamp 1 |
| P5/A | 2/1 | 2 | 3: take alarmclock 2 from desk 2; 5: use desklamp 1 |
| P6/Parent | 7/3 | 未观察到 | 未发生 |
| P6/A | 8/3 | 未观察到 | 未发生 |

逐步原始动作和反馈见 TRAJECTORY_EVIDENCE.md，完整候选、请求、响应、状态见 episodes/ 下各 trajectory.json；analysis.json 保存原 verifier、配对条件校验及所有代理明细。任务实例、初始观察、模型配置、固定 Skill/最近两步协议匹配；实际时序并发有用户授权的中途改变（Parent P1–P3 串行），不能掩盖。

A P1 在第 1 步直接到 coffeetable，2 take、4 move；Parent 直到 36 才找到。这与新增表面搜索文字一致，但单条随机轨迹无法隔离条款因果。A P2 依次检查 countertop 1/2/3，4 stoveburner 找到、7 clean、10 move；说明 Actor 没有机械遵守每次不同类别，也保留了必要处理。P4 与 P5 的成功动作链和步数保持，P5 回返是灯具共位所需。

A P6 第 13 步原输出混入解释文字，形成候选外动作和 Nothing happens；14 examine 后 15 才 open，保留全过程，没有人工修复。它是执行输出格式问题，不能自动归因于 Preconditioner 策略。

A P3 仍有 24 次同位置同反馈重复，导航位置 12→11，未到 diningtable/fridge；50 步无 mug、take、heat 或交付。A P6 同样有 32 次重复，导航位置 7→8，增加 sidetable 3 但仍未找到 watch，无获取或两次交付。P1/P2 的重复减少解释了总重复代理 70→57，不能称长期循环已解决。两条失败没有早停于类别覆盖完成；不能把实际 step_limit 归因成执行了类别终点。

研究者曾仅凭动作名把 P3 cabinet 7 误判为关闭容器未打开；原反馈明确为 On the cabinet 7，已即时撤回，见 researcher_fact_correction.json。此处不把它算作漏开容器。

目标首次观察指标来自实际反馈，不读取隐藏布局；未找到不等于环境没有目标。同类实例遗漏用完整执行位置列表与可见菜单交叉检查，不凭历史任务名称猜测。归因需区分 Effective 的风险、Editor 落实、Actor 实际遵循。
