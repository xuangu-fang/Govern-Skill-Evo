# V22 统一 D/S/C 预条件化机制：真实模型语义验证

本次验证的对象是 `v22.unified_dsc.v1` 的真实模型行为，使用 `deepseek-v4-pro`。调用时间为 2026-10-15 22:50:07—23:02:02（北京时间）。独立档案为 [09 验证目录][archive]。算法、Prompt、Schema、生产运行器、Gate 和旧实验产物保持不变。

## 1. 结论

**已观察到模型利用条件化历史响应作出具体 S/C 决定，但尚不能认定统一更新作用链已通过真实语义验证。不建议直接转入正式新一轮 ALFWorld 流式实验。**

这一判断不是因为模型没有强制使用历史、没有产生足够多变换，或尚未证明成功率收益，而是存在直接影响更新构造和忠实落实的反例：

- 真实 Diagnosis 和 Fusion 都把不可直接执行的主动 `stop` 保留为可执行策略，Fusion 仍返回 `ready`；输入已有该动作无效的证据。
- Diagnosis 从一个错误类型处理案例泛化出较宽的恢复禁止；真实 Fusion 又扩大了一个已知有效分支的触发范围，支持证据不足。
- 合成 Editor 将有效 Update 未选定的 `unknown` 恢复分支补成强制验证义务，尽管文本映射全部合法。
- 部分适用历史的 Fusion 返回无效 JSON，不能形成有效更新；未重试或手工修补。
- Replay／Memory 保留了若干重要未知范围，但仍将跨路径的行为机会混用，并把一条未验证的触发条件写进新 Effect。

同时，不能把这些反例解释成整个算法没有价值。合成历史适用探针确实将实际联合编辑后的响应联系到尺度扩大、减少冗余义务及依赖协调；Editor 也保留了大部分已选策略与重要例外。问题是这些能力尚未在同一项 Update 的各阶段稳定保持。

本报告分别评价程序与来源、模型输出语义和仍未知的环境效果；不将旧两轮的 7/10→8/10 作为本次新 profile 的收益。

## 2. 冻结协议、材料与调用边界

### 2.1 先固定，再调用

正式请求前已读取 [统一设计][design]、[最小实现说明][implementation]、[机制审查][audit]，并核对实际规则和装配代码。调用使用 [unified_dsc.py][rules]、[grouped_messages][messages-builder] 和 [实际历史消费视图][memory-view]，没有另外编写一套测试 Prompt。

所有七个案例的 `payload.json / messages.json / request.json / criteria.json`、请求预算、失败政策及调用脚本均在首次请求前冻结。冻结清单 SHA256：

```text
04de9c5f0bd111fa4d509b566649b1e24e00e31bbbb66524a02b585a90ce09a5
```

见 [protocol.json][protocol]、[freeze.json][freeze]、[输入装配脚本][prepare]。没有根据首次输出更换案例、修改标准或重新采样。后续 [独立输入有效性复核][input-review] 只补充结论边界，未改变请求或预注册标准。

| 探针 | 冻结输入与目的 | 调用数 |
|---|---|---:|
| `diagnosis_real` | R2 真实 Parent 十条轨迹及冻结分类；无 Memory；检查原始 Update | 1 |
| `fusion_real` | R2 原始 `initial_plan.json`＋真实 Parent＋正式 R1 Memory；不预修旧 Plan | 1 |
| `fusion_applicable` | 合成条件化联合编辑响应；检查 S 扩大／减强度和 C 协调 | 1 |
| `fusion_limited` | 合成稿已覆盖历史支持分支，另有未测 `unknown` 探索分支；允许 Keep | 1 |
| `fusion_nohistory` | 与 applicable 完全相同初稿和当前证据，仅清空历史 | 1 |
| `editor_frozen` | 预先人工编写并经 Compiler 验证的合成有效 Plan；独立检查落实 | 1 |
| `learning_real` | R2 实际有效 Plan、旧 Editor、旧 Candidate/diff、真实二十条配对轨迹、R1 Memory | 1 |

Diagnosis、Fusion 和 Editor 是独立探针，**不是本次模型连续生成的一轮更新**。尤其 Editor 没有使用本次任何 Fusion 输出。其输入来自 [预先冻结的人工增量][editor-fixture]。学习也没有使用这份新 Editor Skill；它只读取旧 R2 实际执行过的版本。

### 2.2 真实学习材料的身份核对

材料来自 `08_grouped_continual_fusion_resumed_20261015/rounds/r2`：

- Parent SHA：`6ead6e278eddfb70cb00d71ecb6987dc5d59396cfb0bd8e39cfab7797a1862fa`。
- Candidate SHA：`528c86f23bf4e49e40406f0451a5f1f5693036278a9b1f6a6f271cd66ff5d9ad`。
- 20 条轨迹文件哈希逐一匹配；十组记录执行条件一致。
- 重建 diff 与旧实际 diff 相同；有效 `execution_plan`、实际 Editor 文本身份、配对证据及 Gate 通过现有 `prepare_grouped_learning` 检查。
- 新装配的 `parent/candidate/actual_diff/plan/runs/pairs/memory/grouping/command_sets` 与旧学习输入逐值相同；增加的是新 profile、Editor 关联及其绑定信息。
- 输入 Memory 是 R1 正式三条 Effect，不包含 R2 后验五条 Memory，避免答案泄漏。
- 新学习绑定：`6946749f05dbc44f985a9cb8e0aecbc2305887b4a89a099ad8842e3b3b57cd0b`。

见 [旧 R2 目录][real-r2]、[冻结学习输入][learning-input]、[机械事实复核][evidence-checks]。Gate 在此只是既有采用事实，未执行新的发布。

### 2.3 合成材料的作用和局限

合成案例明确标记为 `SYNTHETIC SCRIPTED FIXTURE`。它们是作者给定的机制情境，不是 Agent 环境执行。

共同协议只有可见状态和最近两步；`normalize` 使验证失效，`validate` 使状态 current，`inspect` 只揭示状态，`dispatch` 只在 current 时被接受。历史联合修改是“必要时 normalize，随后每次 dispatch 前 validate”，三组脚本分别表现为：

1. critical、需 normalize：减少一次 stale 导致的 dispatch 拒绝；
2. standard、已经 normalize 但 stale：减少一次拒绝；
3. standard、已经 current：增加一次状态未变的 validate，两侧最终均交付。

所以可以检验模型是否从实际编辑及条件差异导出范围／强度决定。但协议本身和当前 P1/P2 已足以支持不少相同决定；这不是历史不可替代性的强识别案例。

其他局限：limited 是“部分历史适用＋另一分支未测”，不是纯粹无关历史；两个合成案例同属一个决策结构，未充分覆盖跨组迁移、历史冲突、异步失效或有实证替代策略的 D 改向。取消／完成保护只有文本检查，没有对应真实执行。

### 2.4 请求参数和一次性执行

请求固定为 `deepseek-v4-pro`、`temperature=1.0`、`thinking={"type":"enabled"}`、`reasoning_effort=medium`、`stream=false`。Diagnosis／Fusion／Editor 上限 32,768；学习上限 65,536；总 completion 上限 262,144。这里上限包含推理与可见输出，未虚构独立配额。连接超时 10 秒，响应等待上限 600 秒。

预算依据是旧 16,384 上限曾被推理消耗后截断，旧学习恢复实际使用 16,694 completion Token；因此没有直接沿用不足上限，也没有根据本次输出临时调参。

生产 `chat` 有自动重试、常规阶段预算也不同。因此只在验证档案内创建 [一次性传输脚本][control]，复用现有 `RecordingSession` 和生产消息／校验器；直接发送冻结请求，关闭 HTTP 重试及重定向。每案例先建立不可重复的调用占位，再发送一次 POST；最大并发 2。没有修改生产运行器，也没有自动补调用。

每个案例保留原请求、原始响应体、可见内容、完整 provider usage、调用时间、HTTP 状态、结束原因、解析／契约结果。无效结果不进入 Compiler 或正式状态。

## 3. Diagnosis：原始 Update 可表达，但目标、能力和尺度仍有失配

[真实输出][diagnosis-output] 返回 `revise`，结构与来源检查通过。它提出三个具体要求，引用当前决策组及 Parent 事件；搜索判据使用当前／最近两步，没有再要求全局 visited 集。Watch 能观察切换候选或重复处理行为。

但存在三个实质问题：

1. `intent` 直接固定 “adding search and stop behavior”，Goal 与可替换策略未充分分开。它不只是目标措辞问题：后续 Fusion 无权静默改 intent，却可能需要改变这条策略。
2. 三项要求都包含 inventory/look 后主动 stop。真实 P1:20、P6:29 的 `stop` 非 admissible 且返回 Nothing happens，当前执行器也没有该控制出口。模型没有将此限制用于更新构造。
3. u3 从 P6“请求 Pan、实际处理 Pot、失败后又处理另一 Pot”扩展为一般 singular cool/heat/clean 任务：放置后没有成功就禁止重拿重处理同一或另一同类物体。该证据支持检查错误类型和无新信息重复，不能证明正确目标、其他状态操作或合理恢复分支都应禁止。w2 只检验禁令是否执行，没有挑战它是否妨碍有效恢复。

因此，原始 Update 的可调整载体已能生成；**目标／策略边界、实际控制能力及证据支持的 S 尚未可靠保持**。这不是尚未观察到任务收益，而是输出本身已有语义反例。

## 4. Fusion：哪些是响应驱动决定，哪些来自当前证据

### 4.1 真实旧 Plan：修正部分能力限制，但仍放行不可执行分支

[真实 Fusion 输出][fusion-real-output] 返回 `ready`，替换全部三项要求，Compiler 通过。

| 原始选择 | 读取的依据 | 实际决定 | 判断 |
|---|---|---|---|
| u1/u3 使用全局 visited/unvisited | 当前 Actor 仅有最近两步；当前失败事件 | 改为当前可见／最近两步的不同候选判据 | 有实际意义的能力修正，主要不是历史贡献 |
| u2 继续寻找正确类型 | m3 记录短窗口搜索仍可能失败／晚发现 | 保持方向，将 m3 放入具体 `basis/reason`，保留 Watch | 历史可限制预期；未提供已验证替代策略，不证明新方向收益 |
| u3 来源空时扩展搜索 | 当前 P9/P10 成功路径，整体理由提 m2 | 补入先交付、返回来源、再处理第二件的连续路径 | C 保留有依据，但主要依据当前；m2 未进入该项 changes.basis |
| 所有分支中的 stop | 当前轨迹已显示无效 stop | 仍要求主动 stop，`ready/open=[]` | 可执行性语义失败；Watch 只问过早停止，没有处理停止不可实现 |

另一个尺度风险：新 u3 将 Parent 的“第一件后无第二 take 可用”触发前提省略，扩为一般两件任务拿第一件后先 move。P9/P10 都在第二 take 不可用条件下执行，不能支持这一无条件推广。这是依据不足的 S 扩大，尚未执行，不能称为已经造成环境退化。

m3 的具体引用比仅在总理由提到历史更可追踪，但历史内容仍只支持不确定性边界。不能把三项非恒等变换或 Effect ID 数量当作预条件化成功。

### 4.2 合成历史适用：出现具体的 S/C 响应利用

[applicable 输出][fusion-applicable-output] 将 u1 改为 u3，撤回独立 u2 并把其顺序及保护内容并入 u3，Watch 同步迁移。此撤回是合并依赖，不是放弃整个更新。

| 原始 Update | 历史条件化响应 | 有效更新 | 依据边界 |
|---|---|---|---|
| 只对 critical 每次 dispatch 前 validate | standard stale 的联合编辑也减少一次拒绝 | 扩为 active requests，不再限定 critical | 历史支持扩展到已测试 standard stale；协议也独立支持 |
| current 也必须 validate | current 分支仅增加一次状态不变的验证 | current 时直接 dispatch，取消强制冗余检查 | 实际响应进入强度决定；不能证明所有潜在复查都无用 |
| normalize “紧接 dispatch 前”与验证要求并存 | 联合历史按 normalize→validate 执行；当前 P1 也直接显示失效 | 合并为 normalize 后依状态 validate，再 dispatch | C 的主要依据当前协议及执行，历史不是唯一来源 |
| 原稿未选 unknown 策略 | 历史明确未测 unknown | 扩到 unknown 时 validate，Watch 保留未测 | 输出明确诉诸 `base_protocol`，应归当前协议支持的探索，不归历史实测 |

这比“读取了 Memory”更具体：模型把 current 的冗余行为响应联系到义务调整，把 stale 的响应联系到保留验证方向，同时扩大部分作用范围。未要求它输出固定 D/S/C 标签。

但归因仍有一处精度问题：理由称历史支持 `stale/absent`，脚本中初始 absent 先被 normalize 成 stale，真正 validate 前只有 stale 或 current；没有直接 absent→validate 响应。推广 absent 可由协议支持，却不应写成历史已观察。故判为**主要 S/C 决定有条件依据，历史／协议归因仍需更精确**。

### 4.3 同初稿无历史：核心调整仍然出现

[无历史输出][fusion-nohistory-output] 同样取消 critical/current 的过强验证，扩大到 active 的 absent/stale 条件，并保持 normalize→validate 顺序。它引用当前 P1/P2 和协议，没有捏造历史。

输入核对确认：原始 payload 仅 `memory` 不同；系统消息完全一致；模型消费视图只改变 `memory / historical_sources / historical_contexts / historical_updates`。

有历史输出选择合并 u2 并覆盖 unknown；无历史输出保留两个协调要求、未显式扩大 unknown。二者核心 S/C 相近。**这只能说明当前信息足以支持同类决定，以及输出在一次历史条件改变后存在差异；不能证明差异由历史造成，更不能证明额外收益。** 两次均为一次随机采样，不是正式消融；正常主线的空历史程序恒等未被改动。

### 4.4 部分适用历史：输出无效，Keep／探索能力未获有效验证

[limited 原始可见输出][fusion-limited-output] 在字符 1,609 处缺少合法 JSON 闭合，解析错误 `Expecting ',' delimiter`。HTTP 200，provider 结束原因 `stop`，completion 3,399；不是输出上限截断。没有清洗、补括号、改 Schema 或重新调用。

只能把可读文字作为失败诊断，不能称为有效 Plan：它意图保留 u1，把 u2 的 inspect-first 改为 validate-first，主要理由来自当前协议，而非历史响应。并且把从未执行的 inspect-first 称为 insufficient／potentially unexecutable：当前 P3 只有两次 wait，原稿也没把 inspect 当作 validate。这是对未执行策略的负面判断风险。

本案例原本允许 Keep，也允许有依据的有限变换；失败不在于“没有 Keep”，而在于结果无效和解释失真。本次没有获得一个合法的全量 Keep 输出，不能据此认定系统过度 Keep，或合理 Keep／未知下探索已通过验证。

## 5. Editor：映射合法不等于选定语义被完整保持

本探针有效 Plan 是 [人工冻结 u3][editor-fixture]，**不是** §4.2 模型输出的 u3。它要求 absent/stale 时先验证，current 时允许直接 dispatch 并不禁止有理由复查；unknown 只说明“不是 current”，未选择其具体恢复策略。

[Editor 输出][editor-output] 返回 `candidate`，实际 [diff][editor-diff] 相对冻结的合成 Parent 修改；所有摘录和 requirement 映射通过程序检查。

正确落实的部分包括：两种优先级、normalize 后验证、current 可直接执行且允许 justified recheck、保留 Parent 的拒绝后 validate-and-retry、取消／已完成保护和同一请求身份。没有无必要阻断。

**局部忠实性失败：** reason 声称 u3 要求 `absent/stale/unknown` 都主动验证，Candidate 也写入该强制分支。实际 u3 只选择 absent/stale；“unknown 不等于 current”不等于授权 Editor 在 inspect、validate 等可行恢复之间自行选择。协议说明 validate 可使状态 current，支持这是一个可行策略，却不能替代有效 Update 的选择权限。

该案例本来保留 unknown 策略未确定，这是输入局限；不能要求 Editor 凭空补全所有未知分支，也不能把单次输出泛化为 Editor 总会漂移。但它将未确定分支补为明确义务且误述上游要求，已经构成可核查的偏离。`issues=[]`、精确摘录以及 Candidate 可执行性都不能消除这一问题。

这份 Candidate 仅是独立验证文本，没有环境 Replay，也没有正式发布。

## 6. Replay／Memory：条件化学习部分成立，机会和归因仍有错误

[真实学习输出][learning-output] 产生 5 条 Findings、3 条 Open、3 条 delta。现有校验器检查通过；纯函数应用在验证目录得到 [4 条待检视 Effect][staged-memory]，不是正式 Memory。旧 m1、m3 被替换，旧 m2 保留，另增加一条不同来源搜索认识。

### 6.1 真实证据与输出逐项核对

| 实际执行事实 | 模型输出 | 评价 |
|---|---|---|
| Saltshaker C10:4 交付；:5 回 countertop 1 仅见 DishSponge；:7 打开 cabinet；:8 拿第二件；:10 完成 | f1 正确描述该分支，delta 2 学习另一来源寻找第二件 | 有相关机会和行动；但 Parent 也成功，9→10 步，不是该编辑新增成功收益 |
| Keychain C8:18/19 原来源是 sidetable 2；:22 交付；:23 去 sidetable 1；:24/25 在 tvstand 找第二件；:28 成功，没有返回 sidetable 2 | delta 2 将 C8、C10 都写成 returned/original source lacks take 条件下的响应 | **条件归因错误。** C8 支持另一来源完成，不验证“原来源已空后切换”的具体前提；该过强条件进入了新 Effect |
| Parent P6 见过并处理 Pot；Candidate C6 全程没有 Pot 编号观察、没有 take Pot 机会，50 步没有 take/heat/cool/clean/move | f2 称 Candidate 未拿取或加工 “the observed pot type” | **跨路径机会混淆。** 不能把 Parent 机会当成 Candidate 遇到后正确拒绝。f2 没有进入本次 delta，但它是反馈解释的真实错误 |
| C6 在其他异类 take 命令提供时继续搜索；仍没找到 Pan | 输出正确说目标未发现且失败，但未区分 Pot 与其他异类机会 | 可以观察到行为差异；不能验证相同 Pot 机会下的类型规则作用，也不能由终局失败否定未执行分支 |
| C1 没有主动停止并到 50 步；仍有其他 go-to，未证实所有不同候选耗尽；P1:20 stop 无效 | f3／Open 将其列为 nonexecution/realization limit，未判策略被执行后无效 | 避免了“失败＝策略无效”；但没有明确拆开停止接口不可用、触发条件未确认和实际重复行为 |
| C5 成功但 33 步，Parent 8 步；旧 R1 曾晚发现后未完成 | f4/f5 和 delta 1/3 保留慢路径、晚发现、无独立必要性／因果份额 | 正面：成功与效率不同，结果与单项更新效果不同；没有把整体 ACCEPT 当作所有编辑有效 |

以上事实可由 [冻结轨迹机械核对][evidence-checks] 和 [完整旧执行输入][learning-input] 重查。P/C 的观察是动作后的观察，机会以动作前命令集合及前序观察判断；没有生成新轨迹补证。

### 6.2 复合限制退役：未重演旧错误，但不要夸大覆盖

本次没有退役旧 m2 那条合并“另一来源／move 不可用／非 drawer”的限制，而是保留旧 Effect，再保存扩展更新的另一来源响应。新 delta 2 明确保留 “no unavailable move command at the destination was tested”。因此**没有出现未测 move 条件被一并解除**。

不能要求模型一定替换 m2 或复制旧报告的退役方式。旧 m2 描述旧 drawer／同源 move-first 更新，新 Effect 描述扩展后的另一来源更新，分开保存可以合法。该特定复合条目的“部分退役”路径本次并未实际触发，不能宣称已被充分验证。

另外两处真正发生的退役是正向证据：

- delta 1 退旧 m1 `limits[2]`，因新增 mug/microwave 响应扩展已观察对象范围，同时在新 limits 保留其他配对和目标已在关闭容器内的未知；没有把所有未知一并解除。
- delta 3 退旧 m3 `limits[0]` 的“两条历史任务”数量范围，同时保留最近两步、无持久记忆、厨房任务及联合归因限制。

这些结果支持“有限新证据可以扩大认识，同时保留残余条件”，不是每一条复合限制都已可靠修订的证明。

### 6.3 实际编辑、来源关联和持久化边界

程序侧确实接通了关联：新 delta 2 的 f1 经 `about=w5/u5` 自动保留 `watch:w5 / requirement:u5 / intent` 及构造来源，实际版本、diff、Editor 映射随共享 `actual_update` 保留。该机制在真实模型输出上运行成功。[待检视 Memory][staged-memory]、[消费视图][staged-view]。

但模型五条 Findings 的显式 refs 全是执行事件，没有给出有效 Update 与实际 diff／Editor 映射的明确比较。不能由输入中存在这些材料、或程序自动补齐来源，推断模型已经完成“所选策略是否忠实写入”的语义校准。本次可确认行为归纳和部分条件认识修订，不能确认落实偏差已被可靠识别。

此外，delta 1/3 的持久 `claim/limits` 直接使用 `H1::C6` 等临时消费别名，违反新规则要求使用当前别名或精确历史运行身份的约定。当前待检视视图中 H1 恰好仍对应 R1，**没有证据表明本次已串源**；问题是未来重新组织 Memory 时别名不具有稳定身份。结构校验仍允许该文本，故应列为持续学习的来源风险。

## 7. 五模块和共同决策结构的总评价

| 环节 | 程序／来源检查 | 实际模型语义结果 | 不能据此声称 |
|---|---|---|---|
| Diagnosis | Plan、当前来源、分组合法 | 具体原始更新已生成；Goal／策略、控制能力和 S 仍有缺口 | 原始 Update 已稳定可预条件化 |
| Memory 作为输入 | 真实 Effect 的实际编辑、事件、边界可读取；合成资料标记清楚 | 合成 Fusion 使用了具体响应差异；真实历史更多约束预期 | 只要存在 Effect 就产生有益变换 |
| Fusion／Compiler | 3/4 输出合法；增量和 Watch 可编译 | 合成 S/C 有依据；真实控制分支仍错误；Keep探针无有效结果 | 历史独有贡献、D 改向收益或普遍不过度保守 |
| Editor | Candidate 文本、映射和实际 diff 合法 | 大部分既定分支和例外保留；unknown 被擅自补成义务 | 摘录覆盖等于完整语义等价 |
| Replay／Memory Learning | 配对、版本、来源和 delta 应用合法 | 保留多项未知、联合归因并局部修订；机会和条件仍被混用 | 任务成功证明某项编辑有效，或学习已完全校准 |

分类确实参与了本次 Diagnosis／Fusion 的更新组织：真实缺工具、第二件来源、状态处理分别引用当前决策组和具体事件；融合比较也围绕决策条件。合成案例展示同组里的 stale/current/unknown 不能当成同一种历史支持。

不过本次没有新分类调用，也没有专门验证跨组迁移；历史适用性主要依赖自然语言条件判断。不能把 group ID 被引用视为分类已带来额外预条件化收益。已看到的 Keychain 触发条件混淆也说明，来源／分组合法并不保证条件比较正确。

这些是独立探针对共同机制的检验，不是一次从新 Diagnosis 到新环境反馈的完整在线闭环。真实学习读取的是旧闭环；新 Editor 从未执行。

## 8. 成本、有效率和失败账

完整账见 [accounting.json][accounting]；请求与响应保存在各案例目录。下表 output 包含 reasoning；visible 为 provider completion 减 reasoning，并非重新分词估算。

| 探针 | 输入 Token | 输出 Token | 其中推理 | 可见输出 | 请求耗时（秒） | JSON／契约 |
|---|---:|---:|---:|---:|---:|---|
| Diagnosis 真实 | 51,170 | 8,809 | 8,144 | 665 | 153.2 | 通过／通过 |
| Fusion 真实 | 65,970 | 6,570 | 5,501 | 1,069 | 110.3 | 通过／通过 |
| Fusion 历史适用 | 7,080 | 14,154 | 13,567 | 587 | 230.7 | 通过／通过 |
| Fusion 部分适用 | 7,763 | 3,399 | 3,043 | 356 | 57.3 | 失败／未进入 |
| Fusion 无历史 | 4,112 | 11,428 | 10,863 | 565 | 184.3 | 通过／通过 |
| Editor 独立 | 6,571 | 5,294 | 4,839 | 455 | 74.9 | 通过／通过 |
| Replay／Memory 真实 | 109,941 | 20,980 | 18,559 | 2,421 | 320.1 | 通过／通过 |
| **合计** | **252,607** | **70,634** | **64,516** | **6,118** | **1,130.9 累计** | **6/7** |

- 总 Token **323,241**；命中缓存输入 **2,048**，均来自无历史探针。失败请求的全部 Token 已计入。
- 7 次逻辑调用、7 次 HTTP 尝试，全部 HTTP 200；无重试、无重复采样、无截断。并发 2，实际调用窗口 **715.7 秒**（约 11 分 56 秒）；累计请求时间不等于墙钟。
- 严格 JSON／契约有效率均为 **6/7＝85.7%**；Fusion 为 3/4。小样本描述，不估计稳定成功概率。合法结构内仍有语义问题，不另用一个未经预注册的“语义通过率”掩盖部分符合。
- reasoning 占输出约 **91.3%**。本次预算避免了已知截断，但提高上限没有解决 JSON 失配，也不能说明成本已适合多轮生产训练。
- provider 没有返回货币费用，内部代理计费单价未提供。**货币成本未知，不是零**；未套用外部公开价格猜账。

全部调用都使用预先确定的上限；没有观察失败后追加预算。有效输出率只是接口可用程度，不是预条件化收益指标。

## 9. 是否进入新的 ALFWorld 流式实验

**建议暂缓正式新流式实验。** 当前阻碍集中在统一作用链的三个关系及一个调用可靠性事实，而不是需要五个模块各增加一套新功能：

1. **构造关系：目标→可执行且范围受支持的 Update。** 真实 Diagnosis/Fusion 仍放行无控制出口的策略，并从局部条件扩大义务。即使环境最后成功，也不能解释为所选预条件化策略被执行。
2. **落实关系：有效 Update→实际编辑。** Editor 将未选定分支变成强制策略；后续行为就不再严格对应已选更新。需要保持语义权限边界，而不是针对某个状态名增加专用禁令。
3. **学习关系：机会→行动→条件化响应。** 新 Effect 仍可能把没有实际验证的触发条件写成响应前提；临时历史别名也不适合持久知识。若直接进入持续训练，这些认识可能影响下一轮 D/S/C。
4. **一次调用可靠性。** 一个短输出在无截断情况下 JSON 失败。6/7 不足以证明现有零重试路径稳定；本次没有通过修复或补采样遮蔽它。

这不是要求现在增加新 Agent、逐项证明表或全面阻断未知更新，也不要求把所有输出强迫为 Keep。后续若经确认开展完善，应围绕上述关系检查最小必要变化；本轮只交付反例和边界，不修改规则。扩大环境预算不能替代对已知语义偏离的确认。

尚需未来独立验证的内容包括：可比较历史支持的新 D 策略替代、合法 Keep 与未测条件探索、跨组条件迁移、真实 Editor Candidate 的行为机会与响应、成本与稳定性，以及无历史对照下的实际更新收益。新 Train 和正式消融必须另外冻结，不能在这七次结果上反复调参后宣称泛化。

## 10. 交付与不可变性核对

- 新增报告和独立验证档案；没有修改算法、Prompt、Schema、Gate、正式运行器或旧产物。
- 首次调用前冻结的 **33 个文件**逐字节保持不变；每个实际发送请求的哈希与冻结请求一致。
- 基线覆盖的 **1,160 个既有文件**全部哈希相同，无删除；包括 V22 源码、相关测试、文档、配置和旧实验档案。工作区原有修改保留，没有提交或回滚。
- 所有新 Skill／Memory 仅为验证目录中的未执行／未发布数据；**0 个新 ALFWorld episode，0 次正式 Skill／Memory 发布**。
- 本次未再次运行完整 345 项离线回归；其结果是前一步已有证据。本次执行的是实际消息重建、输入／版本校验、七次真实语义调用、输出契约检查、纯函数编译／待检视 Memory 应用和人工语义核对。
- 报告只使用模型最终可见输出评价决定；推理 Token 仅用于成本统计。

[archive]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015
[design]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_UPDATE_DESIGN.md
[implementation]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_IMPLEMENTATION.md
[audit]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/DSC_MECHANISM_AUDIT.md
[rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:10
[messages-builder]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/grouped_update.py:150
[memory-view]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/effective_memory.py:38
[protocol]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/protocol.json
[freeze]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/freeze.json
[prepare]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/prepare.py
[control]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/control.py
[input-review]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/input_review.json
[editor-fixture]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/editor_fixture_decision.json
[real-r2]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2
[learning-input]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/learning_real/payload.json
[evidence-checks]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/archived_evidence_checks.json
[diagnosis-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/diagnosis_real/parsed.json:5
[fusion-real-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/fusion_real/parsed.json
[fusion-applicable-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/fusion_applicable/parsed.json
[fusion-nohistory-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/fusion_nohistory/parsed.json
[fusion-limited-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/fusion_limited/content.txt
[editor-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/editor_frozen/parsed.json:4
[editor-diff]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/editor_frozen/actual.diff
[learning-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/learning_real/parsed.json
[staged-memory]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/learning_real/staged_memory.json
[staged-view]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/learning_real/staged_memory_view.json
[accounting]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/accounting.json
