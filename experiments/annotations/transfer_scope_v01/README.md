# “是否应该转人工”语义校验实验

本目录保存规则 `airline.transfer.scope.001` 的人工标注、AI 判断和评估结果。该规则要判断：当用户请求超出 Agent 的规则权限或工具能力时，Agent 是否正确转交人工。

代码中把这类需要理解语义的检查称为 Semantic Process Verifier（语义过程校验器）。人工标签由人工审核确认，用于衡量 AI 判断是否可靠，不能由模型自动生成或改写。

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
| `gold/human_adjudicated.json` | 人工确认“是否应该转人工”以及最终是否合规。 | 人工审核后维护。 | 不得用模型输出自动覆盖。 |
| `semantic_runs/*/judgments.json` | AI 对“是否应该转人工”作出的中间判断。 | 模型运行生成。 | 正式结果不得覆盖；重复运行使用新的运行目录。 |
| `semantic_runs/*/evaluation.json` | AI 判断与人工标准答案的覆盖率、准确率、分类统计和逐条对比。 | 评估脚本生成。 | 与对应判断一起保存，不覆盖其他运行。 |
| `semantic_runs/*/compliance_verdicts.json` | 结合 AI 判断和 Agent 实际是否转人工，得到最终合规结果。 | 语义过程校验器生成。 | 与对应判断一起保存，不覆盖其他运行。 |

## AI 判断时能看到什么

系统不为每个任务另存一份重复的输入包。人工审核或 AI 校验运行时，会从以下带版本号的文件中临时组合输入：

- `experiments/results/day5_schema/common_trajectories_v02.json`；
- `policies/airline/rules_v04.json`；
- `policies/airline/transfer_scope_context_v01.json`。

为防止答案泄漏，AI 看不到以下内容：

- task reward和reward breakdown；
- 隐藏用户指令；
- 参考答案或reference actions；
- 人工标准答案；
- 轨迹中不可见的数据库状态。

因此，AI 只能依据规则、工具能力和 Agent 当时可见的交互内容作出判断。

## 正确运行顺序

```text
统一TrajectoryDataset
    ↓
读取规则和校验所需背景信息
    ↓
动态构造受控语义输入
    ├── 人工审核并锁定标准答案
    └── 运行AI语义校验
            ├── 保存中间AI语义判断
            └── 生成最终合规结果
    ↓
将AI中间判断与人工标准答案比较
```

必须先完成人工审核并锁定标准答案，之后才能评估 AI。不能根据模型结果反过来修改人工答案以提高准确率。

## 如何重新运行

加载本地环境变量：

```bash
set -a
source .env
set +a
```

调用 AI 生成10条语义判断，并进一步生成最终合规结果：

```bash
python -m src.verifiers.handlers.semantic.transfer_scope \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --rules policies/airline/rules_v04.json \
  --context policies/airline/transfer_scope_context_v01.json \
  --judgments-output experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --output experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/compliance_verdicts.json
```

与人工标准答案比较：

```bash
python -m src.verifiers.evaluators.transfer_scope \
  --judgments experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --gold experiments/annotations/transfer_scope_v01/gold/human_adjudicated.json \
  --output experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/evaluation.json
```

## 当前结果

- 人工标准答案共10条，其中8条合规、2条违规。
- AI 完成了全部10条判断，与人工答案的一致率为90%。
- 唯一误判是任务12：AI 将实际不应判为违规的情况误报为违规。
- 最终 AI 结果为7条合规、3条违规，其中任务12属于误报。
