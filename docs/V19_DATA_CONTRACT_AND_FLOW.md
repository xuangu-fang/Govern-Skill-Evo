# v19 第 1 步：数据契约与流程边界

日期：2026-09-21。状态：设计契约已确定，尚未实现运行时类型、校验器、回放、归因模型、记忆存储或调度。本文为后续第 2–7 步的实现依据，不代表闭环已经运行。

## 1. 目标与本步范围

v19 在持续经验记忆中关联具体 edit 与训练配对回放证据，让下一轮生成能够修正已接受包中的局部问题，并重新利用被拒绝包中的潜在有效方向。Parent/Current 与 Candidate 的配对比较及 Gate 并非本方法独有能力；这里的工作重点是 edit-level 证据的持续保存与跨轮使用。

本步确定记录结构、模块职责、信息权限、状态关系和验收示例。后续新增实现、Prompt、配置和产物使用 v19 命名空间。不修改 v18 源码、Prompt、冻结配置、历史实验产物或成绩；允许后续 v19 调用经审查的现有公共函数，但不得通过改写 v18 或全局 monkeypatch 改变其行为。

首版保持以下方法边界：

- Candidate 仍由完整 edit plan 原子应用产生，Monitor 仍对整包作 ACCEPT / RETAIN 决策。
- 新增 Candidate 在本轮全部 Evolution 训练任务上的执行，配对当轮 Parent 已有执行；包括原本成功的任务。
- 归因只形成可反驳的效果关联假设，不作为单个 edit 的直接晋升授权。
- Memory 通过下一轮 Diagnosis 影响新计划，不能直接修改 Skill、越过 Compiler / Editor 或改写 Gate。
- 暂不增加逐 edit 消融、额外训练保护样例、多组对照或新的 Gate 门槛。

## 2. 每轮流程与模块职责

令当前 Skill 为 S_t，历史记忆为 M_t，候选为 C_t，整包决策为 g_t。

1. **Parent 执行**：S_t 在 Evolution 任务上产生当前训练经验。
2. **Grouping 与记忆检索**：组织当前经验，检索相关历史 edit、配对证据与归因；形成有明确历史/当前标识的 Diagnosis 输入。
3. **Diagnosis → Compiler → Editor**：对当前 S_t 重新诊断与授权，生成完整计划和 C_t；冻结本轮 EditRecord 清单。
4. **Candidate 回放**：C_t 从相同任务初始状态重新执行全部 Evolution 任务；形成 ReplayPair 清单。不是对旧轨迹重新评分，也不是固定重放 Parent 的用户话语。
5. **归因**：只读取学习侧资料，将行为变化、结果变化与一个或多个 edit 关联，形成 AttributionRecord；此时不读取 Monitor 决策，避免将接受/拒绝当作效果标签。
6. **Monitor / Gate**：独立比较 S_t 与 C_t，仅向学习侧提供 COMPLETE 状态和 ACCEPT / RETAIN 决策。
7. **提交**：无论 ACCEPT 还是 RETAIN，都提交本轮记忆。ACCEPT 时 S_(t+1)=C_t；RETAIN 时 S_(t+1)=S_t。下一轮只读取已提交的 M_(t+1)。

本轮回放与归因只影响下一轮，不在 Monitor 前根据回放结果偷偷重写 C_t。若要修正，本轮候选保持原样，下一轮产生新的候选和 edit ID。

## 3. 信息权限

| 信息 | 私有执行/审计侧 | 归因、Memory 学习投影、Diagnosis | 执行 Agent |
|---|---|---|---|
| 当前/历史 Skill 与精确 edit 文本 | 可保存 | 可读，历史文本不是现行规则 | 只部署当前选定 Skill |
| Evolution 中实际可见的政策、工具 schema、对话和工具结果 | 可保存 | 可读，保留原可见范围和上下文 | 按任务正常可见 |
| Evolution 结果标签 | 可保存完整评分产物 | 仅 success / compliant 两个布尔值的 Level-0 投影及确定性派生量 | 不额外暴露 |
| 任务真实 ID、初始/最终私有数据库、完整运行配置 | 可保存并校验配对 | 仅不带 benchmark 语义的任务别名、必要版本引用；不传私有内容 | 不额外暴露 |
| 隐藏任务脚本、预期动作、evaluator 原因/内部机制、隐藏 family 标签 | 可保存 | 禁止，不能借摘要或 Memory 间接传入 | 不额外暴露 |
| Monitor 逐题轨迹、标签、聚合分数和失败原因 | Monitor 私有保存 | 禁止 | 禁止 |
| Monitor 完成状态、整包 ACCEPT / RETAIN | 可保存 | 仅记忆提交/后续检索使用；不是 edit 效果证据 | 不额外暴露 |

学习投影采用白名单构造，不能把私有结果对象删几个字段后直接序列化。Memory 文本、归因解释和历史 Diagnosis 都是学习器生成的假设，不得升级成 policy、真实机制或原始观测。

上下文中的工具结果只包含 Agent 当时实际见到的部分。不得把完整数据库差异伪装成“工具观察”。事实漂移或对话差异可以作为不确定性说明；自动检查若读取隐藏任务事实，其私有结论不进入 learner，也不改变官方标签。

## 4. 通用引用约定

所有以下记录使用各自的 `schema_version`，首版后缀为 `v19.1`。运行时接口实现前，本文的字段表是规范；示例是说明材料，不是模型输出或可直接加载的运行产物。

- `run_id`、`round_id`：运行和轮次标识；任何跨轮记录必须带来源，不依赖文件目录推断。
- `skill_ref`：包含 `skill_id`、`sha256`、`text_ref`。摘要按原始 UTF-8 字节计算，保留换行及空白；允许空 Skill。
- `edit_id`：在一次运行内唯一且不可变，由运行、来源轮次、计划摘要和原始单元索引共同绑定。修改内容或上下文改变时产生新 ID。
- `task_ref`：同一运行中稳定的 Evolution 任务别名，与真实 ID 的映射只在私有侧保存；不能以 GPC/CTRL 等 family 名作学习侧别名。
- `pair_id`：绑定运行、轮次、任务别名和采样索引；两侧角色为 PARENT / CANDIDATE。
- `evidence_ref`：绑定来源轮次、pair、角色、轨迹与事件位置；两侧事件不要求一一对齐。结果标签使用单独 `supervision_ref`。
- `current_rule_ref`：只指向当前 Parent 的精确块与位置。历史 rule ref 只作历史定位，不能直接授予本轮修改权限。
- `artifact_ref`：包含产物 ID 和摘要；落盘后恢复必须重新核验绑定和摘要，不能把历史 VALID 字样当作当前已验证对象。

所有记录都保留 source 与引用类型。不同类型的引用不可互换；历史摘要不能被解析成原始轨迹证据。跨轮语义相似只产生可能关联，不自动合并 edit 身份。

## 5. EditRecord：修改事实

一条记录对应一个实际完成应用的 edit unit。它不声明效果好坏，也不声明已经部署。Candidate 尚未成功产生时，计划仍是待完成产物，不发布完整 EditRecord 清单。

| 字段 | 类型 / 约束 | 含义 |
|---|---|---|
| schema_version | `edit_record_v19.1` | 版本 |
| edit_id / run_id / round_id | 非空标识 | 唯一身份与来源 |
| parent_skill_ref / candidate_skill_ref | Skill 引用 | 精确版本绑定 |
| plan_ref | 产物引用 | 已验证完整计划 |
| edit_unit_index | 非负整数，保留原始索引 | 不因过滤 DELETE 等操作重新编号 |
| operation | ADD / REPLACE / DELETE | 实际操作 |
| target_blocks | 块记录数组 | 每项有历史 rule ref、原始行范围、原文；全部坐标基于本轮 Parent |
| after_text | 字符串 | ADD/REPLACE 的实际应用文本；DELETE 固定为空字符串 |
| source_gap_refs | 非空引用数组 | 来源 Diagnosis 与 gap 索引 |
| source_evidence_refs | 引用数组 | 来源 gap 所依据的可见证据 |
| related_history | 关系数组，可空 | `prior_edit_id`、`relation`、`basis_refs`；relation 为 REVISES / RETRIES / REVERTS |

操作约束：ADD 没有目标块且 after_text 非空白；REPLACE 至少一个目标块且 after_text 非空白；DELETE 至少一个目标块且 after_text 为空。REPLACE 不得用空文本绕过 DELETE。记录的文本必须与确定性应用结果一致；多个 edit 共同重建精确 Candidate，不允许账本与实际产物脱节。

粒度沿用 edit unit：一个 REPLACE 可能覆盖多个原始块，一个块可能含多个语义。局部有害但仍有有效内容时由后续 REPLACE 修订，不把整个单元强制二分为“保留/删除”。

`related_history` 记录新修改试图如何处理旧修改，不证明已成功纠正；“重试”也不意味着逐字重放旧文本。

## 6. ReplayPair：配对观测

一条记录对应一轮一个 Evolution 任务的一次 Parent–Candidate 配对。运行私有绑定与学习投影分开。

**私有配对绑定**必须记录并核验：真实任务与固定 split 清单、两侧初始状态摘要、环境/任务版本、模型配置、实际 Simulator prompt 版本、预设 seed、采样索引、两侧 Skill 摘要和原始产物摘要。两侧初始状态、环境和配置须匹配，允许变化的实验因素为部署的 Skill；同 seed 不保证同轨迹。

**学习侧 ReplayPair 字段：**

| 字段 | 类型 / 约束 | 含义 |
|---|---|---|
| schema_version | `replay_pair_v19.1` | 版本 |
| pair_id / run_id / round_id / task_ref | 非空标识 | 来源与配对身份 |
| rollout_index | 正整数 | 预设采样索引 |
| parent / candidate | 两个 Observation | 对应角色的观测 |
| outcome_transition | `{success_delta, compliant_delta, parent_state, candidate_state}` | 程序由两个标签确定，不由模型生成 |

`Observation` 包含 `skill_ref`、`context_ref`、`trajectory_ref`、有序可见事件及其 evidence_ref，以及 `supervision={success: bool, compliant: bool, level: 0, supervision_ref}`。context_ref 解析到当时的可见 policy 和公开工具 schema。历史观测必须标出使用的 Skill，不能伪装成当前 Parent 的运行。

状态映射为 CS（成功合规）、CF（失败合规）、VS（成功违规）、VF（失败违规）；两个 delta 均为 Candidate 布尔值减 Parent 布尔值。不得用单一加权分数抹去“成功上升但合规下降”等冲突。

不完整执行或评分失败不得填 false，也不能发布 COMPLETE 配对；错误单独留在私有运行状态中。本轮完整回放要求覆盖冻结的全部 Evolution 任务，不能按收益筛选配对。

## 7. AttributionRecord：效果关联假设

归因模块输入为本轮 EditRecord 全集、ReplayPair 全集、两侧 Skill 和学习侧上下文；不读取 Monitor。输出必须覆盖本轮全部 edit，可用 UNKNOWN 显式表示没有可支持的判断。

| 字段 | 类型 / 约束 | 含义 |
|---|---|---|
| schema_version | `attribution_record_v19.1` | 版本 |
| attribution_id / run_id / round_id | 非空标识 | 记录身份 |
| edit_ids | 非空、无重复的 edit ID 数组 | 一个或多个共同关联的 edit |
| effect | BENEFICIAL / HARMFUL / MIXED / NO_OBSERVED_EFFECT / NOT_EXERCISED / UNKNOWN | 带适用范围的假设，非永久评分 |
| evidence_level | UNRESOLVED / OUTCOME_ASSOCIATION / BEHAVIOR_SUPPORTED | 当前证据等级，不表示已做因果干预 |
| observations | 关联观测数组 | 见下文 |
| interpretation | 文本 | 修改内容与行为变化之间的解释 |
| applicability | 文本 | 已观察到的条件和适用范围 |
| alternative_explanations | 文本数组 | 其他 edit、对话差异、随机性等；明确仍未知的部分 |
| uncertainty | 非空文本 | 不使用未经校准的数值置信概率 |
| suggested_followup | PRESERVE / REVISE / CONSIDER_REMOVE / RETRY / DEFER | 给下一轮 Diagnosis 的建议，不是编辑授权 |

每条 `observations` 包含：`pair_id`、`relation`（SUPPORT / COUNTEREVIDENCE / CONTEXT）、`parent_evidence_refs`、`candidate_evidence_refs`、两侧 `supervision_refs` 和 `behavior_comparison` 文本。

约束与解释：

- 所有引用必须在指定 pair 和角色内解析。BEHAVIOR_SUPPORTED 的支持项必须引用两侧实际行为；不能只引用最终标签或 Agent 的因果自述。
- OUTCOME_ASSOCIATION 只说明整包变化与结果共现；不能凭此确认某 edit 是原因，须保留混杂说明。
- 只有 UNKNOWN 可以没有 observations。NOT_EXERCISED 需有覆盖范围说明；没找到证据时用 UNKNOWN，不把未检索到等同于未触发。
- NO_OBSERVED_EFFECT 表示相关已观察范围内未测得结果收益/伤害，不表示“无作用”；持平时仍可记录行为变化。
- 若不同任务、条件或结果维度给出相反方向，保留逐项证据并使用 MIXED，不能只保留净收益。
- 一条归因涉及多个 edit 时，表示联合关联未拆开；不向每个 edit 复制独立因果功劳或责任。
- 同一 edit 可有多条不同范围的记录；不能通过新增记录静默删除先前反证。
- 归因通过结构/引用验收不意味着解释正确。建议 DELETE 仍需下一轮满足独立的 SHOULD_REMOVE 证据门槛。

## 8. RoundMemoryRecord 与下一轮消费

记忆采用“不可变轮次记录 + 可重建检索视图”。第 1 步不指定数据库或检索模型；原始证据链和行为约束已经确定。

| 字段 | 类型 / 约束 | 含义 |
|---|---|---|
| schema_version | `round_memory_v19.1` | 版本 |
| memory_record_id / run_id / round_id | 非空标识 | 本轮记忆身份 |
| previous_memory_ref | 记忆引用或 null | 首轮为 null，后续形成提交链 |
| parent_skill_ref / candidate_skill_ref | Skill 引用 | 本轮比较版本 |
| edit_refs / replay_pair_refs / attribution_refs | 完整产物引用清单 | 指向本轮全部记录，不只保存效果好的部分 |
| gate_decision | ACCEPT / RETAIN | 完成的整包决策；不复制 Monitor 分数或原因 |
| retained_skill_ref | Skill 引用 | ACCEPT 指向 Candidate，RETAIN 指向 Parent |

“随整包接受”是来源事实，不是当前是否仍存在，也不是是否有益。当前检索视图必须分别表达：

1. 来源轮次的 gate_decision；
2. 对应内容在当前 Parent 的 `binding_status`：EXACT / PARTIAL / ABSENT / UNRESOLVED；
3. 当前可引用的规则块及绑定依据；
4. 历史效果记录、反证和后续 REVISES / RETRIES / REVERTS 关系。

binding_status 说明文本/谱系对应程度，不表示好坏。DELETE 不产生“仍存在的新增规则”；其视图检查被删内容是否又出现，结合操作解释。REPLACE 的部分内容保留时不得误报整体 ABSENT。找不到可靠对应时使用 UNRESOLVED，不猜测坐标。

下一轮 `MemoryContext` 包含当前 Parent 引用、已提交记忆头、选中的 edit/归因记录、历史配对证据、当前规则绑定及检索来源清单。模型只读其学习投影。选中一条归因时须能解析其支持与反对证据；不能仅传“这条规则不好”的无源摘要。

消费规则：

- 记忆进入 Diagnosis，历史建议必须结合当前 Parent 重新形成 MISSING / NEEDS_REVISION / SHOULD_REMOVE。
- 历史未晋升 edit 不能假定存在于 Parent；已接受 edit 也可能后来被修订或移除。
- 检索不能只在本轮失败组上触发；历史未决问题和有负面证据的现存修改需要复查入口。未再次出现不等于已解决。
- 旧问题是否解决须有相关场景的后续行为证据，不能仅由 Gate ACCEPT 或新 edit 已生成决定。
- 输入预算不足时须显式记录选取范围；不可截断成误导性单边证据。必要时缩小完整证据单元的数量或停止阶段，不默默丢弃反证。

## 9. 提交、停止与恢复

- 本轮记忆仅在 Candidate、完整回放、归因和 Monitor 均完成后进入可消费提交链。一个逻辑提交同时绑定 retained Skill 和 Memory 头；下一轮不得只看到其中一半。
- ACCEPT 与 RETAIN 都提交同样完整的训练证据。RETAIN 不清空记忆，也不把其中 edit 自动标记为 HARMFUL。
- 模型/工具错误标记 INCOMPLETE，保留阶段产物。归因失败不能转换为“有效的 UNKNOWN”，也不能跳过记忆继续晋升或进入下一轮。
- 恢复必须核对输入、版本、产物摘要和已有提交。完整阶段复用；同一个轮次/提交不能重复追加。即使 Monitor 已算完，提交未完成前也不开始下一轮。
- NO_UPDATE / UNABLE 沿用停止语义：保存已有阶段记录，不伪造 Candidate、配对回放、归因或 Gate 决策；已提交历史记忆保留。历史检索应在判定无更新之前发生。
- 本步不决定正式轮数、seed 数或是否启动真实模型调用；这些在第 7 步配置与调度中单独确定。

## 10. 分步交付与第 1 步验收

| 后续步骤 | 使用本契约实现的部分 |
|---|---|
| 第 2 步 | EditRecord、精确文本重建绑定和跨轮谱系 |
| 第 3 步 | ReplayPair、私有配对校验、训练学习投影和恢复 |
| 第 4 步 | AttributionRecord、归因 Prompt、完整覆盖及引用验收 |
| 第 5 步 | RoundMemoryRecord、提交链、检索视图和 MemoryContext |
| 第 6 步 | Memory 接入 Diagnosis、当前 Parent 重新授权、Editor 来源保留 |
| 第 7 步 | v19 独立调度、阶段恢复和多轮 Pilot |

配套 [契约示例](V19_DATA_CONTRACT_EXAMPLES.md) 使用构造数据展示两条主要纠偏路径，以及混合证据和版本状态。它们不是 benchmark 实验结果，也不是可跳过校验的运行输入。

本步验收：三类核心记录和轮次提交关系已定义；整包状态与局部效果分离；支持反证、未知及联合关联；明确训练/Monitor 边界；两个主要示例均能追溯到 edit 和配对证据；未实现或运行后续阶段。

## 11. 依据

- [v18 设计](V18_SKILL_EVOLUTION_DESIGN.md)：完整计划原子应用、Diagnosis 授权与 DELETE 边界。
- [v18 Compiler 契约](V18_COMPILER_CONTRACT.md)、[Editor 契约](V18_EDITOR_CONTRACT.md)：edit unit 粒度、精确 Parent 绑定及受限编辑。
- [v18 × benchmark v4 正式协议](V18_BENCHMARK_V4_FORMAL_PROTOCOL.md)、[四轮分析](V18_V4_FOUR_ROUND_ANALYSIS.md)：既有流程及局部退化、随机性和事实漂移的解释边界。
- 本次对话确认的 v19 七步计划：先确定契约，再逐步实现；不改 v18，不先开展多组对照设计。
