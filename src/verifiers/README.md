# Verifier与Semantic Judge

本目录负责把统一轨迹转换为任务结果或过程合规结果。项目将“任务是否完成”和“执行过程是否合规”作为两个独立维度。

## 文件说明

| 文件 | 作用 | 是否调用模型 |
|---|---|---|
| `schema.py` | 定义`SchemaEvidence`、`Violation`、`TaskVerdict`、`ComplianceVerdict`及其Dataset。 | 否 |
| `task_verifier.py` | 将`Trajectory.outcome.score`转换为带证据的任务成功判断。 | 否 |
| `process_verifier.py` | 检查`airline.transfer.protocol.001`：转人工工具调用与固定提示语的顺序。 | 否 |
| `transfer_scope_judge.py` | Semantic Judge针对`airline.transfer.scope.001`的当前实现，判断是否应该转人工。 | 是 |
| `evaluate_transfer_scope_judge.py` | 将Semantic Judge判断与Human Gold比较，计算覆盖率、准确率和混淆矩阵。 | 否 |
| `transfer_scope_verifier.py` | 比较“实际是否转人工”和“是否应该转人工”，生成最终`ComplianceVerdict`。 | 否 |

`Semantic Judge`是通用方法类别；`transfer_scope_judge.py`是当前针对转人工规则的具体实现。后续可以增加其他语义规则，而不需要把全部Semantic Judge都限定为转人工判断。

## 两类Verifier

```text
Trajectory
├── Task Verifier
│   └── TaskVerdict：任务是否完成
└── Process Verifier
    └── ComplianceVerdict：过程是否合规
```

Task Verifier只读取上游任务结果，不判断Policy合规。Process Verifier只判断指定规则，不应把一条规则的结论扩展成整个Policy的总体结论。

## Semantic Judge链路

```text
Annotation Packet
    ↓
Semantic Judge：判断should_transfer
    ├──→ Judge-vs-Gold评估
    └──→ Process Verifier
              + 轨迹中的实际转人工事实
              ↓
        ComplianceVerdict
```

Semantic Judge与最终Process Verifier是分开的：Judge只提供语义判断；Verifier负责提取确定性事实并比较两者。`transfer_scope_verifier.py`本身不会调用模型。

## 常用命令

任务结果：

```bash
python -m src.verifiers.task_verifier \
  --input experiments/results/day5_schema/common_trajectories_v02.json \
  --output experiments/results/day5_schema/task_verdicts_v01.json
```

确定性流程规则：

```bash
python -m src.verifiers.process_verifier \
  --input experiments/results/day5_schema/common_trajectories_v02.json \
  --output experiments/results/day5_schema/compliance_verdicts_v01.json
```

Semantic Judge完整运行顺序见：

[`../../experiments/annotations/transfer_scope_v01/README.md`](../../experiments/annotations/transfer_scope_v01/README.md)
