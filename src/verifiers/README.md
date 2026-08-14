# 任务结果与执行过程校验器

本目录负责检查 Agent 的任务运行记录。项目把两个问题分开判断：

1. **任务结果校验（Task Verifier）**：任务最终是否完成；
2. **执行过程校验（Process Verifier）**：Agent 完成任务时是否遵守规则。

因此，任务成功不一定代表过程合规，过程合规也不一定代表任务成功。

有些规则可以直接由代码判断，例如工具调用顺序；另一些规则需要理解自然语言，例如用户的请求是否应该转交人工。下文分别称为“确定性规则”和“AI 语义规则”。

## 文件说明

| 文件 | 作用 | 是否调用模型 |
|---|---|---|
| `schema.py` | 定义证据、违规、单条规则结果、总体合规结果及其保存格式。 | 否 |
| `task_verifier.py` | 将`Trajectory.outcome.score`转换为带证据的任务成功判断。 | 否 |
| `registry.py` | 登记每条规则由哪个处理程序负责，加载已保存的 AI 中间判断，并检查任务是否全部覆盖。 | 否 |
| `builtin_handlers.py` | 内置规则处理程序的登记入口。新增规则时在这里登记，不修改通用入口。 | 否 |
| `process_verifier.py` | 通用执行入口：逐条分发规则并汇总结果，本身不写死具体规则。 | 否 |
| `handlers/deterministic/` | 代码可以直接判断的规则，例如转人工顺序、工具调用与用户回复互斥、付款方式归属。 | 否 |
| `handlers/semantic/common.py` | AI 语义规则共用的模型调用和证据步骤转换。 | 是 |
| `handlers/semantic/transfer_scope.py` | 判断用户请求是否应该转人工，再与 Agent 的实际行为组合。 | 是 |
| `handlers/semantic/write_confirmation.py` | 判断写入数据前是否说明操作详情并得到明确确认。 | 是 |
| `evaluators/transfer_scope.py` | 将 AI 的转人工判断与人工标准答案比较。 | 否 |
| `evaluators/write_confirmation.py` | 将 AI 的写操作确认判断与人工标准答案比较。 | 否 |

## 通用执行过程校验器如何工作

通用执行过程校验器接收四类输入：任务运行记录、要检查的规则、判断规则所需的背景信息，以及 AI 规则已经生成的中间判断。它会让对应处理程序逐条检查规则，再汇总出最终结果：是否合规、违反了哪些规则、违规发生在哪一步，以及证据是什么。

图中的英文名称是代码里的正式对象名：

```text
TrajectoryDataset + PolicyRuleSet + VerificationContext
                         + Saved judgments
                              ↓
                     process_verifier.py
                              ↓
                       CheckerRegistry
                 ┌────────────┴────────────┐
                 ↓                         ↓
      deterministic handlers    semantic handlers
                 └────────────┬────────────┘
                              ↓
                 RuleVerdict[] → ProcessVerdict
```

`process_verifier.py` 不包含具体规则名。规则登记表会根据配置选择对应的处理程序，并在运行前检查：处理程序是否存在、AI 中间判断是否对应正确规则、所有任务是否都有结果。增加规则时，只需要实现新的处理程序，在 `builtin_handlers.py` 中登记，并更新规则 JSON。

任务结果校验器只读取上游任务结果，不判断过程是否合规。执行过程校验器也只检查当前规则文件明确列出的规则，不能据此宣称整个 Policy 已经被完整验证。

每条规则只能有三种结果：

- `compliant`：符合规则；
- `violation`：违反规则；
- `indeterminate`：证据不足，无法判断。

如果任务没有触发某条规则，该规则按合规处理。总体结果的计算方式是：只要有一项违规，结果就是 `false`；没有违规但至少一项无法判断，结果就是 `null`；其余情况为 `true`。配置错误或模型调用失败属于程序运行错误，不能伪装成“证据不足”。

## 当前检查的五条规则

当前统一运行使用`rules_v04.json`：

| 规则 | 类型 | 判断内容 |
|---|---|---|
| `airline.transfer.protocol.001` | 代码直接判断 | 转人工工具调用与规定提示语的顺序。 |
| `airline.tool.response_exclusivity.001` | 代码直接判断 | 同一条 Agent 消息是否同时包含用户回复和工具调用。 |
| `airline.payment.method.001` | 代码直接判断 | 付款方式是否已经存在于目标用户账户中。 |
| `airline.write.confirmation.001` | AI 理解语义 | 写数据库前是否列出操作详情并获得明确确认。 |
| `airline.transfer.scope.001` | AI 理解语义 | 用户请求是否应该转人工，以及 Agent 的实际行为是否正确。 |

AI 语义处理程序会先生成并保存结构化的中间判断，之后再与人工标签独立比较。通用过程校验器只读取已经保存的判断，并与代码从任务记录中提取的事实组合；汇总阶段不会再次调用模型。

### 工具调用与用户回复互斥规则

`airline.tool.response_exclusivity.001` 使用 `source_turn_idx` 还原 Agent 原始消息的边界。同一条消息包含多个工具调用本身不算违规，因为 τ³ 会逐个执行并记录这些调用；本规则只检查一条消息中是否同时存在面向用户的回复和工具调用。

## 常用命令

任务结果：

```bash
python -m src.verifiers.task_verifier \
  --input experiments/results/day5_schema/common_trajectories_v02.json \
  --output experiments/results/day5_schema/task_verdicts_v01.json
```

### 转人工范围规则

`airline.transfer.scope.001` 运行时会从统一任务记录、规则和带版本号的背景信息中临时组合 AI 输入，不为每个任务另存重复输入包。AI 只能看到 Policy、可用工具和规范化后的可见事件，看不到任务得分、隐藏任务信息、参考答案或原始模型响应。

生成中间语义判断和规则合规结果：

```bash
python -m src.verifiers.handlers.semantic.transfer_scope \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --rules policies/airline/rules_v04.json \
  --context policies/airline/transfer_scope_context_v01.json \
  --judgments-output transfer_scope_judgments_v01.json \
  --output transfer_scope_verdicts_v01.json
```

### 写操作确认规则

`airline.write.confirmation.001` 规则版本为 `0.1.0`，检查以下会修改预订数据的工具：

- `book_reservation`
- `cancel_reservation`
- `update_reservation_baggages`
- `update_reservation_flights`
- `update_reservation_passengers`

`send_certificate` 虽然在工具目录中被标记为写操作，但它不会修改预订，因此暂不在本规则范围内。AI 会分别判断每次受检查的写操作是否说明了足够详情、是否获得有效确认，并记录相应的详情步骤和确认步骤。代码再负责检查这些引用是否存在、顺序是否正确，以及所有写操作是否都已覆盖。

生成中间语义判断：

```bash
python -m src.verifiers.handlers.semantic.write_confirmation \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --rules policies/airline/rules_v04.json \
  --context policies/airline/write_confirmation_context_v01.json \
  --output write_confirmation_judgments_v01.json
```

与人工标准答案比较（不会调用模型）：

```bash
python -m src.verifiers.evaluators.write_confirmation \
  --judgments experiments/annotations/write_confirmation_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --gold experiments/annotations/write_confirmation_v01/gold/human_adjudicated.json \
  --output experiments/annotations/write_confirmation_v01/semantic_runs/gpt-5.6-terra/evaluation.json
```

### 付款方式归属规则

`airline.payment.method.001`的`statement`直接引用Policy原文：`All payment methods must already be in user profile for safety reasons.`

当前校验程序覆盖三个带有明确付款参数的写工具：

- `book_reservation.payment_methods[*].payment_id`
- `update_reservation_flights.payment_id`
- `update_reservation_baggages.payment_id`

校验程序只使用写操作之前 Agent 已经看到的证据。订票时通过 `user_id` 定位账户；修改预订时，先通过 `get_reservation_details` 确定预订属于哪个用户，再与该用户资料中的付款方式比较。付款 ID 不在账户中时判为违规；执行了受检查的写操作，但缺少用户资料、预订归属或无法解析付款参数时判为证据不足；没有执行相关写操作时判为合规。

### 运行当前五条规则

执行过程校验器读取两份已经保存的 AI 中间判断；另外三条确定性规则只由代码检查，不会调用模型：

```bash
python -m src.verifiers.process_verifier \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --rules policies/airline/rules_v04.json \
  --judgments airline.transfer.scope.001=experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --judgments airline.write.confirmation.001=experiments/annotations/write_confirmation_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --output experiments/results/day6_process_verifier/process_verdicts_v04.json
```

“是否应该转人工”中间判断的完整生成和评估顺序见：

[`../../experiments/annotations/transfer_scope_v01/README.md`](../../experiments/annotations/transfer_scope_v01/README.md)
