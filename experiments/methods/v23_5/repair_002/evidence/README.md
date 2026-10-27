# repair_002：候选、结果与归档导航

[原说明](../README.md) · [Prompt](../repair_prompt.md)

三轮原始候选及采用的 Verifier 输出按原字节保留。授权修复位置为 R01 [0,4]、R02 [0,2]、R03 [0,1]；不把漏检的 R03 [0,3] 加入修复范围。

| 轮次 | 修复前候选 | 采用的核验结果 |
|---|---|---|
| R01 | [candidate](cases/R01/candidate.json) | [verifier_output](cases/R01/verifier_output.json) |
| R02 | [candidate](cases/R02/candidate.json) | [verifier_output](cases/R02/verifier_output.json) |
| R03 | [candidate](cases/R03/candidate.json) | [verifier_output](cases/R03/verifier_output.json) |

本组使用 v2 冻结输入完成三次 Repair 请求；三个局部输出及合并候选均已有保存记录。本次只复制这些结果，不调用 merge、validate 或恢复函数。

| 轮次 | 实际局部修复 | 修复后候选 | 回答与校验 |
|---|---|---|---|
| R01 | [repair_output](repair_run_001/runs/R01/attempts/001/repair_output.json) | [merged_candidate](repair_run_001/runs/R01/attempts/001/merged_candidate.json) | [回答](repair_run_001/runs/R01/attempts/001/response.json) · [校验](repair_run_001/runs/R01/attempts/001/validation.json) |
| R02 | [repair_output](repair_run_001/runs/R02/attempts/001/repair_output.json) | [merged_candidate](repair_run_001/runs/R02/attempts/001/merged_candidate.json) | [回答](repair_run_001/runs/R02/attempts/001/response.json) · [校验](repair_run_001/runs/R02/attempts/001/validation.json) |
| R03 | [repair_output](repair_run_001/runs/R03/attempts/001/repair_output.json) | [merged_candidate](repair_run_001/runs/R03/attempts/001/merged_candidate.json) | [回答](repair_run_001/runs/R03/attempts/001/response.json) · [校验](repair_run_001/runs/R03/attempts/001/validation.json) |

原审阅认为三处原问题已修正，但 R01 新增轻微空间表述问题；15 条未授权 Knowledge 保持原样，R03 [0,3] 漏检仍未修正。没有第二次语义 Verifier 或正式 Memory 提交。

- [历史修复结论与局限](../LIVE_RESULTS.md)
- [逐项修正前后审阅](../results/live_adjudication.json)
- [结构与成本汇总](../results/live_structural_usage_summary.json)
- [三轮调用状态](../results/live_run_summary.json)

[运行协议](repair_run_001/protocol.json)保持原始预算与范围。

原 README.md 是现有 prepare.py 的 FILES 中一项，会与冻结副本比较，所以保留其原文。本页补充结果导航，不改源码、Prompt、原 README、历史 LIVE_PROTOCOL/LIVE_RESULTS 或冻结契约。

## 来源链

[原候选与 v1 输入](../../verifier_input_001/evidence/README.md) → [v2 共享菜单输入](../../verifier_input_002/evidence/README.md) → [事实筛查](../../verifier_fact_screen_001/evidence/README.md) → [Repair v1 准备](../../repair_001/evidence/README.md) → [Repair v2 与实测](README.md)

这是材料和版本依赖顺序，不表示 v1 Repair 的输出被交给 v2；两版读取相同原候选与事实筛查结果。

[原输入归档](../../../../../artifacts/methods/v23_5/repair_002) 中的完整 inputs、messages、Memory 和来源快照保持原位。已有 JSON 中的历史来源路径不改写。

## 保留与归档边界

这里的 JSON 是已有结果的静态证据副本，未重新请求模型、重新解析校验输出或合并候选。完整输入、messages、request、HTTP 正文、Memory 和冻结来源仍保存在 artifacts；运行器与测试继续读取原路径，证据副本不作为恢复入口，也不会自动同步更新。

2026-10-27 整理未运行实验、测试或哈希函数。原报告的测试数字、基准标签和阶段结论仍是历史记录；结构有效不表示语义完全正确。原有参考审阅不是经人类确认的金标准。完整归档被 Git 忽略，必要研究证据可随 Git 保存。
