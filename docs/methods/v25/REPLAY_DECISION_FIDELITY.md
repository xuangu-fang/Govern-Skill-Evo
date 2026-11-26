# Replay v4：条件比较与 Knowledge 保真

2026-10-28。采用 v3 加已审阅局部修改的生产稿作为默认 Replay，版本为 `v25_replay_decision_fidelity_v4`。这次选择的是更合理的研究基线，不以消除所有错误作为采用条件，也不宣称已有实验证明稳定性能提升。本次安装仅做离线验证，没有调用模型、发布 Memory 或运行完整链路与训练。

## 修改内容

生产正文与[已审阅生产稿](../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/production_candidate.md)逐字一致，没有再追加要求。三个方向落实为五处替换，合并原有相关表述：

| 位置 | 修改及目的 |
|---|---|
| §1 观察边界 | 等分或相同错误坐标只说明这些测量结果未变，不能单凭此排除某个行为或失败机制的影响。 |
| §3 比较要求 | 在同一相关输入或状态条件下对齐双方，按需要追踪信息来源、选择优先级、回退触发与后续使用；避免共同字段名称掩盖不同决策，也避免把单分支扩成整个程序。 |
| §3 响应类别 | 将 “adherence without added benefit” 改为 “adherence with no measured outcome change”，区分未测得结果变化与没有机制收益。 |
| §4 Knowledge 选择 | 按条件性经验价值选择比较，不要求每项比较成为独立 Knowledge；压缩时转到 §6 核查重要含义。 |
| §6 保真核查 | 检查删去条件、优先级、回退或同时发生的其他变化后，是否改变读者对行为和原因的理解；必要时恢复区别或收窄结论，通用 caveat 不能修复错误事实或无依据的因果排除。 |

仍允许有依据、尚待验证的机制假设与合理经验泛化。不强制穷举所有分支，不限制比较或 Knowledge 数量，不要求逐条抄写实现细节。生产输出仍只有 `entries`；没有引入诊断实验的 `comparisons` 字段。历史 Memory 修订约定、§2、§5、§7 及视图说明均保持不变。按空白分词，学习模板由 2,839 词增至 3,041 词（+202），不是 tokenizer token 统计。

## 采用依据与实验边界

[同期单配对初筛](../../../experiments/methods/v25/replay_local_revision_screen_20261028_001/reports/README.md)得到混合结果：局部修改后的诊断稿更明确地保留 R06 的 name/code 优先级，但仍遗漏完整回退判据，并出现无依据的因果排除；R05 也仍有把分支行为扩成所有行的概括错误，同时产生了一些可核对的行级推断。

此前“未通过预设初筛”的实验结论和原始档案保持不变。本次在用户明确认可后，从生产基线选择的角度采用该稿：这些要求具有通用的比较与归纳意义，保留探索空间，且没有写入 R05/R06 的目标答案。采用不等于将初筛改判成功；诊断实验使用额外比较输出，也不能直接充当生产格式 v4 的效果验证。下一阶段的评估应以这个固定基线为准，而不是继续以两例必须全部正确为条件反复叠加提示。

## 默认与归档兼容

- 默认学习 Prompt：`v25_replay_decision_fidelity_v4`，正文为 [replay.md](prompts/replay.md)。
- 旧 v3 正文逐字归档为 [replay_legacy_v3.md](prompts/replay_legacy_v3.md)，v1/v2 原归档保持不变；读取时按保存的 Prompt 版本重建原请求。
- 输入视图仍为 `v25_replay_pairs_knowledge_only_v4`。Prompt v4 与输入视图 v4 是独立版本，视图的配对邻接、共享输入、完全一致代码去重与无损还原均未修改。
- Preconditioner 继续默认 `v25_preconditioner_evidence_decision_boundaries_v7`。
- 更新供后续运行使用的 `experiments/methods/v25/configurations/v25_spreadsheetbench_full120_batch15.json`；旧 campaign 和实验配置不回写。

兼容读取旧归档不等于绕过旧训练的 method freeze。旧 campaign 仍不能被静默改用新默认继续运行；本次没有恢复或启动训练。

离线测试、旧实际归档重载及新版本保存/读取检查见[安装校验记录](../../../experiments/methods/v25/replay_prompt_v4_offline_20261028_001/reports/README.md)。其中新版本 fixture 复用旧响应，仅检查工程契约，不能当作 v4 模型输出或学习质量证据。
