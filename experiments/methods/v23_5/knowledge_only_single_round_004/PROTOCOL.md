# R03 Preconditioner Knowledge Only：用户授权的补充重试

问题：在 003 组 Knowledge Only 连续两次 length 和一次 JSON 失败后，同一协议的额外有限尝试能否得到可校验的方案？本组是观察失败后由用户明确要求的继续重试，不是独立的对称重复实验。

## 固定条件与授权范围

- 仅执行 R03 / preconditioner / knowledge_only，最多新增三次请求，取首个结构有效结果。
- 输入、Prompt、32,768 输出上限、模型、temperature、reasoning_effort、thinking、300 秒超时与 003 完全一致。
- 为复用既有运行器准备相同 R03–R06 输入；实际只运行上述一个单元。其余单元不发请求。
- 不重置或改写 003 的三个失败尝试；004 保存新增记录。003 已在执行的 Replay 按原预算继续。
- 这次增加额度来自用户明确指令，不改变自动重试机制。新增次数用尽后不自行追加。

## 统计边界

004 与 003 分开记录，同时报告 Preconditioner Knowledge Only 两组累计请求与 usage。后续即使补充重试成功，也不能把原始 003 结果改成首轮成功；不能把两视图当作仍具有对称尝试额度。所有失败计入成本，不按语义质量挑选结果。
不调用 Actor，不发布 Skill 或 Memory。结构有效不等于 D/S/C 判断正确，仍需阅读有效方案。

```bash
python -u -m src.skill_evolution.v23_5.comparison run \
  --root artifacts/methods/v23_5/knowledge_only_single_round_004 \
  --rounds R03 --stages preconditioner --arms knowledge_only
```

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](README.md)。
