# 文档索引

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
| 9 | [`V18_SKILL_EVOLUTION_DESIGN.md`](V18_SKILL_EVOLUTION_DESIGN.md) | 基于 v17 四轮实验的 v18 设计：语义保持、Simulator 修复与 DELETE |
| 10 | [`V18_DIAGNOSIS_CONTRACT.md`](V18_DIAGNOSIS_CONTRACT.md) | v18 Diagnosis 三类 gap、删除证据门槛与独立验收契约 |
| 11 | [`V18_DIAGNOSIS_PILOT_REPORT.md`](V18_DIAGNOSIS_PILOT_REPORT.md) | v18 Prompt 首次三组固定输入结果及未解决的语义问题 |
| 12 | [`V18_DIAGNOSIS_V2_PILOT_REPORT.md`](V18_DIAGNOSIS_V2_PILOT_REPORT.md) | Prompt v2 五组固定输入、REPLACE/DELETE 边界与核心语义评分 |

文档属于研究 artifact。实质修改 narrative、policy interpretation、数据、方法或验收条件时，必须在 `04_EXPERIMENT_LOG.md` 的 Decision Log 中说明日期、证据和原因。

v18 第 4 步：[Compiler 契约与 DELETE 离线验证](V18_COMPILER_CONTRACT.md)。

v18 第 5 步：[Editor 与确定性文本应用](V18_EDITOR_CONTRACT.md)。

v18 第 6 步：[完整调度、冻结与恢复](V18_FORMAL_EXPERIMENT.md)。

v18 Diagnosis 统一聚合边界：[v3.2.1 固定输入回归](V18_DIAGNOSIS_V321_AGGREGATION_REPORT.md)。

v18 Diagnosis v3.1：[通用可学习性边界与 6+5 固定输入回归](V18_DIAGNOSIS_V31_REGRESSION_REPORT.md)。

v18 第 7 步：[单轮端到端真实模型 Pilot](V18_END_TO_END_PILOT_REPORT.md)。

v18 Diagnosis v3：[六组固定输入语义回归](V18_DIAGNOSIS_V3_REGRESSION_REPORT.md)。

v18 Benchmark：[Skill-critical Joint Family 冻结准入契约](V18_JOINT_FAMILY_ADMISSION_CONTRACT.md)与[候选机制 shortlist](V18_JOINT_FAMILY_CANDIDATE_MECHANISMS.md)。

[v18 × benchmark v4 正式协议与 run/resume 命令](V18_BENCHMARK_V4_FORMAL_PROTOCOL.md)。

v19 第 1 步：[数据契约与流程边界](V19_DATA_CONTRACT_AND_FLOW.md)及[构造示例与验收映射](V19_DATA_CONTRACT_EXAMPLES.md)。仅完成契约设计，后续实现使用独立 v19 版本，不修改 v18。

v19 第 2 步：[edit 账本与跨轮追踪实现](V19_EDIT_TRACKING.md)。独立的确定性账本、来源/版本校验和历史视图；尚未接入回放或 Memory 模型。

v19 第 3 步：[Candidate Evolution 配对回放](V19_EVOLUTION_REPLAY.md)。完整训练集配对、Parent 复用、私有检查点恢复及 Level-0 学习侧投影；尚未接入归因、Memory 或 campaign。

v19 第 4 步：[edit-level 效果归因](V19_EDIT_ATTRIBUTION.md)。归因 Prompt、完整 edit 覆盖、证据引用与冲突校验及可恢复阶段产物；结构验收不代表因果结论成立，尚未接入 Memory 或 campaign。

v19 第 5 步：[持续记忆的保存、更新和检索](V19_PERSISTENT_MEMORY.md)。不可变完整证据归档、记忆头与保留 Skill 原子提交、当前规则绑定重建及带预算的证据检索；尚未接入 Diagnosis 或 campaign。

v19 第 6 步：[Memory 驱动 Diagnosis 与 Skill 生成](V19_MEMORY_GENERATION.md)。当前经验与历史观察分源引用、逐 edit 显式复查、当前 Parent 重新授权、受限 Editor 与跨轮来源保留；尚未运行真实模型或第 7 步 campaign。

v19 第 7 步：[独立调度、多轮工程验证与 Pilot](V19_CAMPAIGN.md)。独立 run/resume、完整配对、私有 Monitor Gate 和原子记忆提交；真实 Pilot 进展与工程 fixture 结果分开记录。

v19 职责拆分第 1 步：[Current Diagnosis 与 Memory Review 独立契约](V19_SEPARATED_DISCOVERY_REVIEW.md)。当前发现与历史证据状态分离；含严格校验、原始事件访问和稳定 ID，尚未接入 Reconciliation 或新调度。

v19 职责拆分第 2 步：[逐项 Reconciliation 与 v18 Compiler/Editor 适配](V19_RECONCILIATION.md)。完整来源处置、PROPOSE gap 校验、冲突拒绝及 Candidate provenance；尚未切换 campaign。

v19 职责拆分第 3 步：[新闭环、恢复协议与独立 Pilot](V19_SEPARATED_CAMPAIGN.md)。新 CLI 默认拆分流程，独立目录运行；审阅与处置随账本归档并在下一轮检索。

- [v19 轻量 Issue Fusion：契约、覆盖规则与阶段边界](V19_ISSUE_FUSION.md)

- [v19 逐提案 Evidence Review：局部证据、有限补充与恢复](V19_EVIDENCE_REVIEW.md)

- [v19 局部核验与编译闭环](V19_LOCAL_GENERATION.md)：第三步实现、独立单次运行及完整闭环命令。

- [v19 单次 Evidence Review](V19_ONE_PASS_EVIDENCE_REVIEW.md)：确定性证据包、无 MORE_CONTEXT 的执行协议与运行命令。

- [Pair Attribution v19.2](V19_PAIR_ATTRIBUTION.md)：逐 pair 观察、确定性聚合与新旧 Memory 兼容；旧全局 Attribution 保留。

- [v19 run / resume](V19_RUN_RESUME.md)：当前流程统一入口、网络失败自动归档恢复和使用示例。

v20 第 1 步：[最小 Memory 契约与独立边界](V20_MEMORY_CONTRACT.md)及[构造示例与验收映射](V20_MEMORY_EXAMPLES.md)。按问题维护可更新的尝试记录，由 Issue Fusion 直接消费简明 Memory；冻结 v19，尚未接入 v20 Issue Fusion 或开展实验。

v20 第 2 步：[问题 Memory 保存与增量更新](V20_MEMORY_UPDATE.md)。已实现独立存储、稳定问题/尝试身份、部分更新、CAS 提交与恢复。

v20 第 3 步：[直接消费问题 Memory 的 Issue Fusion](V20_ISSUE_FUSION.md)。当前 Findings、问题/尝试简明状态和 Parent 规则在独立只读契约中融合；支持当前问题、已部署方案纠偏和纯历史方向，尚未接入局部 Evidence Review 或真实 campaign。

v20 第 4 步：[局部 Evidence Review 与修改生成](V20_ISSUE_FUSION.md)。已实现问题级证据闭包、局部 Review、独立 v20 编辑计划与 Candidate 生成。

v20 第 5 步：[多轮闭环与离线验证](V20_ISSUE_FUSION.md)。已接入独立 campaign head、可恢复的 Memory/retained Skill 发布，以及 v19 产物的只读结构验证和保守转换。

v20 第 6 步：[独立 Pilot 与匹配对照实验](V20_ISSUE_FUSION.md)。先验证独立 Pilot 的工程闭环，再在相同任务 manifest、seed 和指标规则下运行 v20 Memory 与 no-memory 对照；两者均不把一次运行直接解释为因果结论。

v20 第 7 步（当前）：[冻结 Pilot、Benchmark 适配与统一 run/resume](V20_ISSUE_FUSION.md)。已冻结 benchmark v4 配置，接入真实 round factory、post-generation、train/monitor split 适配器和零模型调用 preflight；真实模型 Pilot 入口已具备但尚未启动。

v21 第 1 步：[双维归因认识的跨轮学习契约](V21_METHOD_CONTRACT.md)。将 Memory 作为任务成功与程序合规认识跨轮积累、修订和复用的载体，保留真实修改后的证据学习；不新增独立 Agent、重复 Review、状态体系或强制逐 edit 分析。

v21 第 2 步：[接通修改后学习侧证据](V21_POST_MODIFICATION_EVIDENCE.md)。已实现完整回放校验、安全投影、历史归档与局部回查，并用真实 v20 产物离线验证。

v21 第 3 步：[从修改后证据更新 Memory](V21_MEMORY_UPDATE.md)。已实现单次语义更新接口、原始事件引用校验、稳定身份与增量合并、派生档案和显式恢复。114 项相关测试通过，真实证据请求预检完成；未调用真实更新模型、发布活动 head 或启动完整 v21 自进化。

v21 第 4 步：[让双维认识参与下一轮修改](V21_MEMORY_CONSUMPTION.md)。已接通更新后的 Memory → Fusion → 局部 Review → 既有 Compiler/Editor，并保留跨轮证据来源。141 项相关测试通过，历史真实产物预检完成；完整 campaign、原子发布及真实两轮 Pilot 尚待第 5 步。

v21 输入优化：[短引用与无损内容复用](V21_INPUT_OPTIMIZATION.md)。同批证据下 Memory 更新由 238,240 降至 84,051 个代理 token；历史 Review 范围降至 20,625–61,025。原始事件、配对及反证均保留并可精确还原，157 项相关回归通过；未调用真实模型。

v21 补强第 1 步：[修改后新增退化的证据覆盖](V21_REGRESSION_COVERAGE.md)。完整扫描当前回放两维标签，自动补入此前引用未覆盖的退化配对及双侧原文。真实历史材料的默认输入由 6 组扩为 9 组，覆盖 T005/T022/T036；当前代理输入 99,405 tokens。没有新增 Agent、Review 或持久化状态；未调用真实模型。

v21 补强第 2 步：[issue 写回与复查边界](V21_ISSUE_BOUNDARIES.md)。固定原问题范围，区分 issue 的显式来源与共享 edit 带入的上下文，防止后者自动继承为本问题的新评价；Fusion/Review 按原问题复查。保留共享证据和反证，当前 Memory 代理输入 99,761 tokens；未调用真实模型。

v21 补强第 3 步：[简明当前认识与历史消费](V21_CURRENT_UNDERSTANDING.md)。在同一次 Memory 更新中维护 issue 综合认识；Fusion 读取认识和尝试目录，Review 按需打开旧尝试并保留已知反例及历史退化。完整历史留在档案，旧记录无摘要时保持完整读取；未调用真实模型。

v21 小规模验证第 1 步：[案例与判定依据](V21_SMALL_VALIDATION_CASES.md)。冻结行李计费、多人拆单、保障条件不明三组真实历史材料，分别检查双维冲突、反例与因果不确定性、当前条款覆盖及合理 NO_EDIT。保留 2,000 字符硬限制；仅完成材料准备，下一步先验证真实模型的决策使用，再决定是否最小强化，随后接通完整调度与恢复。

v21 小规模验证第 2 步：[真实模型局部对照报告](V21_LOCAL_COMPARISON_REPORT.md)。现有入口完成旧历史与 Replay 更新后 Memory 的两组消费，计入失败共 28 次真实调用。三例最终均 NO_EDIT，未证明修改决策改善；暴露行李退化配对未跨轮带入、已加载正面证据利用不足及重复提案开销。2,000 字符限制和运行源码未改，未新增 Replay 或发布活动 Skill/Memory。

v21 实验后优化第 1 步：[退化证据的跨轮保留](V21_REGRESSION_RETENTION.md)。强化同次 Memory 更新的有界观察与双侧引用要求，保存独立的来源保留核查，并用原实验响应复现 T009 未关联和 T034 单侧引用。210 项相关测试通过；不自动分配 issue、不补写历史认识、不放宽 2,000 字符限制，未新增真实模型调用。

信用卡 v2 的设计、配置、运行适配器和预检产物已迁移到 [`dataset_8bucket_1200_skill_evlaution`](</Users/didi/Desktop/dataset_8bucket_1200_skill_evlaution/docs/V2_CURRENT_PLUS_MEMORY_DESIGN.md>)，信用卡专用文件不放在本仓库。

v21 实验后优化第 2 步：[Evidence Review 证据比较](V21_EVIDENCE_COMPARISON.md)。Review 提示升为 v21.5，在原有理由中比较相关正反证据、实际行为与适用条件，区分观察和假设，保留有依据的 NO_EDIT。三组真实输入不变，每次增加 387 个代理 token；真实模型效果待后续验证。

v21 实验后优化第 3 步：[Fusion 提案依据](V21_FUSION_PROPOSAL_BASIS.md)。Fusion 提示升为 v21.4，要求针对当前 Skill 的有依据行为缺陷提出有限方向；仅有失败标签或泛泛复查愿望时允许 NO_EDIT，并保留问题归属。两组真实输入不变，每次增加 386 个代理 token；Review 保持 v21.5，真实效果待分阶段验证。

v21 实验后优化第 4 步：[分阶段真实模型复验](V21_STAGED_VALIDATION_REPORT.md)。完成 6 次真实调用，5 次通过结构校验、1 次 Fusion 引用失败，共 416,122 tokens。Memory 本次补齐 T009/T013/T034 双侧引用与完整回查；行李 Review 仍漏回应已加载正面观察，Fusion 送审减少但语义质量未证明改善。未自动重试、串联、Replay 或发布，尚不满足完整调度的验证前提。

v21 语义定向修订：[Review 比较与 Fusion 判断](V21_SEMANTIC_FOLLOWUP.md)。经 6 次真实调用，任务/操作原文对照使行李 Review 首次回应此前遗漏的正面观察；未奏效的轨迹重排和额外提示已撤回。Fusion 调整后两组结果均有效，但部分判断仍有争议。217 项回归通过，累计 299,372 tokens；不增加 Agent 或复查流程，未执行 Editor/Replay。


v21 两类语义验收：[已知问题修复与跨问题迁移](V21_SEMANTIC_ACCEPTANCE.md)。冻结运行机制，新增 5 次真实 Review 并复核旧 Fusion，合计 201,938 tokens。行李证据遗漏本次未复现但拒绝理由部分充分，地址局部修改有依据，姓名仍把用户明确字段的重叠泛化为强制再次确认，两个开发集迁移案例的 NO_EDIT 有依据。整体未全部通过；未执行 Editor/Replay 或修改运行代码。


v21 缺陷依据调整：[Fusion / Review 的最小修改](V21_DEFECT_GROUNDING.md)。Fusion/Review 提示升为 v21.6/v21.9，要求原文可以推翻上游缺陷假设，新增程序义务须有依据，同时保留对真实偏差的有限修改。七份固定输入不变，代理 token 分别增加 83/180；59 项工程测试通过，尚未真实模型复验。


v21 三步真实验证：[姓名/地址与迁移检查](V21_GROUNDING_VALIDATION.md)。冻结 Fusion v21.6 / Review v21.9，完成 1 次 Fusion 与实际提案触发的 3 次 Review，共 107,097 tokens。姓名用原文推翻缺陷并 NO_EDIT，地址保留有限修改；代金券在 Fusion 停止，航班识别了计算基准问题但停止/转人工授权仍部分充分。开发集内单次验证，未执行 Editor/Replay，未改 Prompt。


v21 单轮真实闭环：[完整验证报告](V21_CLOSED_LOOP_VALIDATION.md)。真实 Memory → Fusion → Review → Editor → 36 组 Replay → Memory 已执行；成功 27→23、合规 34→35，结构通过而语义部分通过。Memory 正确认识未执行验证和非因果改善，但遗漏直接相关的跨案例航班退化。未改 Prompt 或发布版本。


v21 双维证据修订：[四步定位与跨案例复验](V21_EVIDENCE_REVISION.md)。仅调整 Memory 配对证据呈现，补入各自用户原文、调用及双维标签；保留 Issue—Attempt 与原语义 Prompt。两版共 15 次真实调用、1,253,924 tokens，131 项工程测试通过。第一版错误生日归因在第二版未复现，但姓名缺陷判断和问题边界仍有语义失败，整体部分通过，未执行 Editor/Replay 或发布。
