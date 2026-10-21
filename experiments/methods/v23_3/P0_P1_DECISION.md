# V23.3 P0/P1 决策

2026-10-20。**完成设计，停止于 P1；未进入 P2。** V23.3 以正式 V23 为代码基线，V23.2 仅作研究依据。模型调用、Actor/ALFWorld、Candidate Replay 均为 0。

## 文档入口

| 文档 | 内容 |
|---|---|
| [Baseline](V23_3_BASELINE.md) | Git 基点、真实数据流、接口与复用范围 |
| [Editor Patch Audit](V23_3_EDITOR_PATCH_AUDIT.md) | 八项审计、错误语义、99 项既有测试及单行限制 |
| [Method Design](V23_3_METHOD_DESIGN.md) | 三模块职责、方法增量与验收边界 |
| [Preconditioning Algorithm](V23_3_PRECONDITIONING_ALGORITHM.md) | 五类决定、完整伪代码、R04/R05/R06 走查 |
| [Patch Integration](V23_3_PATCH_INTEGRATION.md) | 最小模型侧适配、原编译器、归档和 Editor 入口衔接 |
| [Validation Plan](V23_3_VALIDATION_PLAN.md) | 三类对照、表示/决策消融、行为指标及数据隔离 |

## 十项最终回答

1. **新增机制是什么？** 按“实际编辑—相容条件—混合响应”限定具体行为关系的变换，再以必要关联的反事实检验限制附带修改。V23 已有宽泛的历史响应原则；新增的是有分支、可反驳的选择规则与落实过程，尚不是已验证性能创新。
2. **历史如何改变 Update？** 正例支持扩大或替换策略的探索方向，反例收窄触发/保证、保留仍有价值的选择，执行不稳阻止把旧文字重复加严当必然解；条件不相容则不直接迁移。M6 可支持重新分配搜索机会，同时反对用类别一次代替实例覆盖。
3. **Diagnosis/Memory 立即改吗？** 不改现有实现、Schema 或历史内容。P1-R 将未来本版 Diagnosis 的多行输出组织列为最小修订；Memory 仍冻结。Goal 已锁实现时需上游处理具体障碍；Memory summary 错误按 sources 限定使用。后续分别对照，不混改。
4. **如何决定方向、范围和关联？** 方向用五种决定表；范围必须可从 Actor 当前/两步历史判断；配套必须说明“保留旧要求为何使新选择矛盾或不可执行”。其他修改需自身问题动机。
5. **Editor Patch 能直接复用吗？** `apply_patch` 可以直接作用于 Update 字符串，固定 `SKILL.md` 是虚拟标签，不解析文档结构。无需新引擎；完整 Editor runner 则不能直接接收新归档。
6. **最小兼容是什么？** 原 Adjustment 外壳不变，模型侧 `to` 项用原 ID + Unified Diff `patch`，程序恢复 `id/text`；撤回沿用 `to:[]`，再调用原 `compile_effective_plan`。本版 loader 和薄 Editor 入口负责原始/派生归档衔接。
7. **为何不增加 D/S/C、role、依赖 Schema？** 它们描述决策关系；现有 basis/reason/checks 与多个同时 Adjustment 足以说明和落实。新字段本身不能证明配套必要或证据充分。
8. **怎样允许探索而避免附带承诺？** 给探索独立的问题动机、可执行触发、反例 Checks；新增出口/强禁令不因方向证据自动获得支持。不以修改长度限制探索，也不承诺程序能消灭语义越界。
9. **什么能保证、什么需验证？** 程序保证定位、基本应用冲突、结构/引用/Checks、Goal 与未改项保留、派生一致性；模型/人工评价判断事实支持、条件迁移和关联必要性；Replay 检验真实行为与收益。单行整行替换不能保护内部未意图修改的语义。
10. **P2 最少实现什么？** `normalize_update_patches`；本版 `messages_for/run_preconditioner/load_preconditioner`；薄 `editor.run_editor` 加载适配；必要离线契约/交接测试。P1-R 增加本版 Diagnosis 的多行输出组织说明及匹配的消息/归档加载边界。原补丁引擎、compiler、Diagnosis 数据契约/校验、Memory、Editor Prompt/模型接口、Replay 数据契约均复用。

## 已确定与未确定

已确定：基点 `08c442f202f05a25a0c30412ef89f8312df0c0f0`；一轮 Preconditioner 一次生成；无新增审核 Agent；不加哈希/锚点/role/依赖图；P2 先支持原 ID 的多 Update 修改与撤回，暂不支持结构拆合/新 ID；不修改正式 V23。

未确定：模型是否可靠执行决策规则、Patch 格式遵循率、是否减少附带承诺、历史增量是否稳定、策略是否提升任务表现、是否需要以后独立修正 Diagnosis/Memory。R04/R05/R06 只是开发走查；尚未选定新的未暴露 Train/验证任务清单，不声称完成泛化验证。

P2 工程完成不自动授权模型实验；本次更不自动进入 P2。后续应先完成原始响应→规范化 Adjustment→原 compiler→原 Editor 接口的离线验证，再按冻结协议开展实验。

## P0/P1 初始阶段检查（历史保留）

- 只新增本目录七份 Markdown 与 `src/skill_evolution/v23_3/README.md`，无 Python/Prompt/默认配置修改。
- 既有补丁和编译相关离线测试 **99 passed**；没有新增实现测试冒充新算法通过。
- Git 基线到 HEAD 的正式 V23 相关 Diff 为空；工作区原有 `docs/04_EXPERIMENT_LOG.md` 的 16 行删除保持。
- 已核查文档引用和范围；最终 Git 检查用于确认正式源码、测试与旧研究归档没有新增差异。未建立额外哈希保护体系。
- 全仓 `git diff --check` 报告既有 `docs/04_EXPERIMENT_LOG.md:6854` 的 EOF 空行；该文件是开始时已有修改，未修动。新文档另作独立空白检查，不把既有告警计为本次新增。

## P1-R：多行表示与更新粒度修订

单行 Original 使 Unified Diff 往往替换多个混合承诺，必须在 P2 前明确表示粒度。未来 V23.3 Diagnosis 直接生成多行 text：可依据不同证据独立判断的要求尽量分行，触发条件和动作保持完整。历史单行档案原样保留，不按标点自动拆分；三例只建立人工设计副本。

算法主线不变：历史响应先确定目标要求和必要关联，随后生成对应 Hunk；禁止先自由重写全文再反向生成 Patch。未改行由原应用器保留，但被改行仍可能夹带无据承诺，不能将行级保护当作语义保证。表示收益、Memory 决策增量和任务收益分别评价。

本轮 **119 项纯离线测试通过（65 项人工兼容 + 54 项既有）**，验证多行增删替换、多 Hunk、失败拒绝、未改行/Goal/其他 Updates/Checks 保留与合法更新，以及原 compiler/Editor 纯交接。没有实现正式 Preconditioner、归档 loader 或 runner，也未调用模型、Actor、ALFWorld、Replay、Gate 或最终 Test。

设计与纯函数兼容前提满足，可以据此开展未来最小 P2；本次停止，不自动进入。详见 [P1-R 决策及归档](p1r_multiline_001/P1R_DECISION.md)。初始五份文档在归档 before 中保留，差异以 Git no-index Diff 记录。
