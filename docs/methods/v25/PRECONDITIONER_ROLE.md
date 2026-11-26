# Preconditioner 的历史经验与计划审查定位

当前默认 Prompt 为 `v25_preconditioner_evidence_decision_boundaries_v7`，输出契约仍为
`v25_explicit_references_v2`。v8 模板和实验记录保留，旧归档仍按原版本读取。
回退依据、验证与后续研究方向见 [v7 默认回退说明](PRECONDITIONER_V7_DEFAULT.md)；
v7 的具体判断边界见 [v7 修改说明](PRECONDITIONER_EVIDENCE_DECISION_BOUNDARIES.md)。
历史经验与计划审查职责、输入及显式引用语法不变。

## 职责与调整依据

Preconditioner 以 Original Updates 为调整对象，综合相关历史 Knowledge、当前引用
证据、Parent Skill 和 Actor 执行条件，判断并调整方向、范围、强度与协调关系。
利用历史实际编辑及行为响应进行预条件调整，仍然是其核心作用之一。

历史 Knowledge 可以揭示当前 Diagnosis 未发现的计划缺陷、帮助确定修正方式，
也可以在计划没有明显缺陷时支持更有希望的方案。这些作用与当前证据、计划逻辑
相互结合，不划分互斥的调整类别，不要求先审查缺陷再使用历史，不新增分类字段。

缺少相关历史 Knowledge，不妨碍纠正有具体依据的计划问题。问题可以涉及事实
前提、推理、过度推广、约束强度、执行可行性或要求间的冲突；必要时可以实质调整
D/S/C 或撤回 Update，不再限于局部事实纠错。每项调整仍须围绕原计划的问题与要求，
不能借助 runs 发现无关问题或重建 Diagnosis。

没有充分调整理由时 KEEP。没有 Memory、没有历史反例，不单独构成 KEEP 理由；
尚未经过验证也不意味着方案有缺陷。合理且可检验的方案可以留给 Candidate 验证。
不以修改条数、Memory 引用次数或全部 KEEP 与否衡量效果。

v8 曾进一步澄清 KEEP 的范围与强度依据、未知前提和保护条件，但当前默认正文已恢复
v7，不将这些新增要求继续描述为默认行为。历史设计及效果边界见
[v8 修改记录](PRECONDITIONER_SCOPE_AWARE_KEEP.md)。

## 输入、理由与契约

模型输入仍为 `parent`、`plan`、`runs`、`memory`，系统提示词继续提供 Actor 执行环境。
runs 是原计划的引用上下文，可用于审查已有主张、推理、范围、强度和可行性，以及
判断历史经验的适用性。历史仍使用 Knowledge Only 视图；历史来源 ID 不等于获得原始记录。

Grouping 不进入模型输入。内部归档和编译器仍保存分组，用于核对上游引用关系。
Plan 原文及 basis 不改写；已有 G 编号只保留上游出处含义，不能视为已查阅的分组证据。
引用校验继续拒绝新增不在原 Plan 中的分组编号。

reason 说明调整对象、具体依据和调整理由。使用历史时解释相关 Knowledge 如何发挥
作用；纠正计划时说明具体缺陷及证据或逻辑依据。二者可以共同说明，不强制引用无关
Memory，即使输入中存在 Memory。不要把纯当前证据纠错称为历史学习收益。

D/S/C、KEEP/撤回/补丁、`adjustments/checks`、每个原 Update 恰好一项、原 ID/Goal
和补丁应用规则保持不变。现有校验没有“修改必须引用 Memory”的要求，因此不放宽
校验器。它继续检查引用身份、结构与补丁，不自动证明理由充分或调整有效。

## 评分与任务要求的边界

任务要求边界修订的 Diagnosis 版本为 `v25_diagnosis_task_requirements_v2`，提出替代实现时须保留
任务要求；评分改善或评分未覆盖某项要求，均不能单独授权取消该要求。
对应 Preconditioner 版本为 `v25_preconditioner_task_requirements_v5`，迁移历史经验
或修改计划时遵守相同边界，收窄或移除违规 fallback，并使 Update、Goal、Checks
保持一致。必要条件必须进入 Update 正文，不能只在 reason 中表达谨慎。

当时两份正文只替换用户确认的两个段落，不增加任务专用规则、模型阶段或输出字段。
上一版 Diagnosis v1、Preconditioner v4 模板单独保留，旧归档按其版本校验；
Preconditioner v3 的既有兼容路径不变。新的运行仍需重新冻结配置。

## 版本与验证范围

当前 v7 默认回退及 v8 归档兼容验证见 [回退说明](PRECONDITIONER_V7_DEFAULT.md)。以下保留此前修订的验证记录。

当时仅更新 V25 Prompt、版本标识和文档，并做本地测试；不调用模型、不重放真实
轨迹、不启动训练。旧实验及配置保持原档，不能用新版本绕过已有 campaign 的冻结检查。
`history_primary_v2` 的两轮结果不属于新版本的行为验证。

本地测试覆盖无 Memory 和有 Memory 时不引用历史的 D/S/C 修改、历史与当前依据共同
参与修改、KEEP/撤回、有效引用及无效引用拒绝、输入投影、模拟流水线和归档重读。
这些测试只验证契约兼容，不证明模型能够识别真实计划缺陷；模型行为验证留待单独授权。

此前 history_and_plan_v3 验证结果：41 项通过（`test_preconditioner_context.py`、`test_configuration.py`、
`test_pipeline.py`、`test_timeline.py`）。使用预设响应和本地模拟执行，无真实模型请求。

2026-10-27 任务要求边界修订验证：V25 离线测试 194 项通过（未运行
`test_executor.py` 的 Docker 执行器专项测试）。另只读重载 `_007` R04 的
Diagnosis → Preconditioner → Editor 归档链，验证旧版本仍按旧模板校验。
两份当前 Prompt 与文档镜像一致，正文差异仅在确认的两个段落区域。
未调用模型或启动训练；以上结果不证明模型行为已改善。
