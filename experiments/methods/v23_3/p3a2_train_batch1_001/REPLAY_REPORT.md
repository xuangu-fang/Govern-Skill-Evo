# Batch-1 三方配对 Replay

固定六条任务，Parent/A 已完成结果直接复用，仅新增六条 B。有效三方配对 6/6；Parent/A、Parent/B、A/B 配对分别为 {'Parent/A': 6, 'Parent/B': 6, 'A/B': 6}。初始状态、任务实例、模型参数、基础协议及实现文件由原 verifier 校验，详见 analysis.json。实际请求时点及 Parent 部分串行是比较限制。

**这是 A2/B7 首个有效方案的授权恢复后行为对照，不是等预算一次生成端到端比较。** A 两次、B 七次；初次输出均无合法 Effective，所有失败和成本纳入报告。

| Task | Parent | V23 A2 | V23.3 B7 |
|---|---|---|---|
| P1 | success / 39 步 | success / 4 步 | success / 12 步 |
| P2 | success / 12 步 | success / 10 步 | success / 9 步 |
| P3 | step_limit / 50 步 | step_limit / 50 步 | step_limit / 50 步 |
| P4 | success / 8 步 | success / 8 步 | success / 7 步 |
| P5 | success / 5 步 | success / 5 步 | success / 6 步 |
| P6 | step_limit / 50 步 | step_limit / 50 步 | step_limit / 50 步 |

| 条件 | 成功 | 正常结束 | 总步数 | 同位置同反馈重复代理 | 候选外动作 | Nothing happens |
|---|---:|---:|---:|---:|---:|---:|
| Parent | 4/6 | 6/6 | 164 | 70 | 0 | 0 |
| A | 4/6 | 6/6 | 127 | 57 | 1 | 1 |
| B | 4/6 | 6/6 | 134 | 55 | 1 | 1 |

“同位置同反馈”只统计 go to 后完整反馈相同的再次访问，包含带物回灯处等有效回返，不能一律当作无效。位置/类别数按 go to 统计，是导航代理，不等于全部内容检查；例如在 countertop 可 examine coffeemachine。目标首次观察来自实际反馈，不读取隐藏布局。未发现目标不等于环境缺少目标。

| Task/条件 | 不同导航位置/类别 | 首次目标反馈步 | 获取、处理、交付动作 |
|---|---:|---:|---|
| P1/Parent | 10/4 | 36 | 37: take box 1 from coffeetable 1; 39: move box 1 to armchair 1 |
| P1/A | 2/2 | 1 | 2: take box 1 from coffeetable 1; 4: move box 1 to armchair 1 |
| P1/B | 6/4 | 9 | 10: take box 1 from coffeetable 1; 12: move box 1 to armchair 1 |
| P2/Parent | 5/4 | 7 | 8: take kettle 1 from stoveburner 1; 10: clean kettle 1 with sinkbasin 1; 12: move kettle 1 to cabinet 1 |
| P2/A | 6/4 | 4 | 5: take kettle 1 from stoveburner 1; 7: clean kettle 1 with sinkbasin 1; 10: move kettle 1 to cabinet 1 |
| P2/B | 5/4 | 3 | 4: take kettle 1 from stoveburner 1; 6: clean kettle 1 with sinkbasin 1; 9: move kettle 1 to cabinet 1 |
| P3/Parent | 12/3 | 未观察到 | 未发生 |
| P3/A | 11/3 | 未观察到 | 未发生 |
| P3/B | 14/5 | 未观察到 | 未发生 |
| P4/Parent | 3/3 | 3 | 4: take apple 2 from countertop 1; 6: cool apple 2 with fridge 1; 8: move apple 2 to diningtable 1 |
| P4/A | 3/3 | 3 | 4: take apple 2 from countertop 1; 6: cool apple 2 with fridge 1; 8: move apple 2 to diningtable 1 |
| P4/B | 3/3 | 1 | 2: take apple 2 from countertop 1; 5: cool apple 2 with fridge 1; 7: move apple 2 to diningtable 1 |
| P5/Parent | 2/1 | 2 | 3: take alarmclock 2 from desk 2; 5: use desklamp 1 |
| P5/A | 2/1 | 2 | 3: take alarmclock 2 from desk 2; 5: use desklamp 1 |
| P5/B | 3/2 | 4 | 2: use desklamp 1; 5: take alarmclock 2 from desk 2 |
| P6/Parent | 7/3 | 未观察到 | 未发生 |
| P6/A | 8/3 | 未观察到 | 未发生 |
| P6/B | 8/3 | 未观察到 | 未发生 |

原始逐步证据见 TRAJECTORY_EVIDENCE.md、episodes/ 各 trajectory.json；完整请求、反馈、动作前菜单、非法动作及传输记录都保留。Parent/A 旧分析和所有此前阶段报告有 amendment_B_generation7/ 等快照。

A P1 第1步到 coffeetable、2 take、4 move；P2 在4 stoveburner 找到、7 clean、10 move。A P3 和 P6 仍 50 步失败、无目标获取或交付，重复代理各24/32；P6 增加 sidetable 3 导航仍未恢复成功。A P6 第13步动作混入解释文字，候选外且 Nothing happens，未重采样。P5 第4步带物回灯处属于必要回返。

研究者曾仅凭动作名把 P3 cabinet 7 误判为关闭；原反馈为 On the cabinet 7，已撤回并记录 researcher_fact_correction.json，不将其算作漏开容器。

B 的逐例行为与归因另见下方最终人工核查。文本局部化、Patch 应用和较短轨迹都不自动证明 Memory 增量；无消融且每例每条件一次，不能将结果外推为稳定泛化优势。
## 最终逐例行为与归因核查

- **P1：39 → 4 / 12 步（Parent → A/B），均成功。** A 直接去 coffeetable；B 先检查 drawer 1/2/3 和 cabinet 1，9 才到 coffeetable、10 take、12 move，之前没有同位置同反馈重访。B 比 Parent 提早发现目标，但比 A 多8步；不能由这一个随机初始搜索顺序推成方法稳定排序。
- **P2：12 → 10 / 9 步，均成功。** B 在3 stoveburner 找到、4 take、6 clean、9 move；A 多检查一次 countertop 3。两组保留精确 kettle、必要清洗和交付；B 第6步429重试没有多执行一次 clean。
- **P3：三组均50步失败。** B 在15检查 diningtable、20到 microwave、21打开见 cup；导航位置/类别14/5，Parent12/3、A11/3。B 重复代理22，Parent/A各24。覆盖有扩展、重复稍少，但三组都未观察到 mug、无 take/heat/交付。B 仍未到 fridge、drawer 2 等可见候选；不能把局部覆盖改善称为目标定位已解决，也不能说环境缺少 mug。热处理能力没有被触发检验。
- **P4：8 → 8 / 7 步，均成功。** B 在1 countertop 看到目标、2 take、3 fridge、4 open、5 cool、7 move；A/Parent 先到 fridge 再找目标，B 少一步。必要冷却与交付保留；优势表现为一次搜索/导航顺序差异，不能隔离归因到 u2。
- **P5：5 → 5 / 6 步，均成功。** B 在2 use 灯，3额外检查 dresser，4到 desk 2、5 take、6回灯旁即原生成功。A/Parent 先拿物再回灯处开灯。必要条件是最终共位与灯状态，不应把一种成功动作顺序当唯一方案；灯具段未修改，多一步不能明确归因到非灯具搜索更新。回灯处的重复代理为有效回返。
- **P6：三组均50步失败。** B 与 A 均额外到 sidetable 3（B21），导航位置8个，Parent7个；三组重复代理各32。B 未观察到 watch、未取物或交付；44空手 inventory 一次（Parent三次、A零次），两实例计数/第二次交付未获实际验证。B36原响应含3对 action 标签，第一对只有空格；原 first-tag 解析得到空动作，环境返回 Nothing happens。这是 Actor 输出格式与既有解析协议交互，不是HTTP失败，未修复/重采样；A也有一次不同形式的非法动作。见 B_actor_empty_action_audit.json。

成功任务集合三组相同：P1/P2/P4/P5；没有救回 P3/P6，也没有把原成功任务变成失败。总步数 Parent164、A127、B134；B较Parent少30步，较A多7步。A/B差主要来自P1（B多8步），P2/P4各少1、P5多1，不能将单项主导差异等同稳定策略优劣。总重复代理70/57/55，但B比A少的2次全在仍失败的P3；该代理也含P5必要回返。

**三层结论：** B7 保留位置级完成条件并允许未检查关闭容器，相对 A2 有较稳妥边界的局部线索；两个 Editor 都真实落实各自方案；Replay 没有显示 B 成功率优势，步数也没有优于 A，只出现局部覆盖/重复改善。局部 Patch 与历史引用不等于历史因果增量。A2/B7 生成机会不等、每任务每条件一次随机执行、B中途限流降并发、同批训练轨迹用于Diagnosis，均限制归因与泛化。
