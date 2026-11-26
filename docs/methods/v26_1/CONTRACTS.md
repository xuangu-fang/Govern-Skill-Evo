# OfficeQA v26.1 输入输出与证据合同

状态：设计规范，尚无 v26.1 运行实现。模型输出均为一个英文 JSON 对象，精确字段集合，不带 fences 或额外说明。下方 JSON 为结构示例，不是真实实验结果。规则冲突应在实现前修订设计，不得用旧 v26 解析器的宽松接受替代本合同。

## 1 版本与请求身份

| 项目 | 设计身份 |
|---|---|
| method / stage / runtime | `v26_1_campaign_v1` / `v26_1_stages_v1` / `v26_1_light_runtime_v1` |
| Prompts | `v26_1_officeqa_{diagnosis,preconditioner,editor,replay}_v1`，花括号表示四个展开标识 |
| Diagnosis / Preconditioner | `v26_1_diagnosis_direct_evidence_v1` / `v26_1_preconditioner_actions_v1` |
| Editor / Replay | `v26_1_editor_mapped_patches_v1` / `v26_1_replay_transition_knowledge_v1` |
| Gate / Memory | `v26_1_gate_selective_em_v1` / `v26_1_memory_commit_v1` |
| Memory 模型视图 | `v26_1_rounds_effective_updates_v1` |
| 模型输入合同 | `v26_1_officeqa_formal_lossless_v1` |
| 编码策略 | 沿用 `v26_officeqa_lossless_input_v2`，允许原实现回退 v1 或无编码 |
| 引用策略 | `v26_1_officeqa_execution_references_v1` |
| Actor profile / 正式事实 / 评分视图 | 沿用 `officeqa_skilladam_aligned_v2` / `v26_officeqa_formal_evidence_v1` / `officeqa_em_f1_no_reference_answers_v1` |

四份 `prompts/*.md` 各自是完整 system 文本，不再拼接其他版本的公共 Prompt。user 为下述模型输入的完整 JSON。编码说明已内联，不重复追加旧说明。纠错时只在冻结的基础消息之后附带最近一次失败普通输出和具体校验错误；不累积多次输出，不暴露隐藏推理或未授权来源。

实际配置值、Prompt 原文、输入视图策略、模块/合同身份、任务顺序和已消费额度都属于请求身份。新运行独立初始化，拒绝把旧 v26、v29.4、v28.3 或 v27.1 的响应静默重标记为 v26.1。

## 2 原始执行与正式事实

复用 v26 OfficeQA 记录包装及公共 Actor 检查点，不改变其原始结构。包装保留 schema、run_id、task_id、公开 task、provenance 和 execution；provenance 保留批次/角色、任务上下文及来源 TXT/解析 JSON 字节身份。不同 Parent/Candidate 必须是不同执行身份。普通事实校验前核对 canonical task、来源、实际 Skill、Actor 参数、完成状态、请求/工具审计和原生评分；评分器可访问标准答案，模型视图不可以。

完整正式 run 精确为：

```text
ref: Pn 或 Qn
task_id: 非空题目 ID
run_id: 非空独立执行 ID
initial:
  ref: Pn:0
  task: {id, split, question, source_files, source_docs, category, task_type}
  declared_source_pages: [{file, source_page, url}, ...]
  messages: [{role, content}, ...]  实际初始 system/user 消息
attempts: [
  {ref, request_context, request_messages,
   assistant, tools: [{ref, call, observation}, ...]}, ...]
outcome:
  {ref, status, termination, answer, model_rounds, tool_calls, api_requests,
   score: {em, f1}}
```

公开 task 的 split 在优化池内为 train；源 split 在数据/运行元数据保留，不能因此开放全部原始行。`task_type=officeqa`。source_files/source_docs/category 均来自原白名单，不附加 answers、ground_truth、reference 或任意 metadata。

`request_context=formal_history_without_temporary_format_feedback_v1`；`request_messages` 是本轮生成前的正式历史。assistant 为原生接受的消息白名单（role/content，以及有工具时完整 tool_calls）；tool call 保留 id/type/function(name/arguments)，observation 精确含 role/tool_call_id/name/content。普通 content 可按原协议为空/null，但合法无工具最终响应必须非空。工具参数字符串和返回文本不重新序列化或改写。

`attempts` 长度1–24，轮号连续。outcome.answer 是**字符串**；status=completed；termination=answer 或 max_tool_turns。计数必须与正式轮次、工具事件及已消费请求一致；api_requests含技术/格式失败，范围为 model_rounds 至6×model_rounds。技术失败耗尽没有完成 run；正常24轮耗尽可构成空答案、EM=F1=0的完成 run。它们不能互换。

EM接受原生0/1或0.0/1.0，拒绝bool、非有限数及其他数值；F1为[0,1]有限数。保留原生评分，不引入浮点类型误拒绝、数值容差、新别名或外部正确性判定。标准答案、matched-reference identity、隐藏 reasoning、失败正文和临时纠错只留在各自受限原始归档，不通过任何模型输入字段、错误反馈或 Memory 泄漏。

## 3 可见性与引用

| 模块 | 可见输入 | 不可获得 |
|---|---|---|
| Diagnosis | Parent、完整当前 Parent runs | Grouping、Memory、Candidate、标准答案、隐藏推理 |
| Preconditioner | Parent、冻结 Original Plan、Plan 引用的完整当前 runs、只读 Memory | Diagnosis reason、未选 runs、历史原始轨迹、Candidate |
| Editor | Parent、goal、Update id/text | basis、runs、Memory、分数、上游 reason |
| Replay | Parent、actual diff、有效 goal/id/text、patch映射、EM翻转 pairs及完整 runs | basis、历史 Memory、未翻转任务、上游 reason、Gate决定 |

P编号沿用 v26：按本轮完整 Parent 已保存的完成顺序分配，并冻结。Candidate通过 task_id匹配到对应Q编号；不按Candidate完成位置配对。筛选后不重编号。Replay pair顺序沿用完整Parent事实顺序，runs按P/Q邻接；事件输出也规范化到该顺序，M编号据此分配。配置任务顺序与完成顺序分别记录，不相互冒充。

引用包括 `P1`、`P1:0`、`P1:2`、`P1:2_t1`、`P1:outcome`，Q同理。`:2`包含该轮assistant和已提交工具返回；`:2_t1`的独立含义仅为该调用、返回及生成前正式历史，不包含同轮兄弟工具观察。v26.1四模块传完整授权runs，不另设局部source_records接口；引用工具仍不能倒置时间或声称看过未提供的文档。

Diagnosis只可引用当前全批P；Preconditioner只可引用已选P、当前Original ID及已提供Memory ID；Replay每个事件的text只可引用**该题自己的P/Q及子引用**、diff和当前有效Update；Editor只有ID映射权限。历史Memory文本中的旧P/Q是过去报告，不能激活原始来源访问。

结构化basis元素须为单个精确直接执行ID，非空且不重复。自然语言的 `P1/P5`、`P1:2_t1/P5:outcome` 按成员逐项验证；真正 `R03/P1`、`R03/diff` 仍是历史引用，四模块不获该原始证据权限。沿用v29.4显式命名空间单对反引号语法，例如 `Evidence:P1:2_t1`、`Memory:M1`、`Update:u1`；`Evidence: returned text`这类冒号后空格的普通文字不误认来源。Group、Check来源识别后拒绝。与LMB不同，本稿不引入“所有裸P/Q均当数学符号”的特例；工具子引用须完整识别，不能截断成较宽的轮引用。

保留来源解析器已有的Parent轮次范围展开，例如`P1:1-3`、`P1:1–P1:3`，逐项核验真实已提供的轮次；倒序、跨执行或不存在的轮次非法。结构化basis仍逐个精确ID，不使用范围。Q轮次与工具子引用使用逐条ID或本地列表，不新增工具范围、页码范围到证据ID的隐式推断。

Preconditioner筛选扫描整个Original Plan中的合法直接执行引用（goal、text、basis），Diagnosis reason不参与；沿用v29.4引用行为并覆盖工具引用。Update ID不得与证据ID冲突。引用任意子项时传其完整所属run，去重并保留原事实顺序。关键成功例、反例和范围依据仍应明确进入对应basis。

## 4 无损表示

解码后顶层字段是各模块下文规定的精确集合。实际wire payload可另外有 `_officeqa_encoding={format,messages}`；没有该字段则为原始视图，不允许另加`shared_initial`。

完整run先验证每轮request_messages恰等于initial加全部先前accepted assistant及按序tool observations，才省略重复历史。每条当前轮返回只能出现在后续请求中。完整相等system可跨run共享；user仅可同run或经核验的同题Parent/Candidate完整user序列共享，不能跨题。表中不收录后续assistant/tool内容。指针为`{"officeqa_message":"mN"}`，不是证据ID。

本合同无source_records，因而不生成v2局部history指针；原v2策略允许回退v1，完整run时间线能力保留。每请求采用确定性编码选择，并在归档记录实际format。四份Prompt已经解释所有允许形式；长度比较应包含完整system说明开销。解码后全payload类型、文本、空白、Unicode、字段、列表顺序和事件重复次数须相等；编码后再解码并复编码验证规范形式。不同Skill不能用另一侧system重建；answer字符串不采用单轮raw_content捷径。

编码发生在模块权限筛选之后，反馈追加之前；Call原输入、验证和来源归档保留原始事实，模型消息保存实际编码。无摘要、截断、跨阶段共享缓存或隐式来源加载。超容量停止并报告，不自动减批或裁剪证据。

## 5 Diagnosis

输入为`{parent,runs}`；parent为完整Skill字符串或null，runs为完整本轮Parent批次。程序侧事实束可保留facts/background/sources/round_id，但这些封装不是额外模型字段或新阶段。

输出精确为：

```json
{"decision":"revise","reason":"A scoped change has current support; its effect remains unverified.","plan":{"goal":"Improve the supported decision while preserving valid paths.","updates":[{"id":"u1","text":"The complete conditional behavior to implement.","basis":["P1:0","P1:2_t1","P1:outcome"]}]}}
```

decision仅revise/no_change；reason非空。revise要求非空goal和updates，Update精确含id/text/basis，id轮内唯一，text非空。no_change要求plan=null。没有need_evidence、Checks或Group。单案例允许合理提案，不要求每题产生Update，不要求每条都有正反例，不固定数量。必要动作、条件、强度、依赖与保护边界写入text；reason不承担下游实施合同。

## 6 Preconditioner

输入`{parent,plan,runs,memory}`，plan是完整冻结Original，memory为第10节视图。

```json
{"adjustments":[{"target":"u1","action":"REPLACE","text":"The complete revised requirement with its conditions.","reason":"Decisive current or historical grounds and uncertainty."}]}
```

每个Original恰好一个target，无新增/重复/遗漏ID。每项精确target/action/text/reason。KEEP、WITHDRAW的text必须null；REPLACE为完整非空、与原文不同的字符串，不是diff或片段。reason非空。D/S/C为思考维度，不增加输出字段。保持goal、存活项顺序、id和原basis，仅替换text或删除WITHDRAW项；basis仍是Original来源，不声称重新证明了替换内容。Original不可覆盖。

KEEP表示整条提案可作为合理实验保留，尚不是Gate采纳；审查其实际条件、附带动作、优先级和依赖。Preconditioner不另起无关修复，不拆并ID。撤回依赖须同步协调其他Original；允许全部WITHDRAW，无成功弃权或need_evidence字段。无相关历史可以依当前证据决定；不为了展示Memory使用而强制REPLACE。

## 7 Editor

输入`{parent,plan}`，plan精确goal/updates；每Update只含id/text，没有basis或任何reason。

```json
{"edits":[{"update_id":"u1","patch":"--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Old guidance.\n+Revised guidance.\n","reason":"Implemented the effective behavior."}]}
```

每Update恰好一项，精确update_id/patch/reason。非空patch忠实实施；`""`表示原Parent加base已满足；null表示无法忠实实施的语义阻塞。任一null停止整轮，不发布剩余部分，不重采样合法null。空白字符串不是空patch。补丁错误不能转成null或空串。

补丁沿用v29.4所用v29.2映射补丁算法：

- 原Parent非null时头为`--- a/SKILL.md`和`+++ b/SKILL.md`；null用`--- /dev/null`。null或恰好空字符串时非空patch为单个纯增加hunk。
- hunk标题为独立`@@`，无行号。每内容行以空格、减号或加号开头，内容逐字匹配；末尾LF身份通过原`\ No newline at end of file`约定保留。
- 同一patch各hunk均定位原Parent，按源位置递增且不重叠（含context）。非空Parent插入需上下文定位；零匹配或多匹配拒绝，不模糊修复。
- 不同Update可共享只读context；同一行的单行替换以最长相同前后缀形成一个连续字符改动区间，重复文本歧义拒绝，不推断多个改动岛。实际区间重叠即冲突，即使新文本相同。
- 区间内部插入冲突，边界插入允许；同一间隙按Effective Update顺序合并，不按响应edits顺序。全部patch定位同一个原Parent，不依赖另一个patch生成定位文本。
- 全部校验后联合构造非空且不同于Parent的Candidate和实际diff，不让模型另输出Candidate。空patch不构成新干预。
- Gate选择子集后再次对原Parent组合，验证结构有效。不能为解决冲突合并ID或把多项行为全塞到一个patch；无法忠实时null。文本可组合不证明语义依赖独立。

## 8 Candidate 与 Replay

所有有效非空patch联合执行一次完整Candidate批次；复用本轮Parent，不增加独立Update执行或重组验证。先验证全批覆盖、任务ID唯一、源资产/无Skill上下文/Actor设置一致及实际双方Skill，再选`parent.em != candidate.em`的pairs。不得先过滤而跳过未翻转任务的完整性验证。

Replay输入`{parent,diff,plan,edits,pairs,runs}`。plan的Update仅id/text；edits仅update_id/patch，按Effective顺序；diff是Parent到**完整Candidate**的实际改动。pairs每项精确parent/candidate/task_id/parent_result/candidate_result，result精确status/model_rounds/tool_calls/api_requests/em/f1。runs仅为翻转任务双方的**完整**正式轨迹，保留未改变的早期轮次及全部工具事件；不截成差异步骤。无Memory、basis、上游reason、Gate决定或未翻转任务。

```json
{"entries":[{"knowledge":[{"task_id":"synthetic-A","update_id":"u1","text":"Describe the visible behavior change, EM direction, patch connection and its limits."},{"task_id":"synthetic-B","update_id":null,"text":"Preserve the regression and explain why one Update cannot be identified."}]}]}
```

有翻转时entries恰好一个元素，仅knowledge；knowledge非空，每题恰好一条，精确task_id/update_id/text。text非空；关联ID须为本轮有非空patch的Effective Update。只有实际行为变化与一个已实施Update有明确连接才关联；分数翻转、话题相似、预期适用范围或存在patch不充分。多Update无法区分、不可分联合影响或证据不足用null，不强制主责归因，不将一题拆成多票。null不等于噪声或所有Update无关。

无EM翻转时不分配Replay请求槽，程序产生`{"entries":[]}`和skip receipt。`{"entries":[{"knowledge":[]}]}`非法。F1-only、持续失败/成功及工具成本变化不增加事件；正常工具观察可帮助解释已有EM事件。解析失败不能伪装成无事件。不存在revises、evidence数组、置信度、G/L或下一轮Plan字段。

## 9 Gate 与执行来源

```text
G[u] = 明确关联u且EM 0→1的当前任务数
L[u] = 明确关联u且EM 1→0的当前任务数
patch[u] == ""       → gate_decision = null
G[u] > 0, L[u] == 0   → Retain
G[u] == 0, L[u] > 0   → Reject
其他                  → Defer
```

混合收益退化不论净收益多少均Defer；0/0也Defer。null事件保留但不投任何Update，一题至多一票。没有整包净收益门槛、整包否决、F1投票或接受兜底。Reject/Defer只是不采用本轮patch，不删除Parent的旧规则。

输出精确decisions/selection/selected_execution_source；decisions各项为update_id/G/L/gate_decision；G/L是非负整数。selection为selected_update_ids/selected_text/actual_diff，仅选择Retain并保留Effective顺序。

先按完整字符串比较Selected与Parent，相等来源为parent；否则与完整Candidate相等为candidate；否则null。不能按strip后的Actor消息、patch数量或语义等价转移成绩。null表示本轮未执行的新组合，无本轮Selected分数；下一轮Parent或最终Test才产生真实成绩。空选择返回原Parent；组合抵消回Parent也按真实文本处理。

## 10 Memory 与发布

初始`{"rounds":[]}`。Preconditioner只读模型视图为：

```json
{"rounds":[{"round_id":"R01","source_updates":[{"id":"u1","text":"Complete Effective Update text.","gate_decision":"Retain"}],"entries":[{"id":"M1","knowledge":{"task_id":"synthetic-A","update_id":"u1","text":"An event with its conditions and uncertainty."}}]}]}
```

每轮包含全部Effective Updates（含Reject/Defer/无关联/空patch），不含被WITHDRAW的Original。source_updates精确id/text/gate_decision；entries精确id/knowledge。Update ID轮内唯一，历史讨论结合round_id；M1、M2…跨轮连续递增且每事件一个。无事件但已有Effective编辑阶段时仍记录source_updates；历史只追加，不改写、合并或删除。模型不获得历史原始Skill、diff、轨迹或分数表，已记录Knowledge可重新解释但不能篡改。

持久化沿用v29.4的内容寻址提交结构与轻量读取原则，新格式身份隔离：提交序号加规范JSON摘要标识，单写者锁、预期前驱比较、同目录原子HEAD切换。Memory和Selected通过**同一个HEAD**发布，再更新可恢复campaign游标。提交序号不是轮号，no_change可不提交Memory。

当前未发布轮完整核验来源、patch、Replay、Gate、选择及提交内容；已发布历史读取摘要、结构、连续前驱、ID和选择一致性，不逐轮重开Actor来源或重新执行全部Gate。保持原OfficeQA当前执行的来源校验，不增加全仓库源码哈希门槛。来源快照和原始HTTP仍保留，但普通恢复不是历史所有源文件的事后审计。

HEAD领先游标一轮时复用已提交结果完成游标；重复提交相同内容幂等，陈旧HEAD或同标识不同内容拒绝。非空store缺失HEAD不能初始化为空；孤立未发布文件不自动成为HEAD。合法停止与技术故障都不得部分发布Skill或Memory。

## 11 分支与恢复

| 情况 | Candidate / Replay / Gate | Memory与Skill | 下一批 |
|---|---|---|---|
| Diagnosis no_change | 均跳过 | 不追加Memory，保留Parent，保存结果并推进游标 | 继续 |
| Preconditioner全WITHDRAW | 均跳过 | 同上，保留动作归档 | 继续 |
| Editor全空patch | 均跳过 | 追加Effective、null决定和空事件，发布Parent | 继续 |
| Editor任一合法null | 均跳过 | 不提交；保存阻塞、响应及已用额度 | 停止 |
| 有Candidate、无EM翻转 | Candidate全批；Replay模型跳过；Gate程序运行 | 非空patch均Defer，记录无事件轮，保留Parent | 继续 |
| 翻转全部无法归因 | 正常Replay/Gate | 保存全部null事件，非空patch Defer | 继续 |
| 有明确归因 | 正常闭环 | 保存全部事件与Effective，发布Selected | 继续 |
| 子集组合非法 | 组合处停止 | 不回退整包、不自动修复或发布 | 停止 |
| 模型输出结构/引用非法 | 六次额度内最近一次反馈纠错 | 不当作no_change/空事件 | 耗尽停止 |
| 数据/来源/归档/版本损坏 | 不包装为模型格式错误 | 不请求模型修复、不发布 | 停止 |

恢复先检查已保存完整响应，再决定是否还需请求；第六次完整响应落盘可解析，不能因额度已满而丢弃，也不能发第七次。请求发出前记账，未知结果也消耗额度。已提交工具不重放，started结果未知停止；逐题日志的已完成结果复用与未完成题恢复保留原行为。不把同Skill的不同批次/重复评估目录混用。训练完成才导出最终Selected；Test入口独立，完整172题才报告完整集分数，部分完成报告pending和错误，不回流Memory。
