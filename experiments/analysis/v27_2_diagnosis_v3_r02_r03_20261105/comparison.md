# Diagnosis v3 冻结回放：R02 与 R03

R02 保留了一项完整的选择策略；R03 原来集中在 u3 的三种判断，在本次输出中各自有独立的 Update ID。两轮各采样一次，结果用于比较提案结构。

| 历史轮次与行为 | Diagnosis v2 | Diagnosis v3 |
|---|---|---|
| R02：“还有更强结果”与具体选项如何选择 | u1 | u1，仍把选择条件、保留具体答案的例外和输出要求放在一起。新版更强调题干明确求最强结论，文字及触发范围并不完全相同。 |
| R03：更强结果选项 | u1 | u1，仍是一项，但触发条件收窄。P1 被列入依据，实际题干只问哪条定量估计成立，未明确要求“最强”。 |
| R03：辨别蕴含方向 | u2 | u2，保留方向判断。 |
| R03：梯度对象及其指数 | u3 的一部分 | u3，依据 P5。 |
| R03：原环境域与子域的容量 | u3 的一部分 | u4，依据 P4、P8。 |
| R03：频率受限估计与全局结论 | u3 的一部分 | u5，依据 P10。 |

新版 R03 的后三项可以单独取舍。每项关联一个不同的选项分歧，同时也更贴近具体题型；归档没有测量它们的迁移效果。旧 R02 的候选版曾改对三题，本次重放不产生新版的候选分数。

## 对照口径

v2 对照直接使用正式训练中已通过校验的原始输出。v3 从每轮自己的父版和已完成 Actor 记录重建 Diagnosis 请求；R03 沿用历史输入，与本次 R02 输出独立。发送前核验完整用户消息一致，系统文本仅一段不同。模型 deepseek-flash，temperature 1.0，medium reasoning，输出上限 32,768 tokens；两轮均在第 1 次请求返回并通过校验。只执行 Diagnosis。正式配置中的 Preconditioner 仍是 v3，提示词与上次正式训练的冻结文件逐字节一致。

- R02：[v2 输出](../../campaigns/v27_2_precond_v3_lmb53_20261105_131046/rounds/R02/diagnosis/attempts/001/parsed.json) · [v3 输出](R02/attempts/001/parsed.json)
- R03：[v2 输出](../../campaigns/v27_2_precond_v3_lmb53_20261105_131046/rounds/R03/diagnosis/attempts/001/parsed.json) · [v3 输出](R03/attempts/001/parsed.json)
- [历史 v2 系统提示词](../../launches/v27_2_precond_v3_lmb53_20261105_131046/frozen_prompts/diagnosis.md) · [本次 v3 系统提示词](R03/attempts/001/prompt.md) · [冻结回放脚本](replay_frozen.py)。使用 LiveMathematicianBench Python 运行脚本，传入 R02 或 R03 与 --verify-only 可在本地复核。
