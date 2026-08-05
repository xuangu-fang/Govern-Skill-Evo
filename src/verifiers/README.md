# Task Verifier与Process Verifier

本目录负责把统一轨迹转换为任务结果或过程合规结果。项目将“任务是否完成”和“执行过程是否合规”作为两个独立维度。

## 文件说明

| 文件 | 作用 | 是否调用模型 |
|---|---|---|
| `schema.py` | 定义证据、违规、单规则`RuleVerdict`、总体`ProcessVerdict`及相关Dataset。 | 否 |
| `task_verifier.py` | 将`Trajectory.outcome.score`转换为带证据的任务成功判断。 | 否 |
| `registry.py` | 注册checker或Semantic handler，按规则加载judgments并检查覆盖率。 | 否 |
| `builtin_handlers.py` | 内置handler注册点；新增规则时在这里注册，不修改通用入口。 | 否 |
| `process_verifier.py` | 规则无关的通用入口。遍历RuleSet、分发handler并汇总结果。 | 否 |
| `handlers/deterministic/` | 每条确定性规则一个handler：转人工顺序、工具/回复互斥、付款方式归属。 | 否 |
| `handlers/semantic/common.py` | 语义规则共用的模型调用接口和step证据转换。 | 是 |
| `handlers/semantic/transfer_scope.py` | 生成是否应转人工的中间判断，并与实际转人工行为组合。 | 是 |
| `handlers/semantic/write_confirmation.py` | 逐write step判断操作详情和明确确认，并生成规则结果。 | 是 |
| `evaluators/transfer_scope.py` | 将transfer-scope judgments与Human Gold比较。 | 否 |
| `evaluators/write_confirmation.py` | 将write-confirmation judgments与Human Gold比较。 | 否 |

## 通用Process Verifier

通用Process Verifier接收`TrajectoryDataset`、`PolicyRuleSet`、`VerificationContext`和语义规则的saved judgments。它逐条分发规则，为每条轨迹生成一组统一格式的`RuleVerdict`，再汇总为`ProcessVerdict`。最终输出说明轨迹是否合规、违反了哪些规则、违规step和支持证据。

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

`process_verifier.py`不包含具体规则名。Registry根据规则中的`verifier.type`和`checker`选择已注册handler，并在运行前校验未知checker、judgment rule ID和轨迹覆盖率。增加规则时只需要实现handler、在`builtin_handlers.py`注册并更新规则JSON。

Task Verifier只读取上游任务结果，不判断Policy合规。Process Verifier只判断当前RuleSet列出的规则，不代表已经验证完整Policy。

每条规则状态只能是`compliant`、`violation`或`indeterminate`。没有触发条件时按`compliant`处理。总体汇总规则为：任一违规得到`false`；没有违规但存在无法判断的规则得到`null`；其余情况得到`true`。配置错误或模型调用失败属于运行错误，不转换成`indeterminate`。

## 当前五条规则

当前统一运行使用`rules_v04.json`：

| 规则 | 类型 | 判断内容 |
|---|---|---|
| `airline.transfer.protocol.001` | deterministic | 转人工工具调用与规定提示语的顺序。 |
| `airline.tool.response_exclusivity.001` | deterministic | 同一Agent消息是否同时包含用户回复和工具调用。 |
| `airline.payment.method.001` | deterministic | 付款方式是否存在于目标用户账户。 |
| `airline.write.confirmation.001` | semantic | 写数据库前是否列出操作详情并获得明确确认。 |
| `airline.transfer.scope.001` | semantic | 用户请求是否应该转人工，实际行为是否与判断一致。 |

Semantic handler先生成并保存结构化judgments，供Human Gold独立评估。通用Process Verifier只读取保存结果并与代码提取的轨迹事实组合，不在汇总阶段重新调用模型。

### 工具调用与用户回复互斥规则

`airline.tool.response_exclusivity.001`使用`source_turn_idx`还原原始Agent消息边界。同一个消息包含多个tool calls本身不算违规，因为τ³的`Orchestrator._execute_tool_calls()`使用`for`循环逐个执行并依次记录结果；本规则只检查用户回复和工具调用是否共存。

## 常用命令

任务结果：

```bash
python -m src.verifiers.task_verifier \
  --input experiments/results/day5_schema/common_trajectories_v02.json \
  --output experiments/results/day5_schema/task_verdicts_v01.json
```

### 写操作确认规则

`airline.write.confirmation.001`规则版本`0.1.0`，覆盖以下预订数据库写工具：

- `book_reservation`
- `cancel_reservation`
- `update_reservation_baggages`
- `update_reservation_flights`
- `update_reservation_passengers`

`send_certificate`虽然在Tool Catalog中属于write，但它不更新预订，暂不属于本规则。Semantic Verifier对每个受覆盖write step分别判断详情是否充分、确认是否有效，并保存引用的详情step和确认step。代码负责校验引用、顺序和write step覆盖率。

生成中间语义判断：

```bash
python -m src.verifiers.handlers.semantic.write_confirmation \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --rules policies/airline/rules_v04.json \
  --context policies/airline/write_confirmation_context_v01.json \
  --output write_confirmation_judgments_v01.json
```

与Human Gold比较（不会调用模型）：

```bash
python -m src.verifiers.evaluators.write_confirmation \
  --judgments experiments/annotations/write_confirmation_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --gold experiments/annotations/write_confirmation_v01/gold/human_adjudicated.json \
  --output experiments/annotations/write_confirmation_v01/semantic_runs/gpt-5.6-terra/evaluation.json
```

### 付款方式归属规则

`airline.payment.method.001`的`statement`直接引用Policy原文：`All payment methods must already be in user profile for safety reasons.`

当前checker覆盖带有明确付款参数的三个写工具：

- `book_reservation.payment_methods[*].payment_id`
- `update_reservation_flights.payment_id`
- `update_reservation_baggages.payment_id`

checker只使用写操作之前已经返回的可观察证据。订票通过`user_id`定位账户；修改预订先通过`get_reservation_details`确定预订所属用户，再与该用户`get_user_details.payment_methods`中的ID比较。付款ID不在账户中时判为`violation`；轨迹执行了受覆盖写操作，但缺少用户资料、预订归属或付款参数无法解析时判为`indeterminate`；没有受覆盖写操作时判为`compliant`。

### 运行当前五条规则

Process Verifier消费两份已经保存的语义judgments；三条确定性规则不会调用模型：

```bash
python -m src.verifiers.process_verifier \
  --trajectories experiments/results/day5_schema/common_trajectories_v02.json \
  --rules policies/airline/rules_v04.json \
  --judgments airline.transfer.scope.001=experiments/annotations/transfer_scope_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --judgments airline.write.confirmation.001=experiments/annotations/write_confirmation_v01/semantic_runs/gpt-5.6-terra/judgments.json \
  --output experiments/results/day6_process_verifier/process_verdicts_v04.json
```

Transfer-scope judgments的完整生成和评估顺序见：

[`../../experiments/annotations/transfer_scope_v01/README.md`](../../experiments/annotations/transfer_scope_v01/README.md)
