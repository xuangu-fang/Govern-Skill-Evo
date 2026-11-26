# v28.4 设计合同

状态：2026-11-04，**独立 SearchQA v28.4 实现和离线验收已完成，未启动正式训练或 Test**。本文与[设计稿](README.md)、[四份提示词](prompts/)共同约束实现；离线覆盖和边界见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。不能直接将这些提示词替换到 v28.3 实验中。所有模型响应为单个英文 JSON 对象；字段集合为精确集合，不接受额外字段。正常响应不带 Markdown fences；本文代码块仅展示结构。

## 1. 身份与版本

以下身份已在独立 v28.4 实现中绑定，与设计预留值一致。版本隔离不改变继承接口的字段或算法。

| 项目 | 绑定值 |
|---|---|
| method.version | `v28_4_campaign_v1` |
| method.stage_contract | `v28_4_stages_v1` |
| runtime | `v28_4_light_runtime_v1` |
| 四份 Prompt | `v28_4_searchqa_diagnosis_v1` / `v28_4_searchqa_preconditioner_v1` / `v28_4_searchqa_editor_v1` / `v28_4_searchqa_replay_v1` |
| Diagnosis contract | `v28_4_diagnosis_direct_evidence_v1` |
| Preconditioner contract | `v28_4_preconditioner_direct_evidence_v1` |
| Editor contract | `v28_4_editor_mapped_patches_v1` |
| Replay contract | `v28_4_replay_transition_knowledge_v1` |
| Gate contract / gate_rule | `v28_4_gate_selective_em_v1` |
| Memory contract | `v28_4_memory_commit_v1` |
| memory_view | `v28_4_rounds_effective_updates_v1` |
| Diagnosis/Preconditioner input view | `v28_4_shared_execution_text_v1` |
| replay_input_view | `v28_4_em_transitions_shared_initial_v1` |
| 普通响应事实视图 | 沿用 `v28_searchqa_pairs_content_v1` |
| Actor / scorer profile | 沿用 `v28_searchqa_actor_answer_element_words_v1` / `v28_searchqa_skilladam_scoring_v1` |
| request_context | 沿用 `searchqa_single_turn_v1` |
| retry_policy | `previous_output_validation_error_v1` |
| semantic_resampling | false |
| knowledge_review | `disabled_v1` |

没有 Grouping Prompt、contract、调用槽或目录。Prompt 原文、版本、输入消息和完成响应须一同记录。方法、stage、runtime、Prompt、contract、配置或冻结文本不符时，在发送请求或恢复之前拒绝；不能重命名 v28.2/v29.4 的响应冒充本版本。相同算法可复用纯函数，但不能带入 DocVQA 的评分、数据或事实校验器，也不能使上游验证重新要求 Grouping。Diagnosis、Preconditioner、Editor 使用本目录修订文本；Replay 使用独立新版本身份，正文与冻结的 v28.3 完全相同。

直接基线为已完成实验、撤回 question/context 字符范围表示后的 SearchQA v28.3。沿用其无 Grouping 链路、SearchQA 评分/数据/Actor 边界与顺序 Memory ID；本次只修订三个模块的决策和实施指导。DocVQA 不作为验收或运行依赖。轻量恢复行为见第 9—10 节。预算与固定实验边界见 [设计稿](README.md)，配置逐项校验，不能仅凭身份相同接受不同预算。

## 2. 证据、评分和无损视图

### 2.1 执行事实

保留 SearchQA 已完成训练执行的 `ref/task_id/run_id/initial/attempts/outcome` 投影：

- `initial`：`ref/task/messages`；`task` 保留 question、context；messages 保留原始角色、内容、元数据和顺序。完整 task.question/context 与原始 user message 均保留；不转为字符范围或模板引用。
- `attempts`：恰好一个已接受 stop 回合，含 `ref/request_context/request_messages/assistant`；assistant 仅普通 `role/content`，不含 reasoning_content。
- `outcome`：`ref/status/termination/answer/reference_answers/model_rounds/tool_calls/api_requests/score`；answer 含 `raw_content/extracted_answer`，score 含 `em/f1`。
- P 引用属于当前 Parent，Q 属于 Candidate。P/Q 及 `:0/:1/:outcome` ID 在完整批次中确定，再过滤；过滤后不得重新编号。

完整训练归档先通过数据、完成状态、任务顺序、实际 Skill 和配对验证，再生成模型视图。Test 不可注册为优化证据。技术失败和 length 响应不作为额外推理步骤、候选答案或评分；请求计数不代表模型回合数。

EM 来源是原生评分器的二值数值，允许实际产生的 `0.0/1.0` 和等值 `0/1`，拒绝 bool、其他值与非有限数。F1 必须是 [0,1] 有限数，拒绝 bool，EM=1 时 F1=1。不照搬 v29.2 对 `hard` 的严格整数校验导致合法 SearchQA 浮点 EM 被拒绝。Gate 计数 G/L 始终为非负整数。

### 2.2 Diagnosis / Preconditioner 共享视图

在各模块完成证据权限筛选后，增加 `shared_initial={format,messages}`，format 为 `execution_shared_initial_v1`。完整 system 消息按首次出现顺序放入 `messages.system_1` 等；原位置用仅含 `shared_message` 的对象代替；user 消息保持内联。不同 system 文本不能因为逻辑等价就合并。

仅在逐字/结构相等已验证后，省略 `attempts[0].request_messages`（等于该 run 的 initial.messages）和 `outcome.answer.raw_content`（等于 assistant.content）。共享指针解析后必须无损还原原始事实。顶层完整 parent 独立保留，不能用选中某个 run 取代。共享只发生在本次请求，不跨阶段/轮次；指针不构成 Evidence ID。

### 2.3 Replay 共享视图

完整批次验证通过后，先选 EM 翻转 pairs/runs，再用 `replay_shared_initial_v1` 格式共享：相同 system 消息可跨 runs；完全相同的 user 消息序列只在已验证的同一个 Parent/Candidate pair 内共享。其余内联。重复 request_messages/raw_content 的省略规则相同，initial.task 独立保留。不得摘要、截断或从 Parent 重建 Candidate system。

### 2.4 引用权限

| 模块 | 可用引用 | 不可用引用 |
|---|---|---|
| Diagnosis | 全批当前 Parent runs 及子引用 | Group、Candidate、Memory、历史执行 |
| Preconditioner | Plan 引用所选当前 Parent runs；当前 Original IDs；提供的 Memory IDs | Group、未选 runs、Candidate、历史原始执行 |
| Editor | Update ID 只用于 edit 映射 | 无执行或 Memory 检索权限 |
| Replay 每条 Knowledge | 该事件自己的 P/Q pair 及子引用、diff、当前 Effective Update IDs | 其他题执行、未提供题、Memory、Group、Check、历史执行 |

结构化 `basis` 使用单个精确 ID 组成数组，不把 `P1/P5` 塞进一个数组元素。文字中的 `P1/P5/P7`、`P1:1/P5:outcome` 是本地引用列表，各项逐一检查；`R03/P1`、`R03/diff` 仍是历史引用，不能因斜杠解析而获得权限。

Preconditioner/Replay 正式紧凑引用如 `Memory:M1`、`Evidence:P1:1` 需单对反引号，且符合各模块权限。`Update: the rule ...` 等冒号后空格的普通文字不误判为引用；真正不合法的紧凑引用不能通过文字放宽获得权限。不给模型增加不必要的强制引用格式清单；有需要时沿用当前修复后的明确错误反馈。Memory 正文中的旧 P/Q 文本是历史报告，不授权 Preconditioner 访问原记录。

## 3. 直接事实入口与 Group 来源拒绝

程序从完整已完成 Parent 批次构造事实束，保留 `facts/background/sources/round_id`，facts 精确含 parent/runs；这是事实验证与归档，不是新模型阶段。拒绝带旧 grouping 交接对象的输入；不生成分组摘要、隐藏分类报告或 Group ID。

Diagnosis 的 reason、Plan goal、Update text/basis，以及 Preconditioner 的 reason/REPLACE text 不授权 `G1`、`Group:G1` 等 Group 来源。引用解析器仍应识别旧标记以明确拒绝，不能因删除 Grouping 就把它们当普通文字放行。合法普通词汇不得被误判为来源引用。basis 只接受当前执行及其子引用，不接受 shared-message 键或历史引用。

## 4. Diagnosis

模型输入精确为 `{parent,runs,shared_initial}`，runs 为全批当前 Parent，保留成功与失败执行；没有 grouping 或 Memory。程序原始输入为 parent/runs，模型投影才增加 shared_initial。

输出精确为 `decision/reason/plan`：

```json
{"decision":"revise","reason":"A scoped behavioral change is supported; its effect remains unverified.","plan":{"goal":"Improve the supported decision while preserving valid alternatives.","updates":[{"id":"u1","text":"A complete conditional behavioral change.","basis":["P1:0","P1:1","P1:outcome"]}]}}
```

- decision 仅 `revise/no_change`；reason 非空。revise 要求 plan 精确含 goal、updates，二者非空；no_change 要求 plan=null。
- Update 精确含 id/text/basis；ID 唯一且不与证据 ID 冲突；text 非空；basis 非空、去重、仅授权精确 ID，必须含直接执行证据。
- 没有 Checks，也没有 need_evidence。实施条件、例外、依赖、强度、优先级和保护边界写入 text。
- 比较共同判断问题与重要差异，使用相关可用的成功、失败和反例；单案例也可支持合理提案，并非每题都要产生 Update。Update 按共同问题及修正方向组织，不按题目、错误标签、句子或预期 Gate 去留划分。同一修正必需的动作、条件、例外、旧规则处理和依赖保持完整；相同错误标签不强制合并。
- 检查问题与 Parent/base 指导的关系，选择新增、修改、合并相关指导、替换、删除有问题的指导，或不修改；不预设新增或修改更好，不设操作比例。已有覆盖不证明规则足够有效，执行失败也不证明必须增加规则。
- 每条 text 必须足以表达选定修正及必要的旧规则处理：相关行为或可辨识文字、需要怎样改变、哪些有效条件保留。无需 operation、rule_id、行号、额外检查字段或 Editor patch；规则合并不等于合并 Update ID。Diagnosis reason 解释依据，但不得作为实施条件的唯一载体。
- **reason 不传给 Preconditioner**。沿用 v29.4 从整个 Plan（goal/text/basis）中的合法直接执行引用选择完整 runs，按原批次顺序去重。不是只扫描 basis；但决定范围的成功例、反例和支持证据仍应明确进入对应 basis，不能只写在 reason。

执行失败不自动证明 Skill 缺陷；提案需有具体行为增量，不要求先证明因果。纯粹缩短或改写行为不变的文本不是独立优化目标；有依据的行为修正可包含必要的局部整理。实体/关系、答案边界、参考形式是 SearchQA 分析区别，不是额外分类字段或新阶段。结构验证不证明这些判断正确。

## 5. Preconditioner

模型输入：`{parent,plan,runs,memory,shared_initial}`。plan 是冻结的完整 Original Plan；runs 是 Plan 直接引用的当前 Parent 子集；memory 是第 9 节只读轮次视图。Diagnosis reason、Group 来源、历史原始执行不传入。

输出：

```json
{"adjustments":[{"target":"u1","action":"REPLACE","text":"The complete revised behavioral requirement, including its conditions.","reason":"Decisive current or historical grounds and uncertainty."}]}
```

每个 Original 恰好一个 adjustment，精确含 target/action/text/reason；不漏项、不增加 ID、不重复 target。

| action | text | 编译结果 |
|---|---|---|
| KEEP | null | 保留原 Update 全文 |
| REPLACE | 完整非空且与原文不同的字符串 | 替换整个 text，不输出 diff 或片段 |
| WITHDRAW | null | 移除该 Update |

reason 非空，记录判断依据；D/S/C 只用于思考，不输出 focus/change/to 等旧字段。程序保留 goal、存活 Update 的原顺序、id 和 basis；basis 是原提案 provenance，不声称已重新证明替换文本。Original Plan 永不原地覆盖；审计可生成差异，不能把差异当作模型合同。

沿用 D/S/C 与整条 KEEP 审查，并检查修正方式及必要旧规则处理。主方向合理不自动支持附加条件、fallback 或强制顺序。Preconditioner 可以根据当前证据和相关历史，在 Original 问题边界内改变修正方式；不能把修改旧规则的方案退化为追加警告，也不能为了减少规则而强行合并。部分内容需要修正时输出完整 REPLACE，包含最终修正方式、受影响旧指导的处理、有效条件与依赖，不能只写在 reason。Editor 不会读到这些 reasons。

合并 Skill 中的相关规则不等于合并 Original IDs。保持 Goal、ID、顺序、basis 编译合同；需要的协调无法在现有问题边界内完成时撤回受影响提案，不能伪造完整修正。历史关联不是独立因果证明，Defer 不自动等于无效，空 entries 不等于已报告的负面实验。不增加流程、Knowledge 类别、统计字段或长度 Gate。

全部 KEEP 仍进入 Editor；全部 WITHDRAW 得到 effective_plan=null，保留 Parent、继续下一批。撤回依赖时必须在现有 Original 范围内协调相关 Update；不偷偷新增依赖字段或另做 Diagnosis。

## 6. Editor 与组合

模型输入：`{parent,plan}`；plan 精确为 goal/updates，Update **仅含 id/text**。basis、runs、Memory、Diagnosis/Preconditioner reason 均不传入。

输出：

```json
{"edits":[{"update_id":"u1","patch":"--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Old guidance.\n+Revised guidance.\n","reason":"Implemented this Update against the original Parent."}]}
```

Effective Update 决定行为修正方式；Editor 决定其忠实实施的措辞、位置与 patch。既能新增，也能按要求改写、合并、替换或删除相关旧指导；不得独立重选策略。Update 要求修改旧规则时，追加一个保留旧冲突的例外说明不算实施；Update 要求新增时，也不能为减少数量而强制合并。允许准确实施所必需的局部整理，保留无关有效指导。若缺失必要的行为选择而无法忠实实施，按现有 null blocker 合同报告，不自行诊断。

Workflow / Error Avoidance 仅是三个模块共享的组织建议：前者表达可复用判断流程与分支，后者表达具体误用及边界。不是固定标题、恰好两节、规则上限或长度指标。保持清楚的既有组织，使条件、例外和优先级靠近对应决策；不在两类中重复同一规则，不为填模板创造新步骤。初始无学习规则时也只组织授权内容。组织调整若改变行为范围或优先级，必须在 Update 中授权；Editor 不能借排版改变策略。

每条 Effective Update 恰好一个 edit，精确含 update_id/patch/reason，reason 非空。

| patch | 含义 | 行为 |
|---|---|---|
| 非空 diff | 实际修改 | 参与共同构造与后续选择 |
| 精确空字符串 | 原始 Parent + base 已满足该 Update | 不分配收益/退化，不产生修改级 Gate 决定 |
| null | 不能忠实实现的语义阻塞 | 整轮停止，不构造部分 Candidate，不重采样 |

空白字符串不是空 patch；格式非法、定位失败或冲突是校验失败，不自动转成 null/空串。某条空 patch 的判断基于原始 Parent，不依赖另一 patch 将添加的内容。

patch 合同继承 v29.4 沿用的 v29.2 mapped-patches 语义，并使用 SearchQA Actor 边界：

1. 原 Parent 存在时头为 `--- a/SKILL.md` / `+++ b/SKILL.md`；Parent=null 时旧头为 `/dev/null`；hunk 标记只有 `@@`，无行号/计数。空/null Parent 的非空 patch 使用单个纯添加 hunk。
2. 每个 patch 内 hunk 按原始位置递增、连同 context 不重叠，精确唯一定位；保留空格、Markdown、换行及 `\ No newline at end of file` 身份。无 fuzzy match、归一化、自动修复或全文回退。
3. 所有 patches 定位同一原始 Parent，不串行基于前一 patch 输出。跨 Update 只读 context 可重叠；同一行中唯一可定位、互不重叠的字符修改可组合。单行替换用最长相同前后缀得到一个连续改动区间，歧义拒绝；不推断多个变化岛。
4. 实际修改区间重叠拒绝，即使替换内容相同；区间内部插入拒绝；边界插入允许；同一间隙插入按 Effective Update 顺序组合，不按响应 edits 顺序。
5. 全部校验通过后一次构造 Candidate 和 actual_diff。Candidate 非空且与 Parent 不同；任一 null 阻止发布；全部空 patch 为 editor_no_change。
6. Gate 选中的 patches 再次对原 Parent 按 Effective Update 顺序组合。空选择严格返回原 Parent；有修改时重组文本须有效且非空。组合可恰好抵消回 Parent，仍以实际文本确定来源。

构造器只验证文本结构与组合，不验证自然语言依赖是否满足；不宣称独立因果效果。Editor 不能为消除冲突合并 Update IDs、把联合行为偷偷全放在另一 ID 的 patch、或缩减授权要求。

## 7. Candidate 与 Replay

Candidate 在同一完整批次、相同 Actor 参数和评分器下独立执行；不接收 Parent 答案/参考答案/评分反馈。Parent 使用本轮原执行，不为比较重采样。

模型输入精确为 `{parent,diff,plan,edits,pairs,runs,shared_initial}`：

- parent 为原始 Skill；diff 为实际 Parent→完整 Candidate diff。
- plan 的 Update 仅 id/text；edits 每项仅 update_id/patch，按 Effective Plan 顺序；没有 Editor reasons。有效执行不含 null patch。
- pairs 每项精确含 `parent/candidate/task_id/parent_result/candidate_result`；result 含 `status/model_rounds/tool_calls/api_requests/em/f1`。
- 先验证完整批次所有 pair，再筛选 `parent_result.em != candidate_result.em`。仅筛选后 pair 对应的完整文本 runs 进入模型。未翻转任务即使 F1、答案内容改变，也不提供给 Replay。
- 不提供历史 Memory、basis、Checks、上游 reasons、Gate 决定或隐藏推理。

存在翻转事件时输出精确为：

```json
{"entries":[{"knowledge":[{"task_id":"task-A","update_id":"u1","text":"Describe the supported task condition, actual Parent/Candidate difference, EM direction and behavioral attribution with its limits."},{"task_id":"task-B","update_id":null,"text":"Preserve the observed regression and explain why no single Update can be associated."}]}]}
```

entries 恰好一个元素，元素仅 knowledge，knowledge 非空；每个翻转 task_id 恰好一条，不允许多主题 entries 或把一题分摊到多个 Update。每条精确含 task_id/update_id/text，text 非空；非空 update_id 必须指向当前有非空 patch 的 Effective Update。

只有可观察的行为变化与一个已实施 Update 有明确连接时才关联。主题相似、预期范围、分数改变或存在 patch 均不足以单独归因。无法区分多个 Update、不可分联合影响或缺少明确联系时用 null，保留事件。null 不等于噪声或全部 Updates 无关。

每条 text 只引用自己任务的 P/Q 及 diff，不能用另一事件的执行记录充当证据。程序按原批次任务顺序规范化事件顺序。不接收 evidence 数组、revises、G/L、Gate 决定、Memory ID 或置信分数。

没有 EM 翻转：不调用 Replay 模型，程序生成 `{"entries":[]}` 和明确的 skip receipt；解析失败不能伪装成无翻转。`{"entries":[{"knowledge":[]}]}` 始终非法。

## 8. Gate 与 Selected Skill

Gate 为确定性程序，不读取历史 Memory、不调用模型。先验证 Replay 完整覆盖和来源，再对每条 Effective Update 计算：

```text
G[u] = 已明确关联 u 且 EM 0→1 的当前任务数
L[u] = 已明确关联 u 且 EM 1→0 的当前任务数

patch[u] == ""              → gate_decision = null
G[u] > 0 and L[u] == 0       → Retain
G[u] == 0 and L[u] > 0       → Reject
其他                         → Defer
```

混合收益/退化无论净收益多大都是 Defer；0/0 也是 Defer。未归因事件不计任何 Update 的 G/L；一题最多一票，不按 Knowledge 句子数或模型文字中的数量计票。F1 不投票。不再要求完整 Candidate 的总成功数严格上升，亦无整包接受兜底。

程序结果精确含 `decisions/selection/selected_execution_source`：

```json
{"decisions":[{"update_id":"u1","G":1,"L":0,"gate_decision":"Retain"}],"selection":{"selected_update_ids":["u1"],"selected_text":"The program-composed Skill text.","actual_diff":"The program-computed Parent-to-Selected diff."},"selected_execution_source":null}
```

decisions 按 Effective Plan 顺序覆盖全部 Update，计数为整数；selected_update_ids 仅为 Retain IDs 并保留顺序。Reject/Defer 只是不采用本轮该 patch，不删除 Parent 内的历史规则。下一轮 Parent 使用 selected_text。

执行来源用当前已验证的**完整 Skill 字符串相等**判断，先比较 Parent：相等为 `parent`；否则与完整 Candidate 相等为 `candidate`；两者均不相等为 null。不因模型消息中 strip 后相等、包含相同 Update 或选中部分 patches 而继承执行来源。null 表示本轮未执行的新组合，不记录为“Candidate 已验证”，不把完整 Candidate 分数挂到它名下。下一轮正常 Parent 执行或最终独立 Test 才产生该 Skill 的真实执行。

## 9. Memory 与原子发布

Preconditioner 的模型视图只有：

```json
{"rounds":[{"round_id":"R01","source_updates":[{"id":"u1","text":"The full Effective Update text.","gate_decision":"Retain"},{"id":"u2","text":"Another full Effective Update text.","gate_decision":"Defer"}],"entries":[{"id":"M1","knowledge":{"task_id":"task-A","update_id":"u1","text":"The original event report with its uncertainty."}},{"id":"M2","knowledge":{"task_id":"task-B","update_id":null,"text":"The original unassociated event report."}}]}]}
```

- 初始 `{"rounds":[]}`。round_id 全局唯一；source_updates 为该轮全部 Effective Updates，包括无关联、Reject/Defer、空 patch 的条目；不保存已在 Preconditioner 撤回的 Original 为 Effective Update。
- source_updates 精确含 id/text/gate_decision；Update ID 轮内唯一，跨轮需用 round_id 区分。gate_decision 是 Retain/Reject/Defer/null。
- entries 每项精确含 id/knowledge，每条事件单独获得全局递增 M1、M2…；同一轮 task_id 唯一；knowledge 精确含 task_id/update_id/text。非空关联只引用本轮非空 patch 的 Update。
- events 和 source_updates 按提交轮次追加，不修订、替换、压缩合并或删除旧条目。Preconditioner 可以重新解释旧认识，但不能修改历史报告。
- 本视图不提供历史原始 Parent、diff、context、runs 或分数表。entries=[] 的轮仍提供历史提案与决定；没有关联条目不等于没有事件或无效果。

持久化设计采用独立 v28.4 顺序提交标识（如 `000001`），不采用摘要型 ID 或哈希门槛。提交序号计算 Memory commits，不等同 campaign 轮号；Diagnosis no_change 等分支不会追加 Memory。

提交内容包含 previous head、已验证来源、该轮记录、selection 与 selected_execution_source。单写者锁内比较预期前驱；准备并冻结完整提交，再用同目录原子替换切换 HEAD。**Memory 和 Selected Skill 通过同一 HEAD 一起发布**，随后更新可恢复 campaign 游标。未完成前不得把新 Skill 标记为 committed。

恢复分为当前未发布轮与已发布历史：

- 当前轮：验证实际来源、Editor/Replay、Gate/selection 和待追加记录；准备与发布结果必须一致。已保存且有效的响应直接复用，不能为恢复而重置请求额度。
- 已发布历史：沿用 v29.4 轻量恢复原则，读取提交链、轮次记录、选择结果和已保存的运行身份，验证结构、前驱连续性、序号、ID 与发布一致性；不重新打开历史 Actor 原始来源，不逐轮重新调用上游验证或重算所有历史 Gate。需要深度历史审计时另行只读执行，不作为常规启动/恢复/导出的前置操作。
- Memory HEAD 已提交、campaign 游标落后一轮时，复用已提交本轮结果补完发布；不重新执行 Actor/模型，不重复追加事件。孤立的未发布文件不能自动成为 HEAD。
- 相同内容的重复提交须幂等；同一顺序提交标识已存在不同内容时拒绝覆盖。缺失 HEAD 的非空 store 不得静默初始化为空。

持久化继续采用 SearchQA 的顺序提交 ID 和原文/结构比较，不复制 DocVQA 的摘要型 HEAD、source_digest 或哈希门槛。这与 v29.4 的轻量读取一起定义本版本运行适配：已提交记录被视为已验证检查点，常规加载不提供历史源文件逐项篡改检测保证。完整来源仍归档以供后续审计，不向模型扩展证据权限。

## 10. 短路、停止与恢复

| 分支 | Candidate / Replay / Gate | Memory 与 Skill | 是否继续下一批 |
|---|---|---|---|
| Diagnosis no_change | 均不执行 | 不追加 Memory；Parent 不变，归档该轮结果 | 是 |
| Preconditioner 全 WITHDRAW | 均不执行 | 不追加 Memory；Parent 不变，归档动作 | 是 |
| Editor 全空 patch | 均不执行 | 追加 Effective Updates、gate_decision=null、entries=[]；发布原 Parent | 是 |
| Editor 任一合法 null | 均不执行 | 不提交 Memory/Skill；保留阻塞与已消费额度 | 否，语义停止 |
| 有 Candidate、无 EM 翻转 | Candidate 全批；Replay 模型跳过；Gate 程序执行 | 非空 patches 均 Defer；空 patch 为 null；追加无事件轮，Parent 不变 | 是 |
| 有翻转、全部无法归因 | Replay 正常；Gate G=L=0 | 保存 null 事件；非空 patches Defer；Parent 不变 | 是 |
| 有翻转和有效归因 | 正常 Replay/Gate | 保存全部翻转事件及所有 Effective Updates，发布选择结果 | 是 |
| patch 子集结构非法 | 停在组合校验 | 不发布；保留已完成记录；不自动修复/重采样/退回 Parent | 否 |
| 输入/归档损坏、版本不符 | 停止；不把它包装成模型输出错误 | 不提交，不重置额度 | 否 |
| 模型输出解析/合同不合格 | 按原有有界反馈重试 | 消耗本阶段原额度，不当作 no_change | 额度内重试；耗尽停止 |

所有阶段执行、响应记录、发布边界恢复保持每个调用六次总请求约束。模型/Actor 的具体技术错误分类沿用 SearchQA 已有策略；正常错误答案或合法 KEEP/WITHDRAW/null 不通过抽样获得更好结果。超时/错误后的恢复首先查明已保存响应与已完成阶段，不能无条件重发。完成 20 批后导出最终 selected_text；Test 为独立显式入口，train 完成不自动启动 Test，Test 不反馈到 Memory。独立入口和运行配置已在第 4 步实现，第 5 步已完成 SearchQA 离线验收；本次未启动正式训练或 Test。未来若另行授权训练后自动 Test，由独立监督器编排，不改变训练入口合同。

方法输出反馈沿用 previous_output_validation_error_v1：以冻结的原始输入为基础，只附带最近一次不合格普通输出及对应校验错误，不累积历次失败答案，不暴露隐藏 reasoning 或未授权归档。技术失败、length 与输出校验失败共享该调用的总额度；归档/事实/版本错误直接停止，不包装成模型可修复的输出错误。请求参数和输出预算不随重试提升；合法语义决定不触发反馈重采样。离线验收须覆盖这些边界，不能因 JSON 合法就跳过来源验证。

## 11. 设计示例的解释边界

本文 JSON 是结构示例，不是跨阶段完整模拟轨迹，也不是真实题目或模型结果。`selected_execution_source=null` 只有在实际重组文本不同于已执行 Parent/Candidate 时成立，不能从示例字符串推断。

结构验证能检查字段、引用、覆盖、计数、patch 和发布关系，不能验证自然语言归因的真实性、规则的泛化质量或隐含行为依赖。后续离线测试和真实实验应分别报告这两类结论，不能用手写响应证明新 Prompt 已提升效果。

## 12. 语义指导与验证边界

第 4—6 节的修正方式、完整性与组织建议是模型决策指导，不新增结构拒绝条件。不得用“未输出 Workflow 标题”“新增规则过多”“字数增加”“修改比例不足”触发重试或改写响应。现有字段、引用权限、ID 覆盖、patch 精确定位/组合及发布一致性仍须严格验证。

后续离线验收需覆盖新增、修改、合并、替换、删除、无修改等合法路径及相关边界；手写模型响应只能证明接线和合同，不能证明模型已学会选择合适修正。真实行为应沿 Original→Effective→patch→Candidate/Selected 的链条审阅，效果由独立执行评估。设计阶段静态记录见 [design_validation.json](design_validation.json)；本次离线运行验收及其保证边界见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。
