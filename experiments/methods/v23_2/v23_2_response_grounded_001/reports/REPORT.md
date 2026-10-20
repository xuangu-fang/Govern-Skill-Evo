# Response-Grounded Strategy Construction：固定材料验证

日期：2026-10-20（Asia/Shanghai）。本报告评价最终Update的实际文本，不把合法JSON、Memory引用或Adjustment数量当作语义通过。所有版本均从同一轮正式Original独立开始；旧Effective没有作为本次输入。

## 设计、冻结与比较材料

[调用前离线分析](OFFLINE_ANALYSIS.md)与[设计说明](DESIGN.md)先界定反复出现的推导问题，再形成统一原则：历史实际行为、揭示的问题及建议探索的办法必须区分；以这种认识结合当前证据构造或保留Update。失败现象不能直接确定原因或唯一替代策略，合理动机也不能自动为附带限制背书。

[完整Prompt](../config/preconditioner_prompt.md)仅替换正式V23第二节的一句历史响应使用要求，新增段落117词；[精确Diff](../config/v23.diff)。原Parent／Actor能力约束及全部JSON、Keep、合法停止、Checks和编译要求未变。旧候选第一节补丁未叠加。默认仍原V23。

[冻结记录](../config/freeze.json)及[实现快照](../config/implementation.json)覆盖Prompt、Diff、设计、离线分析、读取凭据、离线测试和调用代码；[验证配置](../config/plan.json)记录三轮实际来源、Memory、容量及模型参数。完整六版本Original／Adjustment／Effective见[全文对照](OUTPUTS.md)，各原始响应和输入见[来源索引](EVIDENCE_INDEX.md)。Effective的basis由既有编译器保留Original来源；变换依据应同时查看Adjustment的basis和reason。

## R04：具体操作得到保留，搜索边界仍有连带变化

**历史事实与认识。** M4对应R03实际Diff及三组持物温度操作：cool-pot 18→11步、hot-apple 35→9步、heat-egg 40→15步。前两组Candidate在闭门设备直接操作，第三组先开门再heat。Parent三组也成功，因此证据支持条件下的操作节省，不证明任务成功必要性或单条规则的独立因果效果。R04当前P2:6、P3:7、P4:5在行动前已有heat候选，亦支持减少前置操作。[历史动作索引](../../v23_2_response_inference_analysis_001/reports/EVIDENCE_INDEX.md#历史配对轨迹本次原文件核验)。

**u1实际变换。** 最终明确`When the exact target is held and an explicit heat action is admissible, perform it immediately`，保留精确类别、成功heat后直接交付，并以hot为适用条件。与当轮heat-then-place Goal一致，没有因未扩展cool就判为错误收窄。reason引用M4/M5和当前P1–P4，未把这些操作包装成必然成功。

边界：`open or insert only if needed to make the heat action available`中的“insert”条件分支未得到所引持物操作的具体示例支持。它不是强制插入，但“何时需要插入”未说明，可能重新容纳本来要避免的步骤；属于尚未支持的备用手段，不等于已观察到退化。

**u2实际变换。** 从全局single-pass式要求改为当前／最近两次观察驱动：不立即回到刚见无目标的非目的地位置，偏好不同类别或未开容器。保留计数、精确实例、继续搜索、打开容器和全部交付。对只凭近期信息无法确定新位置的情况也给出fallback；这是一项有循环问题动机的新启发式，不是历史已经验证的补救。

关键连带变化是删除Original的`or all plausible receptacles have been inspected once`，改为`Continue this count-driven search until the requested number ... has been placed`。reason主要解释避免隐含完整历史清单，没有分别说明取消搜索边界的预期成本；最近不可识别新位置时仍偏好换类，可能持续重访。不能将其称为已验证更可执行，也不能说已经造成超时。本次没有Actor执行。

当前P6:23／27／28、P8:1／7／8存在剩余实例及有效回源，本次没有禁止这种回源（限制的是刚见无目标的位置），但也未像正式V23那样补充显式的已知剩余源优先。它仍保留Original计数与交付，不能把未增加回源优先当作删除已有要求。现有checks观察新启发式，但没有清楚标记它为未验证预期。

## R05：识别实例遗漏，却进一步强化追踪与回访限制

**历史观察。** M6描述R03 Q2重复countertop2而遗漏countertop3；对应Parent在countertop3取得bread并成功。历史Diff要求当前／近期避免循环、扩展位置、高步数优先新位置，没有隔离某条确定换类规则。当前P6既有前段drawer／countertop／sink切换与回访，也有后段长扫drawer；P8反复cabinet／sink。这些支持改善具体位置覆盖，不能证明一次特定轮换策略已经失败。

**历史认识。** reason正确指出`a Candidate can revisit one specific location while leaving another uninspected`，没有像symmetric一样断言换类导致该遗漏，也没有推成换类前穷尽。但总体reason的`family rotation alone did not reliably prevent cycling`仍把旧的较宽泛搜索指导概括成已验证的family rotation：R05当前Parent来自R02，所提Original轮换尚未执行；M6真实R03Diff也不是本轮相同轮换。更准确的结论是旧覆盖／避循环指导未稳定消除循环。

**最终要求。** u1精确类别Keep，有P7及M8依据。u2保留轮换，新增`do not let rotation skip a specific ... location`并举countertop2／3；这能回应实例与类别尺度区别，未新增固定数值批次或全局排序，也未要求穷尽当前类别。

但reason将修复称为`concrete per-location tracking`，Effective要求选择`locations you have not yet visited`、识别哪些位置已经检查。Actor仍只有当前及两组历史，没有持久追踪记录，动作候选也不提供访问状态。这是未实现的追踪要求，不能因为说得更具体就成为可执行方案；本次只记录残留问题，不恢复能力优化研究。

另有实质强化：`Only return to a previously inspected location if a current or recent observation shows the exact target or another required exact instance there`。它从避免已知空位置重复，扩为对所有已检查位置回访的唯一许可条件。只看当前／近期是否见目标不能排除所有有用回访；Update没有给出这个排他强度的独立理由。开头是搜索场景，因此不能直接断言它禁止全部后续交付；但若作为通用回访限制落实，会与到已经检查过的处理／目的地发生歧义，原有必要完成流程需保持。此风险尚未经过Editor或Actor验证。

`Avoid inventory checks while carrying nothing`是Parent已有要求，不能算新增无据禁令。`Reserve remaining steps for ... unvisited ... locations`回应搜索预算，但未明确保留取得目标后的处理预算；原Parent和u1仍承担完成流程，不能据此认定它已被删除。总体保留了探索，尚未充分交代新追踪方案与排他回访条件的可检验假设。Check重复观察新规则是否执行，并不证明规则自身已经合理。

## R06：主要修正信息来源，未充分处理调度差异

仅attempt 002是正式有效输出。attempt 001因原有引用校验失败而无有效Effective，不能把其Keep当成另一份合法验证结果，也不能挑选两次中语义较好的版本。

**历史与当前事实。** M10对应R05实际Diff明确要求`spreads across distinct receptacle families rather than exhausting or looping over one type`，也是本轮Parent。R05 Q6到countertop2取得butterknife并成功，Parent已经到过countertop1；Q8到shelf1取得soapbar并成功，仍伴随前段cabinet重复。Q10成功但46步对38步。支持扩大漏查位置覆盖，不证明特定调度胜过其他调度，且M10将新位置概括为新类别并不完全准确。当前P3反复fridge／countertop／cabinet而50步失败，P1/P2在countertop2取得目标，提供改善覆盖的当前动机。

**实际判断与变换。** u1温度指导Keep。u2从初始room description改为当前admissible go-to动作列表，增加“下一计划索引不可用时跳过”，并保留已持目标后处理／交付预算。M6的R03 Q6确有不可用移动及no-op回退，这对“选当前可用动作”的局部操作有直接依据。reason将主要问题定位为Actor不能跨步保留初始房间描述，未讨论Original类内穷尽与Parent／历史反对困在一类之间的差异。

**最终调度仍是类内穷尽。** `Commit to a fixed family order`、类内升序，以及`When the current family has no remaining unchecked admissible destinations, switch to a genuinely uninspected family`构成最终要求。前者没有明确选取顺序的依据，后者保留Original先完成本类才换类的核心安排。reason以`M10 shows family sweeps help only when uninspected families are actually reached`支持继续有序扫查，尚未说明本次类内穷尽为何能更早到漏查位置，或把它明确作为可检验新假设。当前循环不能直接证明穷尽更优。

**局部改善与残留。** 删除了Original的`guarantee progress`，也没有新增每类采样终止、固定数值批次或表面→设备→柜子→抽屉的完整优先序。这些是文本上的局部改善，不能抵消未解释原调度差异的问题。仍称`memory-independent`，要求知道unchecked／已见空及genuinely uninspected family；当前动作候选说明能去哪里，不说明过去到过哪里。固定全类别顺序尚未定义，也未解释从当前／近期状态如何恢复跨类进度。reason称`making it executable`仍过满；本次没有验证执行性，更没有行为收益。

原始房间描述并非只在第一步可见：其内容可随两组历史短暂保留，之后丢失。改用当前动作列表有持续信息来源依据，但不能把有限历史问题概括成每一步都完全没有初始描述。该信息源修正也不能替代本研究要求的历史认识与策略构造判断。

## 六版本变换摘要

每格是相同Original到该版最终Effective的差异，不把旧Effective当新输入；完整原文、reason、basis、checks见[全文对照](OUTPUTS.md)，具体有效attempt见[索引](EVIDENCE_INDEX.md)。

| 轮次／Update | 正式V23 | alignment | construction | symmetric | calibration | 本次grounded |
|---|---|---|---|---|---|---|
| R04 u1：精确目标、heat后直送 | 有条件持物heat/cool | 直接heat；宽温度触发有歧义 | hot条件直接heat | hot条件直接heat | hot条件直接heat | hot条件直接heat；新增未具体支持的insert-if-needed备用分支 |
| R04 u2：计数、继续覆盖、全合理位置一次边界 | 补已知剩余源优先 | Keep | 补已知剩余源优先 | 补回源，扩大every listed | 近期启发式，considered once歧义 | 近期启发式与fallback，删除全位置一次边界，只到计数满足 |
| R05 u1：精确类别不可替代 | Keep | Keep | Keep | Keep | Keep | Keep |
| R05 u2：跨类而非穷尽一类 | Keep，可作新探索 | 轮换为启发式，不漏同类实例 | 近期选择及换类例外 | few例如2–3批次、全程at most once | 类内穷尽判断与换类顺序相连，Check强化 | 保留轮换、不漏具体位置；新增全局追踪和排他回访许可 |
| R06 u1：持物直接温度处理 | Keep | Keep | Keep | Keep | Keep | Keep |
| R06 u2：类内升序穷尽、保证进展 | Keep | 部分扫描轮换；每类采样一次终止；仍保证 | 改信息源，保留类内穷尽／保证 | 全局表面→设备→柜→抽屉 | 预算采样轮换、顺序尺度未定 | 改当前动作来源及不可用索引跳过；保留类内穷尽；删除显式保证 |

不能将所有“单遍”都当作新增停止：Parent已有全合理位置检查一次边界；alignment R06将其缩成类别采样，是较清楚的覆盖边界改变。本次R04反而删除该边界，因此也不能仅因没有提前停止就说构造已改善。

## 行为规定与依据的对应核查

| 本次实质规定 | 历史观察能支持什么 | 当前动机／新假设 | 最终规定是否得到相应支持 |
|---|---|---|---|
| R04持物且heat可用时立即执行 | M4实际动作和条件，减少多余操作 | 当前P2/P3/P4仍先做设备操作 | 主体充分；条件式insert备用手段缺具体依据，不是必然错误或已发生损害 |
| R04近期不同位置／类别启发式 | M3/M6避循环不稳定，存在漏查 | 减少近期重复而无需完整清单，可合理探索 | 有动机；取消全位置边界和持续fallback的成本未充分说明，未验证 |
| R05轮换不能跳过同类具体位置 | M6漏countertop3、重复countertop2 | 保留覆盖方向同时关注位置尺度 | 认识合理；“具体追踪”未构造为Actor实际可执行的信息方法 |
| R05只有当前／近期见目标才回访 | 历史可见收益回源与空位置循环应区分 | 让返回更有目标 | 排他强度超出所列反例；其他有用回访／必要流程的边界未交代 |
| R06只选可用go-to、缺失索引跳过 | M6有不可用移动／no-op，当前候选可见 | 避免重复无效动作 | 有直接局部依据；不能证明整套搜索方案因此可执行 |
| R06固定类别顺序、类内穷尽 | M10支持到漏查位置，且混合反馈 | 当前循环需要更有序；这可作新假设 | 未解释与旧跨类方式差异、排序选择或穷尽预期；支持没有覆盖最终强度 |
| R06删除guarantee、保留处理交付预算 | M6/M10仍循环／增步，当前需完成温度与交付 | 去掉过强承诺、保留原有效要求 | 文本上改善；memory-independent及全局进度需求仍未解决 |

## A／B／C分别判断与候选建议

**A：局部准确，未证实整体改善。** R04正确采用M4条件性操作经验；R05准确识别“重复一个实例而漏另一个”的事实，没有直接断言必须类内穷尽。但R05仍将旧宽泛覆盖指导称为已试的family rotation，R06未核清M10实际反穷尽编辑与Original的差异。没有看到新Prompt稳定促成“观察→有限认识”的完整改善。

**B：尚未通过。** R04主体温度要求和R06可用动作选择有依据，R06去掉进展保证。然而R05从具体遗漏转成未落实的信息追踪和排他回访规定，R04又连带改了搜索结束边界，R06主要修正信息源而保留未充分说明的原调度。缺少无据数值阈值或旧采样终止词，不足以证明推导问题减少；它以不同形式保留。

**C：没有表现为机械保守过滤，但有依据的探索尚未充分构造。** R05/R06 u1均有据Keep；R04两项、R05/R06搜索项均调整，允许较大的近期启发式／位置层次变换，没有因历史负例撤回整个搜索方向。可是reason通常把这些说成必要澄清或可执行修正，未清楚区分新方案的预期与已观察效果。原Checks或修订Checks可观察部分行为，但没有补足每项附带强度的理由。故可确认探索仍存在，不能确认“合理探索与减少无据规定”同时达成。

**建议保留为研究档案，不晋升下一优先候选或默认配置。** 本次没有充分延续alignment对R06原调度差异的关键识别，也没有解决替代要求的构造。该判断针对这三组单次随机输出，不证明通用原则无效或Prompt导致结果退回。历史多项编辑共同执行、单次配对与模型随机性均限制因果归因；没有新增行为验证，不能声称提高ALFWorld成功率。

## 离线核验、冻结、用量和保护

离线在禁用网络的测试进程中运行V23.2局部验证、V23 Diagnosis和Preconditioner相关回归：**171 passed，2.33秒**。[结果与参数](../results/offline_tests.json)、[日志](../results/offline_tests.log)。额外静态断言核对Prompt只有一处替换、三轮user消息相同、原Execution Context、默认V23及技术上限不变。不是新增自然语言审核器。

冻结时间为**2026-10-20 00:39:44 +08:00**；首个请求开始于00:39:55。冻结哈希在调用前、调用后分析时均验证相等。模型始终deepseek-flash、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300秒；容量各轮4,000,000字符／6,000,000 UTF-8字节，没有压缩或改预算。用户消息、实际请求参数及渲染后system唯一替换通过[逐attempt核验](../results/verification.json)。

| 轮次／attempt | 状态 | Input tokens | Output tokens | 其中reasoning | Total tokens | 请求及校验耗时 |
|---|---|---:|---:|---:|---:|---:|
| R04 / 001 | 合法ready | 356,203 | 12,429 | 11,174 | 368,632 | 65.779秒 |
| R05 / 001 | 合法ready | 470,239 | 10,277 | 9,621 | 480,516 | 59.816秒 |
| R06 / 001 | 引用契约失败 | 432,963 | 7,311 | 7,190 | 440,274 | 45.134秒 |
| R06 / 002 | 合法ready | 432,963 | 8,243 | 7,771 | 441,206 | 43.903秒 |
| 合计 | 3逻辑调用、4 HTTP请求 | 1,692,368 | 38,260 | 35,756 | **1,730,628** | 全轮墙钟 **221.010秒** |

Reasoning是output内含量，不重复加总；用量均来自实际API响应，包含失败请求，无未知用量。R06第一次正常finish=stop，但reason的当前引用简写`P4/P5`被既有历史引用正则识别为不可用历史引用，报`reason: unavailable historical reference`。原机制判retryable并自动重试一次；没有人工修补、选择性重采样或修改校验器。失败原文亦完整保留，但没有有效Effective。详见[全部attempt](../results/attempts.json)及[总用量](../results/summary.json)。

**12,090个保护文件的集合与SHA-256完全一致**：[保护核验](../results/protection.json)。范围包括V23/V23.2源码、ALFWorld Adapter、正式训练／Test产物、既有实验和设计文档；Test仅计算保护哈希，未用于研究。所有旧Prompt、失败尝试、Memory与结果均保持原样。本次只增加独立profile、冻结材料、真实Preconditioner档案与分析文件，没有改模块或默认配置。

已完成前三步并停止。未调用Diagnosis、Editor、Replay/Memory、Gate，未生成Candidate、运行ALFWorld或正式六轮实验，也未追加Prompt补丁。

最终独立复核见[final_verification.json](../results/final_verification.json)：冻结早于全部请求、冻结内容与默认V23未变、12,090个旧文件一致、报告链接无断链、仅三轮Preconditioner目录。`git diff --check`通过；未重复运行与本次无关的测试。
