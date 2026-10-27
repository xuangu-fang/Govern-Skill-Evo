# verifier_input_001：候选、结果与归档导航

[原说明](../README.md) · [Prompt](../verifier_prompt.md)

本目录保留三轮原始 Replay 候选和旧版 Verifier 的五次请求证据。原始三轮中 R02/R03 有效，R01 失败；两次授权追加仍失败。R01 三份响应的 content 均为空、finish_reason 均为 length，不从独立推理字段补造核验结果。有效覆盖仍为 13/18 条。

| 轮次 | 原始候选 | 首轮核验结果 |
|---|---|---|
| R01 | [candidate](cases/R01/candidate.json) | [截断失败](verifier_run_001/runs/R01/attempts/001/validation.json) |
| R02 | [candidate](cases/R02/candidate.json) | [核验输出](verifier_run_001/runs/R02/attempts/001/verifier_output.json) |
| R03 | [candidate](cases/R03/candidate.json) | [核验输出](verifier_run_001/runs/R03/attempts/001/verifier_output.json) |

三份候选来自 verifier_input_001 冻结输入包，对应历史 Replay 的 R01/001、R02/002、R03/001；没有根据本次核验结果修改候选。

| 独立运行批次 | 请求数 | 状态与协议 |
|---|---:|---|
| verifier_run_001 | 3 | [原汇总](verifier_run_001/run_summary.json) · [原协议](verifier_run_001/protocol.json) · [回答与校验](verifier_run_001/runs/) |
| verifier_run_001_retry_R01_001 | 1 | [原汇总](verifier_run_001_retry_R01_001/run_summary.json) · [原协议](verifier_run_001_retry_R01_001/protocol.json) · [回答与校验](verifier_run_001_retry_R01_001/runs/) |
| verifier_run_001_retry_R01_002 | 1 | [原汇总](verifier_run_001_retry_R01_002/run_summary.json) · [原协议](verifier_run_001_retry_R01_002/protocol.json) · [回答与校验](verifier_run_001_retry_R01_002/runs/) |

每个追加批次仍保留自己的 attempts/001，不能合并目录或覆盖首次失败。

- [历史实测结论](../LIVE_RESULTS.md)
- [含追加尝试的累计对照](../results/live_comparison.json)
- [反馈与分歧审阅](../results/live_adjudication.json)
- [运行前参考标签](../results/reference_review.json)
- [输入统计](../results/summary.json)

后续 [输入 v2](../../verifier_input_002/evidence/README.md) 只调整动作候选列表存储；[事实筛查](../../verifier_fact_screen_001/evidence/README.md) 改变核验目标。两者不回写这里的候选、旧标签或失败记录。

## 来源链

[原候选与 v1 输入](README.md) → [v2 共享菜单输入](../../verifier_input_002/evidence/README.md) → [事实筛查](../../verifier_fact_screen_001/evidence/README.md) → [Repair v1 准备](../../repair_001/evidence/README.md) → [Repair v2 与实测](../../repair_002/evidence/README.md)

这是材料和版本依赖顺序，不表示 v1 Repair 的输出被交给 v2；两版读取相同原候选与事实筛查结果。

[原输入归档](../../../../../artifacts/methods/v23_5/verifier_input_001) 中的完整 inputs、messages、Memory 和来源快照保持原位。已有 JSON 中的历史来源路径不改写。

## 保留与归档边界

这里的 JSON 是已有结果的静态证据副本，未重新请求模型、重新解析校验输出或合并候选。完整输入、messages、request、HTTP 正文、Memory 和冻结来源仍保存在 artifacts；运行器与测试继续读取原路径，证据副本不作为恢复入口，也不会自动同步更新。

2026-10-27 整理未运行实验、测试或哈希函数。原报告的测试数字、基准标签和阶段结论仍是历史记录；结构有效不表示语义完全正确。原有参考审阅不是经人类确认的金标准。完整归档被 Git 忽略，必要研究证据可随 Git 保存。
