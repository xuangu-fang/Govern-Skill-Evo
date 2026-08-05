# Semantic Judge标注实验

本目录保存`airline.transfer.scope.001`的标注与评估数据。该规则判断：用户请求无法在Agent的Policy权限和工具范围内处理时，是否正确转交人工。

当前数据覆盖Task 5–14，共10条轨迹。Task 5–9沿用原运行结果，Task 10–14来自新增运行结果。

## 目录结构

```text
transfer_scope_v01/
├── packets/
│   ├── manifest.json
│   └── task_05.json ... task_14.json
├── gold/
│   └── human_adjudicated.json
└── judge_runs/
    └── gpt-5.6-terra/
        ├── judgments.json
        ├── evaluation.json
        └── compliance_verdicts.json
```

## 文件职责

| 路径 | 内容 | 维护方式 | 是否可以覆盖 |
|---|---|---|---|
| `packets/` | 提供给人工或Semantic Judge的输入，只包含Policy、工具说明和可见轨迹。 | 由`build_transfer_scope_packets.py`生成。 | 可以重新生成，但必须与对应原始运行批次匹配。 |
| `gold/human_adjudicated.json` | 人工确认的`should_transfer`和合规标签。 | 人工审核后维护。 | 不得用Judge输出自动覆盖。 |
| `judge_runs/*/judgments.json` | Semantic Judge对每条Packet生成的语义判断。 | 模型运行生成。 | 可以覆盖。 |
| `judge_runs/*/evaluation.json` | Judge与Human Gold的覆盖率、准确率、混淆矩阵和逐条对比。 | 评估脚本生成。 | 可以覆盖。 |
| `judge_runs/*/compliance_verdicts.json` | 结合Judge判断与轨迹中实际转人工事实得到的最终Process Verdict。 | Process Verifier生成。 | 可以覆盖。 |

## 信息隔离

Packet不包含：

- task reward和reward breakdown；
- 隐藏用户指令；
- 参考答案或reference actions；
- Human Gold；
- 轨迹中不可见的数据库状态。

因此Semantic Judge只能依据Policy、工具能力和当前可见轨迹作出判断。

## 正确运行顺序

```text
统一TrajectoryDataset
    ↓
生成Annotation Packets
    ↓
人工审核并冻结Human Gold
    ↓
运行Semantic Judge
    ↓
Judge-vs-Gold评估
    ↓
Process Verifier生成最终合规结果
```

Human Gold必须先完成人工审核，之后才能评估Judge。不能根据Judge结果反向修改Gold以提高准确率。

## 当前Semantic Judge链路

加载本地环境变量：

```bash
set -a
source .env
set +a
```

生成10条Semantic Judge判断：

```bash
python -m src.verifiers.transfer_scope_judge \
  --packets experiments/annotations/transfer_scope_v01/packets \
  --output experiments/annotations/transfer_scope_v01/judge_runs/gpt-5.6-terra/judgments.json
```

与Human Gold比较：

```bash
python -m src.verifiers.evaluate_transfer_scope_judge \
  --judgments experiments/annotations/transfer_scope_v01/judge_runs/gpt-5.6-terra/judgments.json \
  --gold experiments/annotations/transfer_scope_v01/gold/human_adjudicated.json \
  --output experiments/annotations/transfer_scope_v01/judge_runs/gpt-5.6-terra/evaluation.json
```

生成最终Process Verdict：

```bash
python -m src.verifiers.transfer_scope_verifier \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --judgments experiments/annotations/transfer_scope_v01/judge_runs/gpt-5.6-terra/judgments.json \
  --output experiments/annotations/transfer_scope_v01/judge_runs/gpt-5.6-terra/compliance_verdicts.json
```

## 当前结果

- Human Gold：10条，其中8条合规、2条违规。
- Semantic Judge：覆盖率100%，与Human Gold一致率90%。
- 唯一误判是Task 12的False Positive。
- Process Verifier基于Judge结果生成7条合规、3条违规，其中Task 12属于Judge误报。
