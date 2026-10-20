# V23.2：历史响应支持范围与 Update 变换对齐

日期：2026-10-19。**三次固定材料验证已完成，均首次返回合法 ready。此次最小修改产生了值得保留的研究信号，但最终支持范围尚未可靠对齐：可保留为待验证研究候选，不建议直接替换默认方法或据此启动正式实验。**

R04 保留了历史 M4 支持的直接持物加热；R05 允许搜索探索，并把类别切换降为启发式；R06 明确识别并修改“先穷尽一类”的差异。但 R06 替代 Update 又将终止范围收窄为“所有类别采样一次”，历史证据没有支持这一要求；R04 还有温度适用范围与仅加热操作不完全一致的表述风险。不能用三次都有 Adjustment 代替语义通过。

## 1. 最小 Prompt 变更及版本边界

基准是正式 V23 `S1/contract.json` 的冻结 Preconditioner 文本，已与原文件逐字核对。原实际句子是：

> Examine whether each Update is appropriate relative to the Parent Skill and executable using information and actions available to the Actor at decision time.

它同时包含 Parent 适当性与可执行性，不能直接用建议的部分句子机械匹配。本次替换为：

> Examine each Update against the Parent Skill and the specific edits, conditions, observed effects, and limitations supported by relevant historical evidence. Examine whether each Update is executable using information and actions available to the Actor at decision time.
>
> Support for an improvement goal does not automatically support a different strategy, scope, or strength; assess the difference using current evidence and historical counterexamples before deciding to keep, adjust, or withdraw.

只在原位置替换历史支持范围要求，保留原来的“决策时可用信息与动作”可执行性语义，其余全文不变。[精确 Diff](../config/prompt.diff)只有一个 hunk，没有新增章节、输出字段、案例或重复粘贴 Memory 使用章节。没有加入此前三次可执行性实验要求，也没有覆盖共享 Actor 能力说明。

新模板位于独立 `config/preconditioner_prompt.md`，显式传给现有 `local_validation.run_stage(..., prompt_path=...)`。**没有修改生产模块代码**；仅增加本实验配置／调用编排和两个小型测试。调用编排复用已有 `material()` 固定材料读取与局部调用器，沿用 V23 输入、契约、编译、技术重试。默认 Diagnosis、Preconditioner、Execution Context 仍指向原 V23；候选配置尚未提升为默认。[冻结核对](../results/baseline_checks.json)

## 2. 固定材料、调用与离线核验

| 轮次 | 当时 Parent | 当时 Active Memory | 本次输入字符／UTF-8 字节 |
|---|---|---|---:|
| R04 | R02 Skill | M1、M2、M3、M4、M5、M6 | 1,218,158 / 1,218,192 |
| R05 | R02 Skill | M1、M2、M3、M6、M7、M8、M9 | 1,613,520 / 1,613,538 |
| R06 | R05 Skill | M1、M2、M6、M7、M9、M10、M11 | 1,493,743 / 1,493,757 |

三轮均使用实际有效 Preconditioner attempt 的 Parent、Diagnosis、Grouping、当前执行事实、证据选择与 Memory sources。R04 已生效的容量恢复配置按原调用时间取用；三组上限均为 4,000,000 字符／6,000,000 字节，没有压缩、截断、删减或增加预算。R05/R06 为正式优化池 Selection 材料，不使用最终 Test。原 V23 侧直接读取已保存真实响应，没有重跑。

模型均为 `deepseek-flash`，temperature=1、Thinking enabled、reasoning_effort=medium、max_tokens=16384、timeout=300、stream=false。最多 3 次逻辑调用，每组最多首次加两次技术重试；实际每组只请求一次，没有触发重试或技术停点。

离线网络禁用，运行 V23.2 局部入口及 V23 Diagnosis／Preconditioner 契约编译相关回归：**165 passed in 2.66s**。[测试输出](offline_tests.txt)。新增测试验证模板精确替换、共享背景和 user 消息不变，以及显式模板的 Keep 档案重读／编译。没有新语义审核器或关键词判断。

调用后逐条核对：完整保存输入与正式归档相等；user 消息逐字相等；system 消息恰为上述一次替换；模型参数相等；原始响应重新解析、既有程序重新编译，与归档 Effective Plan 一致。Memory 未变，Diagnosis 默认消息仍与 V23 一致。[核验结果](../results/verification.json)

## 3. 三组真实对照概览

完整 Original Plan、两版 reason／Adjustments／Checks／Effective Plan 及本次原始响应在 [OUTPUTS.md](OUTPUTS.md)，结构化对照在 [comparison.json](../results/comparison.json)。以下判断均检查最终 `updates[].text`，不只看 reason。

| 轮次／Update | Original 与历史真正支持的内容 | 正式 V23 输出 | 本次最终变化 | 判断 |
|---|---|---|---|---|
| R04 u1 | Original 强调加热一次后直接交付，但加热前具体动作未充分说明。M4 支持已取到精确目标后，显式持物 heat/cool 减少插入／门切换；并非成功所必需 | 调整为明确 heat/cool 操作、精确目标与直接交付 | 调整 u1，保留直接持物 heat、可用就立即执行、按需开门，reason 明确区分步数收益与任务必要性 | 主要正例得到保留；但首句泛指 temperature change，正文只给 heat，存在适用范围歧义 |
| R04 u2 | Original 多实例计数、扩大检索；M3/M6 是混合覆盖反馈，当前 P6/P8/P9 支持计数继续 | 调整 u2，新增源处仍有目标时优先回源及具体表面类型 | Keep Original u2；没有撤回多实例目标 | 不是所有 Keep 都错。没有沿用 V23 的回源细化，但不等于从 Original 删除已有要求；未执行，无法判断行为损失 |
| R05 u1 | 当前 P7 错取洗 knife；M8 支持避免近似类别操作，但不保证任务成功 | Keep | 逐字 Keep | 合理保留，不因历史混合成败删除有效方向 |
| R05 u2 | Original 跨类别 single-pass，不耗尽单类。M6 有 diningtable 救回，也有同类 countertop 3 漏查、晚到 cabinet 9；M3/M6 未验证该新策略一定有效或无效 | Keep，理由认为反例不足以换策略或撤回 | 调整：类别切换为启发式；明确不能因某类已采样就跳过同类未查位置，保留开放表面探索 | 有依据地保留探索，历史限制落实到 scope/strategy；理由把旧反馈概括成 strict family-priority 仍不够准确 |
| R06 u1 | Original 直接持物处理；M7 和当前 P4/P5 支持相同操作条件 | Keep | 逐字 Keep | 没有破坏温度正向经验 |
| R06 u2 | Original 类内升序，穷尽后换类。M10 对应不耗尽一类的跨类别覆盖，且记录持续循环／增步；M6 有已存在目标的漏查反例 | Keep，理由仅说支持方向、不保证治愈 | 实质调整为 family rotation，明确不先穷尽大类；但增加按类采样一次的停止条件、未界定的部分扫描及优先序 | 识别和改变策略差异有进展；替代方案的范围／强度仍越过支持边界，不能判为完整成功 |

全部六项原始更新均有保留或替代，没有撤回整条更新、没有 no_change/need_evidence。观察到允许探索，并非过度保守地过滤新策略；但仍须区分“允许探索”与“为替代策略的所有细节提供了依据”。

## 4. R04：正向经验是否被保留

新 reason 明确：`Memory M4 ... the Parent nevertheless succeeded ... supports step savings and cleaner procedure rather than task necessity`。最终 u1 不只复述收益，而是写入：

> if that action is already admissible, perform it immediately without first inserting the object into the appliance

并保留 exact target、按需开门、加热后直接交付。它对应 M4 的具体编辑与条件，以及当前 P2/P4 的插入／门切换，不是仅由整轮 Candidate 成败推出温度策略正确。正式 V23 也做过类似调整，本次没有因反例或单次证据而机械削弱为“禁止使用该经验”。

局限分开记录：

- 新 u1 首句 `requires a temperature change such as heating`，后面却只要求 `apply the explicit heat action`、`has been heated once`。Original Goal 是 heat-then-place，聚焦加热可以合理；但泛温度触发措辞又可能涵盖冷却，具体动作与范围不完全对齐。正式 V23 的 heat/cool 映射更清楚。此处是文本风险，未实际观察到误加热。
- reason 将 M4 的直接动作概括成在 closed appliance 操作；M4 的 R03/Q9:12 实际先 open、13 才 heat。闭门可直接加热有 R03/Q8 支持，但不是所有示例都如此。最终条款以 admissible 动作作条件，并未强制所有设备必须闭门，因而最终策略比该概括更准确。
- u2 保持 Original，省去了 V23 额外加入的有源处证据时回源细化。当前计数和保留成功行为仍在，无法仅从这一次文本选择证明退化。

**结论：M4 的主要条件性收益及实际操作要求保留；没有整体过度保守，但范围措辞和历史概括尚不完全严谨。** 历史原文及轨迹见[正式证据索引 R03](../../v23_2_memory_analysis_001/reports/SOURCES.md#r03)、[R04](../../v23_2_memory_analysis_001/reports/SOURCES.md#r04)。

## 5. R05：有依据的新探索是否仍被允许

新 reason 把 u2 判为 `directionally correct`，随后真正修改最终文本：

> When repeated checks within one receptacle type are yielding nothing, move to an uninspected type, but do not skip an unvisited listed location merely because its type has already been sampled.

这与 M6 的具体反例有关：R03 Parent P2 到 countertop 3 找到 bread，Candidate Q2 去过 countertop 1/2 却漏 countertop 3。同类还有未查位置，不能以“这个类别检查过”代替完整覆盖。当前 R05/P6 在 drawer 族耗费大量步骤、P8 漏 shelf、P10 晚到 diningtable，则支持继续扩大位置覆盖。新文本保留 single pass、开容器、开放表面和类别切换探索，而非撤回搜索方向；u1 原样保留，精确类别要求未受损。

但 reason 中 `historical M6 and M3 indicate ... strict new-container/family-priority language ... can miss` 的概括过满。M3/M6 测试的是具体开容器／局部反循环／扩大位置范围的联合编辑，不是 R05 此次跨类调度的完整版本；不能把历史遗漏当成“严格类别切换已经被证明造成遗漏”。新原则促使输出关注了实例与类别差异，但仍未完全避免把结果关联写成对某种策略的解释。

新 Update 的 late-step 优先新位置与全部位置一次检查仍来自类似历史／Parent 要求，未新增数值阈值；不因存在未查词汇就判整个更新无效。此前暂缓的累计搜索信息依赖仍在，本次没有解决，也不是本轮判断历史支持范围的唯一标准。

**结论：最终文本显示历史限制影响了策略和范围，未机械禁止新尝试；理由的历史策略归类仍需谨慎，且无法用旧 R05 的 ACCEPT 预言这份新 Effective Plan 的行为。** [M6 原反馈](../../v23_2_memory_analysis_001/reports/SOURCES.md#r03)、[R05 固定当前证据](../../v23_2_memory_analysis_001/reports/SOURCES.md#r05)。

## 6. R06：识别差异有实质改善，替代策略仍超出支持范围

**真正改善的部分。** 正式 V23 的 reason 已说 M6/M10 只支持方向，却 Keep `When the current family is exhausted ... switch`。新 reason 明确指出 `exhaust one receptacle family before switching conflicts with the parent's spread-across-families guidance`。最终 u2 也确实改成：

> Do not exhaust one large family before checking another

这次不是仅在 reason 承认，Original 的关键调度要求发生了改变。M10 来源 Diff 的 `rather than exhausting ... one type`，以及当前 P1:34、P2:8 在 countertop 2 找目标，支持对原策略适用性的重新审视。当前 P3 循环本身不证明类内穷尽更优；新输出没有继续用“覆盖方向有效”直接背书原调度。

**仍未对齐的最终要求。**

| 新最终文本 | 具体问题 | 与已暂缓能力问题的区别 |
|---|---|---|
| `Continue until ... all plausible families have been sampled once` | 从位置覆盖收窄为类别采样终止；采样一类不等于查完同类全部实例。M6 的 countertop 3 漏查恰说明这种区别；新文自己还要求返回大类 later members，终止条件与此有张力 | 即使 Actor 有完整访问日志，采样一次也不保证实例覆盖。这是本次支持范围问题，不依赖先解决记忆能力 |
| `after an ordered pass through part of a family` | reason 称 bounded rotation，但最终没有定义 part 的尺度或可判定边界；“不穷尽一类”的依据没有自动验证这个替代调度 | 属于实现未充分说明；不是因所有固定顺序都无效 |
| `prefer compact open surfaces and then appliances/fridge before returning to later members` | 当前／历史有开放表面发现的支持；整套 surfaces→appliances→later containers 次序没有同等直接验证，应视为待验启发式，不是已有历史结论 | 没有历史验证不等于禁止新策略；需避免把新假设写成历史已支持的完整方案 |
| `rely on this fixed family/index order rather than memory to guarantee progress` | Original 的 guarantee 被保留，M6/M10 的不稳定遵守不支持这种强保证；新 family order 也未完整确定 | 信息依赖仍是已知未解决问题，本次不补丁；同时“保证”超过历史证据强度 |

此外，reason 说 M10 记录 `extra closed-container scanning can add steps`。M10 确有 38→46 的增步事实，但主要描述 Q10 重访空位置；“额外闭容器检查增加步数”的明确例子在 M9 的 candle 对。M10 的完整来源也包含 Parent 在大量 drawers 耗时，但不可把不同现象直接混成同一个被验证机制。M6/M10 都保留联合编辑与单次试验限制，不能从整体成败推出独立调度因果。

**结论：对原策略差异的识别和变换明显比本次读取的 V23 旧输出更到位，但替代 Update 又出现新的范围收窄和过强承诺。核心原则尚未可靠约束变换后的全部要求。** 本次没有执行新策略，不能声称它实际漏查、提前停止或降低成功率。[M10 与实际旧 Diff](../../v23_2_memory_analysis_001/reports/SOURCES.md#r05)、[R06 原始证据](../../v23_2_memory_analysis_001/reports/SOURCES.md#r06)。

## 7. 成本、技术状态与保护

| 实际请求 | 状态 | 输入 tokens | 输出 tokens | 总 tokens | 耗时 |
|---|---|---:|---:|---:|---:|
| R04 attempt 001 | ready，调整 u1、Keep u2 | 356,159 | 9,279 | 365,438 | 50.48 s |
| R05 attempt 001 | ready，调整 u2、Keep u1 | 470,195 | 7,967 | 478,162 | 49.55 s |
| R06 attempt 001 | ready，调整 u2、Keep u1 | 432,919 | 13,185 | 446,104 | 75.09 s |
| 合计 | **3 逻辑／3 HTTP，0 失败、0 重试** | **1,259,273** | **30,431** | **1,289,704** | **175.12 s 请求计时** |

总实验耗时 **178.96 秒**；reasoning tokens=28,075，属于 completion 子集；缓存命中 prompt tokens=5,376，属于输入子集；未知 usage=0。全部 finish_reason=stop，无契约失败、截断、容量停点或人工修补。[每次用量](../results/attempts.json)、[汇总](../results/summary.json)。

修改前冻结的 **11,491 个保护文件**在运行前后及最终重读时 SHA-256 与文件集合全部相同，覆盖 V23 源码／Prompt／正式实验、此前 V23.2 配置／原始产物／分析报告、既有局部调用器与 Actor Adapter。保护包括最终 Test 文件的内容校验，但本次没有读取 Test 轨迹作研究证据。[保护结果](../results/protection.json)。新配置／调用编排与调用前实现快照相等，旧结果不覆盖。

## 8. 候选判断与停止

**建议保留为待验证研究候选，不认定通过完整语义验证，不提升为默认配置。** 支持保留的理由是：R04 的有效历史机制没有被整体过滤；R05 保留探索并利用同类漏查反例改变规则；R06 的原调度差异被明确识别且落实到了最终更新。限制是：新要求仍会在构造替代策略时越过历史支持范围，尤其是类别采样终止条件；这正是本次研究问题的一部分，不能用“产生了 Adjustment”掩盖。

这一结论不是因为要求先彻底解决 Actor 的历史能力问题。即使暂不处理能力，R06 新终止范围和过强保证仍缺乏依据；R04 也有触发范围歧义。当前证据只显示固定材料下的局部文本进展，单次输出有随机性；与保存的 V23 一次结果比较不能提供严格因果证明，更没有 ALFWorld 成功率证据。

三次验证后已停止。未调用 Editor、Candidate、Replay、Actor 或 ALFWorld，未更新 Memory，未启动六轮实验；不根据这些输出继续修改 Prompt 或重采样。V23.2 默认仍使用原 V23 文件，独立候选模板与真实输出作为研究证据保留。
