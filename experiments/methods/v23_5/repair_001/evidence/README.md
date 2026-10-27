# repair_001：候选、结果与归档导航

[原说明](../README.md) · [Prompt](../repair_prompt.md)

三轮原始候选及采用的 Verifier 输出按原字节保留。授权修复位置为 R01 [0,4]、R02 [0,2]、R03 [0,1]；不把漏检的 R03 [0,3] 加入修复范围。

| 轮次 | 修复前候选 | 采用的核验结果 |
|---|---|---|
| R01 | [candidate](cases/R01/candidate.json) | [verifier_output](cases/R01/verifier_output.json) |
| R02 | [candidate](cases/R02/candidate.json) | [verifier_output](cases/R02/verifier_output.json) |
| R03 | [candidate](cases/R03/candidate.json) | [verifier_output](cases/R03/verifier_output.json) |

本组是 v1 离线契约和输入准备，没有本组真实 Repair 请求或修复后候选。后续 [v2](../../repair_002/evidence/README.md) 允许在核验反馈不成立时原样返回，并另行完成真实运行；其结果不归入 v1。

完整测试日志已迁至 [归档 results/tests.txt](../../../../../artifacts/methods/v23_5/repair_001/results/tests.txt)，保留 [23 项测试的历史结论](../results/tests.json)。日志正文没有改写，本次没有执行测试。

原 README.md 是现有 prepare.py 的 FILES 中一项，会与冻结副本比较，所以保留其原文。本页补充结果导航，不改源码、Prompt、原 README、历史 LIVE_PROTOCOL/LIVE_RESULTS 或冻结契约。

## 来源链

[原候选与 v1 输入](../../verifier_input_001/evidence/README.md) → [v2 共享菜单输入](../../verifier_input_002/evidence/README.md) → [事实筛查](../../verifier_fact_screen_001/evidence/README.md) → [Repair v1 准备](README.md) → [Repair v2 与实测](../../repair_002/evidence/README.md)

这是材料和版本依赖顺序，不表示 v1 Repair 的输出被交给 v2；两版读取相同原候选与事实筛查结果。

[原输入归档](../../../../../artifacts/methods/v23_5/repair_001) 中的完整 inputs、messages、Memory 和来源快照保持原位。已有 JSON 中的历史来源路径不改写。

## 保留与归档边界

这里的 JSON 是已有结果的静态证据副本，未重新请求模型、重新解析校验输出或合并候选。完整输入、messages、request、HTTP 正文、Memory 和冻结来源仍保存在 artifacts；运行器与测试继续读取原路径，证据副本不作为恢复入口，也不会自动同步更新。

2026-10-27 整理未运行实验、测试或哈希函数。原报告的测试数字、基准标签和阶段结论仍是历史记录；结构有效不表示语义完全正确。原有参考审阅不是经人类确认的金标准。完整归档被 Git 忽略，必要研究证据可随 Git 保存。
