# Evidence-Grounded Update Transformation：固定材料结果

日期：2026-10-19。**三组调用已完成并停止；本次未得到比 response_alignment_001 更稳定的整体改善，不建议将本版提升为下一优先候选或替换默认方法。**

R04 保留并具体化加热、精确目标与多物体行为；R05 允许明显的策略调整，但新启发式的依据与预期尚未充分区分；关键 R06 保留了类内穷尽，未延续上一轮对历史策略差异的识别。它没有再新增“类别采样一次终止”，却仍将高层覆盖收益用于支持原具体调度，并保留“保证进度”。因此 A 原始更新取舍与 B 替代构造必须分开：此次没有可靠解决任何一项，也不能因某个坏条件未再出现就认定 B 成功。

## 1. Prompt、版本和核验

以正式 `S1/contract.json` 冻结 V23 文本为基准，与上一轮模板逐字核对。只将第一节原有两段相关表述统一替换为用户建议的四段（按完整句排版）：

> Assess each Update against the Parent Skill, current execution evidence, and the specific historical edits, conditions, observed effects, and limitations.
>
> When making an Adjustment, examine the behavioral requirements it adds, removes, or changes—including strategy, scope, strength, sequence, and stopping conditions.
>
> Ground each material change in relevant evidence or an explicit, testable hypothesis tied to the current problem; evidence against the original does not by itself support a replacement.
>
> Preserve otherwise valid requirements, but allow substantial revisions and novel strategies when justified. Distinguish observed outcomes from untested expectations, and check executability using information and actions available to the Actor at decision time.

[完整 Prompt](../config/preconditioner_prompt.md) · [相对冻结 V23 Diff](../config/v23.diff) · [相对 alignment Diff](../config/alignment.diff)。两个 Diff 均只有一个 hunk。未追加章节，第二节 Memory 使用、第三节调整职责、Checks 和 JSON 契约均原样保留；原有“决策时可用信息与动作”要求融入末句，未叠加此前已暂缓的第一项实验规则。

[run.py](../run.py) 只为已有三轮局部验证编排提供独立路径配置，未复制执行框架、修改源模块或改变默认模板。实际调用仍使用 `local_validation.run_stage`，解析、验证与 Effective Plan 编译仍由原程序负责。[analyze.py](../analyze.py) 仅重读归档并导出对照，不进行自然语言评分或模型调用。

网络禁用的相关离线回归 **169 passed in 2.58s**。新增两项测试确认单一规则替换、其余 system/user 装配不变、默认仍为 V23、Keep 契约和历史读取／编译一致。[测试输出](offline_tests.txt)

## 2. 固定材料与三版本全量对照

| 轮次 | Parent | 实际 Active Memory | 本次输入字符／UTF-8 字节 |
|---|---|---|---:|
| R04 | R02 Skill | M1–M6 | 1,218,432 / 1,218,468 |
| R05 | R02 Skill | M1、M2、M3、M6、M7、M8、M9 | 1,613,794 / 1,613,814 |
| R06 | R05 Skill | M1、M2、M6、M7、M9、M10、M11 | 1,494,017 / 1,494,033 |

每组均从正式调用的实际有效 attempt 取得 Parent、Original Plan、Grouping、完整的原证据选择和当轮 Memory；恢复配置按该轮调用时间取用。本次没有把 alignment 输出或后续 R06 Candidate 行为结果送给模型。三版本都是对**同一正式 Original Plan**独立预条件化，不是继续修改上一版 Effective Plan。

模型 deepseek-flash，temperature=1、Thinking enabled、reasoning_effort=medium、max_tokens=16384、timeout=300、stream=false。容量仍为 4,000,000 字符／6,000,000 字节，没有压缩输入或调预算。所有实际请求（含失败）的消息、参数和原材料均核对相等，唯一方法变量是上述 system Prompt 段落。

完整三版本 `Original Plan → reason/Adjustments → Effective Plan`，包括 Effective Update **全文**及本次全部原始输出，见 [OUTPUTS.md](OUTPUTS.md)；机器可读对照见 [comparison.json](../results/comparison.json)。重要 Memory 原文、历史真实 Diff、当前关键动作及原始档案链接见 [SOURCES.md](SOURCES.md)。合法响应均经原解析器和编译器重读，不以模型 reason 自述作为核验。

| 项目 | 正式 V23 | alignment_001 | 本次 construction_001 |
|---|---|---|---|
| R04 u1 | 调整为显式 heat/cool 与直接交付 | 调整；泛温度触发但只写 heat | 调整；明确只对 hot，保留显式持物 heat 与交付 |
| R04 u2 | 调整，增加有剩余目标的回源优先 | Keep 原计数／覆盖要求 | 调整，恢复有当前证据支持的回源优先，保留计数和位置覆盖 |
| R05 u1 | Keep | Keep | Keep |
| R05 u2 | Keep 跨类别 single-pass | 调整为类别切换启发式，并防止漏掉同类实例 | 调整为近期观察驱动的覆盖策略；不撤回搜索，取消全局 single-pass 门槛 |
| R06 u1 | Keep | Keep | Keep |
| R06 u2 | Keep 类内穷尽后换类 | 改为不先穷尽大类，但新增类别采样终止 | 保留类内穷尽；主要改读取动作列表和近期索引，仍保证进度；无类别采样终止 |

## 3. R04：已有有效策略与多物体要求

### u1 的实质变化

最终文本改为 `requires ... to be hot before placement`，并写入：

> When the exact target is held at the microwave and the explicit heat action ... is already admissible, perform it immediately.

| 变化的行为要求 | 实际变化 | 对应依据 | 判断 |
|---|---|---|---|
| 处理前插入／门切换 | 新增立即持物 heat，禁止用插入、开关门、examine 替代加热 | M4 的热 apple/egg 历史动作；当前 P2:7→11、P3:8→12、P4:8→19 的多余处理 | 依据直接相关，不仅是整轮成败关联 |
| 精确类别及处理后交付 | 保留，并举 cup/mug 近似类别排除；补入不得 clean 近似物体 | P1 错取 cup，M5 的精确类别经验；P2/P3 的实际交付 | 核心合理；clean 的扩展继承广义精确类别原则，不是新的温度停机限制 |
| 温度适用范围 | 从 `property such as hot` 明确收窄为 hot；不含 V23 的 cool 分支 | 本轮 Goal/当前 P1–P4 是热处理；M4 同时有 cool 的有效证据 | 比上一版泛温度触发却强制 heat 更一致，但未解释为何不迁移 M4 的 cool 收益；不能宣称完整保留 heat/cool 广义收益，也不能把未新增 cool 写成从 Parent 删除已存在的 cool 条款 |
| 动作不可用时如何开门 | 只规定 heat 已 admissible 时立即执行，没有补充否则路径 | 直接收益来自已有动作可用条件 | 没有新增不当开门限制；属于覆盖不完整，不能把条件性规则看作完整温度流程 |

Original Goal 本身侧重 heat-then-place，故“仅 hot”不是自动判错。本次没有生成 Candidate，也未证明该收窄产生行为退化。reason 正确引用 M4 的操作收益，却未像上一版那样明确重述“不是成功必要条件”的限制；不能据此将观察到的节省当作独立因果。

### u2 的实质变化

最终新增：

> if an already-observed receptacle still visibly contains another unplaced exact instance, return there ... before searching unrelated locations.

当前 P6:23 看见两支 candle，P6:24–30 分次交付并回同一来源；P8:1 看见两份 newspaper，P8:7–10 回源取第二份后成功，支持这项优先级。P8 在两次取物之间也曾绕去 sidetable/drawer，不能把整个历史路径概括成每次都立刻回源；“先回源再无关探索”是有明确行为动机的改进要求。

原计数、继续获取精确实例、开放表面／闭容器覆盖均保留。终止仍是达到数量或检查完所有合理位置，没有改成类别采样即结束。高步数优先新位置来自 M6 原编辑及 P5/P7 循环证据，非凭空数值阈值。`already-observed ... still visibly` 和全局未查集合仍有信息可用性歧义，这是暂缓的一项已知限制，本次不将它偷偷修复或当成全部结论。

**A：本轮利用合理，但正式 V23 已有类似正确调整，不能证明新增 Prompt 带来独有进步。B：新增回源优先和加热要求有对应依据；hot 范围解释仍不充分。**

## 4. R05：探索被允许，但新启发式未充分标明假设

合法输出为第二次技术尝试。u1 逐字 Keep，u2 改写幅度明显，未因为 M6 的负例撤回整个搜索方向。

| 变化的行为要求 | 实际变化 | 对应依据 | 判断 |
|---|---|---|---|
| 全局 single-pass／回访门槛 | 改为当前及最近两组观察驱动，允许观察窗口以外的位置被再次选择 | 原 Actor 输入边界；当前 P6/P8 循环；M6 指出原反循环指导不稳定 | 问题相关，但局部窗口策略的效果尚未被这些历史结果验证 |
| 选择下一位置 | 新增 `whose name has not appeared in the recent observations` | 使用近期信息避免立即重复的可操作设想 | 可检验的新启发式；名称不在近期观察不等于以前未检查，也可能只代表文本未提及。reason 把替代方案称为“makes it executable”，未清楚标为未验证预期 |
| 类别与实例覆盖 | 近期均属同类时优先换类，同时允许当前／近期可见的同类不同实例；不以一个空成员代表全类 | M6 countertop 3 漏查，当前 P6 长扫 drawers、P8 长循环 | 直接回应了反例，保留探索和同类实例覆盖；不能把 M6 写成“已测试本次两步窗口规则” |
| 添加位置例子 | bathtubbasin、toilet | 当前 P8 初始房间确实列出这些 fixtures | 有实际输入来源，不是无关场景规则；未强制固定访问顺序 |
| 搜索终止与完成 | 未新增类别采样停止或固定步数阈值；u1 仍要求精确搜索，Parent 处理／放置保持 | 现有任务目标和有效行为 | 未看到机械撤回或过早停止要求；没有具体化取物后预算预留并不等于禁止完成 |

原 P6:18–50 连续推进 drawers，但柜子和多处表面未查；P8 多次回 cabinets/sinkbasin，P8:50 才到 sinkbasin 2。这些支持避免把时间耗在少数区域，**没有直接证明“名称未出现在近期观察”这一选择规则会获得更好覆盖**。Checks 可用于将来观察，但本次并没有执行它们，不能把 Checks 当作结果。

末句仍写 `prioritize any ... unvisited listed surface`，与前面的近期窗口准则并不完全一致。该问题提示替代文本没有彻底统一其信息依据；本次并未恢复第一项能力优化，而是记录原能力背景促成的模型改写及其限度。

**A：历史同类遗漏限制确实影响了最终文本，合理探索未被禁止。B：方向与问题关联清楚，但新局部启发式没有充分区分假设与已验证能力／结果；不宜判为完整通过。**

## 5. R06：原取舍退回，替代构造未得到完整约束

### A. 历史支持范围仍未与具体调度对齐

正式 V23 Keep 原 `When the current family is exhausted ... switch`；alignment 明确改为 `Do not exhaust one large family before checking another`。本次最终又保留：

> When the current family is exhausted without the target, switch to a genuinely uninspected family ...

reason 将 M10/M6 概括为 `a family-switching single-pass sweep can rescue a target located in an uninspected family`，并明确说 `The substantive strategy is preserved`。没有解释为什么 M10 来源 Diff 中的 `rather than exhausting ... one type` 能支持当前的“穷尽后再切换”，也没有给出当前证据足以推翻此前调度的理由。

当前 P1:34、P2:8 在 countertop 2 找到目标，支持及时覆盖这些位置；P3 的循环支持改变重复访问，但不直接证明先耗尽某类更好。M10 的历史总结本身把 countertop 2 描述为 Parent 从未到过的“新类别”，但 Parent 曾到 countertop 1；来源只支持此前未检查的位置，不能总扩大成新类别。完整真实 Diff 和对应动作均在输入 sources 中。本次未识别这些支持范围区别，仍把高层覆盖收益用于为具体调度背书。

因此不能以“u2 有 Adjustment”认定 A 改善。本次调整集中于信息来源与局部索引，原先需要辨别的策略差异没有解决；相对 alignment 反而退回。

### B. 各项实质变化的依据

| 变化的行为要求 | 本次实际变化 | 对应依据 | 判断 |
|---|---|---|---|
| 位置来源 | 从初始 room description 改为当前 admissible actions | 实际动作候选持续提供可去位置，原背景明确其可用 | 使用当前候选合理；关于初始房间在第一步后立即消失的理由不准确，见下文 |
| 类内推进实现 | 新增用最近观察／动作识别最后访问索引 | 近期观察可显示当前位置／最近动作 | 合理的局部实现假设；不能据此证明跨类别进度可恢复，reason 未将其明确标成待验证假设 |
| 调度顺序 | 保留类内升序、穷尽再切换；相对 alignment 不再产生部分扫描／表面→设备优先序 | 原 Diagnosis；M10/M6 高层覆盖反馈 | 原 Plan 不是独立效果证据；当前输出没有提供与“先穷尽”相匹配的支持或比较 |
| 执行强度 | 显化 single-pass，保留绝对不回空位置与 `guarantee progress`，并加动作列表为保证依据 | 近期历史、当前候选只能支持局部决策；M6/M10 仍记录循环／增步 | 保证强度不受证据支持。动作候选不编码过去访问和类别完成状态，新增信息来源没有证明全局保证 |
| 终止条件 | 本次没有产生 alignment 的类别采样一次终止；保留预留处理／交付步数 | 原 Original Plan 与任务目标 | 避免了上轮附带收窄，但不能称“有依据地撤销旧停止条件”：本次从同一 Original 独立开始，未编辑上一轮 Plan |
| 有效要求 | u1 Keep，精确目标、开容器读取、预算及后续处理交付保留 | 当前 P4/P5 与历史 M7 的相关操作反馈 | 没有整体撤回更新或破坏温度方向；这些保留不补足 u2 的调度依据 |

**关于 Actor 背景的事实核查。** 本次 reason 写 `history template omits the initial room description after the first step`，最终 Update 写 `initial room description is available only at the start`。实际渲染保留两组行动前观察：正式 R06/P3 的第 1、2、3 步请求均包含初始房间说明，第 4 步起才不再包含。故“后续长期不能依赖初始说明”的方向合理，“第一步后即无”的描述错误。当前候选也不等于访问日志；这一点不要求重新开启能力优化，只用于判断本次变换所援引事实是否准确。

**B：没有再新增上轮的停止范围，但没有证据表明模型学会约束替代构造。** 新信息源有合理局部依据，局部索引是假设，原保证仍被过度肯定；更重要的是原调度差异没有进入实际取舍。少改或没有某个坏句子本身不构成通过标准。

## 6. 技术失败、成本、保护与证据局限

| 请求 | 状态 | 输入 tokens | 输出 tokens | 总 tokens | 耗时 |
|---|---|---:|---:|---:|---:|
| R04/001 | 合法 ready | 356,207 | 12,103 | 368,310 | 66.50 s |
| R05/001 | 引用契约错误 | 470,243 | 7,157 | 477,400 | 45.62 s |
| R05/002 | 合法 ready | 470,243 | 9,909 | 480,152 | 54.54 s |
| R06/001 | 合法 ready | 432,967 | 13,469 | 446,436 | 71.04 s |
| 合计 | **3 逻辑、4 HTTP、1 技术重试** | **1,729,660** | **42,638** | **1,772,298** | **237.70 s 请求计时** |

总实验耗时 **243.89 秒**，reasoning=39,288（输出子集），缓存输入=475,520（输入子集），未知 usage=0。没有截断或技术重试耗尽，最终三组都有合法 Effective Plan。

R05/001 的 `P6/P8` 被既有校验器识别为不存在的历史命名空间引用，触发 `reason: unavailable historical reference`；这是引用契约／解析规则下的技术拒绝，不能宣称模型捏造了历史实验。首次文本还包含“两次同类空检查后换类”的硬上限，但没有合法编译 Plan，**不把它当作本次有效结果**。原文本完整保留，没有手工改为 “P6 and P8”，也未改校验器；重试沿用相同完整输入与 Prompt，非根据语义选优。契约错误及结果随机性会限制新旧输出比较的解释力。[原始尝试与用量](../results/attempts.json) · [错误说明](../results/technical_failure_note.json)

修改前冻结的 **11,805 个保护文件**在前后及最终重读时集合与 SHA-256 全部一致，覆盖 V23 源码、正式训练／Test、旧 V23.2 Prompt／固定材料实验／行为验证及 Memory。默认 Diagnosis、Preconditioner、Execution Context 均仍为正式 V23。没有读取最终 Test 轨迹作语义判断；保护校验只读取其字节计算哈希。[保护结果](../results/protection.json)

[所有实际请求核验](../results/all_attempt_checks.json) · [合法输出重读／编译核验](../results/verification.json) · [汇总](../results/summary.json)。每条重要判断来自实际最终 Update、当轮 Memory、来源 Diff 或当前动作，模型 reason 只作为待核查的解释。未执行新 Skill，不能将本次文本变化写成任务成功率、步数或泛化收益。

## 7. 分别回答 A、B、C 与候选决定

**A. 历史响应是否更准确地影响原始更新的取舍？** 未见一致改善。R04 有据调整、R05 同类遗漏进入实际规则；R06 未解释关键策略差异，仍保留类内穷尽，逊于 alignment 的一次输出。不能据此推断 Prompt 必然导致退步，但本次不能支持“取舍更准确”的整体结论。

**B. 历史响应与当前证据是否更有效约束替代构造？** 尚未验证。R04 回源／直接 heat 有具体依据；R05 的近期名称启发式、R06 的局部索引等新设想与问题有关，却没有充分说明它们是可检验假设，仍把局部可见信息写成整体可执行或保证。R06 未再产生类别采样停止是一个局部差别，不能抵消 A 未处理及强度依据不足。

**C. 是否过度保守或出现无依据大改／新限制？** 没有机械过滤新策略，u1 多处 Keep、R05 u2 明显改写均被允许，也没有强制减少修改数量。未见整项搜索撤回；但 R05 的近期名称选择限制缺少清楚的假设标记，R04 hot 范围收窄未单独解释，R06 的事实误读与保证仍在。问题不是“大改本身”，而是具体改动、解释与证据未稳定对齐。

**决定：保留本次完整研究证据，不将本版晋升为第二项的下一优先候选，不覆盖上一轮候选或默认方法。** 明确逐项依据的原则仍值得研究，但本次单次三组输出未显示全面优于已有候选；这不是严格因果或显著性结论。

三组验证后停止。未调用 Editor、Candidate、Replay、Actor、ALFWorld 或 Gate，未写 Memory、未启动正式六轮实验，未根据输出补丁或追加语义重采样。后续动作等待用户决定。
