# V23.2 最终 Update 可执行性：第二次固定材料验证

日期：2026-10-19。**两次验证均已完成，最终 Update 的通用可执行性要求仍未验证通过；按边界停止。**

R03 消除了上一轮“穷尽全部候选后才能回访”的具体要求，但未调整的 u1 仍要求全局未检查位置，u3 又留下累计类别进度条件。R06 仍依赖未检查类别、剩余位置和全部类别检查完成等状态。两组均首次返回 ready，0 次失败、0 次重试；没有语义重采样或后续 Prompt 修订。

## 改动与离线核验

[Prompt Diff](../config/prompt.diff)只替换已有要求，保留前一句 Parent 适用性检查，使用以下原文：

> Before finalizing, check every Update in the resulting Effective Plan, including unchanged ones. Each required decision must be supported by information available to the Actor when that decision is made. Otherwise, revise or withdraw the Update without introducing unsupported restrictions.

没有新章节、ALFWorld 案例、输出字段、关键词黑名单、评分器或审核 Agent。Diagnosis 原文不变。Preconditioner 仍输出原有 Adjustments；“resulting Effective Plan”是要求模型考虑调整后的全部更新，不是新增执行或编译模块。现有 `compile_effective_plan` 在响应后照常确定性编译。

新模板独立存入本实验配置。既有 V23.2 局部调用器仅增加显式 `prompt_path` 参数并将其传递到消息装配与档案核验，见[适配 Diff](../config/adapter.diff)。默认仍用上一版模板，已完成的实验档案不改写；旧档案加载测试通过。没有修改 V23、Editor、Replay、Memory、Gate、Actor 或 Orchestrator。

[离线结果](offline_tests.txt)：**597 passed、19 subtests passed，19.58 秒**。覆盖 V23、V23.2、ALFWorld Adapter 与相关 V22 回归；禁用网络与环境执行。新增两项测试检查精确文本替换、只改变系统 Prompt、原契约及编译／纯数据交接不变、显式模板选择、错误模板拒绝读取和上一轮真实档案仍可加载。没有增加自然语言判定程序。

## 固定材料与判断依据

V23 原始 Plan 和当前证据、Parent、Grouping、Memory、Actor 背景全部保持原样；本次模型 user message 与 V23、上一轮 V23.2 逐字一致。R03 是 10 条优化执行中按原规则选择的 9 条引用执行；R06 是 7 条中选择的 5 条。R06 的原任务身份为优化池 Selection，不是 Test。

模型保持 deepseek-flash、temperature=1、thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300s。R03 输入上限仍为 1,000,000 字符／1,500,000 UTF-8 字节，R06 为 4,000,000／6,000,000。完整配置见[冻结计划](../config/plan.json)。旧侧直接复用保存结果，没有新旧同期重跑；随机性和时间差异限制了因果解释。

Actor 的实际输入包括当前观察、动作候选、当前步数和最近两组**行动前观察／动作**；无完整访问记录或可写持久笔记。当前步数存在于实际 history_template，因此“剩余步数”本身并非不可观察；但它不能推出已访问位置集合。完整候选菜单也不包含全部访问历史。固定顺序如果能从当前状态恢复必要进度，可以可执行，不按策略名称或 `unvisited` 等词机械判错。

下文逐条检查最终 Effective Update，统一参照这一实际协议。完整三版 Original／Adjustment／Effective 文本和请求原文索引见 [OUTPUTS.md](OUTPUTS.md)。

## 真实输出与语义核查

### R03：未调整项仍遗漏，改写项消除了一处依赖却留下另一处

本次返回 ready，仅调整 u3，u1／u2 Keep。不能从 reason 的肯定语句推断它已实际检查并修复了所有保留项。

| 最终 Update | V23／上一轮 V23.2 | 本次实际结果与能力核查 |
|---|---|---|
| u1 | 两侧都保留原句 “continue searching uninspected receptacles” | 本次仍逐字保留。前半段精确类别比较有当前任务／观察依据；后半段未将“未检查”限定到可见记录，也没有给出恢复访问集合的方法，因此 Keep 项的信息依赖仍在。 |
| u2 | V23 和上一轮均调整为显式温度动作已可用时优先执行；上一轮又加了插入／取回备用流程 | 本次保持 Original Update：显式热／冷动作、准确对象和交付目标均保留，没有新增备用流程。观察关闭状态后先开门的信息条件可判断；当动作本已可用时可能多开一次门，是效率／策略问题，不能混同为不可见历史。 |
| u3 | V23 替换仍含未检查／未访问位置；上一轮最后要求 “revisit a location only after exhausting the listed candidate receptacles” | 本次删去全候选穷尽后才准回访的条件，改为根据最近两步排除刚访问的空位置，并以找到目标为继续条件。这一处全局回访门槛确实消除了；但新分支要求 “If the cabinets, fridge, and countertops have been checked without finding the target …”，仍需判断多个类别已检查，且未说明只在这些检查证据仍可见时触发。两组历史和当前步数不能支撑一般的累计类别进度。 |

u3 的开头 “direct each move using the current observation and the two most recent steps” 没有自动使后续全部条件可观察。尤其类别已检查分支仍可能要求窗口外信息；不能只因删掉原句就判定问题已解决。

新增策略及语义问题：

- “because a closed receptacle has not yet been searched” 将当前关闭状态等同于从未检查。协议没有保证容器一经搜索便永久保持打开；实际 R03 的 C34 候选中包含 `close cabinet 2`，已检查容器可以重新关闭。状态可见不代表这条历史推断成立。即使“到达关闭容器后打开”本身可执行，也不能用这个推断保证全局进度。
- 新增从柜子／冰箱／台面转向抽屉／架子的具体顺序，并用厨房场景表达规则。当前证据支持考虑遗漏的候选类型，但不足以把这种类别顺序提升为一般必要限制。这是模型输出中的实例化倾向，不是 Prompt 增加了搜索特例。
- 对 “go to” 返回 “Nothing happens” 改选另一个候选，作为即时反馈分支有实际依据：R03 P5:12 尝试到 stoveburner 3 后得到该反馈，P5:13 改去 stoveburner 2 并到达。若把 “do not repeat that destination” 扩大为永久封禁，则证据不足；文本未明确限制作用时长，不能据单次无移动证明目的地永远不可达。
- 空手时不用 inventory 的触发被写成 “when the last observation shows you are carrying nothing”，有观察依据。当前步数增长也可观察；这两点本身不属于缺少信息。

结论：局部回访条件比上一轮更接近实际窗口，但 u1 的 Keep 遗漏和 u3 的类别进度依赖仍在，并出现“关闭＝从未检查”的错误概括。**R03 未通过完整最终 Update 的可执行性核查。** Checks 未修改；它们是执行后观察问题，不作为 Actor 指令另行判错。


### R06：固定顺序的名称仍未提供可恢复的进度

本次返回 ready，u1 Keep，u2 替换。u1 的持有准确目标、执行显式热／冷动作、完成后交付等要求逐字保留，没有因关注可执行性而被删除。

三版 u2 的区别：

| 版本 | 最终策略中的实际要求 | 可执行性判断 |
|---|---|---|
| V23 | Original Plan 被 Keep；类别内部按编号前进，当前类别穷尽后换到 “genuinely uninspected family” | 类别内从当前可见位置确定下一编号可能可执行，但没有恢复全部类别访问进度的办法。 |
| 上一轮 V23.2 | “at most two consecutive empty receptacles” 后换到未检查类别；其他类别采样完后返回原类别剩余位置；终点为全部位置／类别检查一次 | 增加阈值和交叉回返调度，仍需全局集合及各类别剩余进度。 |
| 本次 | “after a small run in one family yields no target” 后换到 “different uninspected family”；“return to the remaining receptacles of the earlier family only after the other plausible families have been sampled”；终点为所有类别已采样且容器已检查一次 | 将明确的两个位置阈值换成含糊的 “small run”，没有消除全局类别集合和跨类别恢复进度的需求。 |

逐个决策点核查：

- **类别内推进：** 固定升序本身不被否定；若当前位置与候选能识别下一编号，局部前进有依据。但这个局部性质不能证明离开后再返回时，过去在各类别的进度仍可恢复。
- **类别切换：** 当前候选能告诉 Actor 有哪些可选位置，不能告诉它哪些类别在窗口外已检查过。“small run”也没有定义可从当前输入恢复的长度或切换时点。
- **回返及执行进度：** “其他类别均采样后返回原类别剩余位置”需要记住已采样类别及原类别已检查位置。当前步数、两组行动前观察及候选列表没有包含这些累计集合，文本没有给出可恢复它们的固定全序或其他可观察状态。
- **终止：** “all plausible families have been sampled and their containers inspected once”仍需全局检查完成状态；它不是仅凭当前动作候选可判定的终点。
- **预算：** “reserving enough remaining steps”可以使用当前步数，但足够完成后续处理的成本只是策略估计，不能将步数可见当作访问进度也可见。

最终文本还声称 “rely on the fixed family and receptacle order rather than memory to guarantee progress”。本次并未规定一个足以恢复跨类别游标的完整顺序，且仍以已检查／未检查决定动作；“保证进度”超出了实际文字支持的范围。reason 主要解释搜索覆盖和历史 M10，没有证实这些必要状态在每个决策点都可获得。

相比上一轮没有添加更多编号阶段，但仍保留类别采样、延后回返和全局完成条件等复杂调度；“small run”引入新的含糊切换要求。当前证据可以支持尝试扩大搜索范围，不足以证明此方案或限制是必要的。没有实际执行 Candidate，所以不能把这些风险写成已观察到的行为退化。

**R06 未通过最终 Update 可执行性核查。** 没有错误撤下 u1；u2 未真正消除原有的关键进度依赖。

## 哪些依赖被消除，哪些仍存在

- **确实消除：** R03 u3 上一轮明确的“穷尽所有候选才准回访”门槛；立即回避刚看到的空位置有近期可见信息支持；本次未沿用上一轮 u2 新增的插入／取回备用流程。
- **仍存在：** R03 u1 未限定范围的未检查位置要求；R03 u3 对柜子／冰箱／台面已检查的累计判断；R06 未检查类别集合、各类别剩余位置、全局完成判断。
- **新增或保留的语义问题：** R03 “关闭意味着从未搜索”的错误历史推断、具体类别顺序的泛化，以及“禁止重复目的地”的作用时长未明确；R06 用 “small run” 替换阈值但没有定义可恢复进度，并保留无充分依据的进度保证。
- **保留的有效内容：** 两组精确目标类别要求、显式温度动作及目标交付仍在；本次没有全盘撤回搜索或不必要删除原有温度处理要求。保留这些内容不代表其中每一句都经过有效能力修正，R03 u1 的混合情况即为反例。

因此，本次只支持局部文字修正的观察，不能支持“所有最终保留 Updates 均可执行”。没有把 reason 自述、Adjustments 非空或结构通过当作机制成功证据，也不能将结果单独归因为 Memory 收益。

## Token、耗时与停点

[全部请求审计](OUTPUTS.md#请求审计)与[机器记录](../results/attempts.json)保留实际响应。两组均一次请求，无失败、重试、截断、上下文／本地容量超限或合法 no_change／need_evidence 停点。

| 组 | 请求数 | 结果 | 输入 Token | 输出 Token | 总 Token | 尝试耗时 |
|---|---:|---|---:|---:|---:|---:|
| R03 | 1 | ready | 230,371 | 11,832 | 242,203 | 64.08 秒 |
| R06 | 1 | ready | 432,898 | 10,235 | 443,133 | 59.78 秒 |
| 合计 | 2 | 两个合法结构 | 663,269 | 22,067 | **685,336** | 123.87 秒 |

整体实验耗时 **126.53 秒（约 2 分 7 秒）**，含装配与归档；尝试耗时与整体时间分开记录。推理 **20,875 tokens** 已包含于输出；缓存输入 **2,816 tokens** 已包含于输入；未知 usage=0。没有账户账单，不估作实际货币费用。

R03 实际消息 784,756 字符／784,774 字节，R06 为 1,493,606／1,493,620，均沿用原容量。没有压缩证据或 Memory。两次请求后没有其他模型调用。

## 归档、保护与停止

- [三版完整对照](../results/comparison.json)及 [OUTPUTS.md](OUTPUTS.md)保存 Original Plan、三版 reason／Adjustments／最终 Effective Plan 原文，不人工改写。
- [原始产物](../../../../../artifacts/methods/v23_2/v23_2_executability_002/)独立保存完整输入、Prompt、HTTP 请求／响应、解析、验证和正式编译结果。
- [保护核验](../results/protection.json)：V23 方法／Actor 源码、正式训练及 Test 配置和产物、上一轮 V23.2 实验目录及原始产物、原 Diagnosis／Preconditioner 模板共 **10,256 个文件**逐字节核对，无变化、无增删，排除 Python 缓存。V23.2 调用适配器的可选模板参数变更另有精确 Diff，未冒充为完全零代码改动。

本次只研究自然语言更新构造，没有执行 Editor、Candidate Replay、Actor 或 ALFWorld，也未写入 Memory。历史输出对照受模型随机性和调用时间差异限制，不证明稳定改善或行为收益。

**工作按本次边界完成并停止：不针对 R03／R06 追加 Prompt 补丁或调用，不开展历史反例约束更新，不启动正式六轮实验。第一项能力问题仍作为未解决研究结果保留。**
