# Evidence-Calibrated Update：固定材料结果

完成时间：2026-10-20（Asia/Shanghai）。**本次有局部校准改善，但A、B、C未共同通过，不建议晋升为V23.2下一优先候选。** R06确实从类内穷尽改成预算约束的跨类采样，没有再引入整套表面优先排序、类别采样一次终止或显式进度保证；但采样尺度、固定顺序及假设性质仍不清楚。R05反而把“不要漏掉同类实例”扩成查完该类再换类的倾向，说明历史反例仍可能被转成过强调度。R04温度操作的条件与强度匹配较好。

## 1. 离线分析与统一设计

先完成[已有版本离线分析](OFFLINE_ANALYSIS.md)，期间无模型调用、未修改Prompt。通过既有读取器重读3组正式结果与9组旧候选有效响应，核对共同Original及编译结果；[HISTORY.md](HISTORY.md)记录完整历史Original→Adjustment→Effective。[读取凭据](../config/offline_read_receipt.json)记录Prompt全文共同上下文、替换块和原档案位置。R03/R05实际Editor Diff与R06可见Memory sources再次逐字核对，M6/M10不由结束后的Memory替代。

共同问题：历史经常能够说明需要改进覆盖，但不能独立支持某个具体顺序、阈值、强制禁令或完成边界。需要区分有动机的新策略与缺少对应理由的附带要求。未经历史成功验证不等于错误；反过来，明确提出一种新策略也不自动为它的所有强制细节背书。R04的温度案例条件与动作对应较直接，R05/R06搜索调度的证据更混合。

已完成的alignment行为实验只提供局部观察：新旧Candidate均5/7，新162步对旧202步；plate较早找到，apple/book仍50步循环。没有观察到类别采样后的提前停止，不能把文本风险当作已证实失败原因。Editor实现和Actor随机性未隔离，联合编辑不支持单条独立因果结论。本轮未重跑该实验，也未将其结果加入模型输入。

新设计统一强调：**历史响应与当前证据同时校准最终策略、条件及强制程度，适用于所有保留／修订Update。** 允许大幅修改及问题相关的可检验假设，借既有reason/checks表达预期，不要求把Actor指令写得含糊。详见[设计理由与边界](DESIGN.md)。

## 2. Prompt与调用前冻结

仅在原V23第一节一处替换三段、152个英文词。其余Memory比较规则、模块职责、Keep／合法停止、JSON契约、Checks和编译完全不动。没有重新启用Actor能力补丁，没有新增专用案例、评分或输出字段。

- [完整最终Prompt](../config/preconditioner_prompt.md)
- 精确Diff：[正式V23](../config/v23.diff)、[alignment](../config/alignment.diff)、[construction](../config/construction.diff)、[symmetric](../config/symmetric.diff)
- [冻结全文及设计材料](../config/implementation.json)、[冻结哈希记录](../config/freeze.json)、[三轮固定配置](../config/plan.json)

冻结于 **2026-10-19 15:59:44 UTC（本地23:59:44）**，首次请求始于 **16:00:01 UTC（本地次日00:00:01）**。调用后再核验Prompt、Diff、离线分析、设计、编排、计划和历史对照的冻结内容／哈希一致。没有根据输出修改候选。

相对alignment，本次不止追问原案支持范围；相对construction，校准不只针对Adjustment新增部分；相对symmetric，从差异清单转为scope/force与支持依据的统一匹配，并明确附带限制和必要任务完成条件不能借另一修改的理由自动成立。这是设计假设，不是已证明的Prompt效应。

## 3. 五版本对照与实际输出

每版均独立输入同一轮正式Original，不以此前Effective作新输入。完整五版 `reason/adjustments/checks/effective_plan`、Original全文及本次全部原始尝试见[OUTPUTS.md](OUTPUTS.md)，机器对照见[comparison.json](../results/comparison.json)。以下仅总结实质变化，不替代全文。

| 条目 | 正式V23 | alignment | construction | symmetric | 本次calibration |
|---|---|---|---|---|---|
| R04 u1 | 显式heat/cool、可用时持物执行、按需开门、直送 | 宽温度触发、只明确heat | hot场景直接heat | heated场景直接heat、按需开门 | hot场景；明确到microwave后动作可用时持物heat，按需开门、直送 |
| R04 u2 | 当前／近期仍有第二件时优先回源、计数／覆盖 | Keep | 可见第二件优先、否则新位置 | 已知第二件优先；扩大every listed | 近期避循环与具体候选；无回源优先；结束措辞从inspected变considered |
| R05 u1 | Keep | Keep | Keep | Keep | Keep |
| R05 u2 | Keep跨类single-pass | 换类但不跳过同类剩余实例 | 近期名称／局部换类启发式 | few如2–3个交错批次、绝对单次 | 查完列举成员才视为该类穷尽，Once checked再换类；Checks明确换类前查完 |
| R06 u1 | Keep | Keep | Keep | Keep | Keep |
| R06 u2 | Keep类内穷尽＋保证 | 不先穷尽大类；各类采样一次终止；保证 | 只改信息源，保留穷尽／保证 | 表面→设备→柜子→抽屉；全pass续行限制 | 预算约束的类内采样后换类；固定次序未定义；全位置一次边界，无显式保证 |

本次有效原始响应：[R04/002](../../../../../artifacts/methods/v23_2/v23_2_evidence_calibration_001/R04/attempts/002/raw_output.txt)、[R05/001](../../../../../artifacts/methods/v23_2/v23_2_evidence_calibration_001/R05/attempts/001/raw_output.txt)、[R06/002](../../../../../artifacts/methods/v23_2/v23_2_evidence_calibration_001/R06/attempts/002/raw_output.txt)。同目录含完整输入、messages、request、response、validation和Effective Plan。原编译器重读通过，调整文本实际进入最终`updates[].text`。Effective Update的basis按原编译规则继承，Adjustment依据仍保留在`adjustments[].basis`，未更改契约。

## 4. R04：有依据的强操作保留，搜索校准仍不完整

**u1有直接相关支持。** 最终写 `If the explicit heat action is admissible while holding the exact target, perform it directly`，并允许仅必要时开门。除了M4，当前P2:6、P3:7、P4:5的行动前观察均为closed microwave，动作候选已分别提供heat plate/potato/tomato；因此无需先插入再开关门的理由可从实际候选确认，见[关键当前事实摘录](../results/selected_current_facts.json)。P1错误拿cup并在heat后回microwave，支持精确类别和直送限制。

最终聚焦hot，与R04 Goal的heat-then-place一致，不把通用temperature场景都强制heat。M4同时支持cool，正式V23利用范围更广；本次较窄不等于删除Parent现有cool规则，也不证明cool被破坏。操作有条件且明确，不应为了“校准”故意弱化。

**u2有局部强度改善，也有边界歧义。** 从全局重复检查转向 `a receptacle you just saw was empty`、当前／近期观察，没新增固定阈值或绝对全程禁止回访；计数、精确目标和必要交付保留。未加入V23的已知第二件优先，不能说从Original删除了该要求，因为Original本无这一优先条款。

| 实质要求 | 对应依据 | 判断 |
|---|---|---|
| 近期确认空位置不反复检查，选择其他列举候选 | 当前P5/P7循环、M6混合反馈、Parent原有避循环要求 | 对当前问题有依据；与无限历史禁止回访相比更局部 |
| 用具体地点和近期信息使反循环更可执行 | reason声称M6表明抽象指导不可靠、近期选择更可执行 | 合理设计假设，但M6的实际R03 Diff本已写current/recent和具体位置；不能称新措辞已由M6证明更有效 |
| `all plausible named receptacles have been considered once` | Original为`inspected once`，支持实际覆盖 | considered可被理解为心理考虑，也可口语指检查，至少比原实地检查标准模糊；没有说明为何改变该完成边界。是文本风险，未观察到实际提前停止 |

结论：R04有效经验没有被证据要求机械撤回，温度条件匹配好；但搜索的假设／历史解释及终止措辞没有全面校准。

## 5. R05：合理的“别漏实例”被扩成顺序约束

历史M6实际支持：同类不同实例不能互相替代覆盖；Q2漏countertop3时Parent在那里找到bread。这不自动支持“当前类别的每个成员都必须查完才能去别类”。当前P8的cabinet/sink循环和P10迟到diningtable也只支持摆脱局部重复、到达遗漏位置，未对照证明类内穷尽更优。

最终u2写：

> Treat a receptacle family as exhausted only after checking each listed member ... Once a family has been checked, move to a different uninspected family ...

同时从Original删掉 `rather than exhausting ... one type`，保留 `instead of looping over one type`。这不是纯同义澄清。

“未查完不称穷尽”单独作为定义有依据；但它与`Once ... checked, move`组合后，至少放松了原“不先穷尽”的限制并倾向先查完再换类。新c2更明确写 `inspect all listed members ... before ... moving to another family`。**Checks不是Actor指令，不能把c2直接冒充最终Update的严格禁令**；但它说明模型把实例覆盖判断转成了换类前置条件，也使Update与检查目标的强度存在问题。

| 内容 | 依据／变化 | 判断 |
|---|---|---|
| 不把一个空实例当全类为空 | M6具体countertop3遗漏 | 有据细化，可保留；无需禁止新策略 |
| 换类前查完当前类 | Update倾向＋Checks明确要求 | 当前及历史没有对应顺序比较，reason仅称“preserving breadth”“preventing incomplete coverage”，未识别这是新的调度假设 |
| 不立即回刚查空处 | current/recent限定 | 比symmetric的全程at-most-once更局部，局部校准改善 |
| 精确类别、预算与搜索继续 | u1 Keep，u2保留 | 没有整体撤回探索或丢失目标要求，但不能抵消调度过强 |

未再出现2–3数值阈值，不等于无据强制要求已消失；约束转移到了换类前置条件。此轮A/B未改善，甚至相对Original的跨类意图存在退回风险。仍无新轨迹，不能声称造成实际遗漏或失败。

## 6. R06：取舍与替代构造分别核查

### A 原始Update

新reason明确指出原案 `exhausting one large receptacle family ... conflicting with the Parent Skill's single-pass family sweep`，并引用M10/M6。最终把类内穷尽改成budget-bounded sample后切换，是真实策略变化，不是仅理由提到问题。与construction的保留相比有改善，与alignment／symmetric一样恢复了对原具体调度的质疑。

M10实际Diff确实是跨类而非穷尽单类，当前P3循环也给出改进动机。但reason仍沿用“未到family救回”的概括，P6旧Parent已到countertop1，精确事实是漏了countertop2；历史也没有直接验证本次采样。故可支持探索，不足以证明这套替代调度已有效。

### B 替代Update的范围与强度

| 行为要求 | 实际最终变化 | 对应依据或假设 | 核查 |
|---|---|---|---|
| 类内穷尽→预算约束采样 | `After a budget-bounded sample ... switch`；类明显大于剩余预算时提前切换 | P3循环，M10覆盖条件性收益；M9的candle额外查drawer7/8、34步对Parent30步 | 有明确问题动机的新假设。M9是已可见来源，引用合理；联合编辑不证明采样策略独立有效 |
| 全局顺序 | `visit them in a fixed order`，类内升序 | 有序减少重复的动机 | 没有硬编码surface→appliance→cabinet→drawer，减少此前附带强排序；但fixed order和采样尺度仍未给出可判定规则。少了数值／类别表不等于已形成可执行策略 |
| 采样触发 | 预算约束、next indices unavailable、家族明显大于剩余搜索预算 | 与步数问题相关 | 可作为B类新假设；未说明预算如何分配、动作成本／阈值如何判定，reason没有明确区分预期与观察 |
| 回访限制 | `do not revisit ... confirmed empty while an untested one remains` | 减少无反馈重复 | 比无条件never回访多了条件，但仍是全局优先禁令，适用强度没有单独讨论；累计进度信息依赖仍存在，非仅因出现unvisited判错 |
| 搜索边界 | `until ... exact target ... or all plausible listed receptacles ... checked once` | Parent原有完整位置单遍边界，与覆盖问题相关 | 没有alignment“每类采样一次即可终止”的范围错误；不是凭空新增整项停止。仍需全局覆盖状态，不能因此断言安全或行为改善 |
| 效果表述 | 删Original `guarantee progress`，保留`memory-independent`；reason称`a more executable way` | 固定顺序动机 | 删除保证是局部改善；更可执行仍是未经测试的预期而非已观察事实，未清晰标为假设 |
| 有效任务要求 | u1 Keep，精确目标、开容器读内容、为温度／交付留预算 | M7及当前P4/P5、原Goal | 保留必要操作和完成方向，没有无理由撤回温度处理 |

R06原checks以`checks:null`原样保留，观察有序推进和最终交付，没有为本次budget-bounded sample单独提出可区分的检验问题。Prompt允许按需保留Checks，因此这不是契约错误；但不能说它已把新假设及预期表达充分。Actor两步历史不变，完整跨类进度仍是已知问题，本轮没有重开能力优化。

## 7. A、B、C最终判断与候选决定

**A 历史是否更准确地影响原始取舍？局部有，整体未证实。** R06历史差异落实到调度变化，R04操作保留；但R05将遗漏反例推广成类内完成优先，没有证据支撑该顺序。不能宣称五版本稳定优劣。

**B 是否更有效校准最终策略／范围／强度？局部改善，仍未通过。** R04明确温度条件，R06没有附带全局类别优先表、类别采样终止和显式保证；但R04 considered边界、R05换类前置条件、R06未定义采样及未标识的可执行性预期仍不匹配支持范围。模型写了“evidence”或“more executable”不替代证据核验。

**C 是否在保留探索时减少无据强制要求？保留探索，减少不一致。** 未撤回搜索或有效操作，R06允许大改；局部移除了某些旧强制要求。但R05产生新的顺序收紧，不能以无数值阈值／无旧句子认定整体减少。不是保守过滤器，却仍会把探索固化成强约束。

**建议：保存本候选及研究信号，不晋升为下一优先候选或默认。** 有价值的信号是部分操作条件、R06原取舍和某些附带限制有所改善；证据不足以确认统一校准原则被稳定执行。所有版本只有固定材料单次随机输出，且存在技术重试；不能把变化全部归因于Prompt，也不能推断ALFWorld成功率或独立泛化提升。本次没有根据结果追加补丁或行为实验。

## 8. 离线、成本、技术失败与历史保护

网络禁用的既有V23.2局部入口、V23 Diagnosis／Preconditioner相关回归 **171 passed in 3.09s**；新Prompt单块精确替换断言通过。[日志](offline_tests.txt)。没有新增自然语言审核器或修改原模块；`run.py`只提供独立路径与冻结包装，`analyze.py`只读取／比较。

| 轮次 | 实际输入字符／UTF-8字节 | 实际Active Memory |
|---|---:|---|
| R04 | 1,218,761 / 1,218,797 | M1–M6 |
| R05 | 1,614,123 / 1,614,143 | M1/M2/M3/M6/M7/M8/M9 |
| R06 | 1,494,346 / 1,494,362 | M1/M2/M6/M7/M9/M10/M11 |

全部实际请求（含失败）都核对输入与正式调用相等、非system消息逐字相等、system仅冻结块变化。参数与当轮原配置相等：deepseek-flash、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300；容量4,000,000字符／6,000,000字节，未压缩或删减历史。见[核验记录](../results/verification.json)。

| 请求 | 技术结果 | Prompt tokens | Completion tokens | Total tokens | 秒 |
|---|---|---:|---:|---:|---:|
| R04/001 | 引用契约失败 | 356,256 | 9,357 | 365,613 | 48.607 |
| R04/002 | ready有效 | 356,256 | 15,272 | 371,528 | 66.363 |
| R05/001 | ready有效 | 470,292 | 9,067 | 479,359 | 55.114 |
| R06/001 | 重复JSON键失败 | 433,016 | 6,525 | 439,541 | 40.824 |
| R06/002 | ready有效 | 433,016 | 6,900 | 439,916 | 38.126 |
| 合计 | **3逻辑、5请求、2技术重试** | **2,048,836** | **47,121** | **2,095,957** | **249.033** |

编排总耗时 **257.366秒**，包含读取／保存和重试等待。reasoning=43,201，属于completion子集，不重复计费求和；未知usage=0。两次失败均完整归档：[R04/001](../../../../../artifacts/methods/v23_2/v23_2_evidence_calibration_001/R04/attempts/001/raw_output.txt)的P6/P8简写被原正则当作历史引用，不能称捏造历史；[R06/001](../../../../../artifacts/methods/v23_2/v23_2_evidence_calibration_001/R06/attempts/001/raw_output.txt)在`adjustments[0].to[0]`重复`id`键（两值均u2），原严格解析器拒绝。没有手动去重或改简写。两轮均第二次合法后停止，未语义重采样，未耗尽重试；无容量或合法no_change/need_evidence停点。失败文本不当作有效Effective Plan。[错误说明](../results/technical_failure_note.json) · [全部用量／时间](../results/attempts.json) · [汇总](../results/summary.json)。

**11,964个保护文件的集合与SHA-256一致**，包括V23正式源码、Campaign、最终Skill、Memory和Test，及此前所有V23.2实验和原始产物。[保护核验](../results/protection.json)。Test只做文件哈希保护，未使用其轨迹做分析。原模块、输出契约、Compiler和默认V23 Prompt／Context未变。新增内容限独立实验／artifacts及研究索引／日志；所有原始响应和停点保留。

三次逻辑验证完成后已停止。未调用Diagnosis、Editor、Replay/Memory、Gate、Actor或ALFWorld，未生成Candidate、未启动正式六轮、未写Active Memory。
