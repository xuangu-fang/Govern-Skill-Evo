# R05 冻结对照：Knowledge Only 与 Memory v3

按用户要求直接比较 R04–R06。本组仅运行 R05 的 Preconditioner / Replay × Memory v3 / Knowledge Only 四个单元。三轮使用各自目录独立运行，每轮内部沿用冻结的交替视图顺序。其余已准备单元不发请求。

实际 messages、当前事实、轮前 Memory、Prompt 和模型配置与 003 对应冻结单元完全相同。max_tokens=32,768，沿用每单元最多三次尝试，取首次结构有效输出，不作语义择优；不自动追加额度或修复响应。使用已修正的 Replay 正文引用扫描器，完整识别本轮并列引用；历史授权、evidence 数组、保存后重载规则保持不变。不修改原实验记录。

本次重点比较最终有效输出的判断与知识质量；失败重试成本不作为效果评价依据。运行器仍原样保存调用记录和 usage。若某单元没有有效输出，如实标明，不能从失败正文提取方案充当有效结果。

Preconditioner 检查修改依据、强度、可观察条件、阶段边界、历史条件和反例利用；Replay 检查当前事实准确性、反例、归因范围，以及发生旧 entry 修订时是否保留仍成立的知识。核查为本地读取，不额外调用评判模型。

每轮使用历史冻结 Memory，不传入本组新知识；Replay 使用原历史实际 Diff、Effective Plan 和配对轨迹，不使用本组新 Preconditioner 输出。不是连续 Memory 回放。不运行 Actor，不发布 Skill/Memory；固定轨迹对照不能证明任务成功率改善。

```bash
python -u -m src.skill_evolution.v23_5.comparison run --root artifacts/methods/v23_5/knowledge_only_single_round_008 --rounds R05 --stages preconditioner replay --arms memory_v3 knowledge_only
```

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。
