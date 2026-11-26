# V25 Prompt 定稿包

这里保存运行资源的英文 Prompt 镜像与原始初始 Skill。2026-10-28 当前 Diagnosis 为 v5，允许多个独立修订和有依据的修复假设，仅输出 `revise` / `no_change`；见 [修改与兼容说明](../DIAGNOSIS_EVIDENCE_SCOPED_UPDATES.md)。当前默认 Preconditioner 已退回 v7；v8 以 `preconditioner_legacy_v8.md` 保留并支持归档读取，见 [回退与兼容说明](../PRECONDITIONER_V7_DEFAULT.md)。旧正文按版本另存，构造案例和下文迁移阶段的预算、状态描述不代表当前实验结果。

| 使用方 | 正文与组合方式 | 用户消息 |
|---|---|---|
| Actor | [actor_system.md](actor_system.md)，末尾注入当前 Skill；首次 Skill 为 [initial_skill.md](initial_skill.md) | [actor_initial.md](actor_initial.md)，按历史策略保留正式历史并追加 [actor_runtime_feedback.md](actor_runtime_feedback.md)，新策略的格式修复仅在临时上下文中 |
| Grouping | [grouping.md](grouping.md) 中替换一次执行上下文占位符 | `parent/runs` |
| Diagnosis | [diagnosis.md](diagnosis.md) 中替换一次执行上下文占位符 | `parent/runs/grouping` |
| Preconditioner | [preconditioner.md](preconditioner.md) 中替换执行上下文，再追加 [knowledge_only_view.md](knowledge_only_view.md) | `parent/plan/runs/memory` |
| Editor | [editor.md](editor.md) 中替换一次执行上下文占位符 | `parent/plan` |
| Replay | [replay.md](replay.md)，追加执行上下文、Knowledge Only 说明；v3/v4 附共享初始消息说明，v4 再附 [完全一致代码体解码说明](replay_exact_code_view.md) | v4 保留 `parent/diff/plan/shared_initial/pairs/runs/memory` 及配对邻接，仅相同 executed_code 使用可还原标记；旧 v1/v2/v3 视图保留 |
| Verifier | [verifier.md](verifier.md) | `context/targets/source_records`；上下文在 `context` 内提供 |
| Repair | [repair.md](repair.md) | 仅授权目标与限定来源的 `context/targets/source_records` |

Preconditioner 当前职责与引用边界见 [历史经验与计划审查定位](../PRECONDITIONER_ROLE.md)；旧构造案例中的 Grouping 仅供内部上游校验，实际模型输入不包含该字段。

公共资源：[execution_context.md](execution_context.md) 与 [method_validation_feedback.md](method_validation_feedback.md)。方法输出校验失败时，沿用原请求，再追加上一份完整响应和校验消息；该诊断只返回出错模块，不是 Actor 的运行反馈，也不是新的任务事实。只有显式输出校验错误走此路径，语义停止和技术故障不伪装成格式错误。

当前 Replay 学习 Prompt 为 `v25_replay_decision_fidelity_v4`，采用 v3 加局部修改的生产稿：围绕实际选择条件、优先级、回退和后续使用比较行为，检查重要区别进入 Knowledge 时是否被丢失，区分等分与因果排除；生产输出仍只有 `entries`，不引入诊断比较表。旧正文按字节保留为 [replay_legacy_v1.md](replay_legacy_v1.md)、[replay_legacy_v2.md](replay_legacy_v2.md) 和 [replay_legacy_v3.md](replay_legacy_v3.md)，旧归档按原版本读取。见 [v4 采用依据与离线兼容验证](../REPLAY_DECISION_FIDELITY.md)。此前诊断结果有改善也有残留错误，本次选择不宣称稳定性能提升；生产格式 v4 尚未进行模型实验。

输入视图与 Prompt 分别版本化：输入 v2 恢复 pairs 前置和配对邻接，v3 共享完全相同的初始 system 及 pair 内完整 user 消息序列。当前输入 v4 再去重与 response 代码体完全相同的 executed_code；路径适配记录保留完整原文。当前学习 Prompt v4 沿用这些视图及解码说明，旧视图和旧 Prompt 的请求仍按保存版本精确重建。表示层的历史离线校验见 [配对布局](../REPLAY_PAIRED_INPUT.md)、[共享初始消息](../REPLAY_SHARED_INITIAL.md) 和 [完全一致代码去重](../REPLAY_EXACT_CODE.md)。

## 参数与渲染

以下为本定稿包的审阅配置；原有预算、已确认项与推荐项的状态见[共享上下文](../SHARED_EXECUTION_CONTEXT.md)。这些参数用于构造文本样例，不代表已有 v25 实验配置。

| 模板字段 | 审阅值／来源 |
|---|---|
| `preview_rows / preview_columns / preview_cell_chars` | `5 / 20 / 40` |
| `preview_max_chars` | `100000`；完整生成预览后检查，超过则请求前报错，不截断继续 |
| `max_code_attempts` | `30` |
| `actor_max_output_tokens` | `16384` |
| `request_attempts_total / request_timeout_seconds` | `6 / 300` |
| `program_timeout_seconds / actor_task_timeout_seconds` | `600 / 600`，实际调用受剩余任务时间约束 |
| `runtime_error_detail_chars` | `3000`；仅保留错误详情前缀，不保留尾部 |
| `score_coordinate_limit / score_missing_sheet_limit` | `100 / 100`，仅优化模块的事后评分视图使用 |
| `allowed_libraries` | Python standard library, openpyxl, pandas |
| `formula_policy_description` | No additional formula recalculation; grading reads saved cell values with data_only=True. |
| `skill` | 本任务实际 Parent／Candidate／最终 Skill；不注入 Memory |
| `instruction / instruction_type / answer_region` | 数据集原始任务字段；`answer_region` 明确包含工作表与范围，不能只给无表名地址 |
| `workbook_preview` | 由当前输入生成并通过长度检查的完整有限预览，不含标准答案 |
| `error_category` | `format_error / execution_error / output_file_error` 之一；错误类别来自真实检查 |
| `exit_status` | 实际退出状态；未运行或无退出码时为 `not_executed / unavailable` |
| `error_detail_prefix / detail_truncated` | 真实错误的前 3,000 字符及是否截断；不由模型总结，不附评分器字符串 |
| `code_attempts_used / code_attempts_remaining` | 第 n 份已完成响应后为 `n / (30-n)`，只在允许继续时发送反馈 |
| `location / error` | 方法输出校验的位置和诊断；诊断沿用 v24 最多 600 字符，不混入 Actor 3,000 字符规则 |

执行上下文中另有三个 Actor 模板字段，分别插入上述系统、初始和运行反馈模板。展示模板时，配置参数填实值，任务动态槽位展示为 `[runtime field: 字段名]`；某一次实际调用的可见事实以该次保存的消息为准。不得把标注槽位当作真实任务值发送给 Actor。

每份原始模板仅按其原有槽位替换一次；先构造 Actor 模板视图和执行上下文，再嵌入方法 Prompt。插入的 Skill、任务文本、代码、日志及模板视图一律按文本保存，不递归解释其中的 `{{...}}`。方法用户消息为实际输入对象的 JSON；单元格地址不是证据 ID，无法用引用自动打开额外文件。

Actor 系统说明虽告知提交后会评分，但不带任何实际评分、错误坐标、标准答案内容或另一侧记录。模块共享上下文不能直接作为 Actor 的系统消息。

## 证据对象的最小模型视图

为使各 Prompt 可一致审阅，本包明确以下模型输入命名；代码迁移时再接入事实提取器，不能直接声称旧验证器已经支持这些字段。

- 每个 `run` 含 `ref/task_id/run_id/initial/attempts/outcome`。`initial` 保存 `ref` 和初始实际消息；`attempts` 每项含 `ref/request_messages/response/executed_code/executed/execution/feedback_to_actor`。程序执行状态、退出码、日志放在 `execution`，未执行时为 null。响应是完整原文；未执行的代码不虚构成 `executed_code`。
- `outcome` 含 `ref/status/termination/submitted_attempt/score/code_attempts/program_executions/api_requests`；`score` 在已评分时含 `hard/per_cell_pass_rate/correct_cells/total_cells/mismatched_cells/mismatched_cells_total/missing_sheets/missing_sheets_total`。列表长度和总量明确区分；技术中断时指标未定，不编造零分。
- `pairs` 显式给出 `parent/candidate/task_id/parent_result/candidate_result`，两侧结果含 `status/hard/per_cell_pass_rate/code_attempts/program_executions/api_requests`。构造输入前核对原始输入、实际 Skill、执行和评分条件，不能仅凭编号配对。实际消息引用同一 Parent 记录。
- `memory` 保留 `format/entries`；每项有 `id/knowledge`，Knowledge 有 `text/evidence`。格式标签沿用结构契约 `memory_knowledge_only_v1`，不表示依赖旧 benchmark。历史证据只能使用输入中已经给出的完整 ID。
- Verifier 的目标为 `target/knowledge`；Repair 目标另有 `issues`。`source_records` 仅包含按既定引用取出的原始允许证据，不给模型自行检索权。`context` 保存实际 Parent、Diff、执行上下文和已核对配对。

程序执行日志可由优化模块在其授权轨迹视图内看到；只有 `feedback_to_actor` 标为实际回传的内容，才能说 Actor 收到了它。`outcome.score` 从不出现在任何 Actor 消息中。

## 审阅材料

- [逐模块迁移说明](../PROMPT_MIGRATION_REVIEW.md)：保留内容、替换内容、禁止越界及源码依据。
- [构造案例与检查结果](../prompt_review/REVIEW_RESULTS.md)：包括渲染后的消息、各模块示例输入输出和边界案例。所有示例为人工构造，未调用模型或运行真实任务。

上述构造案例属于最初迁移审阅记录。当前资源已接入运行代码；文档及离线检查不证明模型效果；v8 修改时未启动实验；后续已单独完成单模块尝试并回退默认至 v7，结果与限制见 [回退说明](../PRECONDITIONER_V7_DEFAULT.md)。

2026-10-27：Actor 和共享执行上下文按 profile 渲染历史语义。`execution_only_v1` 的临时格式修复及执行证据边界见 [协议说明](../EXECUTION_HISTORY.md)；未设置该策略时维持旧的渲染文本。
