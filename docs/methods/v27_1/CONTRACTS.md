# v27.1 模块与运行合同（设计初稿）

状态：2026-11-04，**已按本合同完成独立实现与离线验收**，见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。本文与[四份提示词](prompts/)共同定义运行行为；[实验参数](README.md#6-拟固定实验设计)及 experiment_plan.json 是设计材料，不是可执行配置。所有模型输出为单个英文 JSON 对象，字段精确，不接受额外字段、重复 JSON key、非有限数或 Markdown 包裹。以下代码块仅说明结构。

## 1. 身份与版本隔离

| 项目 | 值 |
|---|---|
| method.version | `v27_1_campaign_v1` |
| stage / runtime | `v27_1_stages_v1` / `v27_1_light_runtime_v1` |
| Prompt | `v27_1_lmb_diagnosis_v1` / `v27_1_lmb_preconditioner_v1` / `v27_1_lmb_editor_v1` / `v27_1_lmb_replay_v1` |
| Diagnosis / Preconditioner contract | `v27_1_diagnosis_direct_evidence_v1` / `v27_1_preconditioner_direct_evidence_v1` |
| Editor / Replay contract | `v27_1_editor_mapped_patches_v1` / `v27_1_replay_transition_knowledge_v1` |
| Gate / Memory contract | `v27_1_gate_selective_em_v1` / `v27_1_memory_commit_v1` |
| Diagnosis/Preconditioner input view | `v27_1_shared_execution_text_v1` |
| Replay input view | `v27_1_em_transitions_shared_initial_v1` |
| Memory model view | `v27_1_rounds_effective_updates_v1` |
| Actor execution profile | `lmb_single_turn_65536_six_v1`；原行为协议，显式绑定 65,536 |
| Actor prompt profile | 沿用 `lmb_answer_element_words_v2` 原文 |
| Scorer / facts / request_context | 沿用 `v27_lmb_em_v1` / `v27_lmb_facts_v1` / `lmb_single_turn_v1` 的内容语义 |
| Method retry / semantic_resampling | `previous_output_validation_error_v1` / false |
| Knowledge review | `disabled_v1` |

这些新身份尚未注册于代码。新方法必须使用独立配置、campaign、Memory、请求日志和 Test 目录；不复用旧版本的学习产物或模型响应。记录实际 Prompt 原文、版本、配置、输入消息、输出和来源。配置、版本、冻结原文或任务对应关系不符时，发送请求/恢复前拒绝；不能只改旧归档标识冒充新版本。

不产生 Grouping Prompt、contract、结果、目录或预算。可以复用纯函数，但不能直接借用会重新要求 Grouping、旧 Checks、旧 Gate 或旧 Memory 的完整验证链。旧 v27 scorer ID 只标识评分；不得因复用它而调用旧整包 Gate。65,536 应通过独立显式配置绑定，不靠改变全局 v27 常量影响其他运行。

## 2. 数据、Actor 与评分事实

### 2.1 数据与输入

使用原 `v27_lmb_skilladam53_v1` 成员视图：35 Train + 18 Selection 合并为 53 train，Test 124，177 个唯一 ID；成员与顺序见 [experiment_plan.json](experiment_plan.json)。不采用 prepared_v1 的 35/17/125 分组作为本实验划分。保留 source_split，内容 revision、任务顺序、原题干处理、选项文本与映射不变。

按原 `shuffle_choices` 以 seed=42 和 task ID 生成确定性置换，重新标 A–E，并同步正确标签。Parent/Candidate 必须使用同一题目和同一呈现；重复选项文本不能用于替代原始标签置换身份。此 seed 只控制选项顺序，不声称控制模型采样。

Actor 请求保持原 system/user 模板、Skill 插入位置和题干/五选项呈现。Actor 只收到固定协议、当前 Skill、题干、呈现选项；不传 reference、score、Memory、原始定理/证明草图元数据或其他任务。原题干/选项中已有数学文字不得删去。单轮、无工具、无额外解释请求。运行参数为 Actor 65,536、300 秒、连接 10 秒、六次总尝试；其他值见实验设计。

### 2.2 原评分与格式标志

评分来源为 [v27 scoring.py](../../../src/skill_evolution/v27/benchmarks/lmb/scoring.py)、[原生 extraction](../../../external/SkillAdam/skilladam/benchmarks/lmb/evaluation.py)和[choice normalization](../../../external/SkillAdam/skilladam/benchmarks/lmb/choices.py)：

1. 只以普通 content 构造 `{"response": content}`，不接受 provider 的 answer/predicted_answer 覆盖。
2. 取最后一个完整 answer 元素（大小写不敏感、允许跨行）；没有时取最后一个非空行，空输出取 strip 后文本。
3. 优先把全文按 `strip → upper → rstrip(".):")` 解析为呈现标签；否则尝试 strip 后全文与选项文本 casefold 精确相等；再否则尝试首个空白分隔 token 的标签规范化。
4. `em = int(predicted_label == mapped_correct_label)`；`f1 = em`。解析无效为 EM=0，不新增数学等价、语义分或参考答案。
5. 保留 `parse_valid` 与原 `format_compliant` 计算。后者检查一个完整 answer 捕获、相应标记计数以及捕获内容 strip 后为大写 A–E；没有完整验证元素外无文字。基础协议仍要求一个元素、单标签、元素外无文字且无嵌套元素，不能把该标志当作完整协议验证器。两标志不改变 EM 或 Gate。

LMB facts 接受实际原生二值数值 0/1 及等值 0.0/1.0，拒绝 bool、非有限值或其他数；em 必须等于 f1。G/L 一律是非负整数。不得把 SearchQA 的 token F1 或 DocVQA hard/ANLS 阈值迁入。

### 2.3 普通执行事实

沿用 LMB 完整事实，不添加 `reference_answers` 或 SearchQA context 字段：

| 对象 | 精确字段/约束 |
|---|---|
| run | `ref/task_id/run_id/initial/attempts/outcome` |
| initial | `ref/task/messages`；task 精确为 `question/choices`；choices 为五个 `label/text` |
| attempts | 恰好一个完成 stop 回合：`ref/request_context/request_messages/assistant` |
| assistant | 仅 `role/content`；完整普通文本，不含 reasoning_content |
| outcome | `ref/status/termination/answer/model_rounds/tool_calls/api_requests/score` |
| answer | `raw_content/extracted_answer/predicted_label/predicted_text/parse_valid/format_compliant/correct_label/correct_text` |
| score | `em/f1`，二值且相等 |

initial.messages 为实际 system/user 文本和原顺序；system 保留该次实际 Skill，Candidate 不可重标为 Parent。Parent/Candidate 使用不同 run_id、相同 task_id；映射标签、参考选项、请求、分数和普通 content 必须对应真实归档。运行配置、完成状态和数据成员先验证，再形成方法视图。

P/Q 及 `:0/:1/:outcome` 在完整批次中确定后过滤，不重编号。model_rounds=1、tool_calls=0；api_requests 是物理请求数，不能解释为推理步数。失败/length 尝试只归档，不进入 completed run；六次耗尽不伪造零分或完整 pair。原始隐藏字段、Test 执行或非当前 Skill 执行不得注册成优化事实。

## 3. 无损共享与引用权限

Diagnosis/Preconditioner 的模型视图使用 `shared_initial={format,messages}`，format=`execution_shared_initial_v1`。完整相同的 system 消息按首次出现依次存为 system_1 等，原位置改为仅含 shared_message 的指针；user 保持内联。顶层 parent 独立保留。逐字/结构一致后才省略重复 `attempts[0].request_messages` 和 `outcome.answer.raw_content`，分别由本 run 的 initial.messages 与 assistant.content 恢复。其他事实字段不删减。

Replay 先验证完整批次，再筛选 EM 翻转，使用 format=`replay_shared_initial_v1`；相同 system 可跨 runs 共享，完全相同的 user 消息序列只在已验证的同一 pair 内共享。其余内联，同样省略已验证重复字段。initial.task 的完整 question/choices 保留。任何共享都不摘要、截断、规范化或从 Parent 重建 Candidate 请求，必须精确可逆。

| 模块 | 可引用 | 不可引用 |
|---|---|---|
| Diagnosis | 当前全批 Parent runs 和子引用 | Group、Candidate、Memory、历史执行 |
| Preconditioner | Plan 所选当前 Parent runs、当前 Original IDs、提供的 Memory IDs | Group、未选 runs、Candidate、历史原始执行 |
| Editor | Update IDs 用于 patch 映射 | 无运行/Memory 检索权限 |
| Replay 单条事件 | 自己 task 的 P/Q 及子引用、diff、当前 Effective Update IDs | 其他任务、未翻转任务、Group、Memory、Checks、历史执行 |

共享表键不是证据 ID。引用策略为 `v27_1_explicit_prose_references_v1`，Diagnosis、Preconditioner、Replay 和 Plan 执行筛选使用同一自由文本规则。数学对象名与执行编号可能重名，不能据此推断来源。

- 自由文本中的裸 `G1`、`P12`、`Q12`（包括单独放在反引号中）是普通文本；裸 `P1/P2` 也可能是多项式商，不据此拒绝输出或选择 runs。是否恰好存在同名执行不改变解释。
- `basis` 等结构化引用字段仍按精确 ID 校验：`P1` 可表示整次执行，`P1:1` 可表示子引用；不存在的 ID、Group ID、重复 ID、用一个 `P1/P2` 元素代替两个 ID 均拒绝。Replay 的 task_id/update_id 和调整 target 权限不变。
- 自由文本的 `P1:1`、`P1:outcome` 是明确执行引用；含子引用的列表（如 `P1/P2:outcome`、`P1:1/P2:outcome`）逐项验证。数值范围仍展开并校验，不允许跨执行或倒序范围。
- `R03/P1`、`R03/diff`、`campaign_R03/P1` 以及带子引用的历史路径仍视为历史来源，不得扩权。
- 三个模块的紧凑命名空间引用均需单对反引号，如 `Evidence:P1`、`Evidence:P1:1`。Preconditioner 可引用提供的 `Memory:M1` 和当前 `Update:u1`；Replay 可引用本事件 P/Q、`Evidence:diff` 和当前 Update。不存在的来源、明确的 `Group:G1`/Check 来源和错误引用语法仍拒绝。`Group: the mathematical object ...` 等带空格的普通标签不视为引用。已验证的命名空间标记按其声明类型解释，不再把 Update/Memory ID 中类似执行编号的文本重复解析为执行来源。

Diagnosis、Preconditioner、Replay 的引用说明已同步上述解析规则；Editor 保持原文。不要求模型改写数学符号。裸来源名与同名数学对象无法仅凭字符串可靠区分，因此不做启发式来源判定；重要依据仍由结构化 basis 保证。没有扩大可检索的来源集合。

## 4. Diagnosis

程序事实束保留 `facts/background/sources/round_id`；facts 只有 parent/runs，没有 grouping。这是确定性事实构造，不是新模型阶段。模型输入精确为 `{parent,runs,shared_initial}`，包含全批成功与失败。

```json
{"decision":"revise","reason":"A visible choice distinction supports a scoped hypothesis; the internal calculation is unobserved.","plan":{"goal":"Improve a supported option comparison while preserving valid alternatives.","updates":[{"id":"u1","text":"A complete conditional behavioral change.","basis":["P1:0","P1:1","P1:outcome"]}]}}
```

- 输出精确 `decision/reason/plan`。decision 为 revise/no_change；reason 非空。
- revise 的 plan 精确 `goal/updates`，goal、updates 非空；Update 精确 `id/text/basis`，ID 唯一、不与执行证据 ID 冲突，text 非空，basis 非空、去重且每项有权限。
- no_change 的 plan=null，含义是未形成合理更新，不是 Skill 完美，也不是技术失败的替代状态。
- 没有 Checks、need_evidence、固定 Update 数量或每题一条提案要求。保留原 v29.4 的 focused intervention、independently justified/actionable、必要依赖及合理探索自由度。
- 所有触发、动作、强度、例外、依赖和保护边界写入 text。只写进 reason 的要求不会传到下游。

Preconditioner 的执行筛选读取**Plan goal/Update text 的明确引用，以及结构化 basis 的精确 ID**，按原批次顺序去重、交付完整 runs；不扫描 Diagnosis reason、Update ID 或裸数学符号。重要支持和保护边界的证据仍要求进入对应 basis。不用 Group 展开其他执行。

## 5. Preconditioner

模型输入精确 `{parent,plan,runs,memory,shared_initial}`；plan 为冻结 Original，runs 为第 4 节选中的执行，memory 为第 9 节视图，parent 独立完整。不接收 Diagnosis reason。

```json
{"adjustments":[{"target":"u1","action":"KEEP","text":null,"reason":"The scoped proposal remains a justified experiment under the supplied evidence."}]}
```

每个 Original 恰好一个 adjustment，精确 `target/action/text/reason`，reason 非空：

| action | text | 编译行为 |
|---|---|---|
| KEEP | null | 原 Update 全文保留 |
| REPLACE | 完整非空且与原文不同的字符串 | 全文替换 text，不接受 diff/省略片段 |
| WITHDRAW | null | 移除该 Update，不用空字符串表达撤回 |

D/S/C 是判断方法，不新增字段。不得新建、拆分、合并 ID 或另起无关 Diagnosis。编译保留 goal、存活 Update 的顺序、id、basis；basis 仍是原提案来源，不声称重新证明 REPLACE 文本。Original 永不原地修改。

KEEP 审查整条要求，不能只认可主方向；附加触发、fallback、顺序与强度也属于判断范围。修正必须进入全文 text，不能只出现在 reason。撤回必要前提时在原有提案范围内协调其他 Update，不增加依赖求解器。全部 KEEP 继续 Editor；全部 WITHDRAW 得到 effective_plan=null，保留 Parent 并继续下一批，不追加 Memory。

历史 Knowledge、明确关联和 Gate 决定不等同独立因果证据。null 不给某条 Update 增益/损失归因；Retain 不证明当前 Parent 仍保留该规则；Defer 不等于有害或无效；entries=[] 不是失败实验结论。保持 v29.4 方法，不另加 v29.3/v28.2 v2 的审查流程。

## 6. Editor 与 patch 组合

模型输入精确 `{parent,plan}`，plan 为 `goal/updates`，Update **只有 id/text**。不传 basis、runs、参考、Memory 或上游 reasons。Parent 为完整字符串或 null，正式实验从原非空 Skill 开始，合同保留空/null 边界。

```json
{"edits":[{"update_id":"u1","patch":"--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Old guidance.\n+Revised guidance.\n","reason":"Implement the effective requirement against the original Parent."}]}
```

edits 覆盖每个有效 Update 恰好一次，精确 `update_id/patch/reason`；reason 非空。patch 非空字符串为实际修改，精确空串表示原 Parent + base 已满足，null 表示不能忠实实现、整轮语义停止。空白串不是空 patch。无关改进、隐藏合并 ID、弱化要求或用其他 patch 的未来效果冒充“已满足”均不允许。

1. 现有 Parent 头为 `--- a/SKILL.md` / `+++ b/SKILL.md`；null 旧头为 `/dev/null`。null/精确空 Parent 的每个非空 patch 为一个纯添加 hunk。
2. hunk 头仅 `@@`，无行号/计数/说明。每行以空格、-、+ 开始，余下为字面内容。保留空格、Markdown、行尾与 `\ No newline at end of file` 身份。
3. context/deletion 唯一精确定位。单 patch 内 hunks 按原位置递增，连同 context 不重叠；没有模糊匹配、自动修复、重排或全文回退。
4. 所有 patches 定位同一原始 Parent，不按前一 patch 的结果串行定位。跨 Update 只读 context 可共享；同一行唯一可定位且不重叠的字符修改可组合。单行替换用最大相同前后缀定位一个连续区间；重复文本导致前后缀重叠/歧义则拒绝，不猜多个变化岛。
5. 实际改动区间重叠拒绝，即使内容相同；区间内部插入拒绝，边界插入允许；同一间隙插入按 Effective Update 顺序，不按模型 edits 顺序。
6. 全部校验后共同构造非空、与 Parent 不同的 Candidate 和 actual_diff。没有独立 Update Actor 执行。全部空 patch 走 editor_no_change；任何合法 null 不构造部分 Candidate。
7. Gate 子集仍对原 Parent 按 Effective Update 顺序组合。空选择严格返回原 Parent；非空选择重组须结构合法且非空。子集可能抵消回 Parent，以实际文本判断来源。

组合器验证定位、改动冲突与文本结构，不验证自然语言依赖或行为独立性。必要耦合应在完整 Update 中表达；出现非法子集时停止，不自动删 patch、修复、重采样或退回整包 Gate。

## 7. Candidate 与 Replay

Candidate 用本轮同一完整批次、Actor 配置、呈现选项、映射和 scorer 独立执行；没有 Parent 答案、评分或参考反馈。Parent 复用本轮已经用于 Diagnosis 的执行，不再采样。

完整 pair 校验包括任务与顺序、完成状态、实际执行 Skill、消息、选项和评分；在此之后才筛选 `parent_result.em != candidate_result.em`。未翻转任务即使换成另一个错误选项、格式标志改变，也不发给 Replay。所有翻转的原 P/Q 身份保留。

模型输入精确 `{parent,diff,plan,edits,pairs,runs,shared_initial}`：

- parent 为原 Skill；diff 为程序实际 Parent→完整 Candidate 差异。
- plan 的 Update 仅 id/text；edits 每项仅 update_id/patch，无理由；均按 Effective Plan 顺序。空 patch 可在清单内，null 不可出现在已执行 Candidate。
- pair 精确 `parent/candidate/task_id/parent_result/candidate_result`；result 精确 `status/model_rounds/tool_calls/api_requests/em/f1`。用显式 pair 对应，不能按邻接推测。
- runs 为所选 pair 的完整允许文本投影，按第 3 节共享。
- 不提供 Memory、basis、Checks、上游 reasons、当前 Gate 或未翻转结果。

```json
{"entries":[{"knowledge":[{"task_id":"task-A","update_id":"u1","text":"A synthetic option-content difference supports a limited association with the implemented change, with EM moving from 0 to 1; no internal proof is observed."},{"task_id":"task-B","update_id":null,"text":"A synthetic regression from EM 1 to 0 is observed, but no single implemented Update can be distinguished as responsible."}]}]}
```

有翻转时 entries 恰好一个对象，只含非空 knowledge；每个翻转 task_id 恰好一条，精确 `task_id/update_id/text`，text 非空。非空 update_id 只允许指向本轮非空 patch 的 Effective Update。明确关联需要实际 patch 的行为与具体选项内容/可见回答变化相联系；题目同类、标签翻转或参考匹配本身不足。多 Update 无法区分、不可分联合影响或无明确关联时用 null，仍保存事件。

每条 Knowledge 自足，记录题目条件、双方实际选择差异、EM 方向、关联或限制；只引用本 task 的 P/Q 及 diff，不借另一题证明。禁止 evidence 数组、revises、attributions、Memory/round ID、G/L、置信度、Gate 决定或下一轮 Plan。程序按原任务顺序规范化事件，每条以后单独分配 Memory ID。

无 EM 翻转时不分配 Replay 模型请求槽，由程序生成 `{"entries":[]}` 与 `replay_called=false/replay_skip_reason=no_em_transitions` 回执。`{"entries":[{"knowledge":[]}]}` 始终非法；有翻转不能靠返回空数组或漏题绕过归因。

## 8. Gate 与 Selected Skill

Gate 是确定性程序，无模型调用、无历史投票。对已验证当前事件，按每个非空 update_id 对应 pair 的实际 EM 计数，不从正文抽取模型自报分数：

```text
G[u] = 明确关联 u 的 EM 0→1 任务数
L[u] = 明确关联 u 的 EM 1→0 任务数

patch[u] == ""           → null
G[u] > 0 且 L[u] == 0    → Retain
G[u] == 0 且 L[u] > 0    → Reject
其他                     → Defer
```

混合正负无论净收益多少都 Defer，0/0 也 Defer。null 关联不投票，但保留在 Memory；f1、格式、历史决定不投票。完整 Candidate 不必总分严格上升，没有整包风险否决或接受兜底。

输出精确 `decisions/selection/selected_execution_source`。decisions 按 Effective Plan 顺序，每条 `update_id/G/L/gate_decision`；selection 为 `selected_update_ids/selected_text/actual_diff`，只包含 Retain IDs 并保持原顺序。Reject/Defer 只不采用本轮 patch，不删除 Parent 中历史规则。

selected_execution_source 按**完整原 Skill 字符串相等**判断：先与 Parent 相等为 parent，否则与完整 Candidate 相等为 candidate，否则 null。不是按 Actor 插入时 strip 后的文本判断，也不能从 patch 数量推断。新组合不得冒用 Candidate 分数或声称已验证；下一轮 Parent 执行或最终 Test 才产生它的真实结果。

## 9. Memory 与发布

Preconditioner 的唯一历史模型视图为：

```json
{"rounds":[{"round_id":"R01","source_updates":[{"id":"u1","text":"Complete historical Effective Update.","gate_decision":"Retain"},{"id":"u2","text":"Another complete historical Effective Update.","gate_decision":"Defer"}],"entries":[{"id":"M1","knowledge":{"task_id":"task-A","update_id":"u1","text":"Original event report and its limits."}},{"id":"M2","knowledge":{"task_id":"task-B","update_id":null,"text":"Original unassociated event report."}}]}]}
```

初始 `{"rounds":[]}`。每轮保存全部 Effective Updates，包括无事件、Reject/Defer、空 patch 条目；不把 Preconditioner 已撤回的 Original 当作有效修改。source_update 精确 id/text/gate_decision；Update ID 轮内唯一。round_id 唯一；entry ID 全局递增 M1、M2…，每个 entry 一个事件，一轮 task_id 不重复，关联不能跨轮。空 patch 的 gate_decision=null。entries=[] 时仍记录有效提案和决定。

历史按发布顺序追加，不替换、合并、删除或压缩改写；后续可重新解释历史，但不修改过去报告。历史原始 Parent、diff、question/choices、runs 和分数表不进入模型视图。没有条目不证明成功保持、无改善或未执行。

采用 v28.3 的顺序提交 ID（000001 等）和原文/结构比较；不引入 DocVQA 内容摘要 HEAD 或新的源码哈希门槛。**这是运行持久化选择，不改变 v27 数据内容校验与当前执行归档本身已有的身份/摘要字段**；SHA-256 用于既有数据校验或确定性选项打乱也不受影响。不为本次设计新增全仓库扫描门槛。

一次提交包含前驱、已验证本轮来源、追加轮记录、Selected 和执行来源。在单写者锁内核对预期 HEAD，完整准备后原子替换同目录 HEAD，使 Memory 与 Selected 经同一提交一起可见，再更新可恢复游标。相同提交重复操作幂等；同 ID 内容不同、陈旧 HEAD、非空 store 缺 HEAD 时拒绝，不静默初始化或覆盖。提交序号不是 campaign 轮号。

常规加载校验已发布提交的结构、前驱、序号、ID、选择结果和运行身份；不重开全部历史 Actor 来源或重新计算每一轮 Gate。当前未发布轮仍完整校验事实、patch、Replay、Gate 和待提交内容。若 HEAD 已发布而游标落后一轮，用已提交记录补完发布，不重发请求或重复追加。孤立未发布文件不能自动成为 HEAD。

该轻量路径以已提交记录为已验证检查点，不承诺每次加载都检测历史源文件逐项变动。来源归档保留，但不新增独立深度审计工具或把历史重放放回正常运行路径。旧 v27 存储不原地迁移。

## 10. 分支、失败和恢复

| 分支 | 执行行为 | 发布与继续 |
|---|---|---|
| Diagnosis no_change | 不执行 Preconditioner/Editor/Candidate/Replay/Gate | Parent 不变，不追加 Memory，继续下一批 |
| 全 WITHDRAW | 不执行 Editor/Candidate/Replay/Gate | Parent 不变，不追加 Memory，继续 |
| 全空 patch | 不执行 Candidate/Replay/Gate | 追加有效提案、null 决定和空事件，发布原 Parent，继续 |
| 任一合法 null patch | 不构造部分 Candidate | 整轮语义停止，不发布新 Memory/Skill，不重采样 |
| Candidate 无 EM 翻转 | 跳过 Replay 模型，运行 Gate | 非空 patch Defer，追加无事件轮，保留 Parent，继续 |
| 所有翻转无法归因 | 正常 Replay，G=L=0 | 保存 null 事件，非空 patch Defer，保留 Parent，继续 |
| 正常归因与选择 | Replay→Gate→组合 | 保存所有事件与有效提案，发布 Selected，继续 |
| 子集组合非法 | 停在组合验证 | 不修复、重采样、改投票或退回旧 Gate，不发布 |
| 输入/事实/版本/归档损坏 | 直接停止 | 不伪装成模型输出错误或重置额度 |
| 输出解析/合同不合格 | 原冻结输入 + 最近普通输出及错误，有界反馈重试 | 消耗本阶段既有六次额度，耗尽停止 |
| 响应已保存/阶段已完成 | 先校验并复用有效记录 | 不重复请求、不把恢复当新槽 |
| Memory 已提交、游标未更新 | 补完单轮发布 | 不重复事件或模型调用 |

Actor 首次/技术错误/length 共六次，方法技术错误/length/输出错误共六次；没有隐藏 SDK 重试、预算升级、技术错误免计或自动外层恢复。正常 stop 错误答案与格式不合规不触发生成。保存失败请求和已用额度；缺失或不一致的完成记录不能被当成未执行而盲目重发。语义 null 阻塞不得通过原配置重采样绕过。

六批完成后才能正式导出最终 Skill。Test 独立入口使用同一数据成员/顺序、Actor 协议与预算和最终 Skill；不反馈 Memory、不按 Test 选 checkpoint。124 题全部完整后才发布正式 EM；未完成时列明 pending/errors，正式 EM=null，不能补零分或把 completed-only 分数冒充完整成绩。原文请求及响应保持可追溯，数据与归档错误不进入模型可修复反馈。

## 11. 实现验收要求与设计检查边界

离线验收要求覆盖：177 题成员/映射/原评分等价；标签 fallback 与格式标志区别；Actor 与方法输入白名单；四阶段无 Group；Plan 引用筛选；共享视图精确还原；所有调整和 patch/子集分支；EM-only/null/空 patch 计数；追加与发布中断；六次额度和已完成请求复用；跨版本拒绝；合成 53 题六轮及 124 Test 调度。使用合成模型响应并阻断真实模型网络。

原设计阶段仅检查文档、来源快照、预算/身份一致性、JSON 示例和链接，不导入执行器、不运行离线实现测试。静态检查不能证明自然语言归因正确、隐含依赖完备或真实成绩提高。提示词示例中的 task-A/task-B 和数学关系为虚构结构说明，不来自真实 Test，也不是完整可运行轨迹。
