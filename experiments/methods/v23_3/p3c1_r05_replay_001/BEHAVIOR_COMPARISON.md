# Effective Update → Skill Diff → 行为：部分证据

本表先依据EDITOR_REPORT和REPLAY_REPORT中的独立观察，再比较；后验解释不是独立因果检验。B没有成功模型动作，不能完成两方法行为归因。

| 上游要求 | 实际Skill变换 | Actor观察 | 解释边界 |
|---|---|---|---|
| A u1加入具体近似类别例子，B保留Original精确目标要求 | 两个Editor都重写general step2；只有A有knife/butterknife等新增例子 | A/P6:3取准确butterknife；A/P7:7看到knife、:8离开；新Parent/P7前缀也未取knife | 与防替代方向一致，但没有证明例子独立起效；P7未完成，不能比较最终成功 |
| A u2要求同类实例覆盖和开放表面，B原始u2要求若干同类检查后换类 | A step1包含remaining same-type及强先后条件；B step1保留不同类至少一个的条件 | A/P6:1–2检查countertop1/2并找到目标；A/P7:1–3检查countertop1–3后转cabinet再drawer | A的实际路线与覆盖方向相符；新Parent/P6同样检查countertop1/2，不是A独有能力，B暂无数据 |
| A u2扩大新位置探索 | A step1具体列出更多表面，保留搜索到找到目标等旧边界 | A/P10:5看到apple；Parent/P10:8看到；随后A被429中断 | 可说本次更早发现，不能说更早完成；无预算耗尽或提前停止的策略证据 |
| A u2与u3可能冲突；B u3同样禁止候选外动作 | 两组新增step5；A step1的“导航不在候选则换位置”仍在 | 72个已执行动作均合法，无Nothing happens；没有已执行的对应冲突场景 | 未触发不等于冲突已解决，无法验证A是否会错过direct action |
| Goal保留精确目标的成功处理/交付 | 两组保留原clean与placement及desklamp段落 | P3 Parent/A同四步成功；P6 Parent/A都完成clean/交付，A少两步 | 仅两个完整配对的保留与效率线索；无照明、多实例行为验证 |

## 与历史响应的联系

M3/M6过去出现扩大覆盖的收益，也有循环和遗漏；A在P6/P7/P10的可见前缀展现了表面/实例覆盖，与这种正向现象相容，但没有测试足够长的失败搜索来排除同样的副作用。M8的防近似替代方向与A/P7看到knife后离开的前缀相容，新Parent前缀也避免了替代，所以不能独立归因于Memory、例子或某条Diff。没有B行为，不存在B与历史响应一致/冲突的结果可供判断。

## 区分三层变化

1. **Preconditioner**：A真实改u1/u2，B真实Keep；没有重生成。
2. **Editor**：两者都在Parent上改step1/2并新增step5，文本不同；共同保留其他段落。其措辞融合是独立一次模型生成，即使大部分差异可追溯上游，也不能忽略Editor随机性。
3. **Actor**：当前只完整观察到Parent–A两个配对，一个持平、一个少两步；B完全缺少可评价动作。不能将B“没有动作”误解为其Skill无效。

旧R05 Parent与新Parent也出现明显差别（旧P3为16步、新为4步；旧P6耗尽50步、新10步成功；旧P10为38步、新14步）。它们模型路由/实现条件不同且执行随机，不能量化纯随机性，但说明**不可把旧Parent与新Candidate差值直接归功于Skill更新**。本报告只用新Parent作为行为配对基线。

本轮支持“不同Effective经同一Editor形成不同真实Skill”以及“A在一个完整配对中出现局部效率线索”。不支持“V23或V23.3方法获胜”、Patch粒度优势、历史预条件化因果增益或ALFWorld总体收益。完成缺失行为证据比据此新增D/S/C机制更优先。
