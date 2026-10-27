# R06：Editor 对冻结 Effective Plan 的忠实性验证

日期：2026-10-22（Asia/Shanghai）。本次沿用 semantic_generation_004 的首次合法 Effective Plan 和同一 Parent，执行一次真实 Editor 生成。**在本样本的逐项文本核对中，Editor 忠实落实了 u1、u2；未发现遗漏关键条件、恢复被调整的旧要求或引入额外策略。** 输入与实际 Diff 核验通过。

依用户最新要求，Checks 保持原样，其覆盖缺口不作为本轮推进或忠实性判断的阻塞条件。没有修改生产 Prompt、算法或生成结果。

## 执行结果

- 1 个 Editor 逻辑阶段、1 次 HTTP，首次结构合法，零重启；耗时 35.914 秒。
- API 报告 prompt 3,128、completion 6,655、total 9,783 tokens；费用未知。
- 使用现有模型、调用配置和 Editor Prompt。没有重新生成 Diagnosis 或 Preconditioner，没有额外审查模型、Actor 或 Replay 调用。
- 冻结上游来源、实际 Editor 输入、消息和生产文件。重新解析上游已选响应并重编译 Effective Plan，确认交接内容没有人工改动。
- 保存完整 [Candidate Skill](runs/R06_editor/attempt_001/candidate.md) 和由真实 Parent/Candidate 重新计算的 [actual.diff](runs/R06_editor/attempt_001/actual.diff)。

## 四项核对

| 审查点 | 证据与结论 |
|---|---|
| 输入正确 | 实际用户消息只有 `parent` 和 `plan`；plan 与 004 的 Effective Plan 完全一致。完整消息与生产 `editor.messages_for` 的结果逐值相等。未把 Original Plan、Memory、Adjustment 或 Preconditioner Patch 送给 Editor |
| 修改忠实 | Candidate 只修改 Parent 第 26 行搜索段和第 28 行清洁/温变段。下表核对两个 Updates 的全部主要行为要求 |
| 没有额外策略 | 未发现新插入/取回步骤、强制先开门、额外搜索结束门槛或全新回访禁令。当前存在的搜索覆盖与回访限制来自 Parent/Effective Update，不是 Editor 另行添加 |
| 真实 Diff | 模型 Patch 严格应用得到 Candidate；另由 Parent/Candidate 计算 actual.diff，再严格应用该 Diff，也精确得到相同 Candidate。两份 Diff 的 hunk 布局不同，但修改结果相同；没有用 Preconditioner 的 Update 文本 Patch 代替 Skill Diff |

## Effective Update → Candidate 逐项映射

Candidate 行号对应保存的原始文本；每行包含一个完整步骤。

| 有效要求 | Candidate 落实 | 核对 |
|---|---|---|
| u1：每个独立容器、每个表面分别作为候选；不能因一两个成员为空就认定整类完成 | 第 26 行明确加入两项要求 | 已落实 |
| u1：继续跨类别搜索，优先未打开/未检查处而不是返回旧位置 | 第 26 行保留 family-spread sweep，并保留新候选优先和 loop-back 前覆盖的要求 | 已落实；未恢复 Original 的连续开容器表述 |
| u1：到达已打开且空，或内容与已检查地点一致的位置时，不再打开、重查或停留，立即离开 | 第 26 行明确写入完整触发条件和动作 | 已落实 |
| u1：小范围位置在近期观察中反复出现且没有目标时停止循环，在步数预算内扩展 | 第 26 行明确写入 | 已落实 |
| u1：空手时不反复查 inventory | 第 26 行保留 Parent 原要求 | 已落实，无需重复新增 |
| u2：持有精确目标，与家电共处；显式 heat/cool 动作可用即执行，包括开门之前 | 第 28 行明确保留 `directly on the held target`、`as soon as ... admissible` 和 `even before opening` | 已落实，未退回“必须打开” |
| u2：仅在动作否则不可用时开门；一次温变足够 | 第 28 行明确写入两项边界 | 已落实 |
| u2：不额外反复开关、不反复放入取出；保留持有物直接冷却 | 第 28 行保留循环限制和 direct cooling | 已落实，未新增插入/取回动作，也未升级为禁止任何一次必要操作 |
| u2：温变后直接到目的地并完成放置 | 第 28 行明确写入，衔接原第 4 步 | 已落实 |

这些是人工语义核对，不是字符串或 Patch 校验程序自动得出的结论。没有用 Editor 自述的 `reason` 代替对 Candidate 的检查。

## Goal 与 Parent 保留边界

- 台灯专用流程和约束完全未改；精确类别识别与禁止近似类别替代的整个第 2 步完全未改。
- 原有清洁条件和跳过清洁绕路的文字保留；原第 4 步目的地交付文字完全未改。温变流程插入取得精确目标之后、目的地交付之前。
- Goal 的“持有目标直接执行温变、避免反复开关”被保留，没有因 c2 的 `co-located/held` 表述将 held 条件放宽。
- 第 4 步仍允许在目的地关闭时先打开再放置。这属于交付条件，与第 3 步“温变动作可用时不必先开家电”针对不同操作，并非恢复温变的打开前置要求。
- Goal 所要求的成功顺序交付未被新增禁止或重写；但是否在实际两物品任务中继续成功，仍须 Actor 验证。
- “找到目标或所有候选检查一次后结束”以及原有单次扫描约束均来自 Parent；不能把它们误报为 Editor 从 Checks 新增的要求。短历史下这些搜索规则能否可靠执行，属于上游策略与执行效果问题，本轮未作有效性结论。

## 验证与边界

[FIDELITY_EVIDENCE.json](FIDELITY_EVIDENCE.json) 保存 12 项通过的机械核对、9 项人工映射以及 Candidate / actual.diff 的哈希。[AUDIT.json](AUDIT.json) 保存请求、输入、配置冻结、首次合法选择、严格重解析与实际 Diff 重建审计。

复核命令（不发 API）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.semantic_generation_005.run audit
```

本次支持“该 R06 样本中 Editor 能忠实实现这份 Effective Plan”，无需据此重新设计 Editor。它只有一次生成，不证明普遍遵循性或 Actor 收益。实际 Diff 已保存且可精确重建；本轮没有运行 Replay，因此不声称已经观察到 Replay 消费该 Diff。Candidate 未部署为新 Parent，完整第五步仍未完成。
