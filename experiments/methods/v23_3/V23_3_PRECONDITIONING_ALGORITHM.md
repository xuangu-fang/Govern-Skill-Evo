# V23.3 P1：历史响应驱动的更新决策算法

本文件定义决策算子，不是已执行的新模型结果。流程中的语义判断由一次 Preconditioner 调用完成；程序只执行后面的 Patch、结构与编译检查。

## 1. 决策单位与证据使用规则

对 Original Update 中可独立保留、修改或撤回的行为要求，理解其**触发条件、行为选择、作用对象、强度、退出条件**。P1-R 规定未来 Diagnosis 将这类完整要求尽量分别组织成行，但决策对象仍是行为含义，不是行号本身。这些维度不序列化为新字段，也不按句号自动切分。

对每个相关历史条目，按以下顺序判定能否使用：

1. **先核对实际编辑。** 对比历史 Parent 与 actual.diff，确认有关指导确实被改变。仅在旧 Skill 已存在的规则不能算该轮新增；多个联合修改不能拆成已证明的单因素效果。
2. **再核对实际响应。** 看动作前条件、动作后结果、具体位置/对象、完整成功/失败链。knowledge 与 sources 不符时以可核查来源为准；保留正确部分，不把整条 Memory 一概弃用。只见未找到不能推断不存在。
3. **判断条件相容性。** 比较任务阶段（搜索/持物/处理/交付/数量）、Actor 视野、合法动作与环境协议、目标/位置粒度、预算约束。条件不同且可能影响效果时，不直接迁移该结论；仍可将其作为需测试的类比。
4. **限制结论强度。** 同任务/实例/初始状态/协议的真实 Parent/Candidate 配对支持“这一编辑组合伴随了这一响应”；单次配对不证明稳定因果。不同实例只提供可行路径或反例线索。聚合成功数不能决定哪条子句有效。
5. **逐关系消费证据。** 同一历史编辑的正例可支持探索方向，负例限制覆盖单位/触发范围，未解决的循环表明旧文字落实不稳。不能把这三者压成一个“策略有效”标签。

不要求持久化证据矩阵；既有 `basis` 标识来源，`reason` 点明实际编辑、正反响应、适用条件和限制。历史细节用 `context/diff`、`context/Pn:step` 等现有引用写在 reason；Adjustment.basis 仍使用原编译器允许的 M ID/当前引用，不能把来源路径误塞进 basis。

## 2. 五种决定的充分动机与边界

表中决定可作用于一个子句，也可影响多个 Update；不是新增枚举字段。先排除事实/能力错误，再选择修正或探索。不存在“Memory 非空必须改”或“没有确定最优策略必须 Keep”规则。

| 决定 | 何时有依据 | 如何改变实际要求 | 适用边界与可反驳点 |
|---|---|---|---|
| **Keep** | 当前要求可执行且与目标相容；历史无关、条件不可迁移，或正反响应已被现有边界涵盖；没有独立修改动机 | 不修改对应要求所在行；整个 Update 均保留时才省略该 Adjustment | 不能仅因没有 Memory 就宣称要求正确；已有不可见状态要求或反例未处理时，Keep 的解释不成立 |
| **收窄** | 原要求量化过强，当前事实/相容历史反例只支持某些状态；存在可见条件可区别适用与不适用情形 | 将无条件命令/禁令改为状态限定，降低“必须/永不”的强度；保留有依据的核心 | R04 “closed 就 open”不能由成功链推出必要；R05 无效后永久禁同类动作须限定状态未变、无新信息。单个反例否定普遍保证，不证明所有相反动作都更好 |
| **放宽** | 原策略排除了仍有价值、合法且目标相关的选择；正例或混合响应支持扩大选择空间 | 撤掉硬前提或增加可观察例外，不要求新选择总是优先 | R04 已知剩余目标回源；R05 不必等穷尽才能探索其他类别。扩大可选集合不证明新增顺序最优，不允许据此降低完成标准 |
| **替换** | 现有行为关系与能力不相容，或相容的混合响应使单纯加严/重复旧指导缺乏理由；新策略有自己的问题动机，能在可见条件下执行 | 用可检验的新选择规则替代旧调度，可大幅重写；reason 明示未知收益，Checks 包含反例 | R05 可尝试近期无进展时跨类探索；不能写成“历史证明跨类必优”。无反例区分信息时，不假装找到了精确最优触发阈值 |
| **撤回** | 某新增分支没有支持且把猜测写成必然，或不可执行/冗余/与必要行为冲突；删除后有其他要求承接必要能力 | 子句用 Diff 删除；整项用既有 `to: []`；同步修订悬空 Checks | R06 “动作未提供就放入并执行”的保证性备用分支可撤回，保留有据处理与交付。不能把“未来收益未知”当撤回所有探索的理由，也不能撤掉唯一必需行为后称 Plan 完整 |

当多个操作都成立时，选择一个可执行候选即可；不要求评分最优。选择依据是哪些问题被解决、哪些新假设进入、哪些边界仍保留。不能按修改字符最少或最保守排序。

**证据足以纠错与证据支持探索不同：** 行动前菜单/协议可以排除不可见状态或错误必要性推断；历史混合响应通常只支持重新分配探索机会。即使方向有历史依据，具体触发和顺序仍可能是新假设，应单独标明并评价。

## 3. 范围与必要关联的操作规则

对每项拟改变的行为要求，执行以下判断，而非笼统“检查副作用”：

- **范围投影：** 写下 Actor 实际用什么判断触发。若需完整访问集合，尝试改用当前观察、候选和最近两组记录；若投影后不再能判断“全部完成”，删除该完成推断，不能用局部状态代替全局状态。若没有可行投影，保留其他独立可行部分或请求上游澄清。
- **依赖反事实：** 暂时保持相关旧要求，目标变换还能合法执行吗？若旧前提直接禁止新选择、要求不可得信息，或使必要任务环节无法进行，则同步改它，并在 reason 指出具体冲突。改变搜索调度而保留处理/交付仍可执行，后者就不是可随意改写的配套。
- **独立动机检验：** 对其余新增要求问“去掉它，目标变换是否仍成立？”若成立，它就需要自己的问题证据和预期行为。类别一次退出并非表达跨类探索所必需；没有另一个独立问题及边界，不能进入输出。
- **闭合检查：** 目标与配套都修改后，重读同一 Update、其他 Updates 和 Goal 是否仍有反向约束。Checks 只能观察行为，不能替 Actor 指令补触发条件。

这不是语义判定器的代码保证。规则规定应作什么选择，既有 reason 提供可审阅理由，后续人工评价检验理由是否成立；不新增审核 Agent 或第二次模型调用。

P1-R 对应关系：先选择受历史响应约束的行为要求，再定位其原文行；配套要求依据具体冲突同时修改，可以跨行、跨 Hunk、跨 Update。一个触发条件及其动作不拆散；关联含义由既有 reason 解释，不增加行 ID 或依赖图。没有独立理由的行保持原文，有据的大范围修改仍允许，不以最少行数为目标。不能先生成整段替代策略，再反向生成 Diff 给既成改动补理由。

旧单行 Original 不自动拆分；它仍受整行替换限制。R04/R05/R06 的多行副本是人工设计材料，表示层保留旧问题，后续测试 Patch 才改变策略；见 [P1-R 走查](p1r_multiline_001/P1R_CASE_WALKTHROUGH.md)。行级保护不等于行内语义保护，新增出口或排他禁令仍需独立评价。

## 4. 完整流程、输入和输出

| 步骤/责任 | 输入与决策依据 | 输出 |
|---|---|---|
| 1 Diagnosis | 当前 Parent、Grouping、执行；目标/可调整策略/保留能力 | Original Plan，未来直接生成按完整行为要求分行的 text；若非 revise 沿用原停点 |
| 2 输入装配程序 | 原 `preconditioner_input`，冻结的 Active Memory 与 sources | 现有 payload；记录实际选入的当前执行，不暗补证据 |
| 3 Preconditioner | Original 行为关系与历史实际 Diff/响应；按第1节检查条件与反例 | 相关支持范围，写入已有 reason/basis；没有独立中间协议 |
| 4 Preconditioner | 第2节决定表，当前可执行条件及 Goal 权限 | Keep 或一组修改/探索意图 |
| 5 Preconditioner | 第3节的范围投影、依赖反事实、独立动机和闭合检查 | 完整修改内容、依据、必要配套及观察问题 |
| 6 同一次 Preconditioner | 选定行为要求、必要配套及 Original 精确行 | 一个或多个 Hunk 的 Unified Diff；未选行保留，Checks 保留或合法替换 |
| 7 确定性程序 | ID 选取、原补丁应用器、原 Adjustment 校验/编译 | 正式 Adjustment + Effective Plan；出错不发布部分结果 |
| 8 Editor | Parent + Effective Plan + Actor 背景 | Skill Patch、Candidate、actual.diff；本阶段不调用 |
| 9 Actor/Replay/Memory | 同条件 Parent/Candidate 执行与真实 Diff，成功/退化/条件差异 | Replay knowledge/evidence 经现有 Memory 提交进入下一轮；本阶段不运行 |

语义过程伪代码（一次生成内的决策，不是串行调用多个模型）：

```text
Original = Diagnosis(current_parent, current_facts, grouping)  # 既有阶段
if Original.decision != revise: return existing_stop
payload = v23.preconditioner_input(Original, frozen_memory)

inside ONE Preconditioner generation:
    for each behavioral relation in Original updates:
        identify current problem and valid behavior it must preserve
        inspect relevant historical actual edits, then positive/negative responses
        restrict each claim by observable conditions, granularity and attribution
        if a claim contradicts a source: discard that claim, retain usable evidence
        if current rule overstates a condition: narrow or remove that condition
        else if it excludes justified options: widen permission or propose replacement
        else if history leaves the current problem unresolved and a new executable
                hypothesis addresses it: propose replacement with falsifiable Checks
        else: Keep
        withdraw unsupported guarantee branches if needed behavior remains covered

    for each proposed extra change:
        if leaving old requirement makes selected change contradictory/unexecutable:
            coordinate it; explain that exact dependency in existing reason
        else if it has its own problem evidence and observable hypothesis:
            include as independent exploration; do not assert guaranteed improvement
        else:
            exclude it

    check local observability, necessary task behavior, Goal compatibility and Checks
    if essential Goal meaning cannot be resolved consistently:
        return need_evidence with reason requesting upstream Goal clarification,
               adjustments=[], checks=null  # 不自动重调 Diagnosis
    locate selected requirements and necessary companions in original text lines
    emit hunks directly against those original lines plus existing basis/reason/checks
    # Do not auto-split historical single lines or rewrite the whole Update first.

formal_result = normalize_update_patches(raw_response, payload)
Effective = v23.compile_effective_plan(formal_result, payload)
if not ready: return existing_stop
Candidate = unchanged_Editor_interface(Parent, Effective)  # 将来执行
paired_runs = same_protocol_execution(Parent, Candidate)   # 将来执行
Replay = existing_replay(actual_skill_diff, paired_runs, Effective, Memory)
Memory_next = existing_commit_memory(Replay)
```

`need_evidence` 只用于确实缺少构造一致 Plan 所需的信息/上游意图。若 Goal 锁定某实现而需要整体取消，reason 必须明确这是待修订的上游契约，不能假称“多读历史就能改 Goal”。能够在现有 Goal 内完成的调整不因此全部停止；但不允许把仍与 Goal 冲突的方案发布为 ready。编译器不会自动发现该冲突。

## 5. R04/R05/R06 只读走查

所有“建议变化”均为本次人工设计推演，不是新模型输出、Candidate 或收益证明。P1-B Original 与正式 V23 Original 不同，不能用正式 Keep 冒充 P1-B 被保留。

原始输入：

- R04：[P1-B Original](../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R04/attempts/001/diagnosis.json)、[当前事实](../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R04/attempts/001/input.json)、[正式历史响应](../../../artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/preconditioner/attempts/002/preconditioner.json)。
- R05：[P1-B 重试 Original](../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json)、[A/B 当前共同输入](../v23_2/v23_2_preconditioner_memory_ab_001/config/common_payload_without_memory.json)、[当轮 Memory](../../../artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R05/preconditioner/attempts/001/input.json)。
- R06：[P1-B Original](../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R06/attempts/001/diagnosis.json)、[当前事实](../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R06/attempts/001/input.json)、[当轮 Memory](../../../artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R06/preconditioner/attempts/001/input.json)。

### R04：动作链不能替代必要条件

| 原始要求与证据 | 规则决定 → 可构造的实际变化 | 配套、保留与验证边界 |
|---|---|---|
| u1：`if the microwave is closed, open it once`；P2:6/P3:7/P4:5 的 before 为 closed，候选已有对应 heat，但实际先 open | **收窄**必要性要求：持有精确目标且所需处理动作当前可用时可直接执行；开门由访问/动作前提决定。菜单否定“现有事实证明必须开门”，不证明提前 heat 一定成功 | 同步协调 `held at the open microwave`，否则新分支被旧前提否定。保留精确类别、成功处理后交付；不自动删所有 open |
| u2：移走过一物体就排除该源；P6:24 取第一 candle、27回源、28取第二；P8:2/7/8 同类路径 | **放宽**回源许可：当前或近期信息确实显示有用剩余目标时允许回源；“移走过一件”不等于“空” | 配套修正“仅从未访问位置继续”。成功回源本身不证明 Actor 在几步后仍能记住全部源；条件必须在决策时可恢复。保留所需数量 |
| Goal 写 `by sweeping all receptacle types once` | 修改上述局部条件有权限；**彻底取消此 Goal 实现承诺没有权限** | 不声称整轮已完全解决。若与数量完成后结束的解释冲突，需要上游澄清；不通过 Update Patch 假装修正 Goal |

正式 R04 已有两项相关 Adjustment，是旧接口具备能力的证据，不是 V23.3 的结果；它仍含全局覆盖文字，不能当作新算法的完美答案。当前证据纠错与历史 M4/M6 的响应依据应分别说明，不能将当前可纠正的问题计成 Memory 独有收益。

### R05：混合响应改变调度，但不授权类别级出口

M6 实际来自 S1_R03 联合编辑：扩展搜索以及精确类别、处理/交付等。Q4:12 到 diningtable、13取 bread、17交付；P2:15/16 在 countertop3 发现并取目标，而 Q2 多次去 countertop2、未到 countertop3、50步失败；Q6 重复不可用 cabinet3 移动，49步才取 plate，50步到 fridge 耗尽，Parent 38步完成。

| 输入关系 | 规则决定与实际文本构造方向 | 为什么其他变化不随之获得授权 |
|---|---|---|
| u1：`once that series is exhausted ... switch` | **放宽/替换探索**：在当前及最近两步显示同类连续检查无目标或无信息重复，且有其他合法合理候选时，允许在耗尽前改变探索方向；同类有价值实例仍保有访问资格 | M6 正例支持扩大有目标位置的机会，反例要求保留同类实例机会；不支持所有新类别一律优先。新触发的收益仍待 Replay |
| `not yet inspected in this search`、`without returning to earlier ones` 与新局部触发冲突 | **必要配套**：用可见近期重复/当前目标线索约束选择；去掉无法恢复的全程访问前提和绝对回返禁令 | 不证明整个空间已查完；当前候选只提供可选动作。多个句子需一起改，可替换整条 u1，不限改字数量 |
| P3-B 新增 `every receptacle type ... sampled once` | **排除/撤回该无据附带承诺**：它不在 P1-B Original 中，因此构造新方案时不加入；在评价旧 B 时判为新增无据出口 | 类别 ≠ 实例；去掉这个出口仍可表达跨类探索，故不是必要配套。Original/Parent 的位置级全局覆盖前提也须单独检查，不因其旧有就认定 Actor 能判断 |
| u2：一次无效后禁止相同/等价动作、立即 state-changing | **独立收窄**：状态与前提未变且无新信息时避免重复；保留前提改变后的有效重试及有信息价值的检查 | 动机来自当前 no-op/观察事实，M6 可加强“旧指导未稳定落实”的认识；不是 u1 调度的必需配套，不能借其依据新增永久动作黑名单 |
| 精确目标、处理/交付、灯具行为 | **Keep**其必要边界；Checks 改问具体位置检查、同类遗漏、局部触发和交付 | Goal 保留不自动证明所有行为不受影响，后续须回放；不得把灯具已知目的地回返误判为空搜索循环 |

这可以形成一次大幅 u1 重写和一项独立 u2 收窄，均由现有单 Update Unified Diff 表达。只读走查没有选出唯一优胜搜索算法。R05 当时没有 M10，不能拿 R06 的后验 Memory 指导 R05。

为保留 P1 设计历史，以下仍展示当时**人工拟议的完整 u1 文本**。它不是 P1-R 的人工多行 Original，也不是未来先全文重写再造 Patch 的流程；P1-R 按原始要求组织的副本及所选行修改另见走查。该文本不保存为模型响应或 Effective Plan，也不作为通用 Prompt 的正确答案：

> During search for the exact requested object, or for the required lamp while holding that object, choose available actions from the current observation and admissible candidates. Inspect a reached closed container by opening it when necessary to see its contents. When current and recent observations show no target and repeated unproductive visits or successive unproductive checks of one type, try another plausible available receptacle, including a different type; do not require exhausting that type first. Do not exclude another instance of the same type or a known useful destination merely because its type or location was visited before. Use only currently observable or recently available evidence to avoid immediate uninformative repetition; do not infer that all locations have been inspected. Finding the exact object ends object search and starts the required acquisition, conditioning and delivery; lamp tasks must preserve holding and co-location requirements. Sampling each type once is not evidence that the search or task is complete. Do not acquire, condition or place substitutes.

相对 Original，它实际移除了“类内穷尽才换类”和全局未访问前提，保留同类实例的访问资格；相对旧 B，它没有类别一次出口。M6 支持的是这一探索的动机与限制，不是这份具体调度已经最优。u2 的独立收窄与 c1/c2 的观察边界还需同时落实，不能只替换此 u1 就宣称整份 Plan 验收通过。

### R06：真实 Diff 的调度差异与 Goal 边界

M10 对 S1_R05 的 summary 省略 `rather than exhausting`；实际 Diff 明确扩展跨类而非耗尽一类。P6:3 已到 countertop1，Q6:16 在 countertop2 发现 butterknife、21步完成，这是同类新实例，不是 Parent 从未去过该类。Q8 的 shelf1 才是新增类别例子。P7/Q7 未找到不证明目标不存在；P10/Q10 均成功但 38→46 步，限制“更快”的普遍保证。

| 输入关系 | 规则决定 → 实际构造方向 | 边界 |
|---|---|---|
| u1 `consumed`、`unvisited instance/wholly uninspected family` | **替换**全局进度要求为可由当前/近期观察判断的探索规则；编号可作局部候选线索，不能充当全局 visited 证明 | 不能因 M10 写 family sweep 就 Keep 任意类内调度。原 Diff 与当前策略不同，历史收益不能直接转移；允许新假设但需检查同类遗漏和增步 |
| u1 的永久 consumed 与 u3 known source | **必要配套放宽**：已知来源仍有有效目标时不被 consumed 一概排除；同时保留数量目标 | 必须说明来源信息此刻可获得，不要求超出两步历史的记忆。u3 的必要数量行为 Keep |
| u2 `If ... not offered ... place the target inside once and perform the action` | **撤回保证性备用分支**或替换为可见前提修复后重新检查动作候选；仍保留必要处理及其成功确认 | P4:7/P5:6 放入后菜单无 heat，但放入前原有 heat，不是相同 fallback 条件的受控反证；不能宣称所有放入方案必失败。撤回的是无据保证，不是处理目标 |
| Goal `numbered receptacle names`、`at the open appliance` | 保留编号线索、修改局部调度可兼容；完全去编号/取消 open 普遍前提不能仅靠 Patch 达成 | 需要上游明确或修订 Goal；不得把编译成功等同契约一致，也不为此重写全部 Diagnosis |

### 走查验收与反事实

五种操作均有上述真实问题对应：Keep 必要能力、收窄开门/禁重复、放宽回源/换类、替换全局进度/调度、撤回无据 fallback。它们是明确的“证据 → 选择 → 修改对象 → 不应新增要求”，不只是输出解释模板。

可反驳预期：若删除 M6 的同类遗漏反例，只保留扩展成功，不能再声称已用该反例限制类别出口；若恢复反例而输出仍给类别一次停止作普遍保证，规则未被遵守。若将 M10 summary 换成正确来源解释，类内/跨类差异应该进入选择依据，不能继续称两者是同一历史策略。这些是未来测试条件，不是本轮新实验。

该设计仍需模型遵循率与真实执行验证。三个已反复参与设计的案例只证明表示能力和可审阅性，不证明泛化或成功率提升。
