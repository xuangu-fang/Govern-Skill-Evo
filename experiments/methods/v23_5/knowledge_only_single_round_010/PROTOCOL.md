# R05 Preconditioner Memory v3：授权补充重试

用户在 008 三次引用格式失败后明确要求继续重试。本组仅执行 R05 / preconditioner / memory_v3，最多追加三次，首次结构有效即停止，不作语义择优。实际 messages、Prompt、模型参数与 008 完全相同，max_tokens=32,768。保留原失败记录，不修复响应，不放宽引用权限。其他已经授权的单元继续运行。

本组用于补齐有效输出的质量比较，不以失败重试成本评价效果；调用与 usage 仍正常留档。固定历史事实与轮前 Memory，不运行 Actor，不发布 Skill 或 Memory。

```bash
python -u -m src.skill_evolution.v23_5.comparison run --root artifacts/methods/v23_5/knowledge_only_single_round_010 --rounds R05 --stages preconditioner --arms memory_v3
```

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。
