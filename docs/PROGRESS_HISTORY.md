# 阶段进展与历史阅读记录

[返回文档总索引](README.md)

Benchmark v5 最新S-A状态：[落地核验与最小实现报告](benchmarks/v5/SA.md#benchmark-v5-sa-offline-report)、[业务契约](benchmarks/v5/SA.md#benchmark-v5-sa-contract)（2026-10-12）。隔离批式固化排程原型已完成，25项测试通过、57条归档轨迹重放/重评分一致，10806个历史文件摘要不变。8批公开记录可识别声明的64项机制族，但一个不读取历史经验的简单组合启发式通过全部7个开发样例。因此当前样例降为工程/执行锚点，不进入Flash校准、不批量扩题；没有模型调用或最终Test，不宣称Success学习挑战已成立。[代码入口](../benchmarks/standalone/editions/v5/sa/README.md)。

Benchmark v5 最新机制筛选：[新机制候选与 Success 优先筛选方案](benchmarks/v5/MECHANISM_REVIEW.md#benchmark-v5-mechanism-screening)（2026-10-11）。完成3个S与1个不同结构G的五问审查，覆盖业务依据、知识缺口、反馈、可辨识性、合法捷径与迁移。首选“小批量作业排程中的状态依赖换型与批处理耗时”进入有条件单原型验证；结算候选暂缓、资源吞吐候选后备、变更后依据复用G待证。仅文档筛选，没有实现新环境、生成任务或调用实验模型；选中不等于学习价值或正式准入已获证明。

Benchmark v5 最新工程状态：[真实Skill两轮闭环报告](benchmarks/v5/SC.md#benchmark-v5-sc-closed-loop-report)（2026-10-11）。单次输出提高至16384后，Flash完成10条执行和2次真实更新，S0→S1→S2已跑通，无截断/超预算；重放、评分与Train来源隔离验证通过。Monitor的S/C/SC分别为S0=2/2、2/2、2/2，S1=2/2、1/2、1/2，S2=1/2、2/2、1/2，保留退化结果，不宣称正式进化效果。未使用最终Test；下一阶段优先扩展并验证S/G/I/K学习机制。旧截断与VPN失败记录保留。

Benchmark v5 统一评价与此前截断记录：[简化协议](benchmarks/v5/SC.md#benchmark-v5-sc-protocol)、[历史重评与最小工程验证报告](benchmarks/v5/SC.md#benchmark-v5-sc-report)（2026-10-11）。新增独立S/C评价器，必要依据记录纳入C；LG1历史轨迹单独版本化重评。该历史报告记录前两步完成、工程试跑因推理截断尚未生成S1/S2的阶段（50项测试通过不等于真实闭环通过）；后续真实闭环状态见上方最新报告。不使用最终Test、不宣称正式进化效果。随后先扩展并验证S/G/I/K学习机制，再冻结v5开展正式实验。下列旧协议和结果作为历史记录保留。

Benchmark v5 第3—5部分：[学习型环境与最小校准报告](benchmarks/v5/LEARNING.md#benchmark-v5-learning-report)（2026-10-11）。已实现隔离LS1/LG1环境及S/C/P评价、方法无关固定经验协议，完成40次Flash主执行与4次独立接口复核；另4格因LS1归纳失败未执行。当前接口/评价器0.2通过38项测试，全部44条真实轨迹可重放。LS1降为执行/账务锚点，LG1保留学习型候选但未正式准入；预算、接口和评分问题及修正均独立记录。[包与复现入口](../experiments/benchmarks/v5/learning/README.md)。

Benchmark v5 当前路线：[学习型设计与实现规格](benchmarks/v5/LEARNING_SPEC.md#benchmark-v5-learning-spec)（Learning Draft 0.1，2026-10-10）。完成第1—2部分：以可学习的未知业务知识为核心，首批LS1售后结算/资金恢复（S）与LG1凭证替代/适用范围（独立G）；明确公开权限、训练反馈、有限机制可辨识性及精确边界证据、Train/Dev/Test与新世界适应隔离、评价和准入。仅参考世界完成纸面公式核算，未实现环境、生成任务或调用模型；业务代表性、工程执行与真实学习效果仍待验证。历史公开规则实验和以下报告保留原结论。

Benchmark v5 最新试跑与去留：[第3—4项最小试跑报告](benchmarks/v5/DECISION_PROBE.md#benchmark-v5-minimal-probe-report)及[运行前冻结协议](benchmarks/v5/DECISION_PROBE.md#benchmark-v5-minimal-probe-protocol)。仅deepseek-v4-flash：D1三个条件9/9、D2两个条件6/6，无工具错误、截断或超预算，15份轨迹精确重放/重评分一致。两者退出复杂候选扩展，保留基础能力锚点候选；D3待契约与业务依据，D4后备，均未运行。638个登记保护文件无变化，未改v4/原v5原型；新增独立[试跑目录](../experiments/benchmarks/v5/decision_probe/README.md)。

Benchmark v5 最新证据与下一步：[决策困难证据审计与试跑候选](benchmarks/v5/MECHANISM_REVIEW.md#benchmark-v5-decision-difficulty-evidence)（2026-10-10）。完成既有证据审计与候选选择：汇总四轮360条Monitor结果、36个历史任务对及90条v5结果，重点审阅50份历史轨迹和5份Flash执行。优先准备共享资金规划、条件报价分支两个S候选；独立G在规则/终态补齐后再试，地址联动为后备。当前无可直接准入的复杂I/K证据；下一次只用deepseek-v4-flash。本轮没有新模型调用、任务生成或运行代码修改。

Benchmark v5：[设计规格草案](benchmarks/v5/DESIGN.md#benchmark-v5-design-draft)（Draft 0.3，2026-10-10）。已修订S2/G1/G2/I2/K2的资金、凭证、退款、代理付款和恢复起点契约；原K1重分类为G3中等合规任务，组合为2S+3G+2I+1K。含最新覆盖矩阵、义务/评分、合法路径与第13节修订决定。八个标准具备工程规格；S2/G2/I1/K2已实现，其他四个未实现；第6步首轮模型校准已完成，难度区分性未正式准入；v4保持不变。

Benchmark v5 第4步：[原型准入审阅报告](benchmarks/v5/PROTOTYPES.md#benchmark-v5-prototype-admission-review)。第1—14节保留Draft 0.2的历史审阅，第15节记录Draft 0.3关键缺口闭合及纸面复核。工程可行性、外部业务真实性和真实Agent区分能力仍待验证。

Benchmark v5 第5步：[隔离原型与工程验证报告](benchmarks/v5/PROTOTYPES.md#benchmark-v5-engineering-validation)。四个原型、46条预期评分路径、29项契约测试和信息边界/业务组件核验；[运行入口](../benchmarks/standalone/editions/v5/README.md)。仅工程验证，无模型成绩、无v21接入。

Benchmark v5 第6步：[真实Agent校准报告](benchmarks/v5/CALIBRATION.md#benchmark-v5-calibration-report)及[固定协议](benchmarks/v5/CALIBRATION.md#benchmark-v5-calibration-protocol)。历史三个候选模型完成72次主实验与独立18次预算诊断；G2/I1/K2饱和，S2受截断及公开语义影响，另发现两次代理输出超请求预算。原始成绩与敏感性分析并列保留，尚无稳定能力排序；后续安排以上方最新证据审计为准，不继续三模型筛选。

建议按照下面的顺序阅读：

| 顺序 | 文档 | 用途 |
|---:|---|---|
| 1 | [`00_README_FIRST.md`](00_README_FIRST.md) | 学生启动规则、前三天目标与安全底线 |
| 2 | [`01_PROJECT_NARRATIVE.md`](01_PROJECT_NARRATIVE.md) | 核心研究问题、假设、边界与 Go / No-Go |
| 3 | [`05_TAU_BENCH_POLICY_COMPLIANCE.md`](05_TAU_BENCH_POLICY_COMPLIANCE.md) | 区分τ-bench policy、task reward与Process Verifier |
| 4 | [`02_HANDS_ON_TODO.md`](02_HANDS_ON_TODO.md) | 10 天研究型 POC 执行计划 |
| 5 | [`03_PAPERS_AND_CODE_MAP.md`](03_PAPERS_AND_CODE_MAP.md) | 核心论文、代码仓库与阅读问题 |
| 6 | [`04_EXPERIMENT_LOG.md`](04_EXPERIMENT_LOG.md) | 环境、实验、轨迹、Skill 修改与决策记录 |
| 7 | [`05_AUTONOMOUS_GSE.md`](05_AUTONOMOUS_GSE.md) | 三步有界自主Governed Skill Evolution的方法与已完成结果 |
| 8 | [`06_ST_WEBAGENTBENCH_INTERACTIVE.md`](06_ST_WEBAGENTBENCH_INTERACTIVE.md) | 基于隐藏UserScenario的交互式benchmark变体、运行配置与补充指标 |
| 9 | [`V18_SKILL_EVOLUTION_DESIGN.md`](methods/v18/DESIGN.md#v18-skill-evolution-design) | 基于 v17 四轮实验的 v18 设计：语义保持、Simulator 修复与 DELETE |
| 10 | [`V18_DIAGNOSIS_CONTRACT.md`](methods/v18/CONTRACTS.md#v18-diagnosis-contract) | v18 Diagnosis 三类 gap、删除证据门槛与独立验收契约 |
| 11 | [`V18_DIAGNOSIS_PILOT_REPORT.md`](methods/v18/DIAGNOSIS_VALIDATION.md#v18-diagnosis-pilot-report) | v18 Prompt 首次三组固定输入结果及未解决的语义问题 |
| 12 | [`V18_DIAGNOSIS_V2_PILOT_REPORT.md`](methods/v18/DIAGNOSIS_VALIDATION.md#v18-diagnosis-v2-pilot-report) | Prompt v2 五组固定输入、REPLACE/DELETE 边界与核心语义评分 |

文档属于研究 artifact。实质修改 narrative、policy interpretation、数据、方法或验收条件时，必须在 `04_EXPERIMENT_LOG.md` 的 Decision Log 中说明日期、证据和原因。

v18 第 4 步：[Compiler 契约与 DELETE 离线验证](methods/v18/CONTRACTS.md#v18-compiler-contract)。

v18 第 5 步：[Editor 与确定性文本应用](methods/v18/CONTRACTS.md#v18-editor-contract)。

v18 第 6 步：[完整调度、冻结与恢复](methods/v18/EXPERIMENTS.md#v18-formal-experiment)。

v18 Diagnosis 统一聚合边界：[v3.2.1 固定输入回归](methods/v18/DIAGNOSIS_VALIDATION.md#v18-diagnosis-v321-aggregation-report)。

v18 Diagnosis v3.1：[通用可学习性边界与 6+5 固定输入回归](methods/v18/DIAGNOSIS_VALIDATION.md#v18-diagnosis-v31-regression-report)。

v18 第 7 步：[单轮端到端真实模型 Pilot](methods/v18/EXPERIMENTS.md#v18-end-to-end-pilot-report)。

v18 Diagnosis v3：[六组固定输入语义回归](methods/v18/DIAGNOSIS_VALIDATION.md#v18-diagnosis-v3-regression-report)。

v18 Benchmark：[Skill-critical Joint Family 冻结准入契约](methods/v18/JOINT_ADMISSION.md#v18-joint-family-admission-contract)与[候选机制 shortlist](methods/v18/JOINT_ADMISSION.md#v18-joint-family-candidate-mechanisms)。

[v18 × benchmark v4 正式协议与 run/resume 命令](methods/v18/EXPERIMENTS.md#v18-benchmark-v4-formal-protocol)。

v19 第 1 步：[数据契约与流程边界](methods/v19/DATA_CONTRACT.md#v19-data-contract-and-flow)及[构造示例与验收映射](methods/v19/DATA_CONTRACT.md#v19-data-contract-examples)。仅完成契约设计，后续实现使用独立 v19 版本，不修改 v18。

v19 第 2 步：[edit 账本与跨轮追踪实现](methods/v19/ATTRIBUTION.md#v19-edit-tracking)。独立的确定性账本、来源/版本校验和历史视图；尚未接入回放或 Memory 模型。

v19 第 3 步：[Candidate Evolution 配对回放](methods/v19/ATTRIBUTION.md#v19-evolution-replay)。完整训练集配对、Parent 复用、私有检查点恢复及 Level-0 学习侧投影；尚未接入归因、Memory 或 campaign。

v19 第 4 步：[edit-level 效果归因](methods/v19/ATTRIBUTION.md#v19-edit-attribution)。归因 Prompt、完整 edit 覆盖、证据引用与冲突校验及可恢复阶段产物；结构验收不代表因果结论成立，尚未接入 Memory 或 campaign。

v19 第 5 步：[持续记忆的保存、更新和检索](methods/v19/MEMORY.md#v19-persistent-memory)。不可变完整证据归档、记忆头与保留 Skill 原子提交、当前规则绑定重建及带预算的证据检索；尚未接入 Diagnosis 或 campaign。

v19 第 6 步：[Memory 驱动 Diagnosis 与 Skill 生成](methods/v19/MEMORY.md#v19-memory-generation)。当前经验与历史观察分源引用、逐 edit 显式复查、当前 Parent 重新授权、受限 Editor 与跨轮来源保留；尚未运行真实模型或第 7 步 campaign。

v19 第 7 步：[独立调度、多轮工程验证与 Pilot](methods/v19/CAMPAIGNS.md#v19-campaign)。独立 run/resume、完整配对、私有 Monitor Gate 和原子记忆提交；真实 Pilot 进展与工程 fixture 结果分开记录。

v19 职责拆分第 1 步：[Current Diagnosis 与 Memory Review 独立契约](methods/v19/CAMPAIGNS.md#v19-separated-discovery-review)。当前发现与历史证据状态分离；含严格校验、原始事件访问和稳定 ID，尚未接入 Reconciliation 或新调度。

v19 职责拆分第 2 步：[逐项 Reconciliation 与 v18 Compiler/Editor 适配](methods/v19/FUSION_AND_RECONCILIATION.md#v19-reconciliation)。完整来源处置、PROPOSE gap 校验、冲突拒绝及 Candidate provenance；尚未切换 campaign。

v19 职责拆分第 3 步：[新闭环、恢复协议与独立 Pilot](methods/v19/CAMPAIGNS.md#v19-separated-campaign)。新 CLI 默认拆分流程，独立目录运行；审阅与处置随账本归档并在下一轮检索。

- [v19 轻量 Issue Fusion：契约、覆盖规则与阶段边界](methods/v19/FUSION_AND_RECONCILIATION.md#v19-issue-fusion)

- [v19 逐提案 Evidence Review：局部证据、有限补充与恢复](methods/v19/EVIDENCE_REVIEW.md#v19-evidence-review)

- [v19 局部核验与编译闭环](methods/v19/MEMORY.md#v19-local-generation)：第三步实现、独立单次运行及完整闭环命令。

- [v19 单次 Evidence Review](methods/v19/EVIDENCE_REVIEW.md#v19-one-pass-evidence-review)：确定性证据包、无 MORE_CONTEXT 的执行协议与运行命令。

- [Pair Attribution v19.2](methods/v19/ATTRIBUTION.md#v19-pair-attribution)：逐 pair 观察、确定性聚合与新旧 Memory 兼容；旧全局 Attribution 保留。

- [v19 run / resume](methods/v19/CAMPAIGNS.md#v19-run-resume)：当前流程统一入口、网络失败自动归档恢复和使用示例。

v20 第 1 步：[最小 Memory 契约与独立边界](methods/v20/MEMORY.md#v20-memory-contract)及[构造示例与验收映射](methods/v20/MEMORY.md#v20-memory-examples)。按问题维护可更新的尝试记录，由 Issue Fusion 直接消费简明 Memory；冻结 v19，尚未接入 v20 Issue Fusion 或开展实验。

v20 第 2 步：[问题 Memory 保存与增量更新](methods/v20/MEMORY.md#v20-memory-update)。已实现独立存储、稳定问题/尝试身份、部分更新、CAS 提交与恢复。

v20 第 3 步：[直接消费问题 Memory 的 Issue Fusion](methods/v20/ISSUE_FUSION.md#v20-issue-fusion)。当前 Findings、问题/尝试简明状态和 Parent 规则在独立只读契约中融合；支持当前问题、已部署方案纠偏和纯历史方向，尚未接入局部 Evidence Review 或真实 campaign。

v20 第 4 步：[局部 Evidence Review 与修改生成](methods/v20/ISSUE_FUSION.md#v20-issue-fusion)。已实现问题级证据闭包、局部 Review、独立 v20 编辑计划与 Candidate 生成。

v20 第 5 步：[多轮闭环与离线验证](methods/v20/ISSUE_FUSION.md#v20-issue-fusion)。已接入独立 campaign head、可恢复的 Memory/retained Skill 发布，以及 v19 产物的只读结构验证和保守转换。

v20 第 6 步：[独立 Pilot 与匹配对照实验](methods/v20/ISSUE_FUSION.md#v20-issue-fusion)。先验证独立 Pilot 的工程闭环，再在相同任务 manifest、seed 和指标规则下运行 v20 Memory 与 no-memory 对照；两者均不把一次运行直接解释为因果结论。

v20 第 7 步（当前）：[冻结 Pilot、Benchmark 适配与统一 run/resume](methods/v20/ISSUE_FUSION.md#v20-issue-fusion)。已冻结 benchmark v4 配置，接入真实 round factory、post-generation、train/monitor split 适配器和零模型调用 preflight；真实模型 Pilot 入口已具备但尚未启动。

v21 第 1 步：[双维归因认识的跨轮学习契约](methods/v21/METHOD.md#v21-method-contract)。将 Memory 作为任务成功与程序合规认识跨轮积累、修订和复用的载体，保留真实修改后的证据学习；不新增独立 Agent、重复 Review、状态体系或强制逐 edit 分析。

v21 第 2 步：[接通修改后学习侧证据](methods/v21/EVIDENCE.md#v21-post-modification-evidence)。已实现完整回放校验、安全投影、历史归档与局部回查，并用真实 v20 产物离线验证。

v21 第 3 步：[从修改后证据更新 Memory](methods/v21/MEMORY.md#v21-memory-update)。已实现单次语义更新接口、原始事件引用校验、稳定身份与增量合并、派生档案和显式恢复。114 项相关测试通过，真实证据请求预检完成；未调用真实更新模型、发布活动 head 或启动完整 v21 自进化。

v21 第 4 步：[让双维认识参与下一轮修改](methods/v21/MEMORY.md#v21-memory-consumption)。已接通更新后的 Memory → Fusion → 局部 Review → 既有 Compiler/Editor，并保留跨轮证据来源。141 项相关测试通过，历史真实产物预检完成；完整 campaign、原子发布及真实两轮 Pilot 尚待第 5 步。

v21 输入优化：[短引用与无损内容复用](methods/v21/FUSION_AND_INPUT.md#v21-input-optimization)。同批证据下 Memory 更新由 238,240 降至 84,051 个代理 token；历史 Review 范围降至 20,625–61,025。原始事件、配对及反证均保留并可精确还原，157 项相关回归通过；未调用真实模型。

v21 补强第 1 步：[修改后新增退化的证据覆盖](methods/v21/REGRESSION.md#v21-regression-coverage)。完整扫描当前回放两维标签，自动补入此前引用未覆盖的退化配对及双侧原文。真实历史材料的默认输入由 6 组扩为 9 组，覆盖 T005/T022/T036；当前代理输入 99,405 tokens。没有新增 Agent、Review 或持久化状态；未调用真实模型。

v21 补强第 2 步：[issue 写回与复查边界](methods/v21/MEMORY.md#v21-issue-boundaries)。固定原问题范围，区分 issue 的显式来源与共享 edit 带入的上下文，防止后者自动继承为本问题的新评价；Fusion/Review 按原问题复查。保留共享证据和反证，当前 Memory 代理输入 99,761 tokens；未调用真实模型。

v21 补强第 3 步：[简明当前认识与历史消费](methods/v21/MEMORY.md#v21-current-understanding)。在同一次 Memory 更新中维护 issue 综合认识；Fusion 读取认识和尝试目录，Review 按需打开旧尝试并保留已知反例及历史退化。完整历史留在档案，旧记录无摘要时保持完整读取；未调用真实模型。

v21 小规模验证第 1 步：[案例与判定依据](methods/v21/VALIDATION_CASES.md#v21-small-validation-cases)。冻结行李计费、多人拆单、保障条件不明三组真实历史材料，分别检查双维冲突、反例与因果不确定性、当前条款覆盖及合理 NO_EDIT。保留 2,000 字符硬限制；仅完成材料准备，下一步先验证真实模型的决策使用，再决定是否最小强化，随后接通完整调度与恢复。

v21 小规模验证第 2 步：[真实模型局部对照报告](methods/v21/VALIDATION_CASES.md#v21-local-comparison-report)。现有入口完成旧历史与 Replay 更新后 Memory 的两组消费，计入失败共 28 次真实调用。三例最终均 NO_EDIT，未证明修改决策改善；暴露行李退化配对未跨轮带入、已加载正面证据利用不足及重复提案开销。2,000 字符限制和运行源码未改，未新增 Replay 或发布活动 Skill/Memory。

v21 实验后优化第 1 步：[退化证据的跨轮保留](methods/v21/REGRESSION.md#v21-regression-retention)。强化同次 Memory 更新的有界观察与双侧引用要求，保存独立的来源保留核查，并用原实验响应复现 T009 未关联和 T034 单侧引用。210 项相关测试通过；不自动分配 issue、不补写历史认识、不放宽 2,000 字符限制，未新增真实模型调用。

信用卡 v2 的设计、配置、运行适配器和预检产物已迁移到 [`dataset_8bucket_1200_skill_evlaution`](</Users/didi/Desktop/dataset_8bucket_1200_skill_evlaution/docs/V2_CURRENT_PLUS_MEMORY_DESIGN.md>)，信用卡专用文件不放在本仓库。

v21 实验后优化第 2 步：[Evidence Review 证据比较](methods/v21/EVIDENCE.md#v21-evidence-comparison)。Review 提示升为 v21.5，在原有理由中比较相关正反证据、实际行为与适用条件，区分观察和假设，保留有依据的 NO_EDIT。三组真实输入不变，每次增加 387 个代理 token；真实模型效果待后续验证。

v21 实验后优化第 3 步：[Fusion 提案依据](methods/v21/FUSION_AND_INPUT.md#v21-fusion-proposal-basis)。Fusion 提示升为 v21.4，要求针对当前 Skill 的有依据行为缺陷提出有限方向；仅有失败标签或泛泛复查愿望时允许 NO_EDIT，并保留问题归属。两组真实输入不变，每次增加 386 个代理 token；Review 保持 v21.5，真实效果待分阶段验证。

v21 实验后优化第 4 步：[分阶段真实模型复验](methods/v21/VALIDATION_RESULTS.md#v21-staged-validation-report)。完成 6 次真实调用，5 次通过结构校验、1 次 Fusion 引用失败，共 416,122 tokens。Memory 本次补齐 T009/T013/T034 双侧引用与完整回查；行李 Review 仍漏回应已加载正面观察，Fusion 送审减少但语义质量未证明改善。未自动重试、串联、Replay 或发布，尚不满足完整调度的验证前提。

v21 语义定向修订：[Review 比较与 Fusion 判断](methods/v21/VALIDATION_CASES.md#v21-semantic-followup)。经 6 次真实调用，任务/操作原文对照使行李 Review 首次回应此前遗漏的正面观察；未奏效的轨迹重排和额外提示已撤回。Fusion 调整后两组结果均有效，但部分判断仍有争议。217 项回归通过，累计 299,372 tokens；不增加 Agent 或复查流程，未执行 Editor/Replay。


v21 两类语义验收：[已知问题修复与跨问题迁移](methods/v21/VALIDATION_RESULTS.md#v21-semantic-acceptance)。冻结运行机制，新增 5 次真实 Review 并复核旧 Fusion，合计 201,938 tokens。行李证据遗漏本次未复现但拒绝理由部分充分，地址局部修改有依据，姓名仍把用户明确字段的重叠泛化为强制再次确认，两个开发集迁移案例的 NO_EDIT 有依据。整体未全部通过；未执行 Editor/Replay 或修改运行代码。


v21 缺陷依据调整：[Fusion / Review 的最小修改](methods/v21/EVIDENCE.md#v21-defect-grounding)。Fusion/Review 提示升为 v21.6/v21.9，要求原文可以推翻上游缺陷假设，新增程序义务须有依据，同时保留对真实偏差的有限修改。七份固定输入不变，代理 token 分别增加 83/180；59 项工程测试通过，尚未真实模型复验。


v21 三步真实验证：[姓名/地址与迁移检查](methods/v21/VALIDATION_RESULTS.md#v21-grounding-validation)。冻结 Fusion v21.6 / Review v21.9，完成 1 次 Fusion 与实际提案触发的 3 次 Review，共 107,097 tokens。姓名用原文推翻缺陷并 NO_EDIT，地址保留有限修改；代金券在 Fusion 停止，航班识别了计算基准问题但停止/转人工授权仍部分充分。开发集内单次验证，未执行 Editor/Replay，未改 Prompt。


v21 单轮真实闭环：[完整验证报告](methods/v21/VALIDATION_RESULTS.md#v21-closed-loop-validation)。真实 Memory → Fusion → Review → Editor → 36 组 Replay → Memory 已执行；成功 27→23、合规 34→35，结构通过而语义部分通过。Memory 正确认识未执行验证和非因果改善，但遗漏直接相关的跨案例航班退化。未改 Prompt 或发布版本。


v21 双维证据修订：[四步定位与跨案例复验](methods/v21/EVIDENCE.md#v21-evidence-revision)。仅调整 Memory 配对证据呈现，补入各自用户原文、调用及双维标签；保留 Issue—Attempt 与原语义 Prompt。两版共 15 次真实调用、1,253,924 tokens，131 项工程测试通过。第一版错误生日归因在第二版未复现，但姓名缺陷判断和问题边界仍有语义失败，整体部分通过，未执行 Editor/Replay 或发布。
