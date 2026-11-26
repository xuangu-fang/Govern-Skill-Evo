# V25 后续训练配置：12 批 × 10 题

**已撤销，仅保留离线分析历史。** 2026-10-26 用户决定恢复 [8 批 × 15 题](BATCH15_TRAINING.md)，中断并删除此次 10 题训练实验；以下内容不是当前启动配置。

2026-10-26 用户确认：暂不增加公共内容共享或响应／代码去重，将 V25 每批任务数从 15 改为 10。本次只准备配置，不初始化 campaign、不调用模型、不启动训练。

后续训练使用 [v25_spreadsheetbench_full120_batch10.json](../../../experiments/methods/v25/configurations/v25_spreadsheetbench_full120_batch10.json)。配置继承 `v25_full120_exec30_gen6_actor32k_w4_20261026_004/config.json` 的运行条件，只重新分批，并将方法版本绑定到当前已调整的 Preconditioner。旧实验归档和 SkillAdam 配置不修改。

| 项目 | 配置 |
|---|---|
| 优化任务 | 原始 80 Train 后接 40 Val，共 120 题；保持原顺序、不打乱 |
| 批次／遍历 | 12 批，每批 10 题，1 epoch |
| Parent／Candidate | 同一批 10 对；Parent 结果原样复用于诊断、Gate 和 Replay |
| 初始 Skill／Memory | 原始 initial Skill；新 campaign 使用空 Memory |
| Preconditioner | `v25_preconditioner_history_primary_v2`，使用当前源码设计 |
| Actor | 并发 4，每次最多 32,768 输出 tokens |
| 尝试预算 | `program_executions_v1`：每题最多 30 次实际程序执行，每份程序最多 6 次 API 总请求 |
| 时间 | 无整题累计时限；单次 API 300 秒、单次程序执行 600 秒 |
| 反馈 | 仅格式／执行／输出文件错误；无标准答案或评分纠错反馈 |
| 输入视图 | 沿用已实现的连续时间线；不增加新的去重机制 |
| 其他条件 | API、模型、优化器预算、任务输入、预览、执行器和评分规则均沿用来源配置 |

新配置中的 `batches` 是实际调度依据。准备器 `baseline.prepare` 默认也按 10 题分批；准备器的其余通用默认参数不代替本页链接的完整训练配置。适配器接受新 12×10 和历史 8×15 两种完整划分，仍检查 120 个优化任务、280 个 Test 的覆盖与隔离；历史配置能通过批次校验不代表可以绕过源码冻结检查恢复旧实验。

12 批意味着最多 12 轮优化和 Gate，不能将其解释为原 8 轮训练的等价执行。每轮成功数严格增加才 ACCEPT 的规则不变。Test 不参与优化，本次不启动 Test。

配置已通过当前 `validate_config` 离线校验，并与来源配置核对：120 个任务顺序完全一致，除 `batches` 和 `method.preconditioner_prompt` 外所有字段一致。输入 Token 的实际下降幅度尚未测量。
