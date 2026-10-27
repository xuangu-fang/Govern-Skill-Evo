# verifier_fact_screen_001：候选、结果与归档导航

[原说明](../README.md) · [Prompt](../verifier_prompt.md)

本组有三次真实核验请求，R01–R03 全部结构有效，覆盖 18 条 Knowledge。新目标是明显重要事实错误筛查，不能和旧版充分性审计的标签口径混用；R03 [0,3] 仍为漏检，没有因模型放行而改写基准。

| 轮次 | 原候选 | Verifier 输出 | 回答与校验 |
|---|---|---|---|
| R01 | [candidate](../../verifier_input_001/evidence/cases/R01/candidate.json) | [判定](verifier_fact_screen_run_001/runs/R01/attempts/001/verifier_output.json) | [回答](verifier_fact_screen_run_001/runs/R01/attempts/001/response.json) · [校验](verifier_fact_screen_run_001/runs/R01/attempts/001/validation.json) |
| R02 | [candidate](../../verifier_input_001/evidence/cases/R02/candidate.json) | [判定](verifier_fact_screen_run_001/runs/R02/attempts/001/verifier_output.json) | [回答](verifier_fact_screen_run_001/runs/R02/attempts/001/response.json) · [校验](verifier_fact_screen_run_001/runs/R02/attempts/001/validation.json) |
| R03 | [candidate](../../verifier_input_001/evidence/cases/R03/candidate.json) | [判定](verifier_fact_screen_run_001/runs/R03/attempts/001/verifier_output.json) | [回答](verifier_fact_screen_run_001/runs/R03/attempts/001/response.json) · [校验](verifier_fact_screen_run_001/runs/R03/attempts/001/validation.json) |

- [历史核验结论及漏检](../LIVE_RESULTS.md)
- [标签对照及 usage](../results/live_comparison.json)
- [具体反馈审阅](../results/live_adjudication.json)
- [三轮运行状态](../results/live_run_summary.json)
- [原参考基准](../reference_review.json)

[运行协议](verifier_fact_screen_run_001/protocol.json)和三份有效输出均原样保留。实际 CONFLICT 的 R01 [0,4]、R02 [0,2]、R03 [0,1] 被后续 Repair 采用；漏检的 R03 [0,3] 未进入修复目标。查看 [Repair v1 准备](../../repair_001/evidence/README.md) 与 [Repair v2 结果](../../repair_002/evidence/README.md)。

## 来源链

[原候选与 v1 输入](../../verifier_input_001/evidence/README.md) → [v2 共享菜单输入](../../verifier_input_002/evidence/README.md) → [事实筛查](README.md) → [Repair v1 准备](../../repair_001/evidence/README.md) → [Repair v2 与实测](../../repair_002/evidence/README.md)

这是材料和版本依赖顺序，不表示 v1 Repair 的输出被交给 v2；两版读取相同原候选与事实筛查结果。

[原输入归档](../../../../../artifacts/methods/v23_5/verifier_fact_screen_001) 中的完整 inputs、messages、Memory 和来源快照保持原位。已有 JSON 中的历史来源路径不改写。

## 保留与归档边界

这里的 JSON 是已有结果的静态证据副本，未重新请求模型、重新解析校验输出或合并候选。完整输入、messages、request、HTTP 正文、Memory 和冻结来源仍保存在 artifacts；运行器与测试继续读取原路径，证据副本不作为恢复入口，也不会自动同步更新。

2026-10-27 整理未运行实验、测试或哈希函数。原报告的测试数字、基准标签和阶段结论仍是历史记录；结构有效不表示语义完全正确。原有参考审阅不是经人类确认的金标准。完整归档被 Git 忽略，必要研究证据可随 Git 保存。
