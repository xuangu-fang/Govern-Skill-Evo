# V23.2：原始与替代 Update 的对称证据约束

**结论：本次有局部改善，尚未同时解决两侧约束。** R06 恢复了对原始类内穷尽策略的质疑，最终 Update 也真实改变；但替代方案把有限的目标位置观察扩展成整套固定搜索排序，仍未清楚标识其假设性质。R04 保留了有效温度操作，R05 允许策略探索，但也产生新的强度要求及历史因果解释偏差。保留本次研究信号和全部产物，**不晋升为下一优先候选或默认配置**。默认仍是正式 V23。

## 1. 调用前核查与问题定位

先完成[只读证据链与设计理由](PRECALL_REVIEW.md)，再写候选 Prompt；核查阶段没有模型调用或 Prompt 修改。M6/M10 sources 中的 Diff 与正式 R03/R05 Editor `actual.diff` 相同；12 条关键历史配对轨迹的动作、反馈和结果与原始归档一致，见[核验凭据](../config/precall_evidence_checks.json)。未使用 R06 之后的 M12/M13。

| 证据环节 | 核查结果与边界 |
|---|---|
| R06 Parent → Original u2 | Parent 已要求 `spreads across distinct receptacle families rather than exhausting or looping over one type`；Original 改为 `When the current family is exhausted ... switch`。这是切换策略变化，不是只把搜索写得有序 |
| M6：R03 实际编辑／响应 | 编辑扩大搜索覆盖并减少循环，同时修改类别和温度指导。Q4 扩展到 diningtable 后成功17步；Q2 漏 countertop3、失败50步；Q6 很晚取得 cabinet9 的 plate、失败50步。支持覆盖与避免遗漏的重要性，不能证明某一类别切换机制导致遗漏 |
| M10：R05 实际编辑／响应 | 实际 Diff 明确反对穷尽单类；Q6 多类搜索到 countertop2 后成功21步，Q8 到 shelf1 后成功23步。但 Q8 先查 cabinet1–4 且回访，Q10 仍循环、46步对 Parent38步。没有统一最优调度或独立因果证明 |
| Memory 本身的歧义 | M10 说救回来自 Parent 未到的 family，但 P6:3 已到 countertop1，漏的是 countertop2。其 `after one family ... yields nothing` 也未明确类内边界；不能只读概括替代实际 Diff/轨迹 |
| construction 实际决定 | basis 为 P3:1/P3:50/P1:34/P2:8/M10/M6；reason 明言 `The substantive strategy is preserved`。只改信息来源和索引定位，仍保留类内穷尽及 `guarantee progress`，未解释历史与当前调度差异 |
| 最有依据的定位 | 历史被读取，但从“覆盖方向有收益”到“当前具体调度应保留”之间缺少支持范围论证。不能据 reason 断言内部推理过程，也不能排除随机性、Memory 歧义与长输入影响 |

具体来源见[原正式输入及历史来源索引](../../v23_2_response_construction_001/reports/SOURCES.md)、本次[固定输入路径清单](../config/plan.json)和调用前核查。当前循环只支持需要改进搜索，不能直接证明类内穷尽更优。历史结果对应整份候选联合编辑，不能归因于单条 Update。

## 2. Prompt 原则比较与冻结设计

| 版本 | A：约束原始策略／Keep | B：约束替代策略 |
|---|---|---|
| 正式 V23 | Parent 适当性及历史比较规则 | 合理调整、保留有效要求；没有显式对称表述 |
| alignment | 明确“改善目标支持不等于具体策略支持”，在 keep/adjust/withdraw 前检查 | 主要依赖原通用规则，没有同等显式的替代要求检查 |
| construction | 保留一般历史对照，但去掉上述显式警示 | `When making an Adjustment`、`each material change` 更突出新增修改的依据 |
| 本次 symmetric | 在 Keep/Adjust 之前比较具体策略、范围、强度、顺序和停止条件 | 将同一标准用于所有 retained/revised 要求，明确反对原案不足以支持替代案；允许问题相关的可检验假设及大幅修订 |

construction 文本的检查重心确有向 Adjustment 偏移的可能，与 R06“保留实质策略”的显式决定相容；这只是有证据的措辞解释，不能声称单句修改导致回退。

新候选只替换原第一节一处要求，三段共130个英文词。其余历史输入说明、第二节 Memory 使用规则、第三节模块职责、Checks 和 JSON 契约逐字不变；不叠加暂缓的 Actor 能力补丁，不新增章节或特定任务案例。核心为原始和替代行为要求采用相同证据标准，而非限制修改幅度。

- [完整新 Prompt](../config/preconditioner_prompt.md)
- [相对正式冻结 V23 的精确 Diff](../config/v23.diff)
- [相对 alignment 的精确 Diff](../config/alignment.diff)
- [相对 construction 的精确 Diff](../config/construction.diff)

候选、三份 Diff、调用前核查及设计理由冻结在 [implementation.json](../config/implementation.json)。计划冻结于 **2026-10-19 15:25:11 UTC**，首次请求始于 **15:25:30 UTC**；调用后冻结内容仍完全一致。未按输出改写候选或补采样。原 Parent 适当性与 Actor 决策时能力约束保留，没有把可执行性重新设为独立研究项。

## 3. 固定材料与实际变换对照

每个版本独立接收当轮正式 Original Plan，不接收前一候选的 Effective Plan。完整 Original、四版 `reason/adjustments/checks` 和 Effective Plan 全文均见 [OUTPUTS.md](OUTPUTS.md)；可读机器对照见 [comparison.json](../results/comparison.json)。正式和前三次局部结果均通过原读取器重新校验、编译；新增 `adjustments[].to[].text` 与编译结果逐字对应，未人工修补。

| 轮次／条目 | 共享 Original | V23 Effective | alignment Effective | construction Effective | 本次 Effective |
|---|---|---|---|---|---|
| R04 u1 | 精确类别、加热后直送 | heat/cool 具体映射、持物处理 | 宽温度触发但仅明确 heat | hot 场景、已有 heat 动作立即用 | 明确 heated 场景；持物 heat、必要时开门、直送；不是对 cool 的新验证 |
| R04 u2 | 多物体计数、继续搜索 | 当前／近期仍见第二件先回源 | Keep | 仍可见第二件优先、否则搜索 | 已观察的已知第二件优先；将 all plausible 扩成 every listed |
| R05 u1 | 精确类别、拒绝近似替代 | Keep | Keep | Keep | Keep，有当前 P7 与 M8 依据 |
| R05 u2 | 跨类单遍覆盖、近期避循环 | Keep | 跨类但勿跳过同类未查实例 | 近期局部选择与跨类偏好 | 新增每类 few（如2–3个）交错批次、后续补查、严格单次访问、全位置一遍边界 |
| R06 u1 | 直接持物 heat/cool、交付 | Keep | Keep | Keep | Keep，有 M7 和当前执行依据 |
| R06 u2 | 类内升序穷尽再换类 | Keep | 不先穷尽大类；采样各类一次终止；保证进度 | 改信息源，但保留穷尽及保证 | 表面→设备→柜子→抽屉；延后大容器；全程单遍；删除显式保证，但仍称 memory-independent |

新原始响应：[R04](../../../../../artifacts/methods/v23_2/v23_2_response_symmetric_001/R04/attempts/001/raw_output.txt)、[R05](../../../../../artifacts/methods/v23_2/v23_2_response_symmetric_001/R05/attempts/001/raw_output.txt)、[R06](../../../../../artifacts/methods/v23_2/v23_2_response_symmetric_001/R06/attempts/001/raw_output.txt)。各自同目录完整保留消息、请求、响应、解析、Effective Plan 和运行元数据。

### R04：有效经验保留，搜索范围仍有附带扩大

u1 引用 M4/M5 与 P1/P2/P3/P4。M4 的 closed-appliance 操作有 cool-pot、hot-apple 支持，heat-egg 仍先开门；本次写 `if ... heat ... available`，并允许 `Open ... only when needed`，没有把“常能直接操作”改成“禁止任何开门”。P1:28 拿 cup 代 mug、P1:31 heat 后又 P1:37 放回 microwave，支持拒绝近似类别与直送。P2:11→13、P3:12→14、P4:19→21支持完成加热后交付。

本次把宽泛 `property such as hot` 明确为 heated；R04 Goal 本就是 heat-then-place，因而可理解为聚焦有当前材料的操作，而不是已证实破坏 cooling。它比正式 V23 利用 M4 的范围窄，不能宣称同样覆盖 heat/cool；Parent 和其他模块未被修改。

u2 的已知第二件优先有 P6:23看到两件candle、27–30回源取得第二件，以及P8:1/7/8/10的newspaper记录支持。但“优先”是从成功回源抽出的策略假设，P8中途仍搜索过别处，不能写成该优先顺序已被对照证明最优。新 Update 将 `all plausible receptacles` 改成 `every listed receptacle`，reason没有独立解释为何合理候选应扩大为全部列举位置；可能增加无关检查。计数和交付要求保留，没有把单件放置视为完成。

### R05：允许新探索，但把历史观察解释成机制证明

u1 Keep 有依据，不因 Memory 含反例而撤回。u2 最终明确提出 `two or three` 的交错批次，补回同类尚未采样实例；这回应 P6 的长drawer序列、P8循环，以及 M6 countertop3遗漏，属于可讨论的新探索，并非必须拒绝。

问题在于依据与强度未充分对应：

- reason称 M6 `shows that a simple 'switch when a family yields nothing' rule can cause premature abandonment`。M6对应的实际R03 Diff没有这条明确切换规则；轨迹只观察到遗漏和循环，不能证明此规则导致遗漏。这是 Preconditioner 将观察扩成机制解释，不能全部归责 Memory。
- reason称 P6 `without sampling cabinets or other families`；实际 P6:3/7/11/15 到过countertop1，P6:8到过sinkbasin1。长时间扫drawer、未到cabinet属实，“其他类完全未采样”不准确。
- `few (for example, two or three)` 是新批次启发式，非历史验证参数；没有明确标识为假设。它有问题动机，不是任意规则，但证据不足以支撑其强制强度。
- `Inspect each listed receptacle at most once`、`do not revisit it` 强于原来的近期避循环；新增“所有 plausible 位置一遍”搜索边界。避免无反馈重复有依据，绝对单次访问的全部适用范围和停止边界没有分别论证。

因此 C 的探索能力保留，不能由此认定 A/B 合格。没有运行新轨迹，以上都是文本及证据判断，不是观察到的行为副作用。

### R06：原取舍有进展，替代排序仍超出支持范围

新 reason 明确指出 `exhaust the current receptacle family ... can spend the step budget`，实际 Update 要求先完成短类再进入长cabinet/drawer，改变了 Original 在任意当前类穷尽后才切换的规则。它不像 construction 仅修改信息源。当前 P1:34在countertop2得到plate、P2:8得到tomato、P4:2在fridge见tomato、P5:1在countertop1见tomato，均是实际记录；P3循环失败也属实。这些使“更早检查表面或fridge”成为有当前问题依据的探索假设。

但 reason 没有完整说明 M10 实际 Diff 的 `rather than exhausting`，主要仍用覆盖收益和当前位置分布支撑决定。不能说已经彻底厘清了历史具体策略；实际输出只是比 construction 更明确地否定了原排序风险。

| 变化的行为要求 | 实际最终文字／变化 | 对应依据 | 核查判断 |
|---|---|---|---|
| 大类进入时机 | `Do not exhaust a long cabinet or drawer sequence before ... earlier short families` | 当前P1长搜后才到countertop2、M10覆盖收益 | 有问题动机，A局部改善；并非证明任何类内穷尽都差 |
| 整套优先级 | `first ... surfaces ... second ... appliances ... third ... cabinets ... fourth ... drawers` | 当前若干目标在surface/fridge | 仅支持可试的优先假设，不能直接支持所有设备都应在所有柜子前、柜子又应在抽屉前；reason未分别说明或明确标识假设 |
| “breadth-first”含义 | 文本实际上按组顺序，组内升序；未要求各组交错 | 新命名／解释 | 不能因名称就认定实现跨类轮换；仍可能在后部大类连续搜索。也不能把未使用轮换本身当错误，关键是顺序的依据不足 |
| 范围 | `closed cabinets`、`closed drawers`；两组表面／设备举例 | 泛化分类 | 已打开但未检查容器的纳入不清楚。`such as`是举例，不能机械判定没列bed/desk就被禁止；但未归类位置缺乏明确排序 |
| 搜索终止 | `If one full pass ends ... continue only with genuinely unvisited locations if any remain` | 反循环动机；原案没有此明确续行限制 | 不再是alignment的“每类采样一次即停止”，完整pass含义更强；但新续行边界和全局穷尽判定仍未单独论证。不能宣称已经发生提前停止 |
| 有效行为 | 精确目标、开容器读取、给conditioning/placement留步数；u1原样保留 | Original及M7、当前温度任务 | 保留必要方向；拒绝近似目标未破坏交付要求 |
| 强度／能力 | 删除 `guarantee progress`，仍称 `memory-independent` 并要求 `unvisited`、`already seen empty`、`one full pass` | 固定顺序本身 | 去掉效果保证是局部改善；跨组顺序及进度仍未说明如何从两步历史恢复。不是关键词判错，也不据此重启第一项优化 |

固定顺序原则上可以帮助恢复进度；问题是此处组内顺序与未访问判定并未充分定义，不能由“固定”推出不依赖历史。保留这项残留局限，不添加能力补丁。

## 4. 分别评价 A、B、C

**A 原始策略取舍：局部改善，未稳定解决。** R06对当前类内穷尽提出明确理由且落实文本，与construction保留原策略不同；R04温度经验、R05精确类别及R06温度Keep均有依据。但R06未充分厘清M10实际编辑，R05更出现把历史遗漏解释成切换规则因果的偏差。不能仅凭发生Adjustment宣布A通过。

**B 替代策略构造：有局部文本改善，未验证整体改善。** R06不再以“各类采样一次”终止，也删除显式进度保证；但新增完整类序、范围歧义和续行限制，没有与其行为作用匹配的独立依据或清楚的假设说明。R05批次强度及绝对不回访、R04扩大至所有listed位置也显示附带要求仍可能失控。

**C 合理探索：保留，未成为保守过滤器。** 三轮均ready；有效温度、精确目标、多物体计数没有被整体撤回，R05/R06允许大幅策略变化。但“允许探索”与“将探索写成有证据的事实”不同，本次对这条界线仍处理不足。

最值得保留的是**A/B对称表达的研究思路及R06原取舍改善信号**。本次固定输出不足以把完整Prompt认定为下一优先候选，更不能晋升默认。单次输出、temperature=1、共同历史材料和Memory歧义使Prompt因果效应无法分离。本次没有Actor行为验证，也没有成功率或泛化收益结论。没有继续修改Prompt、追加调用或自动开展行为实验。

## 5. 离线核验、成本与文件保护

[离线日志](offline_tests.txt)：V23.2局部读取／编排、V23 Diagnosis与Preconditioner相关回归 **171 passed，2.86秒**。离线期间禁止网络；新增两项针对单处替换与原契约Keep往返，未新增自然语言评分器。

三轮实际输入逐项等于正式保存输入；非system消息逐字相同，system只有冻结替换块变化；当轮Memory IDs为R04 M1–M6，R05 M1/M2/M3/M6/M7/M8/M9，R06 M1/M2/M6/M7/M9/M10/M11。模型及全部请求参数与原配置一致：deepseek-flash、temperature=1、Thinking enabled、reasoning_effort=medium、max_tokens=16384、timeout=300秒、stream=false。未改变容量、压缩Memory或截断证据。见[输入与配置核验](../results/verification.json)。

| 轮次 | 结果 | HTTP／技术重试 | Prompt tokens | Completion tokens | 其中reasoning | 总tokens | 实际调用秒数 |
|---|---|---|---:|---:|---:|---:|---:|
| R04 | ready，有效 | 1／0 | 356,232 | 8,149 | 7,018 | 364,381 | 46.464 |
| R05 | ready，有效 | 1／0 | 470,268 | 13,043 | 12,165 | 483,311 | 65.790 |
| R06 | ready，有效 | 1／0 | 432,992 | 7,402 | 6,644 | 440,394 | 45.000 |
| 合计 | 3次逻辑调用 | 3／0 | 1,259,492 | 28,594 | 25,827 | **1,288,086** | **158.254** |

编排总耗时 **161.158秒**（含本地读取、编译和保存）；reasoning包含于completion，不重复相加。无失败、无未知usage、无合法停止或容量停点。详细时间与真实usage见[attempts.json](../results/attempts.json)和[summary.json](../results/summary.json)。

**11,891个保护文件的SHA-256及文件集合一致**，见[protection.json](../results/protection.json)：正式V23源码、Campaign、最终Skill、Memory、Test，以及此前全部V23.2实验／原始产物保持原样。读取历史用对应冻结Prompt，默认仍指向V23。新编排仅复用既有入口并冻结本次设计材料；分析脚本只重读、校验和生成报告。没有修改Diagnosis、Editor、Replay/Memory、Gate、Actor、Orchestrator或Compiler。

本次新增独立实验目录、对应artifacts、两项离线测试；仅更新研究索引和实验日志。三组完成后已停止，未运行Editor、Candidate、Replay、ALFWorld或正式六轮，未写Active Memory、未使用最终Test轨迹。
