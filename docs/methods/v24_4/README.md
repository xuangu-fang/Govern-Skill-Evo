# ALFWorld v24.4

[五次训练、两次首测与 18 项独立分析](../../../experiments/methods/v24_4/README.md)

当前保留实现复用 v24.2 的训练机制，并使用 v24.4 的[阶段实现](../../../src/skill_evolution/v24_4/stages.py)。默认 Diagnosis 取自 [decision_priority](../../../src/skill_evolution/v24_4/revisions/decision_priority/prompts/diagnosis.md)，默认 Preconditioner 取自 [historical_attempt](../../../src/skill_evolution/v24_4/revisions/historical_attempt/prompts/preconditioner.md)。各次启动使用的具体修订可从实验页进入原始启动记录。

[基础 Prompt](../../../src/skill_evolution/v24_4/prompts/) · [各次 Prompt 修订](../../../src/skill_evolution/v24_4/revisions/) · [设计与审阅](revisions/) · [Test 入口](../../../scripts/runs/v24_4/run_v24_4_test.py)

在仓库根目录可用以下命令只读核对已完成训练的 Test 输入。

```sh
python scripts/runs/v24_4/run_v24_4_test.py --validate-only \
  --campaign artifacts/methods/v24_4/v24_4_alfworld_progress_decision_20261107_202453 \
  --evaluation artifacts/methods/v24_4/v24_4_alfworld_progress_decision_20261107_202453_test134
```

progress_decision 的完整首测支持通过 `--resume` 读回。retained 只留下 116 份回执，原进度文件仍记录当时的 running 状态。
