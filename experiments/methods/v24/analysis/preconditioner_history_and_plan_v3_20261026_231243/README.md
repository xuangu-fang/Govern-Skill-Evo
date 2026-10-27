# V24 Preconditioner 历史经验与计划审查重放

[V24 分析导航](../README.md) · [职责与引用边界](../../../../../docs/methods/v24/PRECONDITIONER_ROLE.md) · [分析结论](analysis.json) · [历史来源与调用参数](manifest.json) · [原完成记录](completion.json)

本实验仅重放 Preconditioner，记录为 **三例、四次请求、三个合法输出**。没有运行 Actor、Editor、完整训练或最终 Test，也没有发布新的 Memory。两例使用 v23.5 历史输入，不能算作 v24 新完成的训练轮次。

## 案例、选择与失败边界

| 案例 | 来源与 Memory | 原尝试及选择 | 阅读入口 |
|---|---|---|---|
| v24_smoke_R01 | v24 RC1 单轮 smoke R01，0 条 Memory | 001 成功，选择 001 | [汇总](v24_smoke_R01/summary.json) · [旧输出](v24_smoke_R01/baseline_output.json) · [有效输出](v24_smoke_R01/preconditioner/attempts/001/preconditioner.json) · [Effective Plan](v24_smoke_R01/preconditioner/attempts/001/effective_plan.json) · [Diff](v24_smoke_R01/preconditioner/attempts/001/actual_diffs.json) |
| inherited_v23_5_R03 | v23.5 正式运行 R03，2 条 Memory | 001 成功，选择 001 | [汇总](inherited_v23_5_R03/summary.json) · [旧输出](inherited_v23_5_R03/baseline_output.json) · [有效输出](inherited_v23_5_R03/preconditioner/attempts/001/preconditioner.json) · [Effective Plan](inherited_v23_5_R03/preconditioner/attempts/001/effective_plan.json) · [Diff](inherited_v23_5_R03/preconditioner/attempts/001/actual_diffs.json) |
| inherited_v23_5_R06 | v23.5 正式运行 R06，5 条 Memory | 001 截断，002 成功，选择 002 | [汇总](inherited_v23_5_R06/summary.json) · [旧输出](inherited_v23_5_R06/baseline_output.json) · [有效输出](inherited_v23_5_R06/preconditioner/attempts/002/preconditioner.json) · [Effective Plan](inherited_v23_5_R06/preconditioner/attempts/002/effective_plan.json) · [Diff](inherited_v23_5_R06/preconditioner/attempts/002/actual_diffs.json) |

R06 的 [001 响应](inherited_v23_5_R06/preconditioner/attempts/001/response.json)为 `finish_reason=length`、空正文，记录输出用量 32,768；保留 [error](inherited_v23_5_R06/preconditioner/attempts/001/error.json) 和 [validation](inherited_v23_5_R06/preconditioner/attempts/001/validation.json)。002 是原额度内的技术重试，不是追加授权或按语义好坏重采样。三例原请求上限均为 6，并不表示各执行了 6 次。

三个合法尝试各保留原 response、raw_output、parsed、规范化结果、Effective Plan、Diff 和 validation。各例 `preconditioner/result.json` 原样保留 `attempts/001`、`attempts/001`、`attempts/002`；没有改写编号或合并失败。请求开始时间、反馈上下文和 HTTP 状态等小型证据也分别保留。

## 分析结论与 Prompt

[实际发送的 Prompt](prompts/preconditioner_prompt.md)从原尝试逐字复制；四次保存的 Prompt 正文相同。本页只保留一份阅读副本，完整归档仍保留每次 Prompt。原源码快照位于归档中的 [contract.json](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/contract.json)，不以当前工作区源码替代它。

结构校验通过不代表语义判断可靠。原分析指出：无 Memory 的 smoke 案例提出依据不足的菜单顺序搜索策略，仍有可见性和规则优先级问题；有 Memory 的两例体现了历史与当前计划审查的结合。旧对照还包含 Grouping 输入移除等差异，不能宣称是严格的 v2/v3 Prompt 因果对照，更不能据此断言 Actor 成功率提高。详细依据、请求用量和局限保留在原 `analysis.json`。

## 完整输入与原始运行位置

完整归档位于 [artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/)。

| 案例 | 完整配置与实际输入 |
|---|---|
| v24_smoke_R01 | [replay_config.json](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/replay_config.json) · [expected_model_input.json](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/expected_model_input.json) · [完整尝试](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/preconditioner/attempts/) |
| inherited_v23_5_R03 | [replay_config.json](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/replay_config.json) · [expected_model_input.json](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/expected_model_input.json) · [完整尝试](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/preconditioner/attempts/) |
| inherited_v23_5_R06 | [replay_config.json](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/replay_config.json) · [expected_model_input.json](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/expected_model_input.json) · [完整尝试](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/preconditioner/attempts/) |

完整 input、model_input、messages、request、HTTP 原文和含完整 Memory 的 run.json 仅在归档保存；三份 replay_config 内含冻结环境材料，也归档保存。原 [运行日志](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/run.log)和[历史入口源码](../../../../../artifacts/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/run_replay.py)保留原文。归档包含本次整理前的全部 88 个原文件，便于完整读取，不依赖阅读副本补齐。

原 `manifest.json` 是历史实验来源记录，保留原文及当时记录的验证信息；它不是本次生成的迁移清单。本次没有重新计算其中的历史校验值，也没有重跑其记录的 121 项测试。

## 读取与运行入口

[archive_io.py](archive_io.py)仅使用标准库处理路径和 JSON，不导入实验模块：

- `resolve_path(path)` 接受仓库相对路径或绝对路径，将本分析目录的旧路径定位到完整归档；其他来源路径保持不变。
- `read_json(path)` 按该规则读取完整记录。三份历史 summary 的 `selected` 旧绝对路径不改写，应先经此规则定位，不能直接把阅读副本交给完整结果加载器。
- `selected_attempt(case)` 读取归档中的原选择记录，返回具备完整输入和 Memory 的尝试目录。它不重新校验模型输出、不调用模型，也不创建文件。

[当前运行入口](run_replay.py)将输出固定到对应 `artifacts/` 目录；所有阶段、请求和日志重定向也应使用该归档位置。入口仍在发现原 manifest 时拒绝重新初始化，因此此已完成运行不会被重新生成或重置额度；本次没有新增 resume 或追加请求功能。

入口的原来源文件哈希对照已改为内存中的原文字节比较，并移除对未来运行硬编码“121 项测试通过”的描述。该变更不改写历史 manifest、completion、汇总、调用预算或选择结果。原入口作为历史源码留在归档中，不作为当前启动入口。

本目录的阅读副本不是可恢复运行目录。只克隆 Git 不包含完整输入、Memory 和原始归档；v23.5 来源与 v24 RC1 smoke 原归档继续按原路径读取，v25 所依赖的 RC1 配置和 Prompt 未改动。

2026-10-27 本批仅整理文件、路径与导航；没有运行实验、测试或哈希函数，没有新增模型请求。
