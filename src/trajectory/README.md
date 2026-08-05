# 统一Trajectory Schema

本目录负责把不同来源的Agent运行记录表示成统一、可校验、可序列化的轨迹格式。Verifier和后续学习模块都应读取这里定义的正式Schema，而不是直接依赖τ³原始JSON结构。

## 文件说明

| 文件 | 作用 |
|---|---|
| `schema.py` | 定义当前正式的`TrajectoryDataset`、`Trajectory`、事件类型、环境信息和任务结果。 |
| `migrations/v01_to_v02.py` | 将早期临时common trajectory v0.1迁移为正式Schema v0.2.0。 |
| `__init__.py` | Python包入口。 |

## 主要对象

| 对象 | 含义 |
|---|---|
| `TrajectoryDataset` | 一批使用相同Schema的统一轨迹。 |
| `Trajectory` | 一次完整任务运行，包括环境、Task ID、事件序列和任务结果。 |
| `MessageEvent` | 用户或Agent的自然语言消息。 |
| `ToolCallEvent` | Agent发起的工具调用。 |
| `ToolResultEvent` | 与前序工具调用对应的工具结果。 |
| `TaskOutcome` | 上游benchmark给出的任务得分和终止信息。 |
| `EnvironmentRef` | 轨迹来源的环境名称、Domain和可选版本。 |

每个Event都包含连续的`step_id`。`state_delta=None`表示源数据没有提供可恢复的状态变化，不代表“状态没有变化”。`raw_payload`用于保留转换前的原始证据。

## Schema校验

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
