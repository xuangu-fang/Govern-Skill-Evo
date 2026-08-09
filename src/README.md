# `src` 源码目录

本目录保存项目自己实现的代码。第三方 benchmark 位于 `external/`，实验产物位于 `experiments/`，二者不应与这里的实现代码混在一起。

## 目录说明

| 目录 | 作用 |
|---|---|
| `adapters/` | 将外部系统的数据和运行方式接入本项目。`tau2/`中包含τ³结果到统一轨迹的转换器，以及本地 Skill Agent 补丁。 |
| `policies/` | 定义版本化Policy规则集和Verifier运行上下文。 |
| `trajectory/` | 定义统一Trajectory Schema，并保存旧格式迁移脚本。 |
| `verifiers/` | 保存Task Verifier、Deterministic Process Verifier、Semantic Process Verifier及公共输出结构。 |
| `learners/` | 保存从轨迹中提炼经验和候选Skill的学习流程。当前主要是Day 4的Trace2Skill-style实现。 |
| `skill_evolution/` | 预留给后续Skill选择、更新、门控和回滚逻辑。 |


## 当前数据流

```text
τ³ results.json
    ↓ adapters/tau2/tau2_to_common.py
TrajectoryDataset
    ├──→ verifiers/task_verifier.py
    │       └── TaskVerdictDataset
    ├──→ Semantic rule handlers
    │       + PolicyRuleSet + VerificationContext
    │       └── Saved judgments
    │
    └──→ Process Verifier输入

TrajectoryDataset + PolicyRuleSet + VerificationContext + Saved judgments
    ↓ verifiers/process_verifier.py
CheckerRegistry
    ├── Deterministic handlers
    └── Semantic handlers
    ↓
ProcessVerdictDataset
```

## 使用约定

- 所有命令都从项目根目录运行，例如`python -m src.verifiers.task_verifier`。
- Adapter不得编造源数据中不存在的状态；无法恢复的字段应保留为`None`。
- Verifier输出必须包含可追踪证据和对应的轨迹step。
- Human Gold属于人工审核数据，不能用模型输出自动覆盖。

更详细的说明见：

- [`trajectory/README.md`](trajectory/README.md)
- [`verifiers/README.md`](verifiers/README.md)
- [`adapters/tau2/README.md`](adapters/tau2/README.md)
