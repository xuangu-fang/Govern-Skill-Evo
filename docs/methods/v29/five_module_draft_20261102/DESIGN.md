# v29 DocVQA 五模块 Prompt 草稿

2026-11-02 试跑后确认：后续运行采用 Actor 32768、Grouping/Editor 16384、Diagnosis/Preconditioner/Replay 32768；超时沿用 300 秒。正式配置为 `experiments/configs/v29_docvqa_optimization160.json`。首批试跑已完成；按用户要求，其临时配置、执行归档及专用验收输出已删除。

2026-11-02 试跑调整：按用户要求参照 v27，Actor 输出上限改为 49152；五模块临时采用 Grouping/Editor 16384、Diagnosis/Preconditioner/Replay 32768，超时均为 300 秒。仅试跑第一批 15 题，正式预算仍待试跑结果确定；下文未启动说明描述此前离线阶段。

状态：2026-11-02，供审阅的设计稿。五份完整英文 Prompt、中文修改说明和合成输入输出均在本目录；没有接入 v29 运行代码，没有调用模型。示例输出为人工构造，不是实验结果。

后续实现进展：第一阶段 Actor/评分/文本证据、第二阶段五模块/Plan/Replay/Memory，以及第三阶段训练主循环、调度恢复和 Parent/Memory 联合发布均已通过离线验收，见[实现说明](../../../../src/skill_evolution/v29/README.md)与[第三阶段说明](../CAMPAIGN_IMPLEMENTATION.md)。本目录 Prompt 已安装并包含响应去重修订。五模块预算继续待定，未调用真实模型、训练或 Test；设计及合成示例保留为审阅依据。

本轮已落实五组局部修订及三处同类措辞同步调整：Grouping 不提出视觉原因假设；区分视觉适用机会未知与不存在；Checks 限于可观察证据；Editor 清理选择题残留并明确无图不构成单独阻塞；Actor 转述在历史修订中保留归属。Grouping 公共假设措辞、Diagnosis 元素外解释说明、Replay 转录说明也已同步修正。未改变模块职责、输入字段、D/S/C、补丁合同、Memory 修订方式或 Gate。

## 1. 设计依据与阅读入口

以工作区当前 v28 已接入的五模块 Prompt 为底稿，包括现行 Replay 的完整消息共享表；不是仅复制 v28 最初的历史草稿。只替换 DocVQA 的任务、评分、Actor 协议和文本证据含义。v28 的模块职责、D/S/C、Plan、精确补丁、引用、Knowledge Only、多 Knowledge MemoryEntry、整条修订及发布边界保持不变。

| 模块 | 完整英文 Prompt | 相对 v28 的逐行差异 |
|---|---|---|
| Grouping | [grouping.md](prompts/grouping.md) | [grouping.diff](diffs/grouping.diff) |
| Diagnosis | [diagnosis.md](prompts/diagnosis.md) | [diagnosis.diff](diffs/diagnosis.diff) |
| Preconditioner | [preconditioner.md](prompts/preconditioner.md) | [preconditioner.diff](diffs/preconditioner.diff) |
| Editor | [editor.md](prompts/editor.md) | [editor.diff](diffs/editor.diff) |
| Replay | [replay.md](prompts/replay.md) | [replay.diff](diffs/replay.diff) |

每份 Prompt 都是独立完整的 system 文本，包含其需要的任务边界、Actor 基础协议、运行约束、职责和输出合同；不需要在运行时拼接其他草稿。`context/` 中的两份文件仅便于审阅共同内容。

来源：

- [v28 当前五模块目录](../../../../src/skill_evolution/v28/benchmarks/searchqa/prompts/)。
- [v28 当前输入构造](../../../../src/skill_evolution/v28/benchmarks/searchqa/prompting.py)与[Replay 消息共享视图](../../../../src/skill_evolution/v28/benchmarks/searchqa/replay_input_view.py)。
- [SkillOpt DocVQA Actor](../../../../external/SkillOpt/skillopt/envs/docvqa/rollout.py)与[初始 Skill](../../../../external/SkillOpt/skillopt/envs/docvqa/skills/initial.md)。
- [SkillAdam DocVQA 评分与答案抽取](../../../../external/SkillAdam/skilladam/benchmarks/docvqa/evaluation.py)。

## 2. 已确认的 Actor 与评分语义

完整 Actor System/User 模板、图文请求、执行及评分协议已集中整理为[独立设计稿](../actor_execution_scoring_draft_20261102/DESIGN.md)。下文保留五模块理解执行证据所需的摘要。

Actor 使用 DeepSeek 官方 Chat Completions 接口、`deepseek-flash`，thinking enabled、reasoning_effort=medium、temperature=1.0、max_tokens=32768。每题一个模型轮次，无工具；原图通过 user 图片内容发送，image_detail=auto。请求/连接超时为 300/10 秒，技术错误和 length 共用六次总尝试，正常 stop 的答错或格式问题不触发补答。

基础 system 文本沿用 SkillOpt 与 SkillAdam 共同的 DocVQA 模板，见 [actor_base_protocol.md](context/actor_base_protocol.md)。实际 Skill 在 system 中通过 `## Skill` 段注入；五模块看到的每条执行 system 文本必须保留该执行真正使用的 Skill。Candidate 执行不能被标成使用 Parent Skill。

答案采用 SkillAdam 的最后一个完整 answer 元素；无完整元素时取最后非空行。缺少标签不直接判零分。评分只做小写化和空白合并，保留标点、冠词、单位及数字格式。对每个参考答案计算归一化字符编辑距离，距离大于等于 0.5 时为零，否则为 1 减距离；多参考答案取最高 ANLS。hard=1 当且仅当 ANLS>=0.999。

Gate 沿用当前同批 Candidate hard 成功数严格增加才接受；ANLS 只用于解释和报告。成功数持平而 ANLS 上升仍 RETAIN；成功数增加而平均 ANLS 下降仍 ACCEPT。这里不增加另一套双指标接受规则。

## 3. 完整文本证据与模块输入

Actor 看图，五个优化模块都不接收图片。四个分析模块的完整文本证据包含：问题、Actor 完整普通响应、预测答案、所有训练参考答案、hard/ANLS、该执行的实际 Skill。普通响应不摘要、不截断；另行生成的 OCR、图片说明和视觉分析不加入输入。

Actor 普通响应自身可能包含对图片的描述或转录，这部分原文必须完整保留并标明由 Actor 陈述，不能升级为独立核实的图片内容或内部视觉过程证据。图片路径和占位文字仅标识任务文件，不提供读图能力；优化模块不通过这些路径打开图片。

| 模块 | user JSON 顶层字段 | 执行与历史范围 |
|---|---|---|
| Grouping | `parent, runs` | 完整 Parent Skill、当前全部 Parent 文本执行；无 Memory |
| Diagnosis | `parent, runs, grouping` | 完整 Parent Skill、当前全部 Parent 文本执行及分组；无 Memory |
| Preconditioner | `parent, plan, runs, memory` | 独立提供完整 Parent Skill；Original Plan；Plan 直接引用选中的完整 Parent 文本执行；全部活跃 Knowledge Only |
| Editor | `parent, plan` | 仅完整 Parent Skill 与 Effective Plan；basis 只是来源标识 |
| Replay | `parent, diff, plan, shared_initial, runs, pairs, memory` | 当前整批 Parent/Candidate 配对文本证据、实际修改、有效 Plan、活跃 Knowledge Only；不含 Gate 决策 |

Preconditioner 保留“扫描完整 Original Plan 的直接执行引用选 run”的规则，不只扫描 basis。Group ID 不自动展开全部组员，也不赋予读取 Grouping 描述的权限。Parent Skill 始终是独立输入，不依赖 runs 是否选中某条执行；它用于判断重复、冲突、必要性和协调。此处只是明确 v28 已有字段的职责。

Editor 不接收图片、执行、评分、参考答案、Memory、Diagnosis reason 或 Preconditioner adjustment/reason。程序先编译 Effective Plan，将必要条件落实在 Update 文本中。Editor 不通过 basis 反查材料。

Replay 的 Plan 沿用 v28 投影：保留 goal、Update 的 id/text 和 checks，不将原始 basis 冒充本轮执行事实。历史仍只有 Knowledge 与其证据标识，不补入历史图片、原始响应或历史完整 Skill。

## 4. 执行记录与引用如何迁移

保留 `run.ref/task_id/run_id/initial/attempts/outcome` 的结构和既有引用含义，只做以下必要适配：

| 字段或引用 | v29 含义 |
|---|---|
| `P1:0` / `initial` | question、image_path，以及初始 system/user 消息的完整文本投影 |
| `initial.messages` | 所有原始文字与顺序保留；图片内容块替换为明确声明“图像内容未提供”的文字占位块 |
| `P1:1` / `attempts[0]` | 唯一正常 stop 轮次的完整普通响应；不是 HTTP 尝试历史 |
| `request_messages` | 与该 run 的 initial 文本投影相同；不是完整多模态原始请求 |
| `P1:outcome` | 抽取答案、全部 reference_answers、`score.hard/anls`、完成状态与请求计数 |
| `Q1:*` | 同样结构的 Candidate 事实；其 system 保留 Candidate Skill |

“完整文本”不等于“完整多模态输入”。草稿明确这一差别，避免沿用 v28 的“原始完整消息”说法而误称模块看过图片。图片替换只是已确认的可见范围投影，不引入新的 OCR、摘要或分析阶段。

Replay 延续现行 v28 的 `shared_initial`：相同完整 system 文本可共享；相同完整 user 文本投影只在同题 Parent/Candidate 配对内共享。共享内容可完全恢复，不裁剪文字，不合并两侧执行。该视图省略重复的 `request_messages`，其文本等于恢复后的本 run 初始消息。另省略与同 run 的 `attempts[0].assistant.content` 完全相同的 `outcome.answer.raw_content`；完整普通响应仍在该轮保留一次，预测答案、参考答案及评分照常保留。原始执行、Call.input 和 Memory 归档保留完整字段，离线恢复可重建两处省略字段。证据仍引用 P/Q，而不引用共享表键。

2026-11-02 实现修订：Replay Prompt 标识更新为 `v29_docvqa_replay_v2`，模型输入视图为 `v29_docvqa_pairs_shared_initial_v2`；共享表自身仍使用 `replay_shared_initial_v1`。Memory 采用单次操作内复用：提交锁内首次完整核对历史与批次，后续复用已验证的 archive/contexts/view 进行增量状态转换；退出、异常或中断后丢弃临时结果，新调用重新校验。归档格式、整条修订和先 commit 后 Active 的写入顺序不变。

`pairs` 保留 parent、candidate、task_id、parent_result、candidate_result；两侧结果中的 `em/f1` 替换为 `hard/anls`，状态和计数不变。配对按显式字段识别，不靠编号或列表位置猜测。

## 5. 五模块分别改了什么

### Grouping

将 SearchQA 的 passage、实体消歧、上下文冲突示例换为 DocVQA 可从问题与回答识别的金额角色、日期角色、限定条件和答案边界。不预设分组数量、不把所有失败按分数归在一起、不引入固定错误分类表。

每个 run 仍恰好归入一组，单例组合法；shared_basis 仍需直接引用每个成员的返回轮次。正确与错误可以同组，但必须有共同决策问题。Grouping 根据问题及响应/结果差异组织比较，不提出“可能选错表格列”“可能漏看某行”等视觉原因假设。可以写“Actor 声称使用 subtotal”，不能据此认定图片存在该字段或实际选择了它。公共段落中鼓励合理假设的措辞已在 Grouping 单独移除；其他分析模块仍可提出有依据、保留不确定性的假设。

### Diagnosis

保留 Original Plan、revise/no_change、直接执行依据和可验证假设的职责。ANLS 不是原因标签：局部相似不必然代表格式错误，零分也不必然代表视觉定位失败。

图像相关的条件可以作为给 Actor 的行为指导，例如“若存在匹配标签则优先使用”；它是让 Actor 在图片中判断的条件，不是 Diagnosis 已确认存在的图像特征。提议仍需说明相对 Parent/基础协议带来的行为增量，不因为失败重复已有指导。

不设固定 Update 数量，不引入 v25.2 的最多两个 Update 要求。Checks 仍是比较观察问题，不改变 Gate，不要求额外作答或强制 Actor 增加解释。

图像依赖的 Checks 比较提交答案、参考一致性及带归属的响应陈述，不能要求 Replay 核实图片区域、标签关联或视觉动作。例如，检查“金额答案及 hard/ANLS 是否变化”，而不是“是否正确定位了总金额行”。单位、标点、日期或数字格式差异可能解释字符串得分差异，但单个案例不支持通用删单位或统一格式规则。基础协议要求最终 answer 元素，未明确禁止元素外普通文本；这不要求 Actor 增加解释。

### Preconditioner

明确独立接收完整 Parent Skill。D/S/C、KEEP/修改/撤回、Original ID 与 Goal 保持、精确 Update patch、checks 的 null/空列表/完整替换语义全部保留。

将“遍历所有 passage”的负担示例换为“遍历所有图像区域或数字字段”。判断是否重复、冲突或过度限制时，同时使用 Parent、Original Plan、允许的当前文本证据和相关历史 Knowledge；不将历史失败当成替代策略有效的证明。

Preconditioner 和 Replay 均明确：当适用条件取决于不可见图片时，适用机会本身也可能未知。响应沉默、得分或自报视觉动作不能单独证明该条件不存在、得到遵循或未得到遵循；不能假设图片条件不存在而排除反例。问题文本可支持金额/日期等范围判断，输出标签、提交措辞等响应行为仍可直接观察。这是现有判断语义的澄清，不新增状态字段。

### Editor

任务运行背景由 question/context 转为 question/image，answer 元素包含问题要求的简洁文本答案。移除“不是选项标签”等残留，避免排除文档中合法的字母或编号答案。基础协议未明确禁止元素外普通文本，不等于要求解释。Editor 本身不获得图片或执行事实。

保留仅落实 Effective Plan、精确无行号 patch、空 patch 表示已满足、null 表示必要要求无法落实的规则。不新增策略判断、审批或修复阶段。

交由 Actor 判断的图像条件可以直接实现，例如“存在匹配标签时优先使用”。Editor 缺少图片本身不构成阻塞，也不因此获得补造条件或改变 Effective Plan 的权限。

### Replay

保留实际 diff、完整显式配对、逐条证据、多 Knowledge、整条 Memory 修订及反例保留。将 EM/F1 解释替换为 hard/ANLS；只记录实际发生的字符串/分数变化，不把这种变化视作视觉过程证据。

例如，可确认“Candidate hard 从 0 提升至 1”，可提出“金额角色指导可能有关”，但不能确认“新规则让 Actor 读对了某一栏”。没有看到图片，也没有模型内部视觉过程，就无法建立后一种事实。因果不确定性同样不能抹去已观察的改善和退步。

Replay 不接收或引用 Gate 决策来证明规则有效。ACCEPT 与 RETAIN 都能积累 Knowledge；分数不变也可能存在有价值的输出变化。保留历史事件、条件与不确定性，不用当前结果改写历史。

Actor 的描述或转录在当前比较和历史整条修订中始终保留归属：“Actor 报告 X”不能因反复引用变成“文档包含 X”或“Actor 已核实 X”。历史合成示例明确展示这一点，同时保留另一条不受本轮影响的 Knowledge。

## 6. 输出合同与流程边界保持不变

| 模块 | 顶层输出 | 核心约束 |
|---|---|---|
| Grouping | `groups` | 覆盖全批、每 run 一组；五个既有组字段不变 |
| Diagnosis | `decision, reason, plan` | revise 或 no_change；Plan 为 goal/updates/checks |
| Preconditioner | `adjustments, checks` | 每 Original 恰好一条；D/S/C；to 为 null、[] 或 patch 对象 |
| Editor | `patch, reason` | 精确无行号 patch、空串或 null |
| Replay | `entries` | 每 entry 仅 revises/knowledge；每 Knowledge 仅 text/evidence |

仍然区分：Diagnosis no_change、全部 Update 撤回、Editor 空 patch，以及 Editor null 的必要条件阻塞。前三种有效无更新保留 Parent/Memory 并继续后续批次；不产生 Candidate 和 Replay。存在完整 Candidate 配对时，无论程序 Gate 如何选择，都先完成 Replay/Memory，再发布本轮状态。

不新增模块、图像分析阶段、字段分类器、置信度系统、语义投票或基于得分的 Actor 重试。现有错误反馈和输出合同保留，但本草稿没有实现任何接线或校验程序。

## 7. 合成输入输出与审阅方式

见 [示例说明](examples/README.md)。主链示例给出五模块各自的完整 `.input.json` 与 `.output.json`，以及 Parent、Candidate、Effective Plan。每份 input 都是独立完整 user payload，不需要把其他示例文件合并进模块输入。

所有题目、响应和历史 Knowledge 均为合成文本，没有创建示例图片、调用 Actor、运行训练或 Test。示例中的图片路径是明确的合成占位，不能用来执行 Actor。数值使用本地既有 DocVQA scorer 对合成答案计算，不表示模型成绩。

`review_only.json` 是给人的审阅注释，不属于任何模块输入。期望 Gate 决策只在这些注释里，未写入 Replay 输入或输出。

原草稿检查范围是草稿自洽性：英文 Prompt 与输入边界、示例 JSON 字段和引用、合成评分、实际补丁应用、Replay 文本共享恢复、历史整条修订。历史检查记录见 [draft_review.json](draft_review.json)。它不代表当前实现验收；随后响应去重及 Memory 提交复用的实现、Prompt 和示例同步检查见[修复验收说明](../MEMORY_REPLAY_FIX_20261102.md)。

整理独立 Actor 协议时，合成示例中的 system 字符串及共享表同步补齐了上游模板的末尾换行；问题、响应、评分及 Skill 策略不变。

数据、模型与 Actor 输出额度沿用此前确认。初始 Skill、调度与并发的后续选择见下节；五模块输出预算仍待后续试跑确定，当前不启动训练。

## 8. 初始状态、调度与待定预算

初始 Skill 已由用户选定为 [SkillOpt DocVQA 原始 initial.md](../../../../external/SkillOpt/skillopt/envs/docvqa/skills/initial.md)，使用原文，不先运行 Stage0 改写；初始 Memory 为空。主链合成示例的 Parent 已使用这份原文。SkillAdam 论文设置使用共享 Stage0 产物，因此这里仅参考其优化调度和并发，不声称复现相同的初始状态。

调度与并发参考本地 SkillAdam 的 [DocVQA 主结果配置](../../../../external/SkillAdam/skilladam/experiments/main_results.json)及[训练/Test 参数构造](../../../../external/SkillAdam/skilladam/experiments/planning.py)：

| 项目 | v29 设计选择 |
|---|---|
| 优化池 | 既定 Train 107 + Validation 53，共 160 题 |
| 顺序 | 沿用既定优化池顺序，sequential，不打乱 |
| batch / epoch | 15 / 1，保留最后不足 15 题的批次 |
| 批数 | 10 个 15 题批次 + 1 个 10 题尾批，共 11 批 |
| Gate 样本 | Parent/Candidate 使用当前同一批题目；尾批两侧均为同一组 10 题 |
| Actor 训练 workers | 60；单侧执行受当前批次题数限制，常规批最多同时 15 题，尾批最多 10 题 |
| Actor Test workers | 60；固定 374 题 Test 独立执行 |

workers 是题目执行的并发上限，不是批次大小或优化轮数。训练仍按批串行推进，Parent 与 Candidate 依赖五模块流程先后执行，不为填满 60 workers 跨批并行。无有效更新或 Gate RETAIN 时继续后续批次；不因参考 SkillAdam 而引入其 Momentum、编辑预算、阈值 Gate 或其他方法机制。

五模块的 `max_tokens` 暂不确定，不自动套用 v28 较新的 batch=30 配置，也不把旧版额度作为默认结论。后续在明确的试跑配置中给出各阶段起始额度，再根据完整响应、输出长度和终止情况确定正式额度；当前没有授权或启动该试跑。五模块请求超时也留待运行配置明确。已确定的 Actor `max_tokens=32768`、模型/API 和其他 Actor 参数保持不变。

本节仅记录设计选择，没有创建可运行配置、初始 Skill 副本、训练目录或模型请求。
