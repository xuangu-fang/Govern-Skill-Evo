# R06 单次生成：change / Patch 双向一致性核对

日期：2026-10-22（Asia/Shanghai）。已按用户原句替换 Prompt 中的对应段落，用相同 R06 输入生成一次 Preconditioner。本次限定范围内的人工核对结论：**u2 的实质变更均由 change 表达，Patch 对应落实；未发现 Patch 额外引入动作、前提或顺序。** u1/u3 为 Keep，不提供修改分支的验证证据。

## 执行与对照条件

- 1 次 HTTP，首次结构合法，零重启，耗时 135.784 秒；没有长度截断或输出预算升级。
- R06 Original、Parent、当前事实、Memory、用户消息、模型及 API 参数与 semantic_generation_002 相同；校验器不变。冻结源码比较确认唯一变化是 Preconditioner Prompt 的一致性段落，见 [PROMPT_CHANGE.diff](PROMPT_CHANGE.diff)。
- 本轮使用用户提供的两句话；没有添加 fallback 合理性机制。没有运行 Editor、Diagnosis、Replay、Actor 或 Judge。
- 原始结果见 [parsed.json](runs/R06_pc/attempt_001/parsed.json)，编译结果见 [result.json](runs/R06_pc/attempt_001/result.json)，本地重解析与请求审计见 [AUDIT.json](AUDIT.json)。API 报告 prompt 255,495、completion 19,919、total 275,414 tokens；费用未知。

## 三项观察

| Update | 决定 | change 是否表达实质修改 | Patch 是否落实 | 是否存在额外动作、前提或顺序 |
|---|---|---|---|---|
| u1 | KEEP | 无修改决定 | to=null；Effective text/basis 与 Original 一致 | 无 Patch，不能据此评估修改能力 |
| u2 | S 修改 | 本次识别的实质变更均已表达，见下表 | 与 change 对应 | 未发现；上轮“取回”动作没有出现 |
| u3 | KEEP | 无修改决定 | to=null；Effective text/basis 与 Original 一致 | 无 Patch，不能据此评估修改能力 |

### u2 逐项对应

| 行为决定 | change 的表达 | Patch 的落实 | 核对 |
|---|---|---|---|
| 条件化开门 | `Make appliance opening conditional`；仅持有时动作尚不可用才开门 | `Open the appliance only if the action is not yet offered for the held target` | 一致 |
| 动作已可用就直接执行 | 取得精确目标并到达家电后，持有动作一旦可用即执行；包括关闭状态，不先插入 | `as soon as it is admissible`，包括关闭状态，`without first inserting it` | 动作、条件和顺序均有声明 |
| 排除伪完成 | 插入、关闭/重开、检查家电都不能当作完成温变 | 三类行为均明确写入，未扩展额外禁止行为 | 一致 |
| 单次 insertion fallback | 明确保留：若持有动作始终不提供，放入一次 | `If the action is never offered ... place the target inside once and perform the action there` | 触发措辞与 change 对应；插入后执行承接 Original fallback，不是新发明的取回序列 |
| 单次温变与禁止循环 | 保留一次 action、禁止 repeated close/open 或 remove/reinsert | 相应要求保留 | 未将禁止反复操作升级为禁止所有操作 |
| 完成后交付 | 保留前往目标位置和家电本身就是目的地的情况 | 两种后续交付情况均保留 | 未增加独立新策略 |

保留行为通过明确的 retain 表述及 Original 上下文核对，不要求 change 逐字重复原有动作。Original 本来就有“放入一次并执行”；本次的 `perform the action there` 没有再要求先取回。与上一轮不同，不再需要由 Patch 自行补出放入→取回→持有执行的顺序。

本次核查同时检查 change 中的决定是否遗漏，以及 Patch 新增内容是否有 change 对应。严格 Patch 应用成功只证明文本转换精确，上表的语义对应是当前同一分析者的人工判断，不是程序自动判定或独立盲评。

## 本次结果的边界

本样本在用户指定的三个观察点上未发现新的不一致；但只有一个非 Keep Update、一次采样，不能据此证明修改 Prompt 已稳定降低错误率，也不能将变化全归因于新句子。

本次 c2 已同步改为动作可用即执行，移除了原先的 `at the open appliance`。**冻结 Goal 仍包含打开状态要求，因而此前 Goal 与关闭状态直接执行的冲突并未解决。** 这是整体 Plan 的已知独立问题，不把本次一致性通过扩大为整个 Plan 语义通过。

依用户限定，本轮不重新设计或评判 fallback 合理性机制，也不验证其执行效果、u1 的 Keep 理由质量或总体 D/S/C 收益。未修改任何原始输出，未接纳 Candidate。

## 本地核验

- Prompt 中既有 EOF JSON 示例严格应用检查：1 passed。
- R06 原始输出重解析、v2 校验、严格 Patch 编译、输入及配置冻结、首次合法选择和 HTTP 请求归档审计通过。
- Keep text/basis 保留、u2 精确 Patch 结果、Goal 原样继承、c1/c3 保留与 c2 更新经本地核对。字符串检查不替代上面的语义审查。

复核命令（不发 API）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.semantic_generation_003.run audit
```
