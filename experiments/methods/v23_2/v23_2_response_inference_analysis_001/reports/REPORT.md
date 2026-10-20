# 历史行为响应到策略规定：离线推导核查

日期：2026-10-20（Asia/Shanghai）。**确认存在跨版本重复的证据边界跨越，但不能概括成“所有搜索新策略都错误”或已证明的模型内部推理机制。** 最清楚的现象是：覆盖遗漏或重复搜索能够说明需要改善什么，却被继续用来支持特定的换类前置条件、批次强度、完整优先序或类别采样终止。主要共性出现在“可支持的认识→具体策略规定”，部分案例在“观察→原因解释”就已扩大了结论。R04则提供了有条件、具体操作得到较好支持的正面案例。

本次只有离线读取和报告。没有模型调用、Prompt设计或修改、自进化模块运行、Candidate生成、Memory改写或Test轨迹分析。

## 1. 材料与判断方法

逐项覆盖R04/R05/R06各自u1/u2的Original与五版有效Effective，包括Keep；15组有效输出、30项最终Update的覆盖清单见[证据索引](EVIDENCE_INDEX.md)。五版为正式V23、alignment、construction、symmetric、calibration。所有版本的完整输入与当轮正式输入相等，选用`result.json`指向的合法attempt，核对原始响应／parsed／保存输出及既有全文对照一致。**没有重新运行编译或其他自进化模块。** 无效技术尝试不当作有效Plan。

当轮Memory分别为R04 M1–M6；R05 M1/M2/M3/M6/M7/M8/M9；R06 M1/M2/M6/M7/M9/M10/M11。与各轮`round_input.json`逐字核对；R06的M12/M13未使用。18条关键历史配对轨迹的实际动作、行动后观察、反馈与当时可见sources逐步核对相等，R03/R05实际Diff与对应Memory source相等。R03关键sources在相关旧快照中的一致性另行核验，避免借较晚快照替换早期认识。见[档案核验](../results/archive_checks.json)、[轨迹核验](../results/trajectory_checks.json)、[快照与当前动作候选核验](../results/snapshot_checks.json)。

以下区分四种内容：历史观察、证据支持的认识、新策略假设、理由不足的具体规定。它们可以共存于同一Update，不是自动评分。判断的是**当前材料是否支持这一步推导**，不是某策略永远不合理。明确指令可以承载未验证假设；不能仅因使用“must/never”或没有写“hypothesis”就判错，需要看问题动机、作用范围和附带要求是否得到解释。

## 2. 核心对照表

各行原文、basis、reason、Checks及Effective链接均在相应轮次的[索引](EVIDENCE_INDEX.md)；来源轮次与当前轮次的P/Q编号不能混用。

| 轮次／版本 | 历史观察 | 能够支持的认识 | 实际策略规定 | 是否存在推导跳跃 |
|---|---|---|---|---|
| R04 u1／五版 | M4：已持精确目标时直接heat/cool，省去插入／门切换；Parent也成功 | 相应可用动作和条件下，可避免这些操作，不是保证任务成功 | V23明确heat/cool；其余以heat为主，动作可用时持物执行、之后交付 | 主体依据较充分；alignment宽温度触发只写heat有范围歧义；hot限定与当轮Goal一致，不自动算错误收窄 |
| R04 u2／V23、construction、symmetric | 当前P6/P8回源取得第二件并完成 | 可见已知剩余实例值得优先取，不等于每次回访无效 | 优先回源；symmetric从plausible扩大为every listed | 回源是有具体对象依据的合理优先假设；every listed扩大缺少独立理由 |
| R04 u2／alignment、calibration | 多物体未完成伴随重复搜索；M6扩大覆盖有混合结果 | 保留计数与继续搜索，改善局部重复 | alignment Keep；calibration近期避循环，终止措辞用considered once | Keep并非否认历史；calibration把“更可执行”说得过满，considered相对inspected有歧义，不证明实际提前停止 |
| R05 u1、R06 u1／五版 | M8近似类别操作不能满足精确目标；M7有条件的温度操作收益 | 保留精确类别及持物温度处理 | 各版均Keep | 有据Keep，不因有其他历史负例而撤回有效要求 |
| R05 u2／V23 | M6收益混合，当前P6/P8重复、P10晚发现 | 值得扩大覆盖，历史不足以否定本次跨类探索 | Keep Original跨类single-pass | 作为新探索可合理；可执行／效果肯定不能由方向支持自动推出，不据Keep本身判错 |
| R05 u2／alignment | M6漏countertop3，同时有diningtable救回 | 访问一类不等于覆盖该类所有实例 | 换类为启发式，不能因某类已采样就跳过同类未查位置 | 最终限制对应反例较好；reason将旧反馈归为strict family-priority，历史策略解释过满 |
| R05 u2／construction | 同上及近期循环 | 可试近期信息驱动选择，兼顾同类其他实例 | 近期未出现的名称、近期同类失败后偏好换类、保留例外 | 合理新启发式；近期未出现不等于从未访问，称整体“executable”缺充分依据 |
| R05 u2／symmetric | 同类遗漏与大类耗时 | 可试交错批次并补查同类剩余实例 | `few (for example, two or three)`上限、`at most once` | reason先把遗漏解释为换类规则导致；批次设计有动机，但该尺度／强度未分别论证 |
| R05 u2／calibration | M6遗漏同类实例 | 不能用单个空实例证明全类穷尽 | `Once a family has been checked, move...`；Checks明确换类前查完 | 从穷尽判断转成调度前置条件；最终Update有歧义，不能把Checks直接冒充Actor禁令 |
| R06 u2／V23、construction | M10到遗漏位置后救回，也有循环／增步 | 支持改善覆盖，不直接比较穷尽与轮换优劣 | V23 Keep Original类内穷尽／保证；construction改信息源仍保留 | 主要是未校准原案，不是两版重新发明了穷尽；方向支持没有补足具体策略及保证 |
| R06 u2／alignment | 同上，当前目标曾在countertop2找到 | 可试避免大类占满预算 | 部分扫描换类、表面后设备偏好、每类采样一次终止、保留保证 | 探索动机合理；类别采样替代位置覆盖是明确范围跳跃，保证也超出证据 |
| R06 u2／symmetric | 当前多个目标在表面／fridge，历史大类搜索耗时 | 可试提早查看这些位置 | 固定表面→设备→柜子→抽屉 | 局部优先假设被扩成整个排序；没有说明为何所有设备优先于所有柜子、柜子先于抽屉 |
| R06 u2／calibration | M10覆盖收益、M9额外容器检查增步 | 可试按预算分配各类搜索 | budget-bounded sample、固定未定义顺序、全位置检查一次 | 新假设有动机；采样尺度、次序边界未充分构造，称更可执行仍是预期。未出现旧的类别采样终止错误 |

## 3. 六个重点案例

### 案例一：R04温度处理——为什么具体要求有较强依据

**实际证据。** R03实际Diff加入“已取精确目标→对应设备→显式动作可用则持物执行→按需开门→交付”。M4的三对轨迹：cool-pot P18步/Q11步，Q9直接cool；hot-apple P35/Q9，Q7直接heat；heat-egg P40/Q15，Q12先open、Q13 heat。最后一例说明不能把“能在闭门状态操作”概括成“全部示例都闭门执行”。当轮R04的P2:6、P3:7、P4:5也在closed microwave处提供相应heat候选，Actor却先开门／插入。行动前候选是独立于事后成败的可执行依据。

**模型认识与策略。** V23写动作已经admissible就持物执行，未可用时只按需开门；alignment也区分了步数节省与任务成功必要性。construction、symmetric、calibration均保留条件式直接heat和直送。

**推导判断。** 正向行为本身就是候选操作，条件、动作及局部反馈在历史和当前材料中可以对应，不需要先从“浪费步骤”猜出一整套未知调度。可明确要求避免把插入／examine当成温度动作，但不能把总步数差全部归因于该单条规则；历史同时改了搜索／类别指导，且只有一次执行。

**边界。** 证据不覆盖任何设备、任何对象状态或目标未找到时的成功保证。alignment用宽温度触发却仅写heat，存在范围映射风险；后几版聚焦hot与本轮heat-then-place Goal相容，不能因没扩展cool就判定拒绝有效经验。[R04档案](EVIDENCE_INDEX.md#r04)与[原配对轨迹](EVIDENCE_INDEX.md#历史配对轨迹本次原文件核验)。

### 案例二：多物体回源与合理Keep——反例不能变成所有回访都错

**实际证据。** R04 P6:23看到两支candle，放第一件后27回源、28取第二件、30交付；P8:1看见两份newspaper，7回源、8取第二份、10交付。P8中间还探索过别处，故不能写成历史已对照证明“立即回源”最优。

**模型规定。** V23和construction要求当前／近期仍可见剩余实例时先回源，这与“已看空位置的无反馈重复”有明确条件区别。symmetric也保留回源，但把未知位置搜索扩为`every listed receptacle`，从Original的`all plausible`去掉合理性限定；该扩大没有单独证据。alignment Keep原计数／覆盖条款，未补回源优先；这不是删除Original已有要求。calibration保留局部避循环，却把`inspected once`改成`considered once`，至少使实地检查标准变模糊。

**推导判断。** 选择已知剩余目标是有当前状态依据的合理策略假设，不必先有专门随机试验。把“出现重复失败”推成一律禁止回访则会混淆有收益的回源与无反馈循环；本组较好的输出能保持这种区别。R05 u1的精确类别、R06 u1的温度Keep也有对应当前事件和M8/M7支持，不能把所有Keep记为历史利用失败。M8部分文字称目标absent，轨迹未找到不能单独证明环境中不存在；精确类别要求的合理性不依赖这个过强结论。上述范围／措辞风险未执行验证，不等于已造成任务退化。

### 案例三：M6遗漏countertop3——哪里是合理启发式，哪里是原因臆断

**实际证据。** M6对应R03搜索Diff写当前／近期避循环、开容器、扩展到其他位置及高步数优先新位置，同时还有类别／温度编辑。P2:15到countertop3、16拿bread，20完成；Q2反复到countertop2，未到countertop3，50步失败。另Q4到diningtable找到bread、17步成功，P4失败50；Q6很晚取得cabinet9的plate。可确认遗漏、覆盖收益与循环共存。

**能够支持的认识。** 查过一个countertop不能说明其他countertop也查过；跨一些类别也不保证位置覆盖。不能据此确定遗漏由“切换类别”造成：实际R03 Diff没有本轮那条完整换类触发，联合编辑也未隔离该机制。

**不同规定。** alignment最终写 `do not skip an unvisited listed location merely because its type has already been sampled`，直接守住实例／类别区别；建设性的换类启发式仍可探索。但reason称strict new-container/family-priority可能miss，是比实际编辑更强的历史策略归类。construction用近期名称未出现作为选择启发式、同类近期无目标则优先换类，并保留同类可见未查实例例外：有问题动机，不必判为错误；但不能由近期未出现推出全局未访问，也不能据M6宣布整体执行性已获证明。

正式V23的Keep解释为M6/M3没有提供足够理由换成别的策略或撤回，当前P6/P8/P10仍支持探索。这没有直接否定历史反例或宣称历史已证明新策略最优；其对能力的笼统肯定另有不足。**没有证据表明必须Adjustment才算合理。** [R05五版原文及basis](EVIDENCE_INDEX.md#r05)。

### 案例四：同一遗漏反例生成相反强制安排——symmetric与calibration

**观察→解释跳跃。** symmetric reason称 M6 `shows that a simple 'switch when a family yields nothing' rule can cause premature abandonment`。这是把观察到的遗漏，升级为特定换类规则的因果效果；M6实际Diff及配对轨迹不支持该归因。该版还说当前P6未采样other families，但P6:3已到countertop1、8到sinkbasin1；晚段长扫drawer属实，整个过程从未跨类不属实。

**解释→规定跳跃。** symmetric最终要求同类连续最多`a few (for example, two or three)`，随后换类，再回来补查；交错与补查是合理问题假设，**原文不是严格固定两个**。但为什么用这个批次尺度、为何强制`at most once`，没有与其强度相配的解释。原single-pass已有避重复意图，不能把整条防重复视为全新发明；问题是把局部失败推广成全程禁止的强度未被论证。

calibration reason说澄清何时算family exhausted即可`preventing incomplete within-family coverage`。最终先定义“全成员检查才算穷尽”，再写`Once a family has been checked, move to a different ... family`，同时删去Original的`rather than exhausting ... one type`。新Check更明确：查完所选类别所有成员后才`moving to another family`。

**准确结论。** “尚有未查成员，所以不能宣称整类已查完”是信息判断；“因此换类前必须查完”是额外调度约束。最终Update的when/once写法仍允许不同解读，**不能说它无歧义地禁止提前换类**；但删除原约束、所加顺序和Check一起支持“模型将认知边界转成调度前置条件”的判断。Check本身不是Actor指令，本轮没有Editor落实或行为证据。

两版针对同一M6选择了“少量交错”与“先完成该类”的不同安排，说明观察本身不能唯一决定调度；这不是证明两种策略都无效，而是它们各自需要独立的当前问题理由／可检验预期，不能由反例直接推出。

### 案例五：R06原案被保留——历史方向支持不足以自动批准具体要求

**实际编辑与反馈。** M10的R05 Diff明确写跨类 `rather than exhausting or looping over one type`，它也是R06 Parent。配对Q6到countertop2后21步成功，P6失败50；Q8先查cabinet1–4并回访，18到shelf1、23成功，P8失败50；Q10仍重复、46步对P10的38步。这里不全是理想轮换的正例。M10称两次救回都来自Parent未到family，但P6到过countertop1，实际漏的是同类countertop2；Memory概括也有尺度偏差，不能全归责Preconditioner。

**原案与判断。** R06 Original u2改成类内升序、穷尽再换类，并`guarantee progress`。正式V23 reason承认M6/M10只支持方向且非guaranteed cure，却Keep全部；construction明说`The substantive strategy is preserved`，只改位置来源和近期索引。

**跳跃位置。** 穷尽和保证来自Diagnosis，**不是这些Preconditioner新生成**；问题是预条件化没有为其保留补足支持范围。两步历史与当前循环可以支持尝试有序搜索，却不能证明先穷尽一类比其他覆盖方式更合适，尤其Parent／历史实际编辑已反对困在单类。保证与reason承认局限之间有直接不一致。不能反过来说所有穷尽方案都不合理；当前输入可能允许把它作为探索假设，但现有理由未讨论调度差异及收益预期，且保证超出材料。[R06原案、reason及Effective](EVIDENCE_INDEX.md#r06)。

### 案例六：R06替代方案——合理试探与附带规定必须分开

**共同合理动机。** M10的条件性覆盖收益、当前P3重复失败，以及P1/P2在countertop2取得目标，足以支持重新分配探索，而不要求永久禁用原方向。calibration还引用M9：额外检查drawer7/8的candle候选34步对Parent30步；这是扩大检查可能有成本的相关观察，不是预算采样的独立效果验证。

- **alignment：** 不先穷尽大类、分段换类可以作为新策略。但`all plausible families have been sampled once`把完成边界从位置换成类别；同类还有未查成员就可能达到新边界，恰与M6提示的尺度区别冲突。该限制不是扩大覆盖的必要推论。`part of a family`未充分定义，`guarantee progress`也未获支持；保证本身继承自Original，不应写成全新发明。
- **symmetric：** 当前若干目标在表面／fridge，为优先看这些位置提供试探动机。最终却规定表面→全部设备→柜子→抽屉，未解释后半排序为何成立。这里缺的是各排序关系的问题依据，不是缺少历史成功就一律禁止。它的`breadth-first`名称也不能替代实际顺序：正文仍可能连续扫后部大类。限定closed cabinets/drawers对已开但未检查位置有覆盖歧义，`such as`举例则不能机械读成禁止未列出的bed/desk。
- **calibration：** budget-bounded sample后换类回应预算问题，reason把轮换称为`a more executable way`。新假设有动机，却没有清楚给出采样尺度或fixed order如何确定；不能把“预计更可执行”当作已观察到的效果。但它未再用类别采样终止，也不要求固定两个或固定surface-first，不能把这些旧问题算在它身上。

**对既有判断的必要收紧。** R04/R05/R06的Parent已经有`all plausible candidate receptacles have been inspected once`，因此后续保留完整位置单遍边界，不应一律算新增无据停止。symmetric的full-pass后仅继续未查位置与既有single-pass相关，缺少细节不等于必然新增提前停止；calibration保留全位置边界亦如此。最清楚的新范围错误是alignment的“类别采样替代位置覆盖”。没有新行为执行，不能说这些文本风险已导致提前停止或下降。

## 4. 跨版本共同结论

1. **是否确认这种现象？是，限定于这些档案的显式理由和最终文本。** 同类遗漏被转换为换类前置条件，预算问题被扩展成批次或全局优先序，覆盖目标被扩展成类别采样终止，都是具体可追溯的实例。不能据此宣称所有材料普遍如此或揭示模型内部因果过程。
2. **主要跳跃在哪一环？更广泛的是认识到具体构造。** “存在遗漏／循环”通常有事实支持，但无法唯一决定穷尽、轮换、批次大小、排序和停止。较明确的观察解释错误也存在：symmetric R05把遗漏归因于换类触发；M10把新位置概括成新类别；若再据这些过满认识构造策略，两个连接处会叠加失真。这是定性归纳，不是错误率统计。
3. **有没有反例被过度否定？没有发现有效输出把整个搜索方向永久撤回或因历史失败一律禁止新策略。** alignment的“太依赖rigid switching”和symmetric的因果表述对具体旧方式有过度否定倾向；但其最终仍探索，不等于完全保守过滤。V23 R05明确认为混合反馈不足以撤回，是允许合理Keep的反例。
4. **哪些属于合理新假设？** 基于可见剩余实例优先回源、近期循环后换候选、兼顾类内实例的跨类探索、为避免大类耗尽预算而试分段采样、提早查看当前多次出现目标的表面。这些可以有明确动作要求，未验证并非错误；不足在把相关观察说成验证了整套方案，或让额外顺序／禁令／结束条件借同一个动机自动成立。
5. **R04与R05/R06有何本质证据差别？** R04有同一条件下的正向操作实例、明确动作候选和局部反馈，可以对照“持物直接执行”与具体冗余操作。搜索反例多数只说明哪里没到、何处重复或太晚，没有隔离哪种调度造成结果，也没有给出唯一替代安排。任务成功／总步数仍不能单条归因，温度案例只是推导距离较短、条件匹配较好，不是因果证据完美。
6. **是否足以支持继续研究通用判断原则？足以支持研究这个连接处，不足以认定一条新Prompt就能解决。** 当前发现跨R05/R06、多个候选重复，但仍来自同一ALFWorld材料族、单次随机输出和联合编辑；不能据此推广到其他环境或断言某版Prompt必然更好。也没有本次新行为验证。

## 5. 一条后续研究原则（仅建议，不是新Prompt）

**先界定历史响应对当前更新的含义与边界，再结合当前证据构造有明确问题动机、适用条件和可检验预期的策略；不要把失败现象直接改写成反向强制规则，也不要让一个合理动机自动替所有附带要求背书。**

这允许Keep、大幅调整和新策略探索，不要求所有要求都已有成功案例。现有证据支持研究这个原则；本次没有把它写入Prompt、增加模块、字段或评分器，也未安排后续调用。

## 6. 离线核验与停止

只新增本独立分析目录：[轻量读取脚本](../read_archives.py)、本报告、证据索引及核验JSON。脚本仅用Python标准库读取JSON／计算哈希，没有导入或调用项目自进化模块，没有API或环境执行代码。15组有效档案与原对照一致；18条历史轨迹与可见sources一致；关键早期快照内容一致。

历史保护覆盖V23源码、正式训练与Test产物、V23.2源文件及全部此前实验／原始档案、Adapter和设计文档。Test只读取字节计算保护哈希，不分析轨迹。**12,080个文件的集合与SHA-256全部一致**，见[保护核验](../results/protection.json)。没有覆盖旧报告，也没有改默认方法、Prompt或Active Memory。

本次新增模型调用 **0**，模型Token **0**；未运行ALFWorld、Editor、Replay、Gate或其他自进化模块。完成分析后停止，不自动进入Prompt设计或模型验证。
