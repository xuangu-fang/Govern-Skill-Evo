# verifier_input_002：候选、结果与归档导航

[原说明](../README.md) · [Prompt](../verifier_prompt.md)

本组只对 R01–R03 的动作候选列表做共享引用与还原验证，没有新模型请求，也没有新的 Verifier 输出。保留现有 Prompt、统计和校验结论，完整新旧输入继续归档；不把其他实验的输出标成本组结果。

| 轮次 | 共用原候选 | 完整 v2 输入（归档） |
|---|---|---|
| R01 | [原候选](../../verifier_input_001/evidence/cases/R01/candidate.json) | [共享菜单输入](../../../../../artifacts/methods/v23_5/verifier_input_002/cases/R01/verifier_input.json) |
| R02 | [原候选](../../verifier_input_001/evidence/cases/R02/candidate.json) | [共享菜单输入](../../../../../artifacts/methods/v23_5/verifier_input_002/cases/R02/verifier_input.json) |
| R03 | [原候选](../../verifier_input_001/evidence/cases/R03/candidate.json) | [共享菜单输入](../../../../../artifacts/methods/v23_5/verifier_input_002/cases/R03/verifier_input.json) |

[字符与菜单数量统计](../results/summary.json) · [历史还原校验结论](../results/validation.json) · [历史测试结论](../results/tests.json)

完整 original_input、verifier_input、messages 以及 R01 已有 restored_input 保持原位。[独立构建记录](../../../../../artifacts/methods/v23_5/verifier_input_002_build_001) 也保留原位，不能用它替换默认来源包。后续 [事实筛查](../../verifier_fact_screen_001/evidence/README.md) 继续从原 artifacts/methods/v23_5/verifier_input_002 读取。

## 来源链

[原候选与 v1 输入](../../verifier_input_001/evidence/README.md) → [v2 共享菜单输入](README.md) → [事实筛查](../../verifier_fact_screen_001/evidence/README.md) → [Repair v1 准备](../../repair_001/evidence/README.md) → [Repair v2 与实测](../../repair_002/evidence/README.md)

这是材料和版本依赖顺序，不表示 v1 Repair 的输出被交给 v2；两版读取相同原候选与事实筛查结果。

[原输入归档](../../../../../artifacts/methods/v23_5/verifier_input_002) 中的完整 inputs、messages、Memory 和来源快照保持原位。已有 JSON 中的历史来源路径不改写。

## 保留与归档边界

这里的 JSON 是已有结果的静态证据副本，未重新请求模型、重新解析校验输出或合并候选。完整输入、messages、request、HTTP 正文、Memory 和冻结来源仍保存在 artifacts；运行器与测试继续读取原路径，证据副本不作为恢复入口，也不会自动同步更新。

2026-10-27 整理未运行实验、测试或哈希函数。原报告的测试数字、基准标签和阶段结论仍是历史记录；结构有效不表示语义完全正确。原有参考审阅不是经人类确认的金标准。完整归档被 Git 忽略，必要研究证据可随 Git 保存。
