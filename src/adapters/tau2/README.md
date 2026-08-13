# τ³ Adapter

本目录负责把第三方基准测试 τ³ 接入本项目，包含两项功能：把 τ³ 的运行结果转换成本项目统一格式，以及让 Agent 读取项目中的人工 Skill。Adapter 在这里指“连接两套不同数据或运行方式的适配程序”。

## 文件说明

| 文件 | 作用 |
|---|---|
| `tau2_to_common.py` | 将τ³ `results.json`直接转换为正式`TrajectoryDataset`。 |
| `manual_skill_agent.patch` | 为外部τ³代码增加读取本地`SKILL.md`的Agent。 |

## 转换轨迹

从项目根目录运行：

```bash
python -m src.adapters.tau2.tau2_to_common \
  --input path/to/results.json \
  --output path/to/common_trajectories.json
```

转换器会保留源文件中的原始内容（代码字段名为 `payload`），并使用 `src/trajectory/schema.py` 检查输出格式。新产生的任务记录应直接使用该转换器，不需要再经过旧格式迁移脚本。

## 本地补丁做了什么

补丁会：

1. 新增 `ManualSkillAgent`；
2. 从 `TAU2_AGENT_SKILL_PATH` 读取 `SKILL.md`；
3. 将 Skill 正文加入 Agent system prompt；
4. 注册 `llm_agent_manual_skill` Agent。

## 何时需要应用补丁

仅在一份未修改的 `external/tau2-bench` 中执行：

```bash
git -C external/tau2-bench apply \
  ../../src/adapters/tau2/manual_skill_agent.patch
```

当前本地 `tau2-bench` 已经包含这些修改，通常不需要再次应用。只有重新取得一份未经修改的 `external/tau2-bench` 时，才需要执行上述命令。

## 运行 Human Skill 实验

从项目根目录进入 `tau2-bench`：

```bash
cd external/tau2-bench
```

设置 Skill 路径并运行：

```bash
TAU2_AGENT_SKILL_PATH="$(cd ../.. && pwd)/skills/manual_v0/SKILL.md" \
tau2 run \
  --domain airline \
  --agent llm_agent_manual_skill \
  --agent-llm openai/gpt-5.4 \
  --user-llm openai/gpt-5.4 \
  --num-trials 1 \
  --task-ids 5 \
  --save-to 20260730_task5_manual_v0_smoke
```

未设置 `TAU2_AGENT_SKILL_PATH` 时，`llm_agent_manual_skill` 会停止并提示缺少 Skill 文件。
