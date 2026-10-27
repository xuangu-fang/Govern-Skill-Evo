# R03 两模块 × 两种视图：003 与授权补充批次

四个单元均已取得首个程序校验有效结果；两种 Replay 输出的内容核查都发现了事实错误，因此不能把 valid 等同于知识可靠。max_tokens 全程为 32,768。

003 原始三次预算内仅 Preconditioner Memory v3 通过。004、005、006 分别是用户在失败后授权的 Preconditioner Knowledge Only、Replay Memory v3、Replay Knowledge Only 补充重试；保留原始失败，不将补充结果写回 003。

| 模块 | 视图 | 003 状态／次数 | 追加次数 | 合计次数 | 有效来源 |
|---|---|---|---:|---:|---|
| preconditioner | memory_v3 | valid / 1 | 0 | 1 | 003 / 001 |
| preconditioner | knowledge_only | failed / 3 | 2 | 5 | 004 / 002 |
| replay | memory_v3 | failed / 3 | 1 | 4 | 005 / 001 |
| replay | knowledge_only | failed / 3 | 2 | 5 | 006 / 002 |

## Token 消耗

以下累计包括失败请求；API usage 均可用。缓存输入仍在 prompt_tokens 中，不代表等额计费。本表不包含已中止的 001/002 旧批次。

| 模块 | 视图 | 累计输入 | 累计输出（含推理） | 累计总量 |
|---|---|---:|---:|---:|
| preconditioner | memory_v3 | 225,267 | 29,014 | 254,281 |
| preconditioner | knowledge_only | 448,298 | 144,005 | 592,303 |
| replay | memory_v3 | 1,116,337 | 95,418 | 1,211,755 |
| replay | knowledge_only | 714,251 | 119,195 | 833,446 |

按 003 首次请求的 API usage，Preconditioner 单次输入从 225,267 降到 89,657（减少 60.2%）；Replay 从 279,052 降到 142,858（减少 48.81%）。部分相同消息的请求，API 报告的输入 token 有轻微差异。单次输入减少不等于取得有效响应的累计成本必然下降；Preconditioner Knowledge Only 的五次累计总量高于 Memory v3 的一次。

## 失败与内容核查

- Preconditioner Memory v3 首次通过。Knowledge Only 前三次为两次 length、一次 JSON 失败；补充为一次 JSON 失败后通过。两版有效计划都仍有恢复依据或依赖全局未访问状态的问题，不能仅以输出合法认定设计改进有效。
- Replay Memory v3 原三次为 JSON、length、JSON 失败，补充首次通过。其 7 条新 Knowledge 中存在 Q6 未发生的访问和错误的 admissibility 描述：例如 Q6:19 实际为合法的 go to countertop 1，输出却写成不合法的 go to cabinet 4。
- Replay Knowledge Only 原三次为引用、引用、length；补充为引用失败后通过。三个引用失败的触发片段均包含本轮执行的斜杠并列写法，如 Q6/Q7、P9/Q9，现有扫描器将其识别为历史 ID。原始失败状态保留；未修复响应或改变权限。
- Knowledge Only 的 5 条新 Knowledge 也有事实错误：声称没有本轮执行及时从错误对象类型转向正确类型，但 P7 先拿 pan、后拿 pot 并完成；将 Q5:17 写成不合法的 go to stoveburner 2，实际是合法的 go to countertop 1。此外，对恢复规则的评价没有充分区分其触发条件是否发生。
- 两版 Replay 均新增一个 entry、revises 为空，旧 M1/M2 共 13 条 Knowledge 按追加语义保留。因此本次没有检验整体修订 MemoryEntry 时是否遗漏旧知识，也不足以判断历史经验利用能力。

## 边界与记录

输入、Prompt、模型参数及引用校验未在重试中修改；无响应修复、额外评判模型、Actor 重跑或 Skill/Memory 发布。Replay 使用冻结的历史实际 Diff、Effective Plan 和配对执行，不使用此次 Preconditioner 新输出。追加后的次数不对称，且仅 R03 一个样本；不能推断视图导致质量差异或任务成功率提高。

- [逐次统计与有效输出路径](../results/R03_with_supplements.json)
- [Preconditioner Memory v3 审阅](../results/preconditioner_review.json)
- [Preconditioner Knowledge Only 审阅](../../knowledge_only_single_round_004/results/preconditioner_review.json)
- [Replay Memory v3 审阅](../../knowledge_only_single_round_005/results/replay_review.json)
- [Replay Knowledge Only 审阅](../../knowledge_only_single_round_006/results/replay_review.json)
- [原 Replay Knowledge Only 引用定位](../results/replay_knowledge_only_reference_review.json)
- [补充引用定位](../../knowledge_only_single_round_006/results/reference_review_001.json)

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](../README.md)。
