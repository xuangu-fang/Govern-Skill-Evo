# v25.3 第二项优化设计：SpreadsheetBench 领域指导

本设计已于 2026-11-06 接入 v25.3 优化器提示词，修订标识为 `v25_3_spreadsheet_domain_v1`。完成离线验证，正式实验待后续启动。下文保留设计依据，实施记录见文末。

后续 `v25_3_roles_replay_v1` 调整了 Diagnosis、Preconditioner 和 Replay 的方法正文，共享领域块继续逐字保留。本文“原有全文保留”及字符数记录描述本阶段实施时的状态；最新职责与验证见[职责调整与迁移记录](ROLE_ALLOCATION.md)。

## 一、引入什么

| SkillAdam 来源 | 迁入 v25.3 的领域判断 | 本地适配 |
|---|---|---|
| [failure_types](../../../external/SkillAdam/skilladam/benchmarks/spreadsheetbench/prompts/failure_types.md) | 从规则缺失、规则本身有误、可见程序与已有规则不一致、工作簿读取不足、代码错误和其他原因几个角度解释失败。 | 用作备选解释；同一现象可能有多个解释。输入不足时可保持未定。单次语法或 API 错误可由现有运行反馈处理；只有当前证据支持可迁移的行为修正时，才提出 Skill Update。 |
| [failure_types](../../../external/SkillAdam/skilladam/benchmarks/spreadsheetbench/prompts/failure_types.md)、[success_types](../../../external/SkillAdam/skilladam/benchmarks/spreadsheetbench/prompts/success_types.md) | 检查源表与目标表、表头和数据边界、写入区域、决定年份或筛选条件的控制单元格，以及示例表或参考表的作用。成功轨迹也可呈现有效的数据定位、与现行规则相符的行为、或执行错误后的恢复。 | 按任务选择相关线索。程序可以读取完整原工作簿；Actor 在生成程序前看到的是有界预览。代码含有某个分支不证明该分支执行，答对也不证明某条规则起了作用。 |
| [skill_writing_policy](../../../external/SkillAdam/skilladam/benchmarks/spreadsheetbench/prompts/skill_writing_policy.md)、[iteration_example](../../../external/SkillAdam/skilladam/benchmarks/spreadsheetbench/prompts/iteration_example.md) | 允许把跨工作簿有效的 API 行为、参数或短代码惯用法写入 Skill。示例：追加新记录和覆盖指定区域是两种不同的写入意图；按任务意图区分追加和显式定位。 | 示例用于展示分析粒度。提出 Update 仍须引用当前 runs；不把示例当作证据，也不直接写入初始 Skill。泛化时去掉个案的工作表名、固定行号、答案、路径和评分术语。 |
| [metric_interpretation](../../../external/SkillAdam/skilladam/benchmarks/spreadsheetbench/prompts/metric_interpretation.md) | 区分程序执行并产出可打开文件、目标区域局部正确、整题全部正确。 | 以 v25.2 实际协议为准。Actor 可按格式、执行或无效输出反馈重试；有效工作簿提交后结束，错格和分数是事后证据。公式缓存影响评分，但任务要求公式时，静态值不能替代公式。 |

不引入逐题唯一分类、类型计数、固定 Skill 章节、代码片段配额、Stage0、Momentum 或双指标 Gate。类别名称只作为模型分析词汇，不进入 Plan、patch、事件或 Memory 的结构。领域先验可提示去哪里看，不能替代执行证据。

## 二、删减哪一层

| 旧内容与当前落点 | 建议处理 |
|---|---|
| v25.2 [Diagnosis 第 3 节](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/approved_prompts/diagnosis.md) 分散说明预览未展示、目标范围、重启、公式 fallback、删除无关工作表和固定行号。v25.3 [Diagnosis](../../../src/skill_evolution/v25_3/prompts/diagnosis.md) 已大幅缩短。 | 当前首段里“预览有限”“保留公式要求”“勿写入实例答案”分别归入执行上下文、任务语义、泛化边界，各留一个权威表述。删除重复提醒，保留直接引用当前证据、独立划分 Update、完整表达依赖与例外的条款。 |
| v25.2 [Preconditioner 第 2–3 节](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/approved_prompts/preconditioner.md) 混写工作表、范围、预览等领域例子与 D/S/C 判断。 | 领域块负责命名工作簿中的差异；方法段继续负责判断这些差异是否改变 Original 的方向、适用范围或与 Parent 的关系。保留“历史条件是否相符”“必要条件进入有效文本”“无相关 Memory 时也可判断”。无需恢复 v25.2 的旧长段。 |
| v25.3 [Replay](../../../src/skill_evolution/v25_3/prompts/replay.md) 的缓存值和坐标截断提醒，与[执行上下文](../../../src/skill_evolution/v25_3/prompts/execution_context.md)部分重合。 | 缓存读取、坐标列表上限、反馈时序等事实集中在执行上下文。Replay 留一条推理边界：仅凭错格无法判定公式缓存导致失败，要检查提交程序、实际反馈和同时变化的行为。 |
| v25.3 [Editor](../../../src/skill_evolution/v25_3/prompts/editor.md) 只有实施职责与 patch 合同。 | 建议沿用。Editor 可以表达有效 Update 已授权的 API 指导，但无须读取完整失败分类或另行诊断。 |

## 三、每个模块如何使用

建议 Diagnosis 和 Preconditioner 使用措辞一致的领域核心段，覆盖工作簿结构、可见行为、失败的备选解释与泛化边界。两者分别接一段本模块的使用说明。Replay 只使用与事件解释有关的短段。执行上下文承载环境事实。Actor 和初始 Skill 沿用 v25.2。

| 模块 | 用法与交付 |
|---|---|
| Diagnosis | 从全批 Parent 执行中寻找一个有证据的行为差异。例如，任务要求覆盖已知目标区域，而实际提交程序追加到了末尾。对照成功例、已有规则和其他可能解释；确有可迁移的修正才提出 Update。每项 basis 指向本批执行。 |
| Preconditioner | 对同一提案分别问：方向上，证据指向写入位置还是数据定位？范围上，约束是否仅适用于覆盖指定区域，合法追加场景是否保留？协调上，Parent 是否已有位置规则，相关 Memory 的条件是否可比？原文已充分则 KEEP；缺少适用条件则全文 REPLACE；已有完整覆盖且无行为增量则 WITHDRAW。动作来自判断，类别不预设答案。 |
| Editor | 若有效文本要求“覆盖已有区域时显式定位，追加任务仍可追加”，就在对应旧条款实施这一个 patch。无权自行扩大成“禁止 append”，也无权另加一项通用检查。 |
| Replay | 比较同题的实际提交程序、输出和评分。若写入方式和目标表选择同时变化且无法分离，保留 null；若有明确证据才关联到一条已实施的 Update。整题 hard 翻转仍是唯一事件入口，单元格指标辅助解释。 |

上述追加/覆盖场景是设计示例，不是归档案例。Gate、Memory 和四模块的可读输入、结构化输出、判定方式均沿用已实现的 v25.3 合同。

## 四、参考版本的取舍

[v26.1](../v26_1/PROMPT_REVIEW.md) 和 [v29.6](../v29_6/DOMAIN_GUIDANCE_REVIEW.md) 示范了如何用有来源的领域段替换原有过强或重复的自写段落，并按实际环境修正反馈与证据权限。[v27.2](../v27_2/README.md) 将领域线索与 Parent/Memory 的预条件判断分开。[v28.5](../v28_5/proposals/searchqa_guidance_20261105/README.md) 让 Diagnosis、Preconditioner 共用领域概念，Replay 按归因职责适配，Editor 沿用原职责。本设计采用这种按权限分配领域指导的方式。实际 SkillAdam 对照使用的领域材料可追溯到[首轮优化请求](../../../artifacts/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/campaign/logical_calls/000_iteration_patch_000/request.json)。

## 五、接入与离线验证

Diagnosis 和 Preconditioner 内嵌逐字一致的领域核心段，分别追加角色使用说明。Preconditioner 原有全文保留，D/S/C 判断、Parent/Memory 使用和动作输出仍位于方法正文。Replay 增加与事件解释有关的工作簿指导。各模块直接加载完整提示词文件。

Diagnosis 首段的预览、公式要求和实例泛化提醒已归入执行上下文与领域段。Replay 首段的缓存读取及坐标截断事实由执行上下文提供，事件解释段保留基于提交程序和实际反馈判断错因的要求。公式交付要求补入执行上下文，用于所有取得执行证据的模块。

Editor、优化器运行代码与 CLI 的字节身份经校验。当前提示词继续由现有 campaign 合同进行哈希绑定。此前准备的 campaign 若绑定旧提示词，会被现有恢复检查拒绝，应使用独立新目录。

新增领域指导使完整提示词长度增长。Diagnosis 从 1,198 增至 4,022 字符，Preconditioner 从 1,213 增至 4,436 字符，Replay 从 1,063 增至 1,713 字符。精简删除的是重复提醒，共享段提供了更具体的领域分析内容。

19 项离线测试通过，覆盖实际四阶段消息分配、领域块一致性、原方法文本及输出合同、执行上下文适配，以及原有合成工作簿的选择、Memory、恢复与请求预算。验证期间阻断 HTTP 和子进程调用，实际使用临时工作簿、预设模型响应和本地执行替身。

- [修改前提示词](revisions/spreadsheet_domain_v1/before/)
- [来源与受保护文件哈希](revisions/spreadsheet_domain_v1/manifest.json)，以及 [SkillAdam 许可](revisions/spreadsheet_domain_v1/SkillAdam_LICENSE)
- [离线核验结果与前后字符数](revisions/spreadsheet_domain_v1/offline_validation.json)
- [新增领域指导测试](../../../tests/skill_evolution/v25_3/test_domain_guidance.py)

复跑离线用例可使用 `python -m unittest tests.skill_evolution.v25_3.test_campaign tests.skill_evolution.v25_3.test_domain_guidance`。
