# Diagnosis 回退路径的任务要求边界

2026-10-27，Diagnosis 升级为 `v25_diagnosis_fallback_requirements_v4`。
仅替换原任务要求段落中的两句替代实现说明；其余 Prompt、输出契约、证据范围不变。
Preconditioner 的源码、Prompt 和 `v25_preconditioner_self_check_scope_v6` 版本保持不变。

新增正文：

> Task requirements apply to both the primary path and every fallback. Propose a fallback only if it still satisfies those requirements; failure of an implementation does not authorize a weaker deliverable. For example, when a task requires a formula, storing its current numeric result is not an equivalent substitute. If no supported compliant alternative is available, retain the requirement and the unresolved implementation limitation rather than adding a fallback that violates it.

这不禁止合法的常量输出或其他 fallback，也不要求 Actor 遇到困难立即退出。
它约束的是提出的策略：实现困难不能单独授权改变所需交付物。
不增加模型阶段、输出字段、语义校验器或训练停止规则。

Diagnosis v3 正文保存在 `diagnosis_legacy_v3.md`，旧归档仍按原版本校验。
源 Prompt 与文档镜像、15 题配置模板同步；旧 campaign 不修改。

## 验证设计

复用前次四案例验证的 R05 Diagnosis 完整固定用户输入和原调用参数。
只替换为最新 Diagnosis 系统 Prompt，沿用原生格式校验和每阶段最多六次请求的技术/格式重试。
不得因语义结果不理想重新抽样。

先人工核查结构合法输出是否仍含违规 fallback；判据在调用前保存，不进入模型输入。
只有计划不再含违规 fallback，才调用未修改的 Preconditioner：使用新 Diagnosis 真实输出、
同一 R05 Grouping/Parent/执行证据，以及 R05 原 Preconditioner 输入中的完整 Memory。
不使用上一轮独立 R04 案例的 Memory，不编辑 Memory 或新计划，不调用 Editor、Actor 或完整训练。

如果 Diagnosis 仍违规，停止该验证链并报告；如果没有可交接的计划，不能借此宣布下游验证通过。
如果下游重新引入违规 fallback，才把该次输出作为“主动引入”的直接证据。
单次固定案例结果不证明整体模型效果或因果收益。

材料与结果保存在 `artifacts/methods/v25/analysis/diagnosis_fallback_validation_20261027_001/`。

离线验证结果：228 项 V25 测试通过（40.51 秒，排除 Docker 执行器专项测试）。
逐字差异检查确认正文只替换指定两句；修改前后哈希确认既有 Preconditioner 文件未变。
