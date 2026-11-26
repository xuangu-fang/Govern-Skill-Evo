# Diagnosis 单点修订与条件性下游验证

生产修订：仅 Diagnosis 两句 fallback 说明替换为主路径/回退路径均须满足任务要求的说明，版本 v4；Preconditioner v6 不变。

- `criteria.json`：模型调用前冻结的人工判据，不进入请求。
- `manifest.json`、`contract.json`：固定输入、原归档哈希和生产源码/Prompt 快照。
- `diagnosis_base_messages.json`：完整固定请求，用户消息与前次 R05 案例一致。
- `original_memory.json`：R05 原 Preconditioner 所见 Memory，保留历史缓存与常量回退经验。
- `diagnosis/attempts/`：原生每次请求、HTTP 响应、输出、校验和错误；最多六次总请求，不因语义结果不好重采样。
- `diagnosis_review.json`：人工门槛审查及所选输出哈希。只有明确通过才允许运行 Preconditioner。
- 若进入下游：`handoff.json` 和 `preconditioner_base_messages.json` 保存精确交接；`preconditioner/attempts/` 保存原生完整归档。

两个模块沿用原实验 API/模型/输出上限/超时/重试方法。没有 Actor、Editor、Gate、完整训练或 Memory 发布。
下游不是旧 R04 独立案例重跑：它使用同一 R05 的新 Diagnosis 计划和原 Memory，以观察是否主动重新引入违规 fallback。
一次链式观察不能估计整体错误率或隔离所有上游文本变化的影响。

离线验证：228 项通过（40.51 秒），命令：
`python -m pytest tests/skill_evolution/v25 --ignore=tests/skill_evolution/v25/test_executor.py -q`。
新增 v3 归档兼容用例确认 Diagnosis 单独改版时，Preconditioner 请求无需变更；最初旧测试假设两个 Prompt 同时变化，已修正此测试假设并重新完整通过。

## 运行期间源码漂移与保留预算续跑

前两次 Diagnosis 请求截断后，工作区 `baseline.py` 和 `evolution.py` 被本任务之外的操作修改。
原生冻结检查在第三次尝试、API 调用前拒绝继续。全部原记录保留，没有删除失败记录或回退工作区。
`source_snapshot/` 采用本次冻结的生产源码；隔离副本继续同一验证，`continuation_manifest.json` 固定其哈希。
保守地把原第三次本地失败也计为已使用尝试，Diagnosis 仅剩 3 个请求槽，不是重新获得 6 次。
后续 Preconditioner 如果满足门槛，仍为首次调用，保留原六次总请求预算。

## 前次独立运行器与本次原生运行器的差别

用户消息保持完全一致。本次调用生产原生 Diagnosis 运行器，会附加既有的 execution timeline 解释段；
前次四案例的独立运行器只替换了系统 Prompt 正文，没有附上该段。本次没有修改这项生产机制。
具体系统消息差异见 `system_prompt_comparison.diff`。因此与前次输出的对比不属于仅改变一句 Prompt 的严格消融实验；
本次主要回答当前版本能否生成合规计划，以及未改的下游是否重新引入违规 fallback。
