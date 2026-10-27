# 方法 V23.4 文档

[文档总索引](../../README.md) · [V23](../v23/README.md) · [V23.2](../v23_2/README.md) · [V23.3 实现](../../../src/skill_evolution/v23_3/README.md)

[全部实验与归档入口](../../../experiments/methods/v23_4/README.md) · [正式配置与已保存结果](../../../experiments/methods/v23_4/v23_4_alfworld_formal_001/README.md)。下文状态描述保留各阶段的历史时间点，后续运行状态见上述入口。

更新日期：2026-10-22（Asia/Shanghai）。

V23.4 研究历史响应驱动的 D/S/C 条件化更新变换：历史实际编辑及其行为响应参与决定 Original Update 的方向、适用范围与协调关系；每项 Update 对应一个 Adjustment，其 focus/change/reason 表达决定，to.patch 落实具体修改。目标同时包括减少退化与促进持续改进。

| 材料 | 内容与状态 |
|---|---|
| [多 Knowledge P4 候选与离线验收](MULTI_KNOWLEDGE_P4.md) | 用户原稿仅两处修订，独立学习 Prompt 版本，三版本重载与链路检查，R05/R06 待发送消息冻结；没有真实模型调用 |
| [多 Knowledge P3 链路适配](MULTI_KNOWLEDGE_P3.md) | Replay、v3、历史 Pair、Preconditioner、Patch、共享编译器与 Editor 交接统一 memory_contract；默认仍旧格式，P4 学习 Prompt 与真实验证未完成 |
| [多 Knowledge P2 存储实现](MULTI_KNOWLEDGE_P2.md) | 显式新契约、逐 Knowledge 校验与引用限定、完整数组替换、旧格式只读转换、混合提交重载与幂等恢复；下游链路和真实语义验证尚未完成 |
| [输入输出契约](INPUT_OUTPUT_CONTRACT.md) | 当前为简化输出协议 v2：顶层 adjustments/checks；逐 Update 一个含 target/focus/change/reason/to 的 Adjustment；程序推导 Editor 交接，明确失败与适配边界 |
| [D/S/C 决策规则与人工案例](DSC_DECISION_RULES.md) | 第二步：R1–R7 决策规则、8 个合成人工案例，覆盖收窄、重构、扩大、协调、Keep、探索与失败边界 |
| [Preconditioner Prompt](../../../src/skill_evolution/v23_4/preconditioner_prompt.md) | 依据规则编写的英文模板，使用 v2 扁平输出；已接入最小运行器 |
| [最小实现与调用说明](../../../src/skill_evolution/v23_4/README.md) | 第三步：v2 校验、Patch/编译适配、版本化归档与 Editor 交接，含离线验证命令 |
| [Diagnosis / Memory 微调与离线报告](OFFLINE_REVIEW.md) | 第四步：两个 Prompt 的针对性微调、完整合成案例、语义走查、版本化交接与 Memory 生命周期检查 |
| [Editor 最小定向审查](EDITOR_REVIEW.md) | 第五步前补充：Effective Plan 输入、忠实实现、额外策略与实际 Diff 四项核对；9 项离线检查，真实生成遵循性仍待验证 |
| [第五步首轮状态与定向修订](../../../experiments/methods/v23_4/semantic_generation_001/REVISION.md) | 已执行 4 个逻辑阶段、7 次 HTTP；R06 三次重启耗尽。修正 Prompt 的 EOF 指引与合法 Check 引用，151 项离线检查通过；完整第五步仍未完成 |
| [R06 修订后重启报告](../../../experiments/methods/v23_4/semantic_generation_002/REPORT.md) | Preconditioner 和 Editor 均首次结构通过，2 次 HTTP、零重启；发现 change/Patch 与 Goal/Check 语义不一致，Candidate 尚不进入 Actor |
| [R06 双向一致性单次生成](../../../experiments/methods/v23_4/semantic_generation_003/REPORT.md) | 采用用户指定一致性表述；1 次 HTTP、零重启。唯一修改项 u2 的 change/Patch 对应，未再新增取回动作；Goal 冲突仍保留，不代表整体 Plan 通过 |
| [R06 新 Diagnosis 与冻结 Plan 核对](../../../experiments/methods/v23_4/semantic_generation_004/REPORT.md) | 相同当前事实、新 Diagnosis、原 Memory；3 次 HTTP、1 次技术重启。打开状态与 Goal 的冲突消失，但 c2 未覆盖条件化开门且持有边界偏宽，未判整体语义通过 |
| [R06 新 Effective Plan 的 Editor 忠实性](../../../experiments/methods/v23_4/semantic_generation_005/REPORT.md) | 1 次 HTTP、零重启；两个 Updates 逐项落实，未发现额外策略；真实 Candidate/Diff 重建通过。依最新范围约定，Checks 覆盖不阻塞推进；未运行 Actor |
| [R06 Parent / Candidate 真实执行](../../../experiments/methods/v23_4/r06_actor_comparison_001/REPORT.md) | 同批 7 个开发任务，两组新执行、8 并发；5/7 → 6/7，1 项修复、0 项成功率退化；共同成功任务 97 → 43 步。温变机制获得直接证据，搜索防循环仍不稳定 |
| [R06 Replay / Memory 验证](../../../experiments/methods/v23_4/r06_replay_memory_001/REPORT.md) | 1 次 HTTP、0 重启；原样提案修订 M7/M10，隔离 Memory 往返与投影通过。语义核对发现步号错误和局部/整体效率混淆，暂不直接采用；历史 Active 未变。补充空动作证据兼容修正，当前 V23.4 测试 156 项通过 |
| [R05 冻结输入与当前版本生成](../../../experiments/methods/v23_4/semantic_generation_006/REPORT.md) | 复用 Original Plan 和原 Memory，Preconditioner → Editor 均首次结构通过，2 次 HTTP、0 重启；u1/u3 Keep，u2 做 S 变换。理由存在事实与归因问题，Editor 再次将 u3 局限于非 desklamp 章节，语义未完全通过；未运行 Actor |
| [R05 Editor 章节范围最小修订](../../../experiments/methods/v23_4/semantic_generation_007/REPORT.md) | 加入用户指定的章节位置/范围要求；固定上一轮 Parent 与 Effective Plan，仅生成 Editor，1 次 HTTP、0 重启。u3 改为独立 Admissible Actions 章节，u1/u2 忠实落实，本次定向文本审查通过；144 项相关测试通过，未运行 Actor |
| [R05 Parent / Candidate 真实执行](../../../experiments/methods/v23_4/r05_actor_comparison_001/REPORT.md) | 完整 10 对开发任务、8 并发；两组均 8/10，0 修复/退化，共同成功任务 52 → 49 步。u1 仍操纵替代物、u2 循环持续、u3 仍有非法导航；20 条首次 episode 完成，10 次单步技术重试，未运行 Replay |
| [R05 Replay / Memory 验证](../../../experiments/methods/v23_4/r05_replay_memory_001/REPORT.md) | 1 次 HTTP、0 重启，不改机制；新增一条、修订 M6/M8，原样隔离提交/重载/投影通过。发现历史动作误写、未找到推为不存在和条款范围归因问题，三个预览暂不采用，原 Memory 未变 |
| [V23.4 对照 V23 的设计研究](../../../experiments/methods/v23_4/v23_design_comparison_001/REPORT.md) | 离线核对 V23 已有 Memory 与 D/S/C；整理显式决定、Keep、严格 Patch、状态及配套差异。历史 R05 与当前输入不等价，提出先固定同一输入的 Preconditioner 对照；尚未调用对照模型或运行消融 |
| [Replay 输入视图契约](REPLAY_INPUT_VIEW.md) | 当前 Pair 相邻与任务结果统计、复用 Memory v3、从真实归档补历史 Pair；完整事实与模型视图分离，输出仍为三字段 Memory 提案 |
| [Replay 输入实现与离线验证](../../../experiments/methods/v23_4/replay_input_view_001/REPORT.md) | 第 1—3 项完成；409 项相关测试通过，6 项历史检查排除。R05/R06 完整事实投影通过，用户消息字符减少 40.89%/40.70%；原 Memory 未变，尚未调用新视图的真实 Replay |
| [R05/R06 新视图真实 Replay 验证](../../../experiments/methods/v23_4/replay_input_view_live_001/REPORT.md) | 2 次 HTTP、0 重试；输入 token 降低 40.56%/40.27%，隔离 Memory 往返及未来 Pair 恢复通过。部分旧错误未重复，但仍将未找到推为不存在，并出现任务概括/对象误写；四条原样提案暂不采用，原 Memory 未变 |
| [用户提供的 Replay 候选 Prompt 验证](../../../experiments/methods/v23_4/replay_prompt_candidate_001/REPORT.md) | 附件原样冻结，程序追加原背景与视图说明；R05/R06 User 消息与参数不变。2 次 HTTP、0 重试，事实和比较覆盖部分改善，仍有回退机会否认、范围混用及重要对照遗漏；五条原样提案仅隔离预览，未覆盖默认 Prompt |
| [多 Knowledge 统一契约](MULTI_KNOWLEDGE_CONTRACT.md) | P1：固定逐 Knowledge text/evidence、完整数组替换、显式版本与只读旧格式兼容；v3 算法和 D/S/C 不变，尚未实现新链路 |
| [多 Knowledge 依赖审计](MULTI_KNOWLEDGE_AUDIT.md) | 覆盖存储/提交/重载、Replay、v3、Preconditioner/共享编译器、历史脚本与 Prompt；旧实现基线 104 通过、2 项既有 Editor Prompt 重载失败，未运行新模型 |

当前已完成前四步：契约、D/S/C 规则与 Prompt、最小 Preconditioner/适配，以及 Diagnosis / Memory 协同微调。前四步记录为 341 项离线测试通过（122 项 V23.4、219 项 V23 回归），排除 5 项历史归档测试。第五步已完成 R06、R05 的真实生成、定向修订、Parent/Candidate 配对执行及 Replay/Memory 验证；两轮 Replay 结构通过但有语义偏差，原样预览不自动采用。相关测试的版本与数量见各轮报告。已开始以 V23 设计为基准的离线比较，尚未运行该方法对照、注册默认方法或完成全套消融；单批开发任务结果不证明 D/S/C 的独立贡献或持续改进收益。
