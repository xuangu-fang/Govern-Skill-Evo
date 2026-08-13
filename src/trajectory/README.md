# 统一任务交互记录格式

本目录把不同来源的 Agent 运行记录整理成同一种结构，使后续程序可以稳定读取、保存和检查。代码中把一次完整任务运行称为 `Trajectory`（轨迹），把格式规则称为 `Schema`。

校验程序和后续学习模块都应读取这里定义的统一格式，不能直接依赖 τ³ 等外部系统各自的原始 JSON 结构。

## 文件说明

| 文件 | 作用 |
|---|---|
| `schema.py` | 定义一批任务记录、单次任务记录、消息、工具调用、环境信息和任务结果的格式。 |
| `migrations/v01_to_v02.py` | 将早期临时格式 v0.1 转换为当前正式格式 v0.2.0。 |
| `__init__.py` | Python包入口。 |

## 主要对象

| 对象 | 含义 |
|---|---|
| `TrajectoryDataset` | 使用同一种格式保存的一批任务运行记录。 |
| `Trajectory` | 一次完整任务运行，包括环境、任务编号、事件顺序和最终结果。 |
| `MessageEvent` | 用户或 Agent 的自然语言消息。 |
| `ToolCallEvent` | Agent发起的工具调用。 |
| `ToolResultEvent` | 与前序工具调用对应的工具结果。 |
| `TaskOutcome` | 上游基准测试给出的任务得分和结束信息。 |
| `EnvironmentRef` | 记录任务来自哪个环境、业务领域及版本。 |

每个事件都有连续的 `step_id`，用于表示发生顺序。`state_delta=None` 表示源数据没有提供可恢复的状态变化信息，不代表“状态确实没有变化”。`raw_payload` 保存转换前的原始内容，便于追查证据。

## 格式会检查什么

`schema.py`会检查：

- `step_id`从0开始且连续；
- `tool_call_id`不重复；
- Tool Result必须对应前面已经出现的Tool Call；
- Tool Call与Tool Result的工具名称一致；
- 未声明字段不能静默进入正式Schema。

未完成的轨迹允许最后一个Tool Call暂时没有Tool Result。

## 新轨迹与旧轨迹

新产生的τ³轨迹应直接通过Adapter生成正式Schema：

```bash
python -m src.adapters.tau2.tau2_to_common \
  --input path/to/results.json \
  --output path/to/common_trajectories.json
```

只有早期临时common trajectory才需要迁移脚本：

```bash
python -m src.trajectory.migrations.v01_to_v02 \
  --input path/to/common_trajectories_v01.json \
  --output path/to/common_trajectories_v02.json
```

迁移脚本不是新轨迹的必经步骤。
