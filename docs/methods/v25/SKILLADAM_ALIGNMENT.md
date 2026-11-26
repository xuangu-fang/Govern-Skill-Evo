# SkillAdam 与 V25 的 Actor 历史和证据对齐

2026-10-27 实现于 `scripts/runs/skilladam/spreadsheetbench/shared_actor/run_skilladam_spreadsheetbench_aligned.py`。本次只更新接入层、文档和离线测试；未启动新实验，未修改旧实验归档、冻结配置、清单或上游 SkillAdam 源码。

## 新实验的显式配置

未来新 V25 与 SkillAdam 对照实验的共享 `actor_profile` 应同时采用：

```json
{
  "attempt_budget_policy": "program_executions_v1",
  "actor_history_policy": "execution_only_v1",
  "actor_task_timeout_seconds": 0
}
```

SkillAdam 的 `skilladam.json` 顶层另需显式声明：

```json
{"actor_evidence_view": "execution_only_v1"}
```

上述只是完整配置的增量示例，不会自动改写现有配置。`shared_config.json` 仍必须与所对照 V25 配置完全一致（旧实验为 campaign 的 `config.json`，新版配对准备为 `v25/config/campaign.json`），包括初始 Skill、数据顺序、8×15 批次、API、模型、Actor 并发 4／49152 输出、30 次执行／每份程序 6 次请求、超时、预览、执行器和评分条件。最新输出额度见 [TOKEN_BUDGETS.md](TOKEN_BUDGETS.md)，SkillAdam 优化器仍为 16384。

预检及 backend 初始化均检查历史策略与证据策略匹配、共享 Actor 配置合法、无嵌套重试。新 Actor 策略缺少证据声明、声明未知视图、配成旧 Actor、启用累计任务时限等均拒绝。预检输出两项策略；新协议 batch 签名和 backend 元数据也保存两项策略。

新协议预检要求 `shared_config.json` 和 `skilladam.json` 均列在 manifest 的文件哈希中。已有的共享配置一致性、V25 源码冻结、运行时和镜像核对继续保留，不允许通过改旧配置或重写冻结清单迁移旧实验。

## 共享执行与不同优化机制

SkillAdam 的所有 Actor rollout 继续调用 V25 的 `actor.run()`。格式校验失败仅用于当前程序生成的临时修复；网络错误、API 超时、截断、空输出保持当前请求重试。它们共用每份程序的 6 次请求，不占 30 次执行额度；临时上下文、预算和恢复行为由共享 Actor 实现，不在接入层重写。

生成额度耗尽暂停并保存，不评分、不进入优化；已执行程序结果未知时不重复执行。所有阶段无标准答案或评分纠错反馈。详见 [V25 执行历史协议](EXECUTION_HISTORY.md)。

新协议的 `convert_record()` 先调用 V25 `facts.build_facts()`，完成原始请求审计并取得相同的执行证据，再序列化为 SkillAdam 的 assistant/tool 轨迹：

- assistant 只包含实际执行的完整响应。
- `harness_execution_not_actor_feedback` 包含实际执行记录、实际代码、执行计数、证据 ID 和视图标记。
- `actual_feedback_to_actor` 只包含真正提供给 Actor 的执行反馈，与完整日志分开。
- `post_execution_outcome_not_actor_feedback` 包含 V25 已限制范围的最终评分视图，不含标准答案值，也不伪装成 Actor 反馈。

上述转换发生在 SkillAdam 原生轨迹整理和 LLM 压缩之前。传给压缩器的说明明确：这是正式执行历史，省略了生成失败及临时格式修复；修复后的程序可能受到临时反馈影响，不能宣称这些是全部真实 API 请求。原始编号允许间隔，不据此推断程序失败次数。

SkillAdam 原有的确定性轨迹整理、LLM 压缩、96000 字符上下文阈值、16384 输出额度、Momentum、自适应编辑预算、原生 Gate 及调用流程均保持原实现。接入层统一的是压缩之前可使用的执行证据；两种方法之后如何表示、压缩和利用证据，仍允许不同。

## 归档与成本

原始 Actor 归档完整保留所有请求、响应、错误和临时反馈。`usage_records` 仍来自全部原始请求，独立进入 SkillAdam 的用量统计，不进入模型轨迹或评分元数据。网络失败计为一次请求；没有服务端用量时 Token 数保持未知，不能假定免费。

证据中的 `n_turns` 是实际执行次数，不是请求数。优化器模型输入不包含生成失败计数，也不从原始请求中补回被过滤的内容。

旧 Actor 历史策略对应 `raw_attempts_v1`；旧配置缺少 `actor_evidence_view` 时仍采用该旧视图。旧记录保持原转换语义，不删除旧失败记录，也不声称旧 Actor 没看过格式反馈。升级采用新的实验目录、配置与冻结清单，不在旧 campaign 中途切换。后续已补充统一配对准备入口，只生成配置和冻结材料，不初始化或启动 campaign；见 [PAIRED_PREPARATION.md](PAIRED_PREPARATION.md)。

## 离线验证

测试使用合成工作簿、预设 Actor／优化器响应和测试执行器，覆盖：

- 与 V25 过滤后的事实逐项一致、执行日志和反馈分离、评分视图保留、原始记录不被修改。
- 网络／截断／空响应／格式失败被过滤，但全部请求仍进入用量统计。
- 篡改真实请求时在转换前被审计拒绝。
- 历史与证据策略不匹配、重试配置不一致、配置未冻结时预检拒绝。
- 原生训练／baseline／candidate 流程、压缩、Patch、Gate 和 Momentum 继续执行，模型输入没有生成失败内容。
- 原始旧配置、旧轨迹和优化器重试测试继续通过。

预检测试的运行时与镜像响应是测试替身，不代表已经完成未来真实实验的环境预检。新实验仍需按其新冻结配置正式执行 `--check`。

本次验证结果：SkillAdam 接入层 18 项测试通过；包含该接入层及 V25 新旧协议的全套回归共 215 项全部通过。未调用真实模型，未启动真实训练或 Test。

新版 CLI 必须显式指定 `--experiment`，不再默认为旧实验目录。新配置使用 `reference_preparation` 引用 V25 的准备目录，避免为预检而创建真实 campaign；旧 `reference_campaign` 读取方式保留。
