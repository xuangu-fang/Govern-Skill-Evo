# P1-B：Diagnosis 策略构造规则的受控验证

**结论：未达到P1-B语义验收，不晋升当前默认Diagnosis，不建议直接进入P2。** R04取消了D1完整微波炉插入链，但保留了依据不足的开门前提，并强化了“移走一个物体后转去未查位置”的条件；R06保留具体策略和多实例回源，却重新绑定编号线索／打开设备条件，引入未经支持的备用温度操作；R05输出截断，没有合法D2可评价。

两条规则没有使所有输出都变得空泛或保守，但也没有可靠落实必要性判断与边界保持。以下把事实理解、策略构造及尚未验证的行为效果分开。一次固定材料输出不能证明稳定优劣；这些案例已经参与设计，不构成独立泛化验证。

## 设计、实现及冻结

本次以P1模板为基线，只替换第三节两段：

1. **策略表达段**：区分任务／状态必要行为、探索策略与成功伴随动作；使用行动前信息、候选、反馈和轨迹差异限制必要性断言。替代动作可见不等于反事实成功；仍允许新策略和大幅修改，既有reason／Checks区分观察与预期。
2. **成功行为保留段**：保持触发条件与覆盖单位；部分覆盖不等于完成；停止、继续与后续动作前提一致；保留有效行为及信息／资源条件。明确Update相对Parent，未重述不自动等于删除。

P1的Goal定义原样保留。没有新增章节、字段、分类器、案例专用策略或能力补丁。完整文本与精确Diff见[冻结记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/reports/FREEZE.md)，设计见[P1B_DESIGN](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/reports/P1B_DESIGN.md)。`config/diagnosis_prompt.md`为唯一候选，从冻结到全部调用结束未修改。

新增代码仅在本实验目录：`run.py`切换独立路径与冻结核验，直接复用P1的material、run_one、run及原local_validation；`tests/test_profile.py`为8项确定性检查；`analyze.py`读取并比较归档，不生成模型输出。未修改共享源码、Schema、默认配置或其他模块。分析脚本在结果返回后补充了共享日志漂移和无合法D2的显示处理，不参与模型生成；冻结的运行入口和测试保持不变。

冻结于 **2026-10-20 13:56:56 +08:00**，离线测试随后通过，首个请求 **13:57:40** 开始。P0 cases原样保留，每轮Parent、完整当前执行、Grouping、Actor背景与原user消息一致，Diagnosis不读Memory。deepseek-flash、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300秒不变；R04容量1,000,000字符／1,500,000字节，R05/R06为4,000,000／6,000,000。

## D0／D1／D2对照

完整Goal、Updates、basis、Checks及原始响应路径见[OUTPUTS.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/reports/OUTPUTS.md)；机器对照见[comparison.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/comparison.json)。D0为正式V23，D1为P1，D2为本次。**D2没有以D0/D1输出为输入**；比较中的“继承”只表示相对Parent／旧文本的要求关系。

| 案例／要求 | D0 | D1 | D2及判断 |
|---|---|---|---|
| R04 Goal | 精确热处理后交付、多实例；未锁定插入链 | Goal写入move/close/open/take/heat/place成功链 | 改为`minimal microwave heat interaction`，热处理绑定减轻；但又把`sweeping all receptacle types once`写进Goal，整体边界未通过 |
| R04 温度策略 | 精确目标、heat后直送，无完整前置链 | 强制open→move→close→open→take→heat | 删除插入／关门／重开／取出链；仍要求闭门先open、在open microwave上heat，必要性仍过强 |
| R04 多实例 | 计数、扩大未查位置覆盖、避免空回访 | only uninspected／交付后只找remaining uninspected | 保留数量和精确类别；增加“位置空**或其中一个物体已移走**则转到未查位置”，未充分保留同源剩余目标 |
| R05 Goal／搜索 | family sweep；跨类single-pass，无每类一次结束条款 | Goal解绑；Update引入category checked once结束歧义 | **无合法D2**。输出length，不评价改善或退化，不把片段作为最终策略 |
| R06 Goal | ordered memory-independent sweep | 删除算法绑定，以行为目标为主 | 没有恢复同名算法，但把numbered receptacle names和open appliance写入Goal，部分重新绑定实现／条件 |
| R06 搜索 | 类内升序穷尽再换类、guarantee progress | 近期避循环、few后换区、近期新颖性fallback | 单向single sweep、每个已查处视为consumed、偏好更高编号未访问实例／完全未查类别；取消D1显式信息不足fallback，全局状态依赖仍在 |
| R06 温度 | 直接持物，必要时开门 | 仅闭门且需要access才开；held动作可用就做；否则最小必要调整 | 改为closed就open；新增动作不可用时“放入一次然后执行”备用方案。弱化了D1的可用动作条件 |
| R06 数量／回源 | 保留在Goal／Checks | 保留在Goal／Checks | 独立u3明确`remaining uninspected receptacles or a known source`，数量、精确类别、普通任务不套单件desklamp收尾得到具体保留 |

## R04：完整必要链减少，但必要性和回源边界仍未解决

### 事实理解

原始Diagnosis输入位置为：

`artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R04/diagnosis/attempts/001/input.json`

其中F的`facts.runs[P2/P3/P4].steps[P2:6/P3:7/P4:5].before.commands_ref`解析出的Actor可见菜单分别已有：

- `heat plate 3 with microwave 1`
- `heat potato 3 with microwave 1`
- `heat tomato 2 with microwave 1`

三步before observation均为到达关闭的microwave，实际动作均为open。P1-A已对照原环境菜单、完整Actor messages与过滤逻辑核验；这次输入完全未变。原始轨迹路径及字段详见[P1-A证据索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/reports/EVIDENCE_INDEX.md)。

D2.reason正确识别cup替代mug、热处理后没交付和重复搜索，也看到了成功多实例行为。但其`P7 did not pursue a second keychain after placing one`若按“没有继续搜索”理解则过强：P7:35交付后，36–50仍在drawer间移动／examine。当前事实是继续搜索却未取得第二件，并非在一件后停止。不能用该表述作为新增“继续搜索”的充分诊断，也不能知道Actor内部到底想做什么。

### 必要性：有部分纠正，仍未通过

D2.u1：

> `(2) Carry it to the microwave; if the microwave is closed, open it once. (3) With the target held at the open microwave, issue exactly one 'heat <target> with microwave 1' action.`

相比D1，它删除了放入、关门、重开、取出的整条强制链，是实质文本改变；没有靠删除热处理策略来避免承诺。精确目标、heat后的成功反馈、必要交付和闭合目标数量等都有明确要求。

但“闭门”仍被当作必须open的充分条件，Goal/Update没有区分**设备关闭**与**动作访问确实需要开门**。行动前heat已经可见，因此不能从成功轨迹使用open就推出它是无条件前置步骤。这个缺口和P1-A定位相同，只是必要链变短。也不能反过来断言早期heat一定成功，或一次open已被隔离证明有害。

D2将重复move/open/close称为`those steps are wasted`，针对当前长循环有问题依据；不能扩成任何条件下放入／取出均无用。当前text主要针对重复循环，不应机械按措辞强弱判错。

### 边界保持：出现更显式的错误条件

D2.u2：

> `When a location is visibly empty or an object there has already been moved, go to a different not-yet-inspected receptacle ...`

> `After delivering one instance ... resume the sweep ... from unvisited receptacles ...`

`or an object there has already been moved`是相对D1更明确的新条件。P6:23 after见两支candle，24拿第一支、26交付、27回源后仍见第二支，28拿取、30成功；P8:1 after见两份newspaper，2拿第一份、4交付、7回源后仍见第二份，8拿取、10成功。**移走一个物体不能证明来源已经空，也不能证明应放弃该来源的剩余目标。** D2的basis甚至包含P6:24、P8:2，完整轨迹又一直可见，不能归为缺少反例输入。

该句后半又提same empty container，若读者补上“仅已经空的来源”可限制风险，但前面的`or`没有保留这一条件；下一句继续指定unvisited，缺少已知非空来源的明确空间。这里报告规格冲突／范围风险，不宣称新Actor已被阻止回源。

D2.u2以实际放置数量作为结束条件，未把“每类采样一次”直接写成结束，这一点不同于D1的R05错误；但Goal中的“all receptacle types once”和u2前段“每类至少一次”仍绑定覆盖方法，不能视为纯行为目标。全局unvisited集合和初始房间列表的持续可用性也未解释，原有能力问题没有被修复。

Checks c2还问是否`avoid leaving the microwave area without delivering the heated object`。对目的地在别处的任务，必须先离开再交付；这种检查表述容易把“热后直接交付”写成时序不清的观察标准。**它不是Actor最终指令**，不计作Skill已经新增禁止离开。

R04小结：精确目标、热处理、交付、数量仍具体；完整插入链减少。但开门必要性、回源边界与Goal绑定未通过，且出现更显式的“移走一个物体”条件泛化。没有执行结果可证实步数收益。

## R05：技术停点，不使用片段做语义验收

请求成功返回HTTP响应，但`finish_reason=length`，completion_tokens=16,384达到原上限，其中reasoning_tokens=16,015。可见文本只有1,863字符，JSON未闭合；原机制在检查finish_reason时停止，因此没有parsed.json、合法diagnosis.json或result.json。

已保留[原始响应](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R05/attempts/001/response.json)、[原始文本](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R05/attempts/001/raw_output.txt)、[停点](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R05/stop.json)。没有重试、修补、调高Token上限或压缩输入。`comparison.json`中的D2=null是研究汇总占位，不是合法no_change／need_evidence。

因此R05七项关注点均为**无法评价**：既不能说类别一次终止已消除，也不能根据未完成片段宣称提出了某种最终强制策略。D0/D1仍可对照历史，但没有D2语义结论。输入字符／字节未超过继承容量；API返回的输出预算耗尽是观察事实，不能据此断言Prompt某句话造成长推理，也不能排除随机性。

## R06：具体探索保留，但部分既有边界退回

原始输入为同一正式R06 `diagnosis/attempts/001/input.json`，不是包含M10的Preconditioner输入。D2.reason仍能辨认P3少数位置循环、P1/P2新表面发现目标、P4/P5温度重复以及P6/P7双物体成功，主要问题识别有依据。

### Goal和搜索策略

D2.Goal未恢复`ordered memory-independent sweep`这一措辞，也没有要求类内穷尽后才能换类或写出`guarantee progress`。但它要求规则依赖`numbered receptacle names rather than a global visited set`；编号作为特定进度方法又进入Goal。当前观察和动作候选属于必要能力边界，而**必须以编号为进度线索**不是同一层次的必要条件。

D2.u1具体写：

> `run a single forward sweep that does not oscillate. Treat each inspected receptacle as consumed`

> `prefer the next higher-numbered unvisited instance or a wholly uninspected family or surface`

> `Continue ... until ... found or all plausible receptacles have been inspected once`

编号推进、早查表面、局部反循环都可以作为针对当前问题的探索：P3重复且未覆盖其他位置，P1:34/P2:8首次到countertop 2才发现目标。但是：

- “更高编号”不证明“未访问”，当前菜单也不提供全局访问表。`wholly uninspected family`和全部位置已查一次仍要求累计进度。相比D1，明确的信息不足fallback消失；虽然Goal声明不用global visited set，实际Update仍需要相应知识。
- `each inspected receptacle as consumed`没有保留是否有目标／是否仍有剩余目标的条件。它是状态标记式的行为要求，不是已有访问状态。不能靠consumed一词创造持久记录。
- “不振荡”可视为目标性行为规范，不自动等于声称策略已经证明保证进展；没有必要把它与D0的显式guarantee完全等同。但其全程single-pass实现仍未有可恢复的状态支持。
- 全位置一次边界主要沿袭Parent，而不是新引入“每类一次”终止。不能把继承问题全归为D2新增。当前没有证据证明编号策略必然更差，也没有证据证明全局一次覆盖能执行。
- budget仍写在Goal/u1，u2保留处理交付。D0显式预留后处理步骤的要求仍未同样重述；Parent的通用预算规则仍在，**不能声称新Skill已删除预算**。没有固定预留步数，也未证明执行资源关系已经充分落实。

### 温度必要性与备用方案

D1的`Open it only if it is closed and access is needed`及held action已available即执行，被D2改为：

> `go to the required appliance ... and open it if closed`

> `If the conditioning action is not offered for the held target, place the target inside once and perform the action`

R06 P4:5、P5:4在closed microwave前已有heat，P4:20/P5:15是实际held heat，P1:38/P2:11是实际held cool。这支持保持“可用时直接完成所需处理并交付”，不支持把open写成所有closed状态的必要前提；Goal也把`at the open appliance`固化为条件。因此温度边界相对D1存在退回。

新增“动作不可用则放入一次再执行”没有对应的当前成功分支。反而P4:6／P5:5放入后，**P4:7／P5:6的行动前菜单没有heat**，直到取回目标后才再次有heat。注意这些放入前其实已有heat，不能当作完全相同fallback前提下的反事实失败；但它足以说明“放入就会使动作可用”并非当前记录直接支持的通用关系。新分支没有规定若放入后仍不可用如何处理，也未在reason或Checks中作为待检验假设界定，是依据不足的附带规定。

### 多实例行为是正面变化

D2.u3明确：

> `continue searching (from remaining uninspected receptacles or a known source) ... until the requested count is placed`

P6:17/18发现并取得第一本书、20交付、22取第二本、24交付；P7同源两张卡，5和10分别交付，支持保留顺序数量任务与有效来源。`known source`不要求全局记住所有剩余目标，具体可用性仍应按Actor当前信息判断。这一表达比R04的单纯unvisited范围更好，允许有效回源，并拒绝把desklamp单物体规则套到普通多实例任务。

不过u1的“consumed”和u3的“known source”优先关系仍需明确；可以按搜索与已知来源取物区分而相容，不能说必然冲突，也不能忽视其边界未说明。独立u3本身是具体、合理的保留，没有因证据要求提高而把策略全部删掉。

## A—E验收及三层评价

| 维度 | R04 | R05 | R06 |
|---|---|---|---|
| A Goal表达改善和必要约束 | 热处理绑定减轻，但新绑定all-types-once；未通过 | 无合法D2 | 编号进度线索／open状态进入Goal；部分退回 |
| B 有具体策略而非空话 | 有完整处理与数量策略；全程可执行性未通过 | 无法评价 | 有具体局部／编号探索、处理和数量策略；全局状态仍有缺口 |
| C 承诺有依据、区分预期 | 未证明开门必要，移走一个物体条件扩大；未通过 | 无法评价 | held处理有据；先开门／放入fallback及全局进度条件不足 |
| D Goal与Update边界 | 没有锁定旧完整链，但Goal仍指定覆盖方法；未充分改善 | 无法评价 | 没有旧完整算法，但新实现线索／操作状态绑定；未通过 |
| E 无新增不合理限制／行为丢失 | moved-one条件、回源范围、Check时序问题 | 无法评价 | 新fallback、consumed范围；已知来源／数量保留为正面 |

**事实理解层：** 能识别主要当前问题，菜单装配未丢失；R04对P7未继续追求第二件的表述过强。R04/R06没有把closed时heat可见充分用于限定必要性，不是证据未提供。

**策略构造层：** 有局部改善（R04缩短强制链、R06明确known source），但两类核心问题仍出现：状态必要性被推广，以及局部事实被扩大为全局状态／排他范围。R05技术停点使三例完整验收也未完成。整体未通过。

**行为效果层：** 没有Editor、Candidate或Replay；没有生成新Skill，不能证明步数、成功率、早停或实际回源损失。不能以合法revise、Update数量或旧关键词消失判断成功。合理探索能力在两个合法输出中仍存在，但“具体”与“有依据”不是同义。

## 失败归因与后续判断

本候选已明确写出成功序列不意味着每步必要、候选替代不能证明反事实成功、部分覆盖不等于完成、不能排除有效行为，输出仍未稳定落实。因此不宜把失败简单归为“缺少更严格的一句规则”。

可确认的是：当前输入中的早期heat候选和同源剩余目标，未始终约束规范；声明不用全局visited也未消除Update所需的全局状态；R05有输出预算停点。这些仍属于P1-A定位的必要性／条件保持缺口，并非已证明的新架构缺陷。

**值得在下一次授权中研究证据组织，而不是默认继续加长Prompt。** 可先研究既有输入里相关行动前选项、成功动作链和保留行为反例的对照关系是否足够容易被识别，以及实际basis是否覆盖决定必要性的那些条件。当前证据不证明输入长度或组织方式造成失败，故只能作为研究假设；本次不重排输入、不裁剪轨迹、不新增字段／审核器，也不再实施第二版。

不建议晋升默认Diagnosis或进入P2：R04/R06核心语义项尚未过，R05无合法结果。如果以后继续，应先决定如何验证上述剩余问题及技术完成率；只有修正达到预期后，才考虑未参与设计的训练案例和P2独立验证。不能用最终Test调参。本次不追加调用。

## 离线测试、调用与成本

179项禁网确定性测试通过（6.22秒pytest报告；外层耗时见结果JSON）：171项既有V23.2／Diagnosis／Preconditioner契约与8项实验检查。覆盖冻结源码／默认、显式模板、完整上游payload无Memory、原解析与下游字段、纯编译兼容、timeout／截断／契约失败均只请求一次。模拟结果仅在pytest临时目录；下游只测纯函数，没有Preconditioner模型调用或正式Effective Plan。

| 案例 | 状态 | Input | Output（含reasoning） | Reasoning | Total | 请求／校验耗时 |
|---|---|---:|---:|---:|---:|---:|
| R04 | 合法revise | 61,109 | 14,115 | 12,889 | 75,224 | 73.491秒 |
| R05 | length，技术停止 | 65,536 | 16,384 | 16,015 | 81,920 | 90.214秒 |
| R06 | 合法revise | 45,949 | 9,566 | 8,473 | 55,515 | 48.320秒 |
| 合计 | 3次逻辑／HTTP请求，0重试 | **172,594** | **40,065** | **37,377** | **212,659** | 全轮墙钟 **212.267秒** |

Reasoning包含于Output，不另加。缓存命中输入5,760 tokens，未命中166,834。原始usage全部已保存，没有未知用量请求；没有账单金额或可核验的本次计费费率，货币成本不编造。R05截断费用仍计入合计。Actor、Preconditioner、Memory、Editor、Replay、Gate和环境调用均为0。

详细记录见[attempts.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/attempts.json)、[summary.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/summary.json)、[输入核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/verification.json)、[离线日志](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/offline_tests.log)。

## 文件保护：保留告警，不宣称全集合未变

保护范围12,298个既有文件，初始已有未提交改动未回滚。本任务所有写入仅在新实验目录及对应新artifacts目录；没有改任何方法或历史输出。

存在两次共享文档变化：

1. **冻结前**：`docs/README.md`、`experiments/methods/README.md`、`src/skill_evolution/README.md`的哈希与任务入口快照不同。首次prepare停止，未调用模型。本任务未写入它们，保留入口快照和差异，按当前状态重新核验后冻结；Prompt没有因此修改。
2. **三次调用完成后的保护检查**：`docs/04_EXPERIMENT_LOG.md`哈希变化，原P1运行器在已保存三轮结果和成本后触发assertion，进程非零退出。这个保护告警不是第四次调用，也不否定R04/R06已存档的合法输出；原`protection.json`保持`unchanged:false`，未被覆盖成成功。

独立分析复核确认，除记录的共享日志外，冻结时保护集合一致；正式V23源码／默认、全部P0/P1/P1-A及历史V23.2档案、真实输入输出、Skill／Memory／Campaign／Test字节未变。Test只作哈希保护，未用于分析。**不能报告整个工作区完全未变**。

见[冻结前漂移](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/pre_freeze_drift.json)、[运行后漂移](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/post_run_drift.json)、[原保护告警](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/protection.json)、[分析期保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/analysis_protection.json)。这些变化来源未通过本任务确认，只能确认本任务没有写入这些文件，不推测具体作者。

本次完成单一候选设计、最小实现、离线验证及最多三次受控调用，真实失败和保护例外均已归档。**停止于P1-B，不修改本候选、不进入P2。**
