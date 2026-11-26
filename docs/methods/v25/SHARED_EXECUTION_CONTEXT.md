# V25 共享执行上下文

本文定稿 Actor 的能力、信息边界和停止语义，作为后续各模块 Prompt 的共同依据。数值表区分已确认的预算、已确认的预览长度检查与错误截取规则，以及其他推荐值；这些内容组成一套完整的首版方案，尚未成为生效的运行配置。本轮不修改运行代码，不启动实验。

本次选择：完整 Python 程序生成；当前任务内保留完整消息历史；所有阶段不向 Actor 提供评分反馈；首次正常执行并产生可打开的输出工作簿就提交。事后评分用于优化任务的分析与比较，不能使已结束的 Actor 继续修正。Test 的事后评分仅进入最终报告。

## 1. Actor 的输入与能力

| 对象 | 可以看到或使用 | 不包含 |
|---|---|---|
| Actor 初始请求 | 固定系统说明、当前完整 Skill、任务指令、任务类型、答案区域及所属工作表、固定输入预览、代码轮数上限 | 标准答案文件或内容、评分、Memory、其他任务或另一侧执行记录 |
| Actor 后续请求 | 原始系统和任务消息、本任务此前完整代码响应、实际返回的格式／执行／输出文件错误、剩余代码轮数 | 评分器发现的错误单元格、评分器发现的缺失工作表、隐式补充的工作簿内容 |
| 模型工具 | 无独立工具调用；每轮输出一份完整 Python 程序，由外部执行器运行 | shell、文件浏览、交互式 Python、联网检索、独立的工作簿探索调用 |
| 生成的程序 | Python 标准库、openpyxl、pandas；完整原始输入工作簿；当前尝试的输出及临时目录 | 标准答案、其他题目及执行产物、前次尝试的临时文件、网络、外部命令执行 |
| 输出 | 在 `OUTPUT_PATH` 保存一份 `.xlsx`；返回单个 `python` 围栏代码块 | 多个候选文件供评分器择优；仅返回说明、补丁或对上一轮代码的局部修改 |

标准库可用不代表开放宿主文件系统、网络或子进程。建议实现时使用独立执行容器，仅放入运行依赖、当前输入与当前尝试的可写空间，关闭网络；评分在 Actor 程序之外进行。容器中不放标准答案或 API 凭据。仅改变工作目录不是文件访问隔离。这里规定的是实际能力边界，尚未声称隔离后端已经实现或验收。

固定系统说明负责协议，不增加表格解题策略。Skill 放在系统消息中固定的 `Skill` 区域，每题执行期间不变。初始 Skill 保留 SkillOpt 原文；其中“探索、执行、检查”等步骤通过生成程序和执行器完成，不能解释成额外工具权限。

执行器绑定 `INPUT_PATH` 和 `OUTPUT_PATH`。保留此前路径适配方案：仅适配简单、独立的顶层路径变量赋值，并同时保存原始响应和实际执行代码；其他重新绑定返回格式／协议错误，不猜测或改写解题算法。具体允许语法及对应样例在实现阶段离线验收。

**完整文件读取能力不等于模型已观察到完整文件。** 模型直接观察的范围以实际请求文本为准；程序可能读取预览之外的数据，但仅凭代码中出现读取语句，不能证明某个分支被执行，更不能证明模型事先知道读取结果。

## 2. 历史、尝试与停止

每个任务开始时只有系统消息和初始任务消息。每次获得完整响应，将该响应原样加入历史；若允许继续，再追加本次运行反馈。后续请求保留这一完整序列，不只保留最近两步，不自动总结、不删除旧尝试。Actor 不直接读取 Memory，也不保留跨任务会话。

每个代码尝试使用新的目录和原始输入副本。重试代码需要自包含，不能依赖上次定义的 Python 变量或生成的文件。API 重试保持同一请求消息，不增加代码轮数；完整但格式错误的响应消耗一个代码轮次。空响应、输出达到额度而被截断等已完成的模型生成也消耗轮次，不因其不可执行而获得免费重采样。传输失败且未得到完整响应，使用同一轮的请求重试额度，不把片段当程序执行。

推荐最多 30 个代码轮次。初始请求显示 `max_code_attempts=30`；第 n 个完整响应处理后，如果还有下一轮，反馈显示 `code_attempts_used=n`、`code_attempts_remaining=30-n`。剩余数包括下一次生成，不能把“剩余 1 次”解释成还可修正两次。时间和请求额度可能使任务更早结束；不在模型请求中维护不断变化的秒级倒计时。

| 触发条件 | 动作 | 能否继续 Actor |
|---|---|---|
| 响应格式不合规、程序异常或执行超时、输出不存在或无法打开 | 保存实际错误；仍有轮数和时间时返回有限错误信息 | 可以，使用剩余预算 |
| 程序正常退出，指定输出存在且能作为 `.xlsx` 打开 | 固定此产物，结束 Actor，之后评分 | 不可以，即使评分不通过 |
| 达到轮数上限或 Actor 总时间预算，仍无有效提交 | 正常预算耗尽，任务失败；记录终止原因，hard 和单元格正确率按 0 计 | 不可以 |
| API 服务重试耗尽、输入无法读取、运行依赖缺失或执行设施故障 | 技术中断；不将未知结果计成算法失败 | 暂停，按恢复规则处理 |
| 请求无法容纳完整上下文 | 明确记录输入容量问题；不得悄悄删历史或扩额度 | 暂停，处理配置问题 |
| Actor 已提交，但评分器或答案文件故障 | 保存提交产物，评分中断 | 不重启 Actor；修复后仅补评分 |

“可打开”只检查文件本身，不检查答案是否正确、目标工作表是否符合标准答案、目标区域是否为空或公式缓存是否存在。能打开但缺少目标工作表，仍先结束 Actor，再由评分器计错。程序自身触发的 `KeyError` 可以作为执行错误返回；事后对照答案发现的缺失工作表不能返回。

不把成功执行的 stdout 当作探索结果开启新一轮。运行错误中的模型自打印内容可以出现在实际错误反馈内，但消耗同样的轮数和时间，不能记成免费观察。错误反馈只包含类别、退出状态和真实详情，不附加自动生成的解题建议。

## 3. 事后评分的边界

Actor 提交和评分是先后两个阶段。评分器持有标准答案；它不能成为 Actor 的工具。评分结果保存为独立的事后记录，不能追加到原 Actor 会话中，即使这个会话只用于归档也应保持消息事实准确。

| 使用方 | 允许的评分信息 | 用途及限制 |
|---|---|---|
| Parent／Candidate／Test Actor | 无 | 不根据评分纠错、不观察另一侧成绩 |
| Grouping、Diagnosis | 本批 Parent 的 hard、正确／总单元格数、单元格正确率、有限错误坐标与缺失工作表信息 | 组织和诊断已结束的优化任务；不能凭坐标单独断言根因 |
| Preconditioner | 其输入中被引用 Parent 执行的同类信息 | 结合计划与 Knowledge 调整更新；不扩展既定证据范围 |
| Editor | 不直接接收评分明细；只接收 Parent Skill、Effective Plan 与本上下文 | 将可执行的通用规则写入 Skill，不生成题目答案 |
| Replay | 当前完整 P/Q 配对的同类信息及实际修改 | 学习改善与失败经验；得分变化不等于独立因果证明 |
| Verifier／Repair | 既定引用与修复范围内的同类信息 | 核对与修正事实，不借机补做任务 |
| Gate | 完整配对的 hard 结果与完成状态 | Candidate 成功数严格更多才 ACCEPT；辅助指标不打破平局 |
| Test 报告 | 最终 280 题的结果及完成情况 | 不用于更新 Skill、Memory、选择配置或继续调参 |

原始答案值不投影给任何模型模块。优化模块评分视图推荐包含精确计数、最多 100 个错误坐标、最多 100 个缺失工作表名称；明确实际总数、已展示数和截断情况。错误坐标按答案区域顺序、区域内按行列顺序稳定排列，不按“重要程度”临时选择；缺失表内单元格计入错误总数，不必重复铺开全部坐标。原始完整评分记录另存，不能用截断后的列表长度重新计算指标。

自身输出值可以出现在已有的输出摘录或实际日志中；评分投影不额外追加预测值或标准答案值。评分器可能产生含答案值的差异说明，因此不能把其原始字符串直接交给模型，应从明确允许的结构字段生成评分视图。

标准答案经由优化任务的评分帮助学习，这是已允许的监督信号。它不等于允许 Actor 在当前题内获得答案纠错。Skill 和 Knowledge 应总结可从输入执行的规则，不携带题号、答案摘录或要求未来 Actor 等待评分器反馈。

同一 Parent 的归档结果供诊断、Gate 和 Replay 复用，不额外重跑 Parent。Candidate 从原始输入独立开始，仅获得自己的 Skill 和任务消息。完整一批为 15 次 Parent 加 15 次 Candidate；no_change 时没有 Candidate 执行。120 个优化任务可用于上述学习，280 个 Test 不进入这条学习流程。

## 4. 参数推荐表与依据

“继承”表示用户已确认保留；“推荐”表示本次给出的设计默认值，后续正式配置应明确采用情况。所有方法对照使用同一份 Actor 参数。参考实现的值只作为依据，不代表其训练反馈、时间约束及请求重试方式与本方案完全相同。

| 参数 | 首版值或规则 | 状态与依据 |
|---|---|---|
| 代码轮数上限 | 30 | 推荐；SkillOpt 默认配置与 SkillAdam 主结果后端均为 30；首个有效产物仍立即停止，不要求跑满 |
| Actor 每次输出 | 16,384 tokens | 继承 v24；不是一次任务全部轮次的总额度 |
| 单轮请求总尝试 | 最多 6 次，含首次 | 继承 v24；外层与 SDK 合并计数，不再额外乘一层重试 |
| 单次 API 请求时限 | 300 秒，实际取该上限与剩余任务时间的较小值 | 继承数值；强制受剩余时间约束为本次推荐 |
| 单次程序执行时限 | 600 秒，实际取该上限与剩余任务时间的较小值 | 继承数值；不保证程序每次能独占 600 秒 |
| Actor 任务总时限 | 600 秒墙钟时间 | 继承数值；推荐从任务取得执行名额、开始准备输入计至提交检查结束，包含预览、请求、重试等待、执行及文件检查；排队不计入 |
| 事后评分计时 | 单独记录，不占 Actor 的 600 秒；不给 Actor 增加时间 | 推荐；评分发生在提交后，其开销不能决定 Actor 能尝试几次；评分中断不改变已提交程序 |
| 系统与 Skill | 固定系统说明后追加完整 Skill | 推荐；与 SkillOpt 注入位置一致，方便统一三种方法的执行条件 |
| 可用库 | 标准库、openpyxl、pandas | 推荐；沿用 SkillOpt 固定系统说明的能力范围；解释器和库版本在环境准备时固定记录，不任意升级 |
| 预览范围 | 每张表前 5 行 × 前 20 列，保留坐标、表名及尺寸 | 推荐；与两份本地参考实现的基本范围一致；按工作簿原顺序，不优先展示答案区域或自动猜表头 |
| 单元格预览文本 | 最多 40 字符，超出显示前 37 字符加 `...` | 推荐；沿用 SkillOpt；空值显式表示，公式按公式文本显示，使用 `data_only=False` |
| 总预览长度检查 | 完整生成各表的有限预览后检查：最多 100,000 字符，不含任务指令、Skill 与历史；超过则明确报错，不截断继续 | 已确认；沿用 SkillAdam 的检查方式。按工作簿顺序逐表输出名称、尺寸及单元格预览，不另设表目录优先填充策略；超限属于输入协议问题，不记作模型解题失败 |
| Actor 错误详情 | 每次保留前 3,000 字符；短于上限则原样 | 已确认；截取方向和长度与 SkillOpt、SkillAdam 一致；错误类别、退出状态、截断标记与剩余轮数另列 |
| 消息历史 | 当前任务全部完整响应与实际反馈；不自动裁剪或摘要 | 推荐；完整程序修正需要此前代码，区别于 ALFWorld 最近两步历史 |
| 模型输入容量 | 使用正式模型的真实上下文限制及继承的请求大小限制；不另设自动裁剪阈值 | 具体模型沿用已确认配置，接入时验证；超限明确中断，不能通过删题或隐藏历史让请求继续 |
| 优化模块评分摘录 | 错误坐标最多 100，缺失工作表最多 100，精确指标不截断 | 推荐；参考 SkillAdam 的坐标反馈大小，但这里只给优化模块，绝不回送 Actor |
| 公式处理与评分 | 不额外执行公式自动重算；评分使用 `data_only=True` 读取已保存的单元格值 | 推荐；本地 SkillOpt／SkillAdam 路径都读取已保存的值评分，未调用重算引擎；明确限制见下文 |
| 首轮功能验证并发 | 1 个任务，执行进程随任务串行 | 推荐；先确认执行条件与时间边界，减少资源争用；批大小仍为 15，并发不是批大小。后续实验并发需统一固定 |
| 方法模块输出与请求预算 | Preconditioner／Replay／Verifier／Repair：32,768 tokens；Grouping／Diagnosis／Editor：16,384；请求 300 秒、最多 6 次 | 继承 v24；与 Actor 代码轮数、任务时限分别计数 |

总预览和错误详情均按 Unicode 字符计数，不把字符数当作 token 数。总预览恰好 100,000 字符允许通过长度检查，超过则在 Actor 请求前明确报错；不删表、不缩小每表范围来绕过检查。每表 5×20 和单元格 40 字符仍是内容展示限制，与总预览超限报错分别处理。后续离线验收覆盖长度边界，不按任务得分改变范围。

600 秒采用实际截止时间：每次请求、等待或程序运行前计算剩余时间，并据此裁剪时限；到期取消仍在进行的 Actor 请求或程序。程序耗尽剩余时间，按预算失败记录；如果仍未取得完整模型响应且中断来自 API 超时／服务失败，按技术中断记录，不将服务不可用伪装成解题失败。必须保留实际耗时与中断原因，不能通过恢复重新发放 600 秒。

恢复时继续已有尝试与累计预算，不能择优重跑已完成任务；已提交只补后处理。遇到需要改变执行条件才能继续的技术故障，应先暂停并决定受影响任务的统一处理方式。对未完成请求的恢复规则在实现阶段覆盖，不能把中断遗失的请求当作未消耗。

**公式处理的具体含义：** 预览与生成程序可读取公式文本；评分器使用 `data_only=True` 读取工作簿保存的值。首版没有 Excel／LibreOffice 自动计算步骤。公式合法但没有缓存，不会因此获得额外纠错机会；评分读取到空值，就按共同的空值比较规则计算，目标值非空时通常判错。`openpyxl` 保存文件也不能被描述成执行了公式计算。

这是选择参考实现执行条件时接受的限制，不表示公式任务都能被公平地验证其数学语义。不能假定重新保存工作簿后，原有公式的缓存仍被保留；这一情况也需离线覆盖。固定 Actor 说明应如实告知“环境不自动重算公式，评分读取已保存的单元格值”，但不额外提供解题算法，也不强制把所有公式改写成常量。若以后采用重算，必须单列新的共同执行配置，固定引擎版本和时限，统一应用于所有方法；保留原始提交与重算副本。重算引擎故障应为评分中断，不能与当前不重算配置混算成绩。

## 5. 供优化模块引用的英文正文

以下正文用于 Grouping／Diagnosis／Preconditioner／Editor／Replay／Verifier／Repair 的共享执行说明，**不是给 Actor 的任务指令**。它描述信息权限，不给各模块增加本来没有的证据输入。数值和 Actor 模板应由同一份实际配置渲染；本节是内容定稿，独立正文及完整模板已保存到 [Prompt 定稿包](prompts/README.md)，运行渲染代码留待后续实现。

```text
## SpreadsheetBench Execution Context

This section describes the Actor's execution conditions. It is evidence for
your assigned optimization role, not an instruction to solve the current task
or to request additional execution. Your module's own input contract still
determines which records you may use.

Actor-visible information
The Actor receives a fixed system instruction, the complete current Skill,
the task instruction, task type, answer region and its worksheet information,
and a bounded preview of the original input workbook. The Skill is fixed for
the entire task. The Actor does not receive Memory, another execution's code
or results, a reference workbook, expected values, or evaluator feedback.

The preview includes worksheet names and dimensions, then up to the first
{{preview_rows}} rows and {{preview_columns}} columns per worksheet with cell
coordinates. Cell text is limited to {{preview_cell_chars}} characters. After
all worksheet previews are generated, a preview longer than
{{preview_max_chars}} characters causes an explicit input-protocol error
before any Actor request; it is not truncated to fit this limit. Formula text
is shown, and row, column, and cell-text omissions are marked. Unshown cells
are not absent cells. Access to the full
input file does not establish that the model saw its contents before acting.

Capabilities and attempts
The Actor has no interactive shell, file browser, Python session, or workbook
inspection tool. It returns one complete Python script in a python fenced
block. An external executor runs the script with INPUT_PATH and OUTPUT_PATH
bound to the current attempt's paths. The supported libraries are
{{allowed_libraries}}. The program can read the complete original input and
write within its current attempt's output and temporary space. It cannot
access reference answers, previous attempts' files, other tasks, the network,
or external command execution. A fresh attempt starts from the original input.
The executor does not repair the task algorithm.

History and runtime feedback
Within a task, the model retains the original messages and every complete
assistant response and returned runtime-feedback message. It has no
cross-task conversation. There are at most {{max_code_attempts}} code attempts;
a complete malformed or truncated generation also consumes an attempt.
Transport retries are counted separately, with at most
{{request_attempts_total}} total request attempts per generation, including
the first. Retries of an incomplete request keep the same messages. Remaining
code attempts are reported after each completed response when continuing.

Only response-format errors, program execution errors, and missing or
unreadable output-file errors can be returned to the Actor. Error details
retain only the first {{runtime_error_detail_chars}} characters when longer
than that limit, with marked truncation. They contain actual runtime
information, not evaluator findings
or extra solution advice. Successful stdout does not open an exploration
round. An exception deliberately used to inspect data is still a budgeted
attempt. Stored logs are not necessarily feedback the Actor received.

Budgets and stopping
Each generation has an output limit of {{actor_max_output_tokens}} tokens.
The request timeout is {{request_timeout_seconds}} seconds, the program
timeout is {{program_timeout_seconds}} seconds, and the Actor task budget is
{{actor_task_timeout_seconds}} seconds. The task clock starts when an execution
slot is acquired and input preparation begins; it includes preparation,
requests, retry waiting, execution, and output checks. Queue waiting and
post-submission scoring are outside this Actor budget. In-flight operations
are bounded by remaining task time. These are upper limits, not guarantees
of that much time for every attempt.

The first normally terminated program that produces an openable .xlsx at
OUTPUT_PATH ends the Actor execution. Opening a workbook is not a correctness
check. A missing target sheet or an incorrect answer discovered by grading
cannot reopen the Actor. Exhausting code attempts or the Actor time budget
without a valid submission is a task failure. API or execution-infrastructure
interruptions and scoring failures are recorded separately, not silently
converted into model failures or omitted from the batch. Complete history is
not silently shortened to fit a request.

Formula and scoring conditions
The formula policy is {{formula_policy_description}}. In the initial profile,
there is no automatic formula recalculation; grading reads saved cell values
with data_only=True. Writing a valid formula does not establish that a cached
result exists. The Actor is told this execution condition.

Scoring occurs only after submission. The main score, hard, is one only when
all designated answer cells pass the shared comparison rules. The auxiliary
per_cell_pass_rate is correct cells divided by graded cells for each task;
aggregate reports average these task-level rates. Neither score is runtime
feedback. Comparison is limited to the evaluator's supported value semantics;
it does not establish that all formatting, formulas, or non-target cells are
correct.

For optimization tasks, permitted post-execution evidence includes scores,
exact cell counts, bounded mismatched coordinates, and missing-sheet names,
subject to your module's input contract. It excludes expected answer values.
The coordinate and missing-sheet lists are limited to {{score_coordinate_limit}}
and {{score_missing_sheet_limit}} entries respectively; marked truncation does
not change the exact counts. Never describe this later evidence as information
the Actor received. Do not propose a Skill step that waits for grader feedback.
Generalize executable rules from evidence; do not copy task answers into Skill
or Knowledge. Test results are for final reporting, not optimization.

Pairing and evidence interpretation
The same Parent execution is reused for diagnosis, Gate, and Replay. Candidate
executes independently from the original input under the same feedback and
budget conditions. It receives no Parent transcript or result. Gate accepts
only a strict increase in successful tasks over the complete paired batch;
the auxiliary metric does not break ties. A no_change branch does not create
Candidate executions. A score change alone is not proof that one Skill edit
caused it. Code text is not a record of which runtime branches executed.

Actual Actor message templates
<actor_system_prompt>
{{actor_system_prompt}}
</actor_system_prompt>
<actor_initial_template>
{{actor_initial_template}}
</actor_initial_template>
<actor_runtime_feedback_template>
{{actor_runtime_feedback_template}}
</actor_runtime_feedback_template>

These templates describe what can be sent. The saved messages for a specific
execution determine what was actually sent. A post-execution record does not
become Actor-visible merely because an optimization module can read it.
```

变量逐一来自第 4 节同名概念，不从某个优化模块的自然语言判断反推参数。`formula_policy_description` 在首版只能描述关闭自动重算的条件。三个 Actor 模板插入实际生效文本；不能用本共享上下文替代 Actor 系统消息，也不能把事后评分段直接交给 Actor。三个 Actor 模板已在 Prompt 定稿包中完成；Skill 原文与任务内容作为数据插入，不再次解释其中的模板占位文本。

## 6. 后续离线验收与范围

本次交付是共享语义与参数方案。后续实现验收至少覆盖：首次有效产物立即停止；缺少答案表仍先提交再评分；无任何评分字段进入 Actor 请求；不因评分为零追加轮次；新尝试使用原始输入；完整历史与剩余轮数一致；请求重试不叠加或免费重发；时间裁剪与恢复不重置预算；每表预览范围与单元格截断可见，总预览超限报错而不截断，错误详情仅取前 3,000 字符；公式无缓存按既定值比较；评分器故障只补评分；Parent 在诊断和 Gate 中复用同一记录。

完整 Actor 模板及方法模块 Prompt 已定稿，构造案例检查见[检查结果](prompt_review/REVIEW_RESULTS.md)。环境版本、具体模型上下文容量、路径适配允许语法和后端实现，属于后续代码迁移工作。它们必须实现本文的能力边界，不能悄悄更改停止规则或反馈权限。本次没有验证方法效果，也不声称 v25 已通过运行验收。

依据为当前仓库内的参考源码：

- [SkillOpt Actor：预览、消息构造与尝试循环](../../../external/SkillOpt/skillopt/envs/spreadsheetbench/codegen_agent.py)、[固定系统说明](../../../external/SkillOpt/skillopt/envs/spreadsheetbench/prompts/codegen_system.md)、[默认配置](../../../external/SkillOpt/configs/spreadsheetbench/default.yaml)。
- [SkillAdam Actor 与反馈投影](../../../external/SkillAdam/skilladam/backends/openai_compatible.py)、[主结果后端配置](../../../external/SkillAdam/configs/backends/gpt55_spreadsheetbench_main_result.example.json)。
- [SkillOpt 值评分](../../../external/SkillOpt/skillopt/envs/spreadsheetbench/evaluator.py)、[SkillAdam 值评分](../../../external/SkillAdam/skilladam/benchmarks/spreadsheetbench/evaluation.py)。
- [v24 共享上下文及真实 Actor 模板嵌入方式](../../../src/skill_evolution/v24/benchmarks/alfworld/prompts/v23/execution_context.md)。

这些依据支持具体执行事实；本方案的统一无评分反馈、时间截止、隔离执行和证据投影是项目选择，不宣称与上游实现逐项等价。
