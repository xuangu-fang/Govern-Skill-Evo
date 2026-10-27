# Knowledge Only：R03 输出预算翻倍对照

问题和假设沿用 [001 协议](../knowledge_only_single_round_001/PROTOCOL.md)。
本组由用户在 001 的 Preconditioner Memory v3 三次失败后提出，属于后续预算调整实验，不能当作事先固定预算的独立重复。

## 本组变更与运行范围

仅将四个单元统一的 `max_tokens` 从 32,768 提高到 65,536；模型、temperature=1.0、reasoning_effort=medium、thinking enabled、timeout=300 秒、每单元最多三次总尝试和输入内容均保持不变。
仍冻结 R03–R06 输入以复用现有运行器，本次只运行 R03 的 Preconditioner / Replay × Memory v3 / Knowledge Only，共四个单元。R04–R06 不发请求。
采用第一个结构有效响应，不挑选语义最优样本。失败后不自动继续提高预算或调整 Prompt。

## 与 001 的关系

001 的 Preconditioner Memory v3 三次分别因 JSON 正文混入额外文本、引用格式不合法、输出长度耗尽而失败。翻倍预算仅直接针对长度不足，不保证解决其余错误。
用户要求重启实验时，001 的 Preconditioner Knowledge Only 首次响应已因引用越界失败，第二次请求正在等待，已中止本地进程；该次无服务响应，usage 记为未知，不记为零。旧原始记录全部保留，001 成本与 002 分开统计。
新组从相同轮前 Memory 与当前事实重新运行全部四个单元，不复用 001 的输出。调用前直接比较两组实际 messages 与参数，确认只改变输出上限，不使用文件指纹。

## 执行与结果

```bash
python -u -m src.skill_evolution.v23_5.comparison run \
  --root artifacts/methods/v23_5/knowledge_only_single_round_002 \
  --rounds R03 --stages preconditioner replay --arms memory_v3 knowledge_only
```

其余引用、补丁、usage 与语义核查口径沿用 001 协议。Preconditioner 与 Replay 独立评估；Replay 使用历史实际修改与配对轨迹，不使用新 Preconditioner 方案。不重跑 Actor，不发布 Skill 或 Memory，不据此推断成功率提高。

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。
