# τ³ Manual Skill Adapter

本目录保存让 τ³ Agent 读取项目内人工 Skill 的本地适配补丁。

## 补丁内容

补丁会：

1. 新增 `ManualSkillAgent`；
2. 从 `TAU2_AGENT_SKILL_PATH` 读取 `SKILL.md`；
3. 将 Skill 正文加入 Agent system prompt；
4. 注册 `llm_agent_manual_skill` Agent。

## 应用补丁

仅在一份未修改的 `external/tau2-bench` 中执行：

```bash
git -C external/tau2-bench apply \
  ../../src/adapters/tau2/manual_skill_agent.patch
```

当前本地 `tau2-bench` 已经包含这些修改，不需要重复应用。

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