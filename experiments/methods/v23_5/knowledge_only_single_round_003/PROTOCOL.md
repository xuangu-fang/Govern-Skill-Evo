# Knowledge Only：R03 输出协议完善后的单轮对照

问题与假设沿用 [001 协议](../knowledge_only_single_round_001/PROTOCOL.md)：Knowledge Only 能否降低历史输入，同时保留 Preconditioner 判断与 Replay 条件性知识？本次另外观察已明确的输出协议能否被模型遵守，但只有一轮、每单元一份有效样本，不能证明错误率稳定下降。

本组由用户在输出协议完善后要求重新启动。统一 max_tokens=32,768，deepseek-v4.1-flash，temperature=1.0，reasoning_effort=medium，thinking enabled，timeout=300 秒；其他参数与 001 完全相同。当前 Preconditioner 两版 Prompt 明确“正式 ID 必须逐个用单反引号包围，普通文字和动作命令不用反引号”，并使用已完成的 JSON、引用和补丁错误定位。

## 范围与约束

- 复用现有运行器冻结 R03–R06 输入，本次仅运行 R03 的 Preconditioner / Replay × Memory v3 / Knowledge Only 四个单元。
- 每单元最多三次总尝试，取首个结构有效输出，不按语义挑选；不扩大预算、不追加修复提示、不自动修改响应。
- 当前事实、Original Plan、配对轨迹及轮前 Memory 与 001 一致。只改变 Preconditioner 系统 Prompt 的公共输出协议措辞；Replay 两版实际 messages 与 001 一致。
- Preconditioner 与 Replay 独立评估；Replay 使用历史实际 Diff、Effective Plan 和配对轨迹，不使用本组 Preconditioner 新输出。不运行 Actor，不发布 Skill 或 Memory。
- 001、002 已停止的输入、配置、Prompt 和结果全部保留，不 resume 或改写。003 的输入和成本独立记录。

## 执行

```bash
python -u -m src.skill_evolution.v23_5.comparison run \
  --root artifacts/methods/v23_5/knowledge_only_single_round_003 \
  --rounds R03 --stages preconditioner replay --arms memory_v3 knowledge_only
```

成本统计包含全部失败尝试，以 API usage 为准；缺失 usage 记为未知。判断质量与知识保留另行核查，结构通过不等于语义正确。结果不能证明新 Skill 的任务成功率提高。

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。
