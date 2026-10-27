# R03 Replay Knowledge Only：用户授权的补充重试

003 的前两次响应被历史引用扫描器拒绝，第三次达到输出上限；用户明确要求继续重试。本组只执行 R03 / replay / knowledge_only，最多追加三次，首次结构有效即停止，不作语义择优。

实际 messages、Prompt、max_tokens=32,768 及其他配置与 003 完全相同。保留现有引用权限、扫描规则、精确校验与保存后重载；不改写斜杠引用，不修复响应。003 失败及 token 消耗全部保留。本组属于失败后的授权补充，不是独立对称重复实验；累计成本须计入所有请求。

复用运行器准备 R03–R06 的材料，但其他单元不发请求。不启动 Actor，不发布 Skill 或 Memory，Replay 仍使用冻结历史实际 Diff、Effective Plan 和配对执行。额度用尽后不自动追加。

```bash
python -u -m src.skill_evolution.v23_5.comparison run \
  --root artifacts/methods/v23_5/knowledge_only_single_round_006 \
  --rounds R03 --stages replay --arms knowledge_only
```

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。
