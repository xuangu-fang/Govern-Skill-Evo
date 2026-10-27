# R06：重新 Diagnosis 后的 Goal / Update / Check 核对

日期：2026-10-22（Asia/Shanghai）。使用相同 R06 当前事实重新生成 V23.4 Diagnosis，冻结首次合法 Plan，再配原有 Memory 运行 Preconditioner。**原先“关闭状态直接执行”与冻结 Goal 要求打开状态的冲突在本次结果中消失；但保留的 c2 对最终 u2 的检查覆盖仍不充分，不能判为完整语义通过。**

## 执行与冻结

- Diagnosis：首次合法，58.575 秒，生成两个 Updates（u1、u2）及两个 Checks。
- Preconditioner：首次技术失败，206.600 秒。删除行遗漏 Original 文本自身的 Markdown 列表符号 `-`，严格 Patch 应用报 `Parent context/deletion text differs at declared position`；没有自动修补输出。
- 第 1 次技术重启合法，191.473 秒。冻结的 Plan、Memory、Prompt 和调用参数完全不变。选择第二次输出后不因语义质量再次采样。
- 共 2 个逻辑阶段、3 次 HTTP、1 次技术重启。API 报告累计 prompt 556,799、completion 67,980、total 624,779 tokens，包含失败尝试；费用未知。
- 没有修改生产 Prompt、校验器或算法，没有运行 Editor、Actor、Replay 或额外审查模型。旧实验结果保留。本次新 Plan 结果不替换旧 Plan 已暴露的冲突。

Diagnosis 的解码用户消息与原始 R06 归档逐值相等，包含相同 Parent、命令集、P1–P7 当前轨迹和 Grouping；不含 Memory。原有 7 条 Memory 从上一实验逐值复制，Preconditioner 继续使用现有 Memory 投影方式。标准 Plan 证据选择本次仍保留 P1–P7。

第一次调用前冻结源码、输入和参数；Diagnosis 成功后，第二阶段调用前再次冻结其输出、派生输入和完整消息。原始输出没有人工改写。详见 [PROTOCOL.md](PROTOCOL.md)、[初始冻结](config/freeze.json)、[交接冻结](handoff/freeze.json)、[AUDIT.json](AUDIT.json)。

## 核对结果

| 对象 | 实际结果 | 判断 |
|---|---|---|
| 新 Diagnosis Goal | 要求搜索扩展、停止循环；持有精确目标直接执行温变、避免反复开关；保留精确类别和成功交付 | 不再把家电打开状态写进 Goal；仍保留持有目标这一具体边界 |
| Original u2 | 仍写 `at the open appliance`、`at the open fridge` | 实现条件位于可调整的 Update 内，不再被 Goal 锁死 |
| Effective u2 | 显式温变动作可用即执行，包括未开门时；只有动作不可用时才开门；一次温变后交付 | 与冻结 Goal 的持有目标、避免反复开关相容 |
| c2 | 保留原文：对 `co-located/held target` 直接执行、避免反复开关/放取，然后交付 | 不要求打开，旧冲突消失；但条件和覆盖不足，见下文 |
| Effective u1 | 个体容器/表面各自作为候选，继续跨类别扩展，优先未探索处，保留退出空地点、停止反复访问与不反复查空库存 | 与 Goal 的扩展和停止循环方向相容；c1 对搜索主线相容，但不覆盖每个操作条款 |
| Goal 保留边界 | 精确类别、直接冷却、顺序交付两个物品 | 两个 Updates 未明确撤回这些行为；没有 Editor/Actor 证据证明最终 Skill 实现和执行已保留 |

这里的“相容”是对生成文本的人工判断，不表示所有条件等价，也不等于 Actor 成功。

### 原先的打开状态冲突

新 Goal 中的温变要求为：

> heat/cool conditioning with an appliance must be performed directly on the held target without repeated door toggling.

最终 u2 保留这两个边界，把开门变成动作不可用时才执行的条件步骤。因此，允许在关闭家电处直接温变不会违反此 Goal。c2 同样没有“必须打开”的要求。编译后 Goal 与新 Diagnosis Goal 完全一致，没有通过偷偷改 Goal 消除冲突。

依据核对：P1:36 的 **after** 状态是关闭的 fridge，C22 已包含 `cool plate 1 with fridge 1`；P4:4 的 **after** 状态是关闭的 microwave，C50 已包含 `heat tomato 2 with microwave 1`。因此本次 reason 的 P4:4 引用可定位到正确证据，不是错一拍的无效引用。M7 的 S1_R04/Q3:5、Q4:5 还提供关闭微波炉时实际加热的历史记录。当前命令可用性不单独证明未执行的反事实结果，也不把微波炉历史成功无限推广到所有家电。

### 尚未解决：c2 与最终决策的覆盖

`checks: null` 合法地保留原 Checks，但 c2 没有明确检查 u2 新增的“动作可用即执行、仅不可用时开门”。一个文本层面的反例是：

1. 已持有目标、家电关闭，显式温变动作已可用。
2. Actor 仍先开门一次，再直接温变并交付。

此序列违反最终 u2 的条件化开门规则，但没有反复开关、反复放取，可能满足当前 c2 的全部明文条件。**这是检查覆盖缺口，不是 Goal 与 Update 之间再次出现直接矛盾。**

此外，c2 的 `co-located/held` 比 Goal、u2 的 `held` 更宽。仅共处而未持有目标的行为在文字上可能被 c2 接受，却不满足 Goal/u2。不能因为环境可能限制动作可用性就忽略契约措辞差异。

若后续修订，只需让 c2 明确持有目标、动作可用即执行、只在不可用时开门，同时保留避免反复操作和随后交付，不需要新模块。本轮依照冻结协议只记录发现，没有修改输出。

### 搜索项及 change / Patch 边界

- u1 的 S/C 调整在 change 中声明了跨类别协调及个体候选保留，Patch 修改第一行落实这些决定；其余三行保留。u2 的 S 调整明确声明扩大到未开门但动作可用的条件，Patch 修改第一、三行落实，没有再新增插入后取回等动作或顺序。
- u2 change 把保留项简称为 `prohibition ... on moving the target in and out`，而原文和 Patch 限制的是 **repeatedly** moving。这是保留边界表述不够精确；结合 `Keep` 和 Original 可读为保留原限制，不能声称所有措辞严格等价。未发现 Patch 私自升级为禁止任何一次移动。
- u1/c1 仍依赖“已经检查过/尚未检查”的判断。短历史条件下能否可靠执行仍未验证；这次没有新增全局访问表机制，也不能据此宣称搜索问题已解决。
- u1 reason 将 `open closed containers one after another` 解释成必然耗尽同一类别，解释偏强；原句本身未明确要求耗尽一类。本轮 Patch 的协调结果可以与 Goal 相容，但不能把该解释当作已证实的退化原因。
- Goal 仍绑定 `held target`，所以本样本只证明“open”条件移出了 Goal，不能推断 Diagnosis 已普遍学会区分目标与所有可修订策略。

## 本地核验及可复查材料

本地审计重新解析两阶段已选输出，重新执行契约校验和严格 Patch 编译，检查所有请求、首次合法选择、冻结哈希、调用参数和技术重启。另核对：新 Plan 与实际 Preconditioner 输入一致、Memory 不变、Goal 原样继承、Checks 原样继承、所有 Check 引用存活 Update。全部通过；这些是结构和来源核验，不代替上述语义判断。

- [新 Diagnosis](runs/R06_diagnosis/attempt_001/parsed.json)
- [冻结 Plan](handoff/diagnosis.json)
- [已选 Preconditioner](runs/R06_pc/attempt_002/parsed.json)
- [Effective Plan 与适配结果](runs/R06_pc/attempt_002/result.json)
- [一致性与证据摘录](CONSISTENCY_EVIDENCE.json)

复核命令（无 API）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.semantic_generation_004.run audit
```

本次仅一份新 Diagnosis 和一次首次合法 Preconditioner 选择；不能作为稳定遵循性、Actor 改善或完整第五步完成的证据。
