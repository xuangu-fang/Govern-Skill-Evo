# Transfer-scope Semantic Process Verifier标注实验

本目录保存`airline.transfer.scope.001`的标注与评估数据。该规则判断：用户请求无法在Agent的Policy权限和工具范围内处理时，是否正确转交人工。

当前数据覆盖Task 5–14，共10条轨迹。Task 5–9沿用原运行结果，Task 10–14来自新增运行结果。

## 目录结构

```text
transfer_scope_v01/
├── gold/
│   └── human_adjudicated.json
└── semantic_runs/
    └── gpt-5.6-terra/
        ├── judgments.json
        ├── evaluation.json
        └── compliance_verdicts.json
```

## 文件职责

| 路径 | 内容 | 维护方式 | 保存规则 |
|---|---|---|---|
| `gold/human_adjudicated.json` | 人工确认的`should_transfer`和合规标签。 | 人工审核后维护。 | 不得用模型输出自动覆盖。 |
| `semantic_runs/*/judgments.json` | Semantic Process Verifier保存的中间AI语义判断。 | 模型运行生成。 | 正式结果不得覆盖；重复运行使用新的run目录。 |
| `semantic_runs/*/evaluation.json` | 中间语义判断与Human Gold的覆盖率、准确率、混淆矩阵和逐条对比。 | 评估脚本生成。 | 与对应judgments一起保存，不覆盖其他run。 |
| `semantic_runs/*/compliance_verdicts.json` | 结合AI语义判断与轨迹中实际转人工事实得到的最终Process Verdict。 | Semantic Process Verifier生成。 | 与对应judgments一起保存，不覆盖其他run。 |

## 动态语义输入与信息隔离

Transfer-scope不保存逐Task Packet。人工审核或Semantic Process Verifier运行时，从以下版本化来源动态构造受控语义输入：

- `experiments/results/day5_schema/common_trajectories_v02.json`；
- `policies/airline/rules_v04.json`；
- `policies/airline/transfer_scope_context_v01.json`。

受控输入不包含：

- task reward和reward breakdown；
- 隐藏用户指令；
- 参考答案或reference actions；
- Human Gold；
- 轨迹中不可见的数据库状态。

因此Semantic Process Verifier只能依据Policy、工具能力和当前可见轨迹作出判断。

## 正确运行顺序

```text
统一TrajectoryDataset
    ↓
读取PolicyRule和VerificationContext
    ↓
动态构造受控语义输入
    ├── 人工审核并冻结Human Gold
    └── 运行Semantic Process Verifier
            ├── 保存中间AI语义判断
            └── 生成最终合规结果
    ↓
中间语义判断与Human Gold评估
```

Human Gold必须先完成人工审核，之后才能评估Semantic Process Verifier。不能根据模型结果反向修改Gold以提高准确率。

## 当前Transfer-scope验证链路

加载本地环境变量：

```bash
set -a
source .env
set +a
```

调用AI生成10条语义判断，并生成最终ComplianceVerdict：

```bash
python -m src.verifiers.handlers.semantic.transfer_scope \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --rules policies/airline/rules_v04.json \
  --context policies/airline/transfer_scope_context_v01.json \
  --judgments-output experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --output experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/compliance_verdicts.json
```

与Human Gold比较：

```bash
python -m src.verifiers.evaluators.transfer_scope \
  --judgments experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --gold experiments/annotations/transfer_scope_v01/gold/human_adjudicated.json \
  --output experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/evaluation.json
```

## 当前结果

- Human Gold：10条，其中8条合规、2条违规。
- Semantic Process Verifier：覆盖率100%，中间语义判断与Human Gold一致率90%。
- 唯一误判是Task 12的False Positive。
- Semantic Process Verifier生成7条合规、3条违规，其中Task 12属于AI语义误报。
