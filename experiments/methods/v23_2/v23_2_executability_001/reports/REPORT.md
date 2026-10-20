# V23.2 第一项改进：Update 可执行性验证

日期：2026-10-19。状态：**实现与本次验证已完成，通用可执行性问题尚未解决，按授权边界停止。**

两处短 Prompt 修改使三组固定 Plan 都产生实际 Adjustment，但 R03、R06 和 R05 串联的最终 Update 仍有明确的全局进度依赖；固定 R05 有局部改善，仍存在信息范围歧义和新的过早停止条件。不能据此宣布第一项改进通过，也不能归因为历史 Memory 的收益。

完成 5 次逻辑调用、9 次 HTTP 请求（含 4 次失败技术尝试），总计 3,311,273 tokens、约 8 分 20 秒；没有语义重采样。没有执行 Editor、生成 Candidate、运行 Replay 或 ALFWorld。

## 实现与验证范围

仅替换 Diagnosis 原有触发条件要求和 Preconditioner 原有可执行性检查段，使用用户指定的短文本。[精确前后差异](../config/prompt.diff)中只有两处替换，没有新增章节、案例、结构化字段或能力清单。历史反例学习条款未修改。

[V23.2 局部适配](../../../../../src/skill_evolution/v23_2/local_validation.py)共 116 行，复用 V23 输入装配、共享背景、校验与 Effective Plan 编译；[实验入口](../run.py)只负责选取冻结材料、限定五次调用及归档。既有 V23 源码和 Prompt 不修改，不复制整套框架。

[离线测试](offline_tests.txt)：**595 passed，19 subtests passed，18.48 秒**。覆盖全部 V23、ALFWorld Adapter、相关 V22 分组回归及 10 项 V23.2 测试。测试时禁止网络连接与环境子进程，只允许已有测试读取 Git 元数据。新增检查包括精确两处模板替换、输入不变、Diagnosis／Adjustment 契约、Effective Plan 重编译、Memory 交接、Editor 纯输入消费、容量停点、技术错误有限重试、合法停点不重试和禁止语义重采样。没有以关键词判定可执行性。

## 材料与比较方法

旧侧直接读取 V23 正式 S1 的有效阶段选择标记及已保存真实响应，不重新调用旧模型；新侧冻结相同模型设置，仅替换指定模块 Prompt。详细路径和容量见[计划](../config/plan.json)，逐项全文见 [OUTPUTS.md](OUTPUTS.md)。这是一组历史输出对照，不能排除调用时间和模型随机性差异，不能作严格的单变量因果估计。

| 材料 | 固定 Plan 的当前执行数量 | 输入 Active Memory | 输入容量（字符／UTF-8 字节） |
|---|---:|---|---:|
| R03 | 9 条引用执行，原批 10 条 | M1、M2、M3 | 1,000,000／1,500,000 |
| R05 | 5 条引用执行，原批 10 条 | M1、M2、M3、M6、M7、M8、M9 | 4,000,000／6,000,000 |
| R06 | 5 条引用执行，原批 7 条 | M1、M2、M6、M7、M9、M10、M11 | 4,000,000／6,000,000 |

这些是各次历史有效调用实际生效的容量（含当时已登记的恢复），不是提高旧初始配置的预算。R05／R06 是正式优化池中的 Selection 任务，仍用于优化阶段，不是 Test。固定 Plan 三侧的模型 user message 与旧侧逐字一致；链路 Diagnosis 用 R05 完整批次，新 Plan 交给 Preconditioner 后按原规则选取 3 条引用执行，Memory 保持原 R05 入轮快照。

所有调用保持 deepseek-flash、temperature=1、thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300s。模型端点沿用冻结配置；环境 seed 不保证模型输出复现。每阶段最多三次既有技术尝试，不对合法输出作语义重采样，不通过追加反馈修正输出。

## 语义核查使用的能力依据

以[实际发送的 Prompt](../../../../../artifacts/methods/v23_2/v23_2_executability_001/fixed_R03/attempts/002/prompt.md)中的 `background` 渲染内容和[共享执行背景](../../../../../src/skill_evolution/v23/execution_context.md)为准：Actor 可见当前观察、动作候选及 “last two pre-action observation/action pairs”，没有完整执行历史、可写持久笔记或隐藏评估状态。history_template 明确含 “You are now at step {current_step}”，所以当前步数和由 50 步上限推导的剩余步数有依据；不能据此推导已经检查过的全部位置。

下文判断的边界是：近期空位置、当前持有物及当前提供的动作可以支持局部决策；跨越历史窗口的未访问集合、所有候选已穷尽等判断，需要另外可观察的状态或可执行的信息恢复方式。固定顺序若能从当前状态恢复下一步可以成立，不因“有序搜索”名称而拒绝。合法 JSON、引用存在、reason 自称可执行，都不替代最终文字核查。

## 真实输出核查

### A1. R03：结构有效，但仍有明确不可获得的信息依赖

原 u3 要求 “track progress within the execution” 和 “a receptacle not yet inspected”。V23 的 reason 已指出无法跟踪全部历史，u3 的替换却仍保留 “uninspected”“unvisited listed location”。

V23.2 有效结果调整 u2／u3，保留 u1。核查如下：

| Update | 最终实际文字与判断 |
|---|---|
| u1 | 保留精确类别和禁止替代物的有效要求，但也原样保留 “continue searching uninspected receptacles”。未限定到可见历史，仍需不可恢复的访问集合；本次未修正。 |
| u2 | “if the explicit action … is available while you are holding the target, perform that action immediately” 可依靠当前动作候选与持有状态。后续新增 “move the target in only when required, then take it back” 没有说明如何判断必须插入；证据显示插入／取回循环曾造成浪费，不能由同批成功执行推导这个备用策略必需。标记为依据不足及新增策略风险，不声称实际已经导致退化。 |
| u3 | 开头改用近期观察避免局部循环，但末尾要求 “revisit a location only after exhausting the listed candidate receptacles”。该句仍需全局已检查集合，近期两组记录与当前步数均无法提供，故可执行性未解决。禁止空手时 inventory／look 的要求也扩展为 “unless needed to identify a newly presented object”，可能限制其他合理的信息获取用途；尚无执行验证。 |

reason 声称替换后可由近期观察执行，但与末尾文字不一致。新增 “past the first third of the 50-step budget” 可根据当前步数判断，**信息上可执行**；约三分之一的阈值本身没有在本次证据中建立依据，属于策略选择问题。没有把它误归为缺失步数。

因此本组是明确的语义未通过，不重采样。精确目标要求和直接温度动作等主要策略仍在；问题同时包括遗漏能力修正和引入未经验证的备用动作／限制。

### A2. R05：全局条件明显减少，但仍有解释歧义和过度收窄

原 u2 为 “single-pass sweep”“a receptacle you have not yet inspected”“different uninspected family”。V23 全部 Keep，并称其兼容可见动作和两组历史，未说明如何恢复全局进度。

V23.2 只调整 u2，u1 精确类别／禁止近似替代要求逐字保留。新 u2 明确 “Use the current observation and the last two observations”，并把回避对象限定为这些观察显示的空位置。这个条件可由实际可见信息判断，相比旧侧不再要求维护全部已访问集合。

仍须保留三个问题：

- “If the last two inspected receptacles are both from the same family …” 不等于最近两组行动前观察。导航、开门等动作可占据窗口，使上一个被检查的容器已经不可见。若将其理解为仅检查窗口内实际出现的两次检查，条件可执行；若要求找出真正最近两次检查，则依赖仍在。文本没有明确这一边界，不能认定完整解决。
- “never move to an already-open receptacle that those observations show is empty” 信息条件可见，但绝对禁止重访比原来的减少循环更强，没有给目标状态变化或合理返回留出空间。本次没有环境执行来证明这种限制安全。
- 新终点 “Continue until the exact target is found or no admissible candidate from a different family remains” 可根据当前候选判断，却可能在同类别仍有其他候选时停止。它把局部跨类别选择扩大成搜索终止条件，缺少忠实保留搜索目标的依据，属于过度收窄，不是不可见状态问题。

结论：观察到实际 Update 变换，而非仅 reason 变化；但持续可执行性的歧义及新的终止条件仍使本组不足以支持全面通过。没有错误地撤下 u1，也没有输出整份 Plan 或改变模块职责。


### A3. R06：产生 Adjustment，却增加了需要记忆的调度要求

原 u2 自称 “memory-independent ordered sweep”，但要求当前类别搜完后进入 “genuinely uninspected family”。V23 全部 Keep，未解决跨类别进度的可获得性。

V23.2 保留 u1 的直接热／冷处理；u2 改为按类别采样。最终文本仍同时要求：

- “visit only receptacles not already inspected”；
- “switch to a different uninspected family”；
- “return to remaining receptacles of the earlier family only after the other families have been sampled”；
- “until … all plausible receptacles and families have been inspected once”。

这些条件分别需要全局访问集合、已采样类别以及离开各类别时的剩余位置。两组行动前观察、当前候选和当前步数不能同时提供这些进度，文字也没有给出从当前状态恢复它们的办法。即使初始房间候选能从当前动作重建，仍不能重建访问历史；固定编号顺序本身也没有规定可观察的跨类别游标。

reason 仍称其保留了 “memory-independent progress rule”，实际 Adjustment 却增加了 “at most two consecutive empty receptacles” 的切换上限和离开后再返回的安排。现有轨迹能支持考虑扩大搜索范围，但不能证明该固定阈值和调度方案忠实、必要或可执行。此处是模型生成的新策略偏差，不是代码或 Prompt 添加了 ALFWorld 专用规则。

u1 直接持有目标执行热／冷动作的已有要求逐字保留，没有撤下。u2 没有被过度删除，而是变得更复杂且依赖更多不可获得状态。**本组语义未通过。**

### B. R05 Diagnosis → Preconditioner 串联

Diagnosis 使用同轮 Parent、完整 Grouping 和 10 条当前执行，不接收 Memory；Preconditioner 接收新 Original Plan、按既有规则筛出的当前证据，以及原 R05 入轮 Memory。没有使用本次三个固定 Plan 输出更新 Memory，也没有使用 R05 之后的历史。

Diagnosis 返回 revise、两项 Update。u1 将精确类别比较明确绑定到 “object label in the current observation and candidate action” 与任务目标，信息依据清楚；没有把识别错误替代物交给 Editor 再设计。u2 将跨类别切换触发条件写成 “recent observations and actions show repeated movement”，比无条件单次遍历更贴近当前可见信息。

但 u2 同时要求 “do not return to that same empty/lacking receptacle … during the search” 和 “other uninspected container”。前者把一次观察延伸为整个搜索阶段的禁返要求，后者仍可能依赖窗口外访问集合。不存在持久笔记或完整历史来自动支撑这些要求，因此 Diagnosis 的短修改没有消除所有多步依赖。

Preconditioner 返回 ready，实际替换 u1／u2；reason 的 “keep both Updates” 只表达保留方向，不是空 Adjustments 的 Keep。u1 保留当前可见标签与任务目标的比较，并增加“任务明确要求的其他物体可用于动作，但不能充当目标”的适用范围澄清；该条件可以从任务文本判断，没有增加隐含记忆要求，本批未验证其收益。

u2 的句首明确 “using only the current observation, candidate actions, and the last two pre-action observation/action pairs”，也把立即回访限制绑定到最近观察。但后续又要求：

- “a different uninspected category available in the observation/action list”：动作列表能列出类别，不能说明类别是否已检查；
- “When the chosen category has multiple unchecked listed instances, inspect each unchecked instance once before returning to an already checked instance”：需要窗口外的实例访问集合；
- “until … all plausible categories have been inspected once”：需要全局类别进度。

同时，“inspect each unchecked instance once” 与 “do not exhaust one container series before checking another broad category” 没有说明何时停止本类别并切换，给后续落实留下策略歧义。**串联未通过语义核查。** Diagnosis 未承担历史学习，Preconditioner 未输出 Skill、未新增字段；接口和分工保持，但自然语言策略没有满足完整可执行性。

## 结果对照摘要

| 材料 | V23 有效调整 | V23.2 有效调整 | 最终核查结论 |
|---|---|---|---|
| 固定 R03 | u2、u3 | u2、u3 | u1 仍要求未检查位置；u3 仍要求穷尽全部候选后才能重访；u2 备用流程依据不足 |
| 固定 R05 | Keep | u2 | 去掉明确的全局单次遍历，u1 保留；“最近两次检查”边界不明，新增跨类别候选耗尽即终止 |
| 固定 R06 | Keep | u2 | 增加类别采样／回返调度，仍依赖全局位置与类别进度；u1 保留 |
| R05 串联 | 历史 Diagnosis 的两项 Update＋Keep，详见上方 R05 | 新 Diagnosis 两项；Preconditioner 替换两项 | 句首声明局部信息，后文仍要求未检查实例集合和全类别检查完成 |

没有以某个 Update 包含 `unvisited` 等词直接判错；判据是这些具体条件是否有实际可获得的信息。没有把显式当前步数当作隐藏信息，也没有禁止可从当前状态恢复下一步的固定顺序策略。没有运行 Candidate，所以所有副作用判断均为文本与证据支持的风险，不能写成已观察到行为退化。

## 请求、费用、耗时与停点

[全部技术尝试](OUTPUTS.md#全部请求及技术尝试)及[机器审计](../results/attempts.json)保留有效与无效原文；下面的 Token 和时间包含失败尝试。

| 逻辑调用 | 实际请求数 | 最终有效尝试 | 总 Token | 尝试耗时合计（秒） |
|---|---:|---:|---:|---:|
| 固定 R03 Preconditioner | 2 | 002 | 481,112 | 109.75 |
| 固定 R05 Preconditioner | 2 | 002 | 958,574 | 103.76 |
| 固定 R06 Preconditioner | 3 | 003 | 1,331,714 | 181.94 |
| R05 Diagnosis | 1 | 001 | 73,075 | 42.91 |
| R05 串联 Preconditioner | 1 | 001 | 466,798 | 48.22 |

- R03/001：`adjustment.reason: unavailable historical reference`；原文斜线并列写法包含 `P8/P9`、`P5/P10`，以及相邻引用组合中被截出的 `22/P10:45`。
- R05/001：`reason: unavailable historical reference`；涉及 `P6/P8`。
- R06/001：同类引用契约错误；原 reason 使用 `P4/P5`、`P1/P2`。这些当前执行实际存在；现有历史引用正则把斜线写法识别为不受支持的历史来源，不能直接描述为模型杜撰了这些执行。
- R06/002：`finish_reason=length`，输出达 16,384 tokens，其中推理 15,615；截断正文原样保留，没有解析补全或人工修复。

上述四次失败均由 V23 既有技术判定允许重试；同一逻辑调用的 messages 与配置完全相同，未追加纠错反馈。没有因可执行性不合预期而再调用。引用识别的歧义仅记录，不在本次修改。

总输入 **3,224,426**、输出 **86,847**、总 Token **3,311,273**；推理 **79,931** 已包含于输出，缓存输入 **1,574,272** 已包含于输入。四次失败请求合计 **1,611,425** tokens 已计入总量，未知 usage=0。无账户账单，未虚构货币费用。

实验整体耗时 **499.92 秒（约 8 分 20 秒）**，含重试等待、装配与归档；各尝试耗时是请求和响应校验范围，二者不应混为一项。5 个逻辑调用均获得合法结构，Preconditioner 均为 ready、Diagnosis 为 revise；没有合法 no_change／need_evidence，没有输入容量或模型上下文超限停点。串联 Preconditioner 实际输入 1,576,346 字符／1,576,364 字节，保持 R05 的 4,000,000／6,000,000 上限。

## 归档与保护核验

- [完整对照](../results/comparison.json)与 [OUTPUTS.md](OUTPUTS.md)逐项保存 Original Plan、V23 reason／Adjustments／Effective Plan、V23.2 对应输出和串联结果；它们是原文视图，不替换实际响应。
- [独立原始档案](../../../../../artifacts/methods/v23_2/v23_2_executability_001/)保留全部输入、版本 Prompt、实际请求／响应、失败及有效尝试、确定性编译结果与阶段选择。
- [保护核验](../results/protection.json)：对 V23 方法源码、ALFWorld Adapter 源码、正式实验配置及训练／Test 产物共 **10,114 个文件**直接逐字节核对，无变化、无增删（排除 Python 缓存）。没有往旧 Memory 中提交内容。
- [最终核查](../results/final_checks.json)：重新加载全部 5 个有效输出；核对三组固定输入、每次重试消息与配置完全相同，串联 Memory 不变；4 份真实 Effective Plan 均通过原 Editor 的纯输入装配，不运行 Editor。文档链接与 `git diff --check` 通过。
- 当前 Git HEAD 为 `7d4749541dab04397ea146e56dc762a26ba81a3b`；V23 文件有未提交内容，故复现依据还包括既有 S1 contract／recoveries 和本次新增实现冻结快照，不能仅凭 HEAD 复现。

## 结论与停止边界

本次验证说明：短可执行性要求能够引发真实 Update 变换，但不能可靠阻止模型在后半段重新引入不可观察的执行进度；reason 与最终文本仍可能不一致。局部信息声明、命名为“无需记忆”以及发生 Adjustment 都不充分。新策略还可能引入未经证据支持的阈值、备用动作或过度收窄的终止条件。

这是单次合法输出、固定历史材料的局部构造研究，没有独立新旧同期配对或行为执行；不报告成功率提升，不证明 Memory 因果收益。未完成通用可执行性目标，不能标为已解决。**按本次任务边界停止，不继续修改 Prompt，不追加调用，不进入历史反例学习或 Replay／Memory 改进，不启动六轮正式实验。**未来同一 134 Test 的比较属于同基准回归。
