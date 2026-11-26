# V25 SpreadsheetBench 候选实现

## 实验记录与离线核对

[原版实验索引](../../../experiments/methods/v25/README.md)列出三次完成训练的实验，以及七次中断或停止的尝试。主方法和 SpreadsheetBench 适配器保留原包名。上游 Actor 提示词的[准备期实现](../../../src/skill_evolution/v25/revisions/upstream_actor_prepared/)和[实际运行实现](../../../src/skill_evolution/v25/revisions/upstream_actor_scheduled/)各自保留包和资源。

从仓库根目录运行。第一条检查精选材料；第二条还读取本机的轮次记录和 840 条评测轨迹。

```sh
python scripts/runs/v25/verify_bundle.py
python scripts/runs/v25/verify_bundle.py --archive
```

[运行与环境](RUNNING.md)列出正式入口和 Docker 验收命令。完整运行现场位于 Git 忽略的 `artifacts/`。

## 2026-10-28 官方接口连续训练已启动

新实验使用官方 `deepseek-flash`，从原始 initial Skill 和空 Memory 开始，冻结 Diagnosis v5、Preconditioner v7、Replay Prompt v4 和输入视图 v4，运行 120 个优化任务（8 × 15），不运行最终 Test。旧内网探索实验保留。官方接口兼容性与离线冻结检查已通过；启动信息、路由适配和实时状态入口见[本次训练记录](../../../experiments/methods/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/reports/README.md)。本条只表示已启动，不表示八轮已完成。

2026-10-27 评分兼容更新：以 SkillAdam 的值比较规则为基础，修复异常区域解析，恢复完整 280 题测试配置；训练、验证、测试共 400 题离线自检通过。详见 [评分兼容边界与验证](SCORING_COMPATIBILITY.md)。旧实验和旧 277 题配置不修改，本次未启动实验。下文关于异常题待处理的描述属于历史记录。

最新准备入口见 [V25 / SkillAdam 配对配置](PAIRED_PREPARATION.md)：共享配置只生成一次，默认并发 4、无任务总时限、实际执行计数、新历史协议及已确认的输出额度。仅准备与预检，未启动训练。

当前新配置的输出额度已更新：两种方法 Actor 为 49152，V25 Diagnosis 为 32768，Preconditioner／Replay／Verifier 为 49152，其他模块不变。详见 [TOKEN_BUDGETS.md](TOKEN_BUDGETS.md)。旧实验配置不自动升级，本次未启动实验。

SkillAdam 对照接入层已同步新 Actor 协议和压缩前证据过滤，配置及兼容边界见 [SKILLADAM_ALIGNMENT.md](SKILLADAM_ALIGNMENT.md)。本次未启动新实验。

2026-10-27：已实现 [临时格式修复与执行证据视图](EXECUTION_HISTORY.md)，通过新配置显式启用 `actor_history_policy=execution_only_v1`。本次只做本地验证，未启动新实验；下文旧实验状态与预算是历史记录，不代表本次运行状态。

当前 Preconditioner 的历史经验与计划审查定位、输入及引用边界见 [PRECONDITIONER_ROLE.md](PRECONDITIONER_ROLE.md)。

当前 Replay 学习 Prompt 默认为 `v25_replay_decision_fidelity_v4`：采用 v3 加已审阅的局部修改生产稿，加强重要决策的条件对齐、比较到 Knowledge 的语义保留，以及测量结果与因果排除的区分；仍只输出 `entries`。旧 v1/v2/v3 模板按字节归档并兼容读取，输入视图继续 `v25_replay_pairs_knowledge_only_v4`、Preconditioner 默认 v7。这是基于文本合理性和实验得失作出的研究基线选择，不代表小规模诊断已证明稳定性能提升；本次注册只做离线校验。见 [Replay v4 默认与兼容说明](REPLAY_DECISION_FIDELITY.md)。此前 [v3](REPLAY_CONDITIONAL_COMPARISON.md) 与 [v2](REPLAY_EVIDENCE_CALIBRATION.md) 说明保留为历史记录。下列输入视图段落按实施顺序记录，所述 Prompt 版本为各次实施时版本。

2026-10-28：Replay 默认输入视图更新为 `v25_replay_pairs_knowledge_only_v2`，恢复 v24 的 pairs 前置及 verified pair 内 Parent/Candidate 邻接。旧输入视图 v1 按原布局重建，Prompt 仍为 v2、Preconditioner 仍为 v7；没有新增去重或模型实验。见 [输入布局恢复与离线验证](REPLAY_PAIRED_INPUT.md)。此前 v2 Prompt 单模块结果见 [R05 / R06 对照](../../../experiments/methods/v25/replay_v2_deepseek_r05_r06_clean_20261028_001/reports/README.md)，其归档仍使用旧输入视图。

同日后续：当前默认输入视图为 `v25_replay_pairs_knowledge_only_v3`，在配对邻接上加入跨 run 完全相同 system 共享及 pair 内完全相同初始 user 消息共享。旧 v1/v2 输入视图保留，新视图可无损还原为共享前的 v2 视图；response/code 不去重。Replay 学习 Prompt 仍为 v2，仅追加表示格式说明，Preconditioner 仍为 v7；只做离线校验。见 [共享初始消息与兼容说明](REPLAY_SHARED_INITIAL.md)。

同日进一步更新：当前默认输入视图为 `v25_replay_pairs_knowledge_only_v4`。在 v3 共享与邻接布局上，仅将与 response 代码体逐字相同的 executed_code 替换为可还原标记；路径适配及其他差异继续保留原文。旧 v1/v2/v3 视图及其 system 解码说明保持兼容，Replay Prompt 仍为 v2、Preconditioner 默认 v7。未跑模型实验，见 [完全一致代码去重与离线校验](REPLAY_EXACT_CODE.md)。

最近一轮正式训练采用 [8 批 × 15 题配置](BATCH15_TRAINING.md)：120 题、1 epoch、Actor 并发 4／32,768 输出 tokens、无整题累计时限，使用冻结的 history_primary_v2 Preconditioner。当前源码的默认 Preconditioner 已退回 evidence_decision_boundaries_v7，v8 保留为实验版本，引用契约及旧归档兼容范围见 [显式引用说明](PRECONDITIONER_REFERENCES.md)；本次修复未启动或迁移实验。10 题方案已撤销；下文首版验收及历史预算描述不覆盖这份新配置。

v25 已实现 SpreadsheetBench Actor、评分器、证据适配和完整自进化流程，候选配置为 `v25_spreadsheetbench_verified400_rc1`。本次仅进行离线验收，未启动真实模型实验。

- [运行说明与候选配置边界](RUNNING.md)
- [离线验收报告](OFFLINE_ACCEPTANCE.md)
- [优化器连续时间线视图与离线验证](TIMELINE_INPUT.md)

- [完整 Prompt 定稿包](prompts/README.md)
- [逐模块 Prompt 迁移说明](PROMPT_MIGRATION_REVIEW.md)
- [构造案例与检查结果](prompt_review/REVIEW_RESULTS.md)
- [共享执行上下文定稿与参数推荐](SHARED_EXECUTION_CONTEXT.md)
- [Actor 与证据协议草案](ACTOR_EVIDENCE_PROTOCOL.md)
- [逐模块迁移清单](MODULE_MIGRATION_CHECKLIST.md)

已确定的数据与方法条件：沿用共同的 80 Train／40 Selection／280 Test 任务列表；120 题参与优化，Selection 已参与优化；每批 15 题，完整遍历为 8 批；280 题仅用于最终评估。初始 Skill 使用 SkillOpt 的 SpreadsheetBench 初始 Skill 原文，Memory 为空。主指标为任务完全成功率 `hard`，辅助指标为逐题单元格正确率的任务平均值 `per_cell_pass_rate`。v25 保持 v24 的严格成功数 Gate 和经验发布机制。

已确认首版不启用标准答案纠错反馈：Parent、Candidate 和 Test 的 Actor 都只接收格式、程序执行及输出文件错误，不接收答案对照产生的错误坐标或评分。首次生成有效工作簿后结束 Actor，再评分。优化任务结束后的评分仍交给 Diagnosis、Preconditioner、Replay 等模块分析；关闭任务内评分纠错不等于关闭 Skill 自进化的结果反馈。

沿用 v24 的轨迹复用方式：同一批 Parent 执行既用于诊断，也作为 Gate 的基准；产生 Candidate 后只执行 Candidate，不额外重跑 Parent。一批 15 题完整走到 Candidate 时，共 30 次任务执行，每次可能包含多轮模型请求。没有形成 Candidate 的 no_change 分支不执行 Candidate 或配对 Gate。

以下表格区分已确认条件与仍需审阅的细节：

| 审阅项 | 推荐方案 | 主要影响 |
|---|---|---|
| Actor 执行方式 | 多轮完整 Python 代码生成；每次从原始输入重新执行 | 不引入交互式文件探索工具或跨尝试工作区状态 |
| Actor 反馈（已确认） | 所有阶段仅提供格式、执行及输出文件错误；不提供标准答案纠错反馈 | Parent 可复用于 Gate，Gate 与 Test 的反馈条件一致 |
| 优化阶段评分信息 | 提供指标、错误坐标、缺失工作表；不提供标准答案值 | 支持诊断，同时避免经验变成答案摘录 |
| Actor 历史 | 当前任务内保留实际代码尝试与反馈；不直接注入 Memory | 明确模型看到的历史，保持方法中的 Memory 使用位置 |
| 初始 Skill 兼容 | 原文保留；执行器统一绑定路径变量，记录必要的路径适配 | 不静默改写初始 Skill 或生成程序的任务算法 |
| 证据引用（建议） | 用 P／Q 标记 Parent／Candidate；同一 Parent 引用贯穿诊断、Gate 和 Replay | 保留初始输入、尝试、结果及实际 Diff 引用，无需独立学习轨迹命名 |

已确认调用预算：Actor 每次输出 16,384 tokens、单次 API 请求超时 300 秒、每轮请求最多六次总尝试；方法模块沿用 v24 的输出额度及请求设置。单次程序执行与单次任务执行的时间预算均为 600 秒，参考 SkillAdam 主结果配置。任务时间预算分别作用于 Parent、Candidate 或 Test 的单次任务执行；复用 Parent 记录不产生额外时间额度。

共享执行上下文已定稿，具体见新增文档。首版推荐：最多 30 轮代码尝试；每表前 5 行 × 20 列、单元格 40 字符；当前任务完整历史；优化模块评分摘录最多 100 个错误坐标及 100 个缺失工作表名称。首轮功能验证并发建议为 1，后续实验并发统一固定。另已确认：总预览完整生成后检查 100,000 字符上限，超限明确报错、不截断继续；运行错误详情仅保留前 3,000 字符。以上已写入候选运行配置。

推荐 Actor 的 600 秒从取得执行名额、开始准备输入计至提交检查结束，覆盖请求、等待与程序执行；进行中的调用受剩余时间约束。事后评分单独计时，不延长 Actor 执行。首版不额外执行公式自动重算；评分使用 `data_only=True` 读取输出工作簿已保存的单元格值，与本地参考路径一致；公式无缓存可能导致判错，这一限制须在 Actor 说明和报告中明确。环境版本、模型输入容量、批次顺序和遍历次数已在候选配置与离线结果中记录。

Actor 三份模板、七个优化模块及公共 Prompt 已形成完整定稿，迁移说明和构造案例检查已完成。代码迁移及离线集成已完成；真实运行另行安排。训练时向 Actor 提供评分纠错可作为未来独立对照，不纳入首版默认流程。Test 中三个异常区域标注保持原样，最终评估前必须在共同 benchmark 配置中处理，详情见运行说明。

当前 Editor 为 `v25_editor_scope_fidelity_v2`，仅补充一句条件性建议不得自行升级为默认规则的澄清，见 [Editor 最小修订与固定案例](EDITOR_SCOPE_FIDELITY.md)。

此前 Diagnosis v3 与 Preconditioner v6 各补充一段自检结论的范围说明，见 [自检范围说明与正反案例](SELF_CHECK_SCOPE.md)。

当前 Diagnosis 为 `v25_diagnosis_evidence_scoped_updates_v5`：允许多个有依据的独立修订及待验证假设，收紧单条修订范围并检查重复、冲突与依赖；决策仅保留 `revise` / `no_change`。见 [Diagnosis v5 修改与兼容说明](DIAGNOSIS_EVIDENCE_SCOPED_UPDATES.md)。该次 Diagnosis 修订未运行实验，Preconditioner 当时为 v6；此前 [v4 回退边界修订](DIAGNOSIS_FALLBACK_REQUIREMENTS.md) 的要求继续保留。

此前 Preconditioner v7（`v25_preconditioner_evidence_decision_boundaries_v7`）修订：基于当次实际输入核对，局部调整事实判断、经验泛化、fallback 与保存／终止边界，保留有依据的探索。该次修改未补充输入证据，修改时未运行实验；详见 [修改与兼容说明](PRECONDITIONER_EVIDENCE_DECISION_BOUNDARIES.md)。

此前实验版本 Preconditioner v8（`v25_preconditioner_scope_aware_keep_v8`）：根据去掉旧回答的 DeepSeek v6/v7 对照，局部澄清不确定性对决策的影响、KEEP 的范围与强度依据、继承与新增规则的一致判断，以及保护条件／Checks。保留合理探索和泛化，修订当时未补充输入证据或运行实验；后续单模块结果及默认回退见 [回退说明](PRECONDITIONER_V7_DEFAULT.md)；见 [修改与兼容说明](PRECONDITIONER_SCOPE_AWARE_KEEP.md)。

2026-10-28 前次回退与审计：默认 Preconditioner 退回 v7，v8 模板及实验记录保留。该次仅进行归档证据审计及离线兼容校验，未修改 Replay / Memory，未运行模型实验。见 [回退说明](PRECONDITIONER_V7_DEFAULT.md) 和 [R05 / R06 Memory 传递审计](REPLAY_MEMORY_R05_R06_AUDIT.md)。后续 Replay v2 局部修订见本页当前版本说明。
