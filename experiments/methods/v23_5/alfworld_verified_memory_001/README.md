# V23.5：Knowledge 核验与定向修正接入

## 2026-10-27 当前材料状态

R01–R02 已完成，R03 Parent Actor 在 train:0025 第 36 步失败；未发现最终 Test 归档。

正式 config/、任务 data/ 原样保留；以下结果来自已有文件，本次没有运行实验或测试。

[逐轮汇总](results/round_summary.json) · [优化逐任务指标](results/optimization_task_metrics.json) · [原状态](evidence/S1/state.json) · [停止记录](evidence/S1/stop.json)

| 轮次 | 状态／决策 | Parent / Candidate 成功数 | 原轮次结果 |
|---|---|---|---|
| R01 | RETAIN | 10/10 → 9/10 | [result](evidence/S1/rounds/R01/result.json) |
| R02 | RETAIN | 7/10 → 7/10 | [result](evidence/S1/rounds/R02/result.json) |
| R03 | 未完成 | 尚未完成同批 Gate | [stop](evidence/S1/rounds/R03/stop.json) |

[停止时已发布的 Skill（不是完整六轮最终结果）](evidence/S1/initial_skill.md)。state 中 active_memory 的完整 commits 仍在原归档，证据区只保留 active 索引、发布候选及对应审计结果，不是可恢复运行目录。

各完成轮次保留 Parent、Editor 候选与实际 Diff、Gate 逐任务配对、Replay 输出；启用知识核验的轮次另保留 Verifier、Repair、knowledge_review 候选。原 result.json 选择路径与原尝试编号保留，未把失败输出改成成功结果。

[Actor 第 36 步失败证据](evidence/actor_failure/train_0025/failure_step.json)及六份原 HTTP 回答保留在同目录：其中一次 HTTP 401，五次记录 action_not_admissible。这里只保留失败步骤，完整轨迹仍在归档。

完整测试日志已归档：[548 项 JUnit](../../../../artifacts/methods/v23_5/alfworld_verified_memory_001/reports/offline_tests.xml)、[652 项 JUnit](../../../../artifacts/methods/v23_5/alfworld_verified_memory_001/reports/unified_retry_tests.xml)。保留原 JSON 测试结论，仅更新 offline_tests.junit 路径（相对本实验根目录）。这些是历史测试数量，本次未重新运行。

当前通用脚本 [run_v23_5_verified_alfworld.sh](../../../../scripts/runs/run_v23_5_verified_alfworld.sh) 默认指向 alfworld_verified_feedback_001；下方旧入口说明保留历史阶段含义，通用脚本不会自动恢复旧目录。本次未执行任何入口。

[原始归档](../../../../artifacts/methods/v23_5/alfworld_verified_memory_001/)继续保存完整输入、HTTP、轨迹、Memory、日志及源码快照；研究副本不参与运行恢复或自动更新。仅克隆 Git 不包含这些原始数据。

## 历史说明（保留原阶段记录）

状态：代码接入与离线配置准备；按用户最新要求，尚未启动 6 轮优化或最终 Test。

从 action-only 实验配置派生，初始 Skill、模型、57 个优化任务、6 批顺序及独立 134 个 Test 任务保持原协议。新实验目录独立，不覆盖原运行或 R01–R03 离线核验结果。

## 提交链路

`Replay 候选 → 按引用提取原始证据并共享动作候选 → Verifier → 有 CONFLICT 时 Repair → 确定性校验 → Memory → 下一轮`

Verifier Prompt 沿用 `verifier_fact_screen_001` 的明显重要事实错误规则，Repair Prompt 沿用 `repair_002`，允许反馈不成立时原样返回。正式源码下两份 Prompt 与离线冻结版本逐字节相同。使用 SUPPORTED/CONFLICT；不做全任务范围审核，也没有第二次语义 Verifier。

新增或变化的 Knowledge 才进入核验；原样继承项跳过。历史证据只按实际引用打开对应不可变档案，身份、任务、前后观察、局部命令 ID 保持原始语义。共享动作候选可无损还原。Repair 只能修改被标记的位置，null 表示删除，其他条目及 revises 保留。

Replay 原始输出继续单独保留。修正候选位于每轮 `knowledge_review/candidate.json`，Memory 提交只使用该候选。正式保存结构未增加字段。最终 Skill 评估入口会重新检查 Memory 提交是否与核验候选一致。

Grouping、Diagnosis、Preconditioner、Editor、Replay、Verifier、Repair 统一使用以下重试规则：

- 每轮每阶段最多尝试 6 次（首次请求 + 最多 5 次重试）。技术失败和输出校验失败共享预算，断点恢复不重置。
- 可重试的 HTTP/传输/API 响应格式错误及输出截断：完整请求保持不变，包括已有反馈、输入、模型参数与 Token 上限。配额耗尽和其他不可重试 HTTP 错误停止。
- 完整输出的 JSON、字段、引用权限或局部合并校验失败：带上上次完整输出正文和具体错误，重新生成完整结果。只保留最近一次校验反馈，不附加模型的思考内容。
- 源档案损坏、输入异常、程序缺陷和本地读写失败：立即停止，不通过模型重试掩盖问题。
- 合法业务结果不重试。`CONFLICT` 正常进入一次 Repair，Repair 后没有第二次语义 Verifier；`SUPPORTED` 不代表穷尽证明经验正确。

中断后若已有完整响应，显式恢复可以继续处理该响应，不新增请求；若请求结果未知，该次仍占用预算。已完成的合法结果直接复用。本次含 Knowledge 核验的新实验使用固定共享预算，不继承旧实验单独授权的 Editor 追加次数。Actor 的逐步请求机制保持原样。

重试耗尽或遇到不可重试错误会保存失败记录，并阻止本轮候选 Memory 提交。所有实际请求与未知 usage 继续进入既有成本统计。Verifier/Repair 输出预算均为 32,768 Token，不自动提高。格式修正通过不等于内容已再次独立语义核验通过。

统一重试的离线验证记录见 `reports/unified_retry_validation.json` 和 [完整 JUnit 归档](../../../../artifacts/methods/v23_5/alfworld_verified_memory_001/reports/unified_retry_tests.xml)；此前接入阶段的验证报告保留为历史记录。

## 入口

只做离线配置检查：

```bash
bash scripts/runs/run_v23_5_verified_alfworld.sh check
```

下列命令会执行真实实验，本次没有运行：

```bash
# 6 轮优化完成后，顺序执行 134 个任务的最终评估
bash scripts/runs/run_v23_5_verified_alfworld.sh full
# 恢复已启动实验
bash scripts/runs/run_v23_5_verified_alfworld.sh resume-full
```

也支持 `run`、`resume`、`test`、`test-resume`、`status`、`test-status`。配置显式开启 `method.knowledge_review`；旧配置不自动新增模型调用。旧 action-only 入口与已冻结配置保留原样。

预定输出：`artifacts/methods/v23_5/alfworld_verified_memory_001/S1`；最终评估位于同级 `evaluation/final`。本次尚无该运行目录，也无新增真实模型请求。

## Actor 动作错误重试

当前未启动配置已启用 `actor_retry_invalid_actions=true`：缺少完整 action 标签或
提取动作不在本步展示列表时，原样重发请求，与技术重试共用每步六次总额度。
校验只在本地执行；无效响应不推进环境，耗尽额度停止并保留记录。Memory 的
Verifier／Repair 流程及其请求额度不变。

