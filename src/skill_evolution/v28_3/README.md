# SearchQA v28.3

独立四阶段实现：Diagnosis → Preconditioner → Editor → Replay；Parent/Candidate Actor 执行、确定性 Gate 与追加 Memory 由本版本运行器接线。没有 Grouping 模块或调用。

- 方法和 Prompt 采用已审阅的 [v28.3 文档](../../../docs/methods/v28_3/README.md)，Diagnosis/Preconditioner 来源为 v29.4，保留 SearchQA 的完整文本证据及 EM/F1。
- Actor、数据和评分复用 SearchQA，使用独立方法来源标识。Train/Test workers 均为 15。
- Diagnosis/Preconditioner/Replay 为 65,536 tokens，Editor 为 **32,768**；方法 timeout 为 600 秒。Actor 仍为 32,768 / 300 秒。
- 当前轮完整验证来源；已提交 Memory 按顺序 ID 读回，常规恢复不重新打开历史 Actor 来源或重算历史 Gate。运行身份、Prompt 和配置仍需一致。
- Editor/Replay/Gate 的算法与已有 SearchQA 适配保持一致，使用本版本上游校验；不存在全局 monkeypatch 或旧版本修改。

入口：[run_v28_3_campaign.py](../../../scripts/runs/run_v28_3_campaign.py)。配置：[v28_3_searchqa_train600_batch30.json](../../../experiments/configs/v28_3_searchqa_train600_batch30.json)。实现与离线结果见 [IMPLEMENTATION.md](../../../docs/methods/v28_3/IMPLEMENTATION.md)。

train/test 为独立显式命令；训练完成不会自动启动 Test。截至 2026-11-04，正式实验已完成 600 题、20 轮训练及后续独立的 1,400 题 Test；Test 答对 1,187 题，EM 为 0.8478571428571429，F1 为 0.9148350340136054。见 [训练汇总](../../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828/training_summary.json)和 [Test 汇总](../../../experiments/evaluations/v28_3_searchqa600_batch30_20261104_022828_test1400/summary.json)。训练汇总中的 test_started=false 仅表示未自动启动 Test；后续独立测试已完成，使用的 Skill 与训练最终导出文本一致。
