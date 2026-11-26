# v28.2 设计合同

状态：2026-11-04 已由独立 v28.2 链路实现；实现与离线验收见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。本文约束 v28.2 代码和 [五份提示词](prompts/)；现有 v28.1 运行器不接收这些新结构。所有模型响应为单个英文 JSON 对象；下列字段集合是精确集合，不接受额外字段。正常输出不带 Markdown fences；本文中的代码块仅用于展示合同。

## 1. 身份与版本

| 项目 | 实现值 |
|---|---|
| method.version | `v28_2_campaign_v1` |
| method.stage_contract | `v28_2_stages_v1` |
| 五份 Prompt | `v28_2_searchqa_grouping_v1` / `v28_2_searchqa_diagnosis_v2` / `v28_2_searchqa_preconditioner_v2` / `v28_2_searchqa_editor_v1` / `v28_2_searchqa_replay_v1` |
| Grouping contract | `v28_2_searchqa_grouping_v1` |
| Diagnosis contract | `v28_2_diagnosis_no_checks_v1` |
| Preconditioner contract | `v28_2_preconditioner_actions_v1` |
| Editor contract | `v28_2_editor_mapped_patches_v1` |
| Replay contract | `v28_2_replay_transition_knowledge_v1` |
| Gate contract / gate_rule | `v28_2_gate_selective_em_v1` |
| Memory contract | `v28_2_memory_commit_v1` |
| memory_view | `v28_2_rounds_effective_updates_v1` |
| Grouping/Diagnosis/Preconditioner input view | `v28_2_shared_execution_text_v1` |
| replay_input_view | `v28_2_em_transitions_shared_initial_v1` |
| 普通响应事实视图 | 沿用 `v28_searchqa_pairs_content_v1` |
| Actor / scorer profile | 沿用 `v28_searchqa_actor_answer_element_words_v1` / `v28_searchqa_skilladam_scoring_v1` |
| request_context | 沿用 `searchqa_single_turn_v1` |

Prompt 原文、版本、输入消息和完成响应须一同记录。配置与方法版本、各 Prompt/contract 不一致时，在发送请求之前拒绝；不将 v28.1 或 DocVQA 旧响应重新命名成 v28.2。独立版本不要求把通用纯函数全部复制；代码复用不能带入 DocVQA 的评分、数据或事实校验器。

本次仅提升两个 Prompt 身份到 v2；方法、stage、输入视图及输出合同版本保持不变。配置中的旧 Prompt 身份或保存的旧 Prompt 文本均不能作为当前请求恢复；不重标记旧归档。

## 2. 证据、评分和无损视图

### 2.1 执行事实

保留 SearchQA 已完成训练执行的 `ref/task_id/run_id/initial/attempts/outcome` 投影：

- `initial`：`ref/task/messages`；`task` 保留 question、context；messages 保留原始角色、内容、元数据和顺序。
- `attempts`：恰好一个已接受 stop 回合，含 `ref/request_context/request_messages/assistant`；assistant 仅普通 `role/content`，不含 reasoning_content。
- `outcome`：`ref/status/termination/answer/reference_answers/model_rounds/tool_calls/api_requests/score`；answer 含 `raw_content/extracted_answer`，score 含 `em/f1`。
- P 引用属于当前 Parent，Q 属于 Candidate。P/Q 及 `:0/:1/:outcome` ID 在完整批次中确定，再过滤；过滤后不得重新编号。

完整训练归档先通过数据、完成状态、任务顺序、实际 Skill 和配对验证，再生成模型视图。Test 不可注册为优化证据。技术失败和 length 响应不作为额外推理步骤、候选答案或评分；请求计数不代表模型回合数。

EM 来源是原生评分器的二值数值，允许实际产生的 `0.0/1.0` 和等值 `0/1`，拒绝 bool、其他值与非有限数。F1 必须是 [0,1] 有限数，拒绝 bool，EM=1 时 F1=1。不照搬 v29.2 对 `hard` 的严格整数校验导致合法 SearchQA 浮点 EM 被拒绝。Gate 计数 G/L 始终为非负整数。

### 2.2 Grouping / Diagnosis / Preconditioner 共享视图

在各模块完成证据权限筛选后，增加 `shared_initial={format,messages}`，format 为 `execution_shared_initial_v1`。完整 system 消息按首次出现顺序放入 `messages.system_1` 等；原位置用仅含 `shared_message` 的对象代替；user 消息保持内联。不同 system 文本不能因为逻辑等价就合并。

仅在逐字/结构相等已验证后，省略 `attempts[0].request_messages`（等于该 run 的 initial.messages）和 `outcome.answer.raw_content`（等于 assistant.content）。共享指针解析后必须无损还原原始事实。顶层完整 parent 独立保留，不能用选中某个 run 取代。共享只发生在本次请求，不跨阶段/轮次；指针不构成 Evidence ID。

### 2.3 Replay 共享视图

完整批次验证通过后，先选 EM 翻转 pairs/runs，再用 `replay_shared_initial_v1` 格式共享：相同 system 消息可跨 runs；完全相同的 user 消息序列只在已验证的同一个 Parent/Candidate pair 内共享。其余内联。重复 request_messages/raw_content 的省略规则相同，initial.task 独立保留。不得摘要、截断或从 Parent 重建 Candidate system。

### 2.4 引用权限

| 模块 | 可用引用 | 不可用引用 |
|---|---|---|
| Grouping | 全批当前 Parent runs 及子引用 | Candidate、Memory、历史执行 |
| Diagnosis | 同上，以及提供的 Group IDs | Candidate、Memory、历史执行 |
| Preconditioner | Plan 引用所选当前 Parent runs；Plan 继承的 Group provenance；当前 Original IDs；提供的 Memory IDs | Grouping 描述、未选 runs、Candidate、历史原始执行 |
| Editor | Update ID 只用于 edit 映射 | 无执行或 Memory 检索权限 |
| Replay 每条 Knowledge | 该事件自己的 P/Q pair 及子引用、diff、当前 Effective Update IDs | 其他题执行、未提供题、Memory、Group、Check、历史执行 |

结构化 `basis` 使用单个精确 ID 组成数组，不把 `P1/P5` 塞进一个数组元素。文字中的 `P1/P5/P7`、`P1:1/P5:outcome` 是本地引用列表，各项逐一检查；`R03/P1`、`R03/diff` 仍是历史引用，不能因斜杠解析而获得权限。

Preconditioner/Replay 正式紧凑引用如 `Memory:M1`、`Evidence:P1:1` 需单对反引号，且符合各模块权限。`Update: the rule ...` 等冒号后空格的普通文字不误判为引用；真正不合法的紧凑引用不能通过文字放宽获得权限。不给模型增加不必要的强制引用格式清单；有需要时沿用当前修复后的明确错误反馈。Memory 正文中的旧 P/Q 文本是历史报告，不授权 Preconditioner 访问原记录。

## 3. Grouping

模型输入：`{parent,runs,shared_initial}`，runs 为完整当前 Parent 批次。

输出：

```json
{"groups":[{"group_id":"G1","members":["P1"],"decision_problem":"A task-visible decision problem.","shared_basis":"P1:1 records the response; P1:0 supplies the question and context.","important_differences":[]}]}
```

groups 非空，group_id 唯一；每组 members 非空、去重；所有 run 恰好出现一次。shared_basis 包含每个成员的返回回合直接引用；important_differences 为非空字符串数组或空数组。分组不生成修复假设、优先级或新事实。

## 4. Diagnosis

模型输入：`{parent,runs,grouping,shared_initial}`，runs 仍为全批当前 Parent，包括成功样本。

输出精确为 `decision/reason/plan`：

```json
{"decision":"revise","reason":"A scoped decision change is supported; its effect remains unverified.","plan":{"goal":"Improve the supported decision while preserving valid alternatives.","updates":[{"id":"u1","text":"A complete conditional behavioral change.","basis":["G1","P1:0","P1:1","P1:outcome"]}]}}
```

- decision 仅 `revise/no_change`；reason 非空。revise 要求 plan 精确含 goal、updates，二者非空；no_change 要求 plan=null。
- Update 精确含 id/text/basis；ID 唯一且不与提供的证据/Group IDs 冲突；text 非空；basis 非空、去重、仅授权精确 ID，必须含直接执行证据。引用某 Group 时，同一 basis 至少直接引用其一个成员。
- 没有 Checks，也没有 need_evidence。条件、例外、依赖、强度、优先级和保护边界都写进 text。
- Prompt v2 按有证据支持的共同决策问题及修正方向组织 Update；相同错误标签不自动合并不同修正，任务/Group 和预期成败/去留不决定边界。同一修正的必要动作、条件和依赖保持完整，不强制固定数量。
- **reason 不传给 Preconditioner**。依据 Plan 内直接执行引用选择完整 runs；Group 不自动展开所有成员。关键成功例、反例及适用范围证据必须进入对应 basis，不能只出现在 reason。

执行错误本身不证明 Parent 指导有缺陷。提案需说明可用的判断增量；可删改或协调旧指导，没有合理修正时允许 no_change。成功与反例用于确定动作/范围/优先级，不要求配对案例；参考接受性不证明形式偏好，未执行提案不声称已改善。这些是 Prompt 决策要求，不增加结构字段，也不由结构校验器证明其语义正确。

## 5. Preconditioner

模型输入：`{parent,plan,runs,memory,shared_initial}`。plan 是冻结的完整 Original Plan；runs 是 Plan 直接引用的当前 Parent 子集；memory 是第 9 节只读轮次视图。Grouping 描述、Diagnosis reason、历史原始执行不传入。

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

KEEP 审查整条提案；附带的名称、编码、单位、范围等变化需要相关依据或必要性。部分内容无依据时用完整 REPLACE 保留合理修正和必要配合。实际成功保持只能依据明确提供的执行/历史内容，缺少事件或关联不能补出保持证据；不引入新的 Knowledge 类别或统计字段。

全部 KEEP 仍进入 Editor；全部 WITHDRAW 得到 effective_plan=null，保留 Parent、继续下一批。撤回依赖时必须在现有 Original 范围内协调相关 Update；不偷偷新增依赖字段或另做 Diagnosis。

## 6. Editor 与组合

模型输入：`{parent,plan}`；plan 精确为 goal/updates，Update **仅含 id/text**。basis、runs、Memory、Diagnosis/Preconditioner reason 均不传入。

输出：

```json
{"edits":[{"update_id":"u1","patch":"--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Old guidance.\n+Revised guidance.\n","reason":"Implemented this Update against the original Parent."}]}
```

每条 Effective Update 恰好一个 edit，精确含 update_id/patch/reason，reason 非空。

| patch | 含义 | 行为 |
|---|---|---|
| 非空 diff | 实际修改 | 参与共同构造与后续选择 |
| 精确空字符串 | 原始 Parent + base 已满足该 Update | 不分配收益/退化，不产生修改级 Gate 决定 |
| null | 不能忠实实现的语义阻塞 | 整轮停止，不构造部分 Candidate，不重采样 |

空白字符串不是空 patch；格式非法、定位失败或冲突是校验失败，不自动转成 null/空串。某条空 patch 的判断基于原始 Parent，不依赖另一 patch 将添加的内容。

patch 合同完整继承当前 v29.2 mapped-patches 语义：

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

持久化设计采用独立 v28.2 顺序提交标识（如 `000001`），不采用摘要型 ID 或哈希门槛。提交序号计算 Memory commits，不等同 campaign 轮号；Diagnosis no_change 等分支不会追加 Memory。

提交内容包含 previous head、已验证来源、该轮记录、selection 与 selected_execution_source。单写者锁内比较预期前驱；准备并冻结完整提交，再用同目录原子替换切换 HEAD。**Memory 和 Selected Skill 通过同一 HEAD 一起发布**，随后更新可恢复 campaign 游标。未完成前不得把新 Skill 标记为 committed。

恢复时按前驱链读回原文/结构，验证轮次、ID、来源和任务关系，并由已保存 Editor/Replay/执行重新计算 Gate、selection、Memory 追加结果。相同提交重复恢复须幂等；不同内容占用同一提交标识时拒绝，不覆盖；已发布提交后不再次发模型/Actor 请求或追加相同事件。保留完整来源和响应记录以支持这些比较，不能仅靠指针名字或状态摘要判定完成。

这是对 v29.2 持久化方式的 SearchQA 适配，保持追加与原子发布语义，满足 v28.1 不使用哈希防御的边界。不能将复制 v29.2 的 `_digest`/摘要 HEAD 实现称作已满足此合同。

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

所有阶段执行、响应记录、发布边界恢复保持六次总请求约束。模型/Actor 的具体技术错误分类沿用 SearchQA 已有策略；正常错误答案或合法 KEEP/WITHDRAW/null 不通过抽样获得更好结果。超时/错误后的恢复首先查明已保存响应与已完成阶段，不能无条件重发。完成 20 批后导出最终 selected_text；Test 独立，不反馈到 Memory。

## 11. 设计示例的解释边界

本文 JSON 是结构示例，不是跨阶段完整模拟轨迹，也不是真实题目或模型结果。`selected_execution_source=null` 只有在实际重组文本不同于已执行 Parent/Candidate 时成立，不能从示例字符串推断。

结构验证能检查字段、引用、覆盖、计数、patch 和发布关系，不能验证自然语言归因的真实性、规则的泛化质量或隐含行为依赖。后续离线测试和真实实验应分别报告这两类结论，不能用手写响应证明新 Prompt 已提升效果。
