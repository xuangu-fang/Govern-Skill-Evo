# 明显事实错误筛查：Prompt、边界与运行前基准

2026-10-27 材料整理入口：[候选、结果与归档导航](evidence/README.md)。以下保留原阶段说明；本次没有重跑实验或测试。

已完成第 1、2 步。独立版本为 `v23_5_obvious_fact_screen_v1`，使用现有 v2 共享动作候选列表输入。原始 Knowledge、证据和输出 JSON Schema 不变；旧版充分性审计的 Prompt、基准和实测结果保留。

后续第 3 步的三轮单次实测已完成，见 [运行结果](LIVE_RESULTS.md)。本页下述“未运行”及调用计数描述的是第 1、2 步冻结时的状态；运行前快照不回写。

## 已交付

- [新版 Prompt](verifier_prompt.md)：聚焦明显重要错误；缺少完整轨迹本身不拦截，不要求穷尽所有断言。明确可见性、时点、规则条件和已有反例的边界。
- [判定边界](BOUNDARY.md)：明确重要性门槛、可见性缺证据与具体观察矛盾的区别、复杂归因和概括措辞的处理，以及后续评价口径。
- [逐条审阅表](REFERENCE_REVIEW.md)与 [JSON 基准](reference_review.json)：18 条目标逐条给出理由、接受的局限、旧标签关系及当前原始依据。
- [冻结与完整性校验](prepare.py)：只准备输入和消息，不具备模型请求入口。基准答案和边界示例不进入 messages。

`SUPPORTED` 兼容旧枚举，但现在只表示“本次未发现明显重要错误”，不代表完整证据支持认证。`CONFLICT` 必须指向当前材料可识别、确有修正价值的问题；单纯缺证据不符合门槛。原输出校验器继续检查 JSON、目标覆盖、原文摘录及引用权限，不自动证明理由正确。

## 基准结果（不是模型结果）

| 轮次 | 目标 | 预期 CONFLICT | 预期 SUPPORTED | 其中 review_only |
|---|---:|---:|---:|---:|
| R01 | 5 | 1 | 4 | 1 |
| R02 | 6 | 1 | 5 | 0 |
| R03 | 7 | 2 | 5 | 1 |
| 合计 | 18 | 4 | 14 | 2 |

四个明确问题：R01 `[0,4]` 的 Q5:49 地点错写；R02 `[0,2]` 的具体水壶可见性错误；R03 `[0,1]` 将 Parent 的设备存放/开关门模式推广到已有不同模式的冷却案例；R03 `[0,3]` 将“未找到目标”误作不能判断搜索规则适用性的理由，与 Diff 的明确触发条件不符。

R01 `[0,3]` 和 R03 `[0,4]` 涉及概括性措辞、必要条件或任务收益口径的歧义。按宽松边界预期通过，但在运行前就标记为 review_only。主评价集为 16 条：4 条应拦截、12 条允许通过；两条边界项始终展示、不进入主指标，不能看完未来输出后再决定排除。

旧档案已发现但未提供给模型的反证，不要求本版检出。例如 R02 `[0,1]` 的 Parent 首步细节错误不能用隐藏的 P9:1/2 作为拒绝依据。这不意味着其事实已变正确，只意味着它不属于当前输入可识别的必检错误。

审阅由 Codex 完成，`human_reviewed=false`；此前已看过旧版结果，`prior_verifier_outputs_seen=true`。这是新版运行前冻结的开发集参考，不是盲评或独立人工金标准。未回算旧模型输出，未声称新版本检出率提高。

## 冻结产物与验证

独立产物：`artifacts/methods/v23_5/verifier_fact_screen_001/`，包含 Prompt、边界、基准、每轮原样复制的去重输入及新 messages、SHA-256 清单和校验结果。严格核对旧输入、旧基准及来源快照未变；逐条检查 Knowledge 一致、目标无遗漏/重复、证据真实存在、锚点字段值正确和答案不进入消息。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_fact_screen_001/prepare.py prepare
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_fact_screen_001/prepare.py verify
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python -m pytest -q experiments/methods/v23_5/verifier_fact_screen_001/test_prepare.py
```

prepare 拒绝覆盖已有目录；需要重建时指定新的 `--output`。12 项离线测试通过，测试证明基准和冻结产物的一致性，不证明模型能遵守新边界。参考标签仅在内存中转换为合成结果做 Schema 检查，未保存或冒充实际 Verifier 输出。

本次模型调用、Actor 调用、Repair 和 Memory 提交均为 0。后续是否运行新版核验属于下一步；本阶段没有选择新的推理配置或重试预算，也没有修改正式主流程。
