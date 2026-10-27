# R03 Replay Memory v3：用户授权的补充重试

问题：003 组 Replay Memory v3 在两次 JSON 失败、一次 length 后，同协议的额外有限尝试能否得到可校验结果？本组由用户观察到原三次失败后明确授权，不是独立的对称重复实验。

仅执行 R03 / replay / memory_v3，最多新增三次请求，取首个结构有效结果。实际输入、Prompt、max_tokens=32,768、模型及其他调用参数与 003 完全相同；不修复响应、不扩展输出预算。复用现有运行器准备 R03–R06 材料，其余单元不发请求。

003 原始失败保留，005 记录新尝试；累计报告 Replay Memory v3 的所有请求与 usage。不能把补充成功写回原始结果，不能将继续重试后的两视图成本视为相同额度下的独立对照。额度用尽后不自动追加。正在执行的其他已授权单元继续。

不重跑 Actor，不发布 Skill 或 Memory。Replay 使用固定历史实际 Diff、Effective Plan 和配对轨迹；本组不使用新 Preconditioner 输出。

```bash
python -u -m src.skill_evolution.v23_5.comparison run \
  --root artifacts/methods/v23_5/knowledge_only_single_round_005 \
  --rounds R03 --stages replay --arms memory_v3
```

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。
