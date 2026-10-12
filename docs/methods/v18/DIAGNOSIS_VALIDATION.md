# Diagnosis 试验与回归验证

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v18 Diagnosis Prompt 第一次固定输入试验](#v18-diagnosis-pilot-report)
- [v18 Diagnosis Prompt v2 固定输入语义 Pilot](#v18-diagnosis-v2-pilot-report)
- [v18 Diagnosis Prompt v3 六组固定输入回归](#v18-diagnosis-v3-regression-report)
- [v18 Diagnosis Prompt v3.1 回归报告](#v18-diagnosis-v31-regression-report)
- [v18 Diagnosis 统一聚合边界回归](#v18-diagnosis-v321-aggregation-report)

<a id="v18-diagnosis-pilot-report"></a>

## v18 Diagnosis Prompt 第一次固定输入试验

2026-09-18；Prompt `v18-group-diagnosis-1`。这是第 3 步的初步语义检查，不是完整 Skill 演化实验或效果验收通过报告。

**2026-09-19 职责边界更正**：本报告记录的是 v1 观察。正式 v18 中，旧 Simulator 的 STOP artifact 属于上游 benchmark 问题，不作为 Diagnosis/Prompt v2 核心语义验收项。下文保留历史事实并按该边界调整归类；原始模型输入、输出和统计均未改写。当前优化只针对未知产生额外义务、候选规律强度提升和条件/范围丢失。

### 设置与来源

固定三份历史 Evolution group 输入：R2 g5（定价）、R2 g3（订票/人数/姓名）、R3 g6（定价）。每组 deepseek-v4-pro 调用一次，temperature=0、reasoning_effort=high、24,000 completion token 上限、300 秒 timeout、无 SDK/应用重试。不运行新的 Agent、User、Grouping、Compiler、Editor 或 Monitor。

输入清单：[sources.json](../../../experiments/methods/v18/v18_diagnosis_pilot_001/config/sources.json)。调用前核对四类历史文件摘要、原始请求与旧输出验收；发给 v18 的 learner payload 与原 v17 请求完全相同。旧 Diagnosis 输出只参与来源复验，不发送给模型。不使用 Monitor 轨迹或隐藏 evaluator 作为新输入。

实际 Prompt SHA-256：`f3ebc4917b7edb6283b0fdbd42e3c85b159704dbd73b5861fce1b6d63f8f3254`。
原始请求/响应/验收产物：[pilot 目录](../../../artifacts/methods/v18/v18_diagnosis_pilot_001)。完整结果：[summary.json](../../../artifacts/methods/v18/v18_diagnosis_pilot_001/summary.json)。这些产物保留在本地 artifacts 中，不纳入正式学习或候选选择。

### 结构结果

| 固定输入 | 结构/引用验收 | Addressability | Gap | 用时 | Provider total tokens |
|---|---|---|---:|---:|---:|
| R2 g5 | VALID | ADDRESSABLE | 2 MISSING | 280.4 秒 | 75,705 |
| R2 g3 | VALID | ADDRESSABLE | 1 MISSING | 144.0 秒 | 53,248 |
| R3 g6 | VALID | ADDRESSABLE | 2 MISSING | 164.6 秒 | 68,240 |

合计 3 次模型调用、5 个 gap、197,193 provider-reported tokens。不是费用估算；各组并发，耗时不相加作为墙钟总时长。三个 Parent 都是 S0，因此本次没有真实 NEEDS_REVISION/SHOULD_REMOVE 语义样本，删除仅有工程测试，尚未做模型侧证据门槛验证。

### 逐组语义检查

#### R2 g5：保留了条件差异，仍有新增执行门槛风险

Analysis 不再把结算变化概括为任意变化：明确 horizon 保留原价，summit 四条均重定价；还明确指出 summit 没有查询保留航段当前搜索价，不能证明它等于结算价。第一个 gap 保留 horizon 计算依据，这是有用的条件信息保持。

第二个 gap 将 summit 的有限机制证据转成 guard：不要仅依据原价/显示价提交最后一次修改，须先取得用户接受实际金额可能不同的确认，否则在工具无法解决时转人工。引用中的真实用户阈值当然不能绕过，但输出尚未充分证明这一新的渠道级前置要求是必要修复，也未证明所有合法信息补救途径都不可用。尤其 reason 将“避免不可逆错配”直接当成 Skill 可修复依据，不等于解决原任务。

评估：条件归纳较历史 v17 输出更具体；避免新增执行门槛这一目标仍未充分达成。不能因缺少精确 summit 机制而硬编码补全正确价格映射，也不能把该 guard 直接评为有效成功修复。

#### R2 g3：未重复生成姓名外观规则，人数指导仍有范围与强度疑问

输出把 T024 缺独立 first/last name 的问题保留为 unresolved，没有产生姓名外观检查或 placeholder 禁止订票 gap。人数对照得到保留：5 人单订合规、6 人单订不合规、7 人拆 4+3 合规；行李问题因精确分类未知未强行生成指导。

人数 Analysis 称其为候选边界，但 gap 使用超过 5 人不得单订、每单至多 5 人的强指令，还附带每笔拆分使用相同付款方式等要求。候选身份虽在后文解释，强度是否被提升、附加付款一致性是否有充分独立依据，仍需审查。

评估：没有复现历史姓名外观门槛，保留了有用数量对照；不能据此认定整组 gap 已语义合格。

#### R3 g6：价格映射保留，另有旧 Simulator artifact

第一个 gap 明确保留 horizon 原价 / summit 当前搜索价的映射，并标注为经验候选而非可见 policy，Analysis 与 gap 的条件关系较完整。

第二个 gap 要求确认后立即执行 update。其引用 `T004/R021/R1/E0035` 是用户确认且包含 `###STOP###` 的最后一条消息。已经核对本次输入中的原文；在该 benchmark 的实际运行中没有下一次 Agent 决策机会。模型却在 reason 中声称这是一个可到达的下一回合，并否认自己是在尝试恢复已结束轨迹。

归类更正：原 v1 分析曾把该项视为 Addressability 语义失败。按正式职责边界，这是旧 benchmark/runtime artifact，不要求 Diagnosis 正确解释其运行时后果；它不作为 v2 核心语义验收项，也不用于继续 patch Prompt。上游修复不改变历史事实，历史输入及输出继续原样保存。

### 结论与边界

本次完成了 Prompt、完整请求、v18 transport/验收的接入验证；三组都成功返回，184 项相关工程测试通过。小规模试验显示部分具体规律和信息缺口被更好保留，同时仍有新增门槛和强度提升问题。**不能宣布 v18 Diagnosis 语义目标已全部通过，不能据此宣布成功率改善。**这一判断不以 STOP artifact 的解释为依据。

历史请求保存 Prompt v1 原文和全部响应，不自动修补、不选择最优输出、不以新版本覆盖本次结果。后续 Prompt 试验另建目录，重点检查“未知是否被转成额外义务或转人工要求”“候选关系到 gap 的强度保持”“条件与适用范围是否保留”；不要简单要求所有未知机制先验证后执行，也不围绕旧 STOP artifact 继续 patch。

这三个定向挑选的开发样本不是独立 held-out 评测，每组一次也不能测量固定输入生成方差。Simulator v18 的修复不会改变历史输入中的终止事件；本次没有测试修复版 Simulator 的实际残余 STOP 率，也没有运行任何 Candidate/Gate。

<a id="v18-diagnosis-v2-pilot-report"></a>

## v18 Diagnosis Prompt v2 固定输入语义 Pilot

日期：2026-09-19。Prompt：`v18-group-diagnosis-2`，SHA-256 `263598dd617827b9c972acf57dbca81664882c76c5ab1431b11d9813d26f5ff8`。

### 目的与边界

本次只验证 v2 的 learner 语义转换：未知是否变成额外义务、候选经验是否被强化、Analysis 的条件/范围/epistemic status 是否在 Gap 中保持。历史 benchmark/runtime 终止 artifact 原样保留，但其解释不参与评分，也不围绕它修改 Prompt。

输入共 5 组：R2 g5、R2 g3、R3 g6 三组历史 Evolution learner payload，以及两个独立构造开发样本。历史输入逐文件摘要绑定并复验原 v17 请求和响应，v2 收到的 payload 与历史输入一致；不运行 Agent、User、Grouping、Compiler、Editor 或 Monitor。构造样本及人工 rubric 固定于 [constructed_cases.json](../../../experiments/methods/v18/v18_diagnosis_pilot_002/config/constructed_cases.json)，明确标为开发样本，不进入正式学习，也不与真实 Evolution 指标混算。

入口为 `scripts/runs/v18/run_v18_diagnosis_v2_pilot.py`，产物位于 [v2 pilot 目录](../../../artifacts/methods/v18/v18_diagnosis_v2_pilot_001)。每组 deepseek-v4-pro 一次调用，temperature=0、reasoning_effort=high、24,000 completion tokens、300 秒 timeout、SDK/application retries=0。没有输出修补、选择或重跑。

### 运行结果

| 输入 | 来源 | VALID | Gap | 核心语义评估 |
|---|---|---|---|---|
| R2 g5 | 历史定价 | 是 | 1 MISSING | PASS |
| R2 g3 | 历史订票/人数/姓名 | 是 | 1 MISSING | PASS |
| R3 g6 | 历史定价 | 是 | 2 MISSING | PASS；历史终止 artifact 排除评分 |
| constructed-needs-revision | 构造开发样本 | 是 | 1 NEEDS_REVISION | PARTIAL_FAIL |
| constructed-should-remove | 构造开发样本 | 是 | 1 SHOULD_REMOVE | PASS |

5/5 通过结构与引用验收，产生 6 个 gap。Provider 报告总计 220,888 tokens；这是 token 使用量，不是费用估算。逐组调用耗时和 usage 见 `summary.json`，原始请求、响应及验收结果位于各组目录。

按预先确定的核心标准：

- 未新增无依据义务：4/5 通过；
- 候选经验没有强化为普适强规则：5/5 通过；
- 条件、适用范围和 epistemic status 得到保持：5/5 通过。

完整人工评分保存在 [semantic_assessment.json](../../../artifacts/methods/v18/v18_diagnosis_v2_pilot_001/semantic_assessment.json)。结构 VALID 不参与替代语义判断。

### 历史输入观察

R2 g5 从 v1 的两个 gap 收敛为一个定价 gap。Analysis 和 Gap 都保留 horizon 使用原预订价、summit 在已观察案例中对应当前可用价的关系，并明确这是工具契约未声明的候选经验。v1 中“接受实际金额可能不同，否则转人工”的 summit guard 没有再次出现。

R2 g3 保留 5 人单订合规、6 人单订不合规、7 人拆 4+3 合规的对照，但不再把它写成已证明的普适“每单最多 5 人”。Gap 明确 exact numeric boundary 未知。T024 仍留在 Analysis，没有生成姓名外观审查；行李机制不完整也没有生成额外规则。

R3 g6 的定价 gap 保留同一渠道条件和经验确定性。原始输出另有“确认后调用更新工具”的 gap；它关联旧 Simulator artifact，按正式职责边界不计入 v2 核心评分，也不作为继续 patch Prompt 的依据。原始输出未删除或改写。

### 操作边界观察

`constructed-should-remove` 正确选择 SHOULD_REMOVE。它引用整块当前规则，说明数字姓名禁令与可见 policy 冲突、两条成功工具结果否定其核心方向、缩小数字范围也无依据，并保留真正有效的 exact supplied fields 与确认要求，没有换成另一种姓名外观检查。

`constructed-needs-revision` 正确选择 NEEDS_REVISION，并保留“使用当前流程的成功 lookup 作为库存核对”的有效核心，去掉了必须做第二次独立核实的要求。但 Gap 仍声明：没有成功 lookup 或 lookup 返回 unavailable 时应转人工。来源 Analysis、policy 和轨迹没有证明转人工是必要动作，因此它保留了一个无依据 escalation obligation。该项按核心标准记为 PARTIAL_FAIL；不因操作类型正确而判为通过。

### 结论

v2 对三组历史 learner 问题有明显改善，并能在两个构造样本中区分 REPLACE 与 DELETE 的意图。但现有保守条款可能在 NEEDS_REVISION 时被缩小范围后继续保留，即使证据只支持删除该条款而不支持它在剩余条件下仍有必要。这说明语义保持仍有一个明确残留点。

本次结果支持继续实现确定性的 Compiler DELETE：Compiler 不应承担这项语义判断，只映射已验收 gap。同时，在进入正式 v18 campaign 前应决定是否用一个小版本 Prompt 调整来约束“修订时，目标规则中保留的限制也必须有证据支持”；若调整，应升级 Prompt 版本并只做定向回归，不能修改或择优重跑本次输出。

一次调用和两个构造开发样本不能证明稳定性或总体成功率。本次没有 Candidate、Monitor 或 Gate 结果。

<a id="v18-diagnosis-v3-regression-report"></a>

## v18 Diagnosis Prompt v3 六组固定输入回归

日期：2026-09-20。Prompt：`v18-group-diagnosis-3`，Prompt SHA-256 `351cad7c15c3d998fbcf30259c8c254487d1cfa44990f44c962380ffe48b36c9`。

### 冻结与边界

修改 Prompt 前，已将端到端 Pilot 当前有效 G01–G06 的 learner payload、provenance、v2 validated output 和 validation 冻结到 `experiments/methods/v18/v18_diagnosis_pilot_003/config/`。`cases.json` SHA-256 为 `7a988250d02dea5be1582da152d18c6613133ec4b2f3e36fd7bcf32691026357`；预写语义 rubric SHA-256 为 `261ad5ef144e8be4f6cb611e82d7a65b4920455197e77ba17d6b0f430165b4a4`。

冻结脚本只读取六组 Diagnosis 的 request、provenance、validated output 和 validation，不读取 Monitor 逐题结果、转移矩阵或 Gate delta。v3 输入摘要逐组与冻结 v2 输入一致。Schema、引用验证、Compiler、Editor 和 Gate 未修改。

Prompt 只增加两条通用原则：ADDRESSABLE 必须存在有证据支持且可实际执行的替代行为；无法证明覆盖、允许或适用不能自动产生核实义务、拒绝、停止、禁止或转人工。Prompt 不包含行李、保险、G03、G06 等专项规则。

### 运行结果

六组均一次调用完成，6/6 结构与引用 VALID，0 重试，总计 284,465 tokens。

| 组 | 角色 | 状态 | Gap | 语义评分 |
|---|---|---|---:|---|
| G01 | 非退化 | ADDRESSABLE | 1 | PASS |
| G02 | 非退化 | NOT_ADDRESSABLE | 0 | FAIL |
| G03 | 目标 | ADDRESSABLE | 2 | FAIL |
| G04 | 非退化 | ADDRESSABLE | 1 | PASS |
| G05 | 非退化 | NO_ISSUE | 0 | PASS |
| G06 | 目标 | ADDRESSABLE | 1 | PASS |

总计 4/6 通过；目标样本 1/2 通过；非退化样本 3/4 通过。因此 v3 当前结果不满足正式四轮实验前的语义门槛。

### 目标样本

G06 的问题已消除。v3 不再要求从可见 policy、工具或用户处证明隐藏保险覆盖并在无法证明时拒绝。输出改为一个由直接对照支持的局部经验规则：只覆盖已观察的 work-related 原因变体，以 T005 的合规拒绝和 T021/T026/T030 的非合规取消为依据；完整保险合同继续保持 unresolved。

G03 只部分改善。v3 正确保留人数规律，并把 business-class 行李问题留为 unresolved；但仍针对 basic-economy 的 2/3 件对照生成第二个 gap，要求不要提交 3 件编码并先澄清 allowance/limit。现有 policy、工具和合法交互没有提供隐藏映射，也不能确定正确的替代 tool arguments，因此该 gap 仍以未知机制产生否定性/澄清行为，按预写标准判 FAIL。

### 非退化样本

G01 保留 partner_direct 的局部 fallback 模式，并明确 consolidated 未决；G04 保留 horizon/summit 结算映射；G05 维持 NO_ISSUE，三组通过。

G02 退化。v3 正确指出 cedar 的失败只与 label 相关、没有直接观察到替代写入顺序，但因此整体判 NOT_ADDRESSABLE，删除了 v2 中带明确 tentative 和 context limit 的 cedar 局部执行假设。预写标准要求保留该已有候选规律，因此判 FAIL。这说明新增的“可执行替代行为”原则被模型解释得过窄，产生了整体保守化。

### 结论

v3 的第二条原则对 G06 有效，但第一条原则尚未稳定地区分两类情况：一类是完全缺少替代动作、会迫使 Agent 猜隐藏映射；另一类是存在可尝试的局部行为假设、只是机制和因果尚未完全确认。当前输出一方面在 G03 仍保留不可满足的澄清/禁止 gap，另一方面在 G02 过度删除候选规律。

因此不要启动正式四轮实验，也不要根据 Monitor 个案定向修改 Prompt。下一次小版本应继续只澄清这一通用边界：候选替代行为需要由组内观察或明确可枚举动作空间支持，但不要求替代行为已经在成功轨迹中直接执行；相反，若输出只能说“不要这样做、先澄清隐藏规则”，且没有可用信息源或具体替代动作，则不得生成 gap。应继续用同一六组冻结输入和同一预写 rubric 回归。

完整输出位于 `artifacts/methods/v18/v18_diagnosis_v3_pilot_001/`，人工评分位于其中的 `semantic_assessment.json`。

相关 v17/v18 回归测试 540 项通过。由于 v3 未通过语义门槛，正式 v18 freeze 未用 v3 重建；正式入口会因 `diagnosis_prompt_v18.py` 摘要漂移而拒绝启动，避免未验收 Prompt 被用于四轮实验。

<a id="v18-diagnosis-v31-regression-report"></a>

## v18 Diagnosis Prompt v3.1 回归报告

日期：2026-09-20。Prompt：`v18-group-diagnosis-3.1`，Prompt SHA-256 `5db3aabc070cbbdc20347fc912efe7c5d91b61cacd5fafc551a38b2ebf22ecf1`。

### 改动与冻结边界

本次只重写 Diagnosis Prompt 的可学习性判定段，Schema、引用校验、Compiler、Editor 和 Gate 均未修改。判定分为三步：识别有支持的选择关系、检查条件与动作是否可执行、检查输出是否依赖无来源的替代动作或信息。候选动作不要求已在成功轨迹中完整执行；有限动作集合加一次失败本身也不能选择其补集。可回答的澄清必须取得具体事实，且回答值能够映射到后续动作。明确 policy、用户约束、工具契约或观察关系支持的禁止不要求虚构替代动作。

Prompt 不包含 cedar、行李、保险、coverage 或任何组编号等专项规则。

原 G01–G06 输入和 v3 rubric 未改，rubric SHA-256 仍为 `261ad5ef144e8be4f6cb611e82d7a65b4920455197e77ba17d6b0f430165b4a4`。在修改 Prompt 前，另行冻结了五类通用边界样本与评分：机制未知但关系稳定、动作有限但无选择依据、有可回答的澄清、仅有负面结果、明确禁止依据。其 cases SHA-256 为 `b2b4da59bb444fbed706880ea2f02e6f483ffb42dc7b30d950a542036dce6fce`，rubric SHA-256 为 `f0f1e582e5449b864226cf994be24639d590c83fcdf9072f00387adfc9a69ee4`。两套评分均未使用 Monitor 逐题数据或 Gate 转移。

### 执行结果

第一次执行因未连接内网 VPN，11 次调用全部在 DNS/传输层失败，没有模型响应或 token 消耗，审计保留在 `artifacts/methods/v18/v18_diagnosis_v31_pilot_001/`。连接恢复后使用新目录执行：11/11 一次完成且结构与引用 VALID，0 重试；prompt tokens 247,423，completion tokens 75,676，总计 323,099 tokens。

原六组按未修改 rubric 为 5/6 通过：G01、G03、G04、G05、G06 PASS，G02 FAIL。G03 现在只保留人数 gap，将缺少额度映射的行李问题留在 unresolved，没有生成禁止、隐藏规则澄清或猜测参数。G06 和其余非退化组保持通过。

五个通用边界样本 5/5 通过：稳定但机制未知的关系被保留为局部候选；有限动作但无选择证据和仅有负面结果均为 NOT_ADDRESSABLE；可回答澄清被识别为可执行信息路径；有明确 policy 依据的禁止被保留。

完整人工评分见 `artifacts/methods/v18/v18_diagnosis_v31_pilot_002/semantic_assessment.json`。

### 剩余语义跳转

G02 的跳转发生在 Analysis → Addressability。Analysis 正确保留 cedar 与失败、orbit 与成功的可观察关联；Addressability 认为没有任何行为对照、查询结果、policy 或工具结果能够为 cedar 选择反向写入顺序，因此不生成 gap。v2 则把“反向顺序”作为失败顺序在二元动作空间中的未观察补集。

这与新增的通用“动作有限但没有选择依据”对照形成直接张力：该对照的预写标准明确要求不能因为一个动作失败、且只剩另一个动作，就推断补集动作。v3 的 G02 rubric 又要求保留同型的 tentative 替代顺序。此时继续增加 Prompt 条款，会把冲突隐藏在措辞里，并重新引入两端摇摆。

因此本轮不再修改 Prompt，v3.1 不进入正式 freeze，正式四轮实验仍不得启动。下一步应先在评估层明确一个统一原则：未观察的互补动作在什么额外证据下可以成为候选。确定后应先更新一套新的预写通用 rubric，再决定 Prompt 是否需要变化；原 rubric 和本次结果保持不动作为历史审计。

### 验证

相关 v17/v18 测试 543 项通过。正式四轮入口继续因冻结的 Prompt 摘要与 v3.1 不一致而拒绝启动。

<a id="v18-diagnosis-v321-aggregation-report"></a>

## v18 Diagnosis 统一聚合边界回归

日期：2026-09-20。最终测试 Prompt：`v18-group-diagnosis-3.2.1`，SHA-256 `24d04f4ed6f8b7542633f7aea8f0745bbba1cd26fbd7be76cd436cddfa6bcfd6`。

### 预先冻结的统一 rubric

在修改 Prompt 前，新建 `experiments/methods/v18/v18_diagnosis_pilot_005/config/`，冻结统一三态语义、逐关系判断后汇总的 group-level 规则，以及一对通用聚合对照。rubric SHA-256 为 `46543c046f046942d1bcfaa93cf209e05795e3eebaae605e41e593b28652b37a`。没有使用 Monitor 逐题结果或 Gate 转移数据。

统一规则要求：先独立判断组内可分离的经验关系；至少一个合法 gap 即为 ADDRESSABLE；unresolved 分支不移除合法 gap；排除一个动作不等于支持其补集；所有 Success/Compliance 都为真时不得仅因 Parent 未记录成功配方而制造 gap。

配对对照包含相同的可学习关系。第二个输入只增加一个没有替代依据的独立失败分支。两份输出应保留相同局部 gap 的条件、动作、范围和不确定性，新增失败只能进入 unresolved。

### Prompt 审查与最小修改

v3.1 已写有“混合组中不可学习问题不移除其他 gap”，但 ADDRESSABLE 仍以整组 observed problem 为中心，没有明确逐关系判断再汇总，也没有说明正向局部规律是否必须修复另一个失败分支。因此更新为 v3.2。

v3.2 首轮 13/13 结构 VALID、0 重试、362,211 tokens。配对对照通过，但 G02 仍为 NOT_ADDRESSABLE，G05 又把全成功/合规行为写成新规则；通用 stable-relation 还为没有替代动作的失败另建 warning gap。基于同一冻结 rubric，v3.2.1 仅澄清三点：全成功/合规组使用 NO_ISSUE；有问题的混合组可以保存不修复另一 unresolved 分支的正向局部规律；只有失败且没有独立限制依据的分支不能生成 warning gap。

Prompt 不包含 cedar、行李、保险、coverage、组编号或其他领域专项规则。Schema、引用校验、Compiler、Editor 和 Gate 均未修改。

### v3.2.1 真实模型结果

13/13 调用一次完成且结构、引用 VALID，0 重试，总计 350,037 tokens。

- 原六组 6/6 通过。G02 只生成观察到的正向局部顺序 gap，失败分支 unresolved；G05 为 NO_ISSUE。
- 聚合配对 2/2 通过。两份输出各有一个同范围、同动作、同有限确定性的局部 gap；新增 unresolved 分支没有产生额外 gap。
- 既有五类通用边界中四类通过。

完整评分见 `artifacts/methods/v18/v18_diagnosis_v321_pilot_002/semantic_assessment.json`。

### 尚未解决的 rubric 冲突

既有 `boundary-negative-only` 预设 NOT_ADDRESSABLE，但输入的 visible policy 同时规定只有在 applicable setting 已知时才调用工具，并明确没有来源提供该值。统一 rubric 又规定明确 visible policy 可以独立支持限制。v3.2.1 因而生成“不猜参数、不调用”的局部 gap，同时把正确替代值留在 unresolved。

这不是继续增删 Prompt 措辞可以一致解决的问题：若服从旧样本标签，会破坏“明确 policy 可支持限制”；若服从统一证据规则，就必须修订该旧对照的输入或 rubric。为避免让 Prompt 迎合混杂样本，先将其记为 `RUBRIC_CONFLICT`，不据此修改 Prompt。

### 冲突裁定与最终结论

随后在新调用前冻结 `experiments/methods/v18/v18_diagnosis_pilot_006/config/`，将混杂样本拆成轨迹和工具完全相同、只改变 visible policy 的两个正交对照：纯 negative-only 不含独立限制依据；explicit-prerequisite 明确要求仅在用户提供参数时执行，并规定缺失时的响应。

Prompt 保持 v3.2.1 不变。两组均一次 VALID、0 重试、合计 17,890 tokens：纯负面组为 NOT_ADDRESSABLE、0 gap；明确前置条件组为 ADDRESSABLE、1 个窄限制 gap，替代参数保持 unresolved。评分见 `artifacts/methods/v18/v18_diagnosis_v321_boundary_resolution_002/semantic_assessment.json`。

最终有效语义语料为 14/14 通过：原六组 6/6，保留的旧通用边界 4/4，替换后的正交边界 2/2，聚合配对 2/2。Prompt v3.2.1 达到进入正式 freeze 的语义门槛。旧 `boundary-negative-only` 保留为历史审计，但因同时测试负面证据和明确 policy prerequisite，不再计入最终通过率。

本步不更新已有正式四轮 freeze，也不启动正式实验；现有入口继续因 Prompt 摘要漂移而拒绝运行。下一步应创建新的、不可覆盖的正式 freeze，并完成无模型预检后再启动四轮实验。

相关 v17/v18、历史 Pilot 与新增聚合/边界裁定测试共 550 项通过。v17 差异摘要与本步开始时一致。现有正式入口已实测因 `diagnosis_prompt_v18.py` 摘要漂移而拒绝启动。

本步实际进行了 28 次模型调用、0 重试，合计 730,138 tokens：v3.2 13 次、v3.2.1 13 次、边界裁定 2 次。所有失败与中间版本产物均保留，未覆盖历史审计。
