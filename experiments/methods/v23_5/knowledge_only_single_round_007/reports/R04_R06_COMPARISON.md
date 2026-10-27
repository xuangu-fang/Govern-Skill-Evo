# R04–R06：Knowledge Only 与 Memory v3 效果比较

结论：本次有效输出没有显示 Knowledge Only 系统性丢失核心问题或主要反例；它大幅减少单次输入，并在 R04 实际修订旧 MemoryEntry 时完整保留了旧知识。证据支持继续采用该方向，但不足以证明与 Memory v3 完全等效。Preconditioner 仍有恢复归因过宽或过窄的问题，Replay 两版也都有事实细节或概括错误。

## 比较范围

007/008/009 分别执行 R04/R05/R06，共 12 单元。按用户授权，010 补充 R05 Preconditioner Memory v3 并取得有效输出。最终 11 个单元有效；R04 Preconditioner Knowledge Only 缺少正式有效方案，其第三次响应的 change 中 P2/P3 被该模块原扫描器当作历史引用。此次修复只覆盖 Replay，本实验未改变冻结规则。该缺口不是 Knowledge Only 语义更差的证据。

模型配置、实际 messages、当前事实和轮前 Memory 与 003 对应冻结单元相同，max_tokens=32,768。只比较首个程序有效输出；不以失败重试成本评价效果。结构有效不等于内容正确。没有启动 Actor、发布 Skill/Memory 或额外评判模型。

## Preconditioner

| 轮次 | Memory v3 | Knowledge Only | 可支持的判断 |
|---|---|---|---|
| R04 | 修正一次访问收集多实例与携带能力的冲突，增加放置后返回，协调搜索与已知来源优先级；仍有全局未搜索状态依赖 | 缺少正式有效方案 | 不进行两版质量排序 |
| R05 | 限定取得对象前的搜索阶段，改用最近两步与 admissible 候选，保留必要返回；u2 仍保留宽恢复 | 同样改进阶段边界并使用 M2/M3，但将未完成放置推断为错误类型或还缺实例，恢复原因收得过窄 | Memory v3 更克制；问题不能单独归因于历史材料缺失 |
| R06 | 区分单实例未覆盖与多实例规则已覆盖仍失败；保留热/冷规则，增加搜索退出条件 | 同样保留核心区别和热/冷规则，强调近期候选、表面覆盖、已知目标返回例外 | 核心判断接近，均有条件可判断性及未经执行验证的策略强度问题 |

R05 Knowledge Only 的主要问题有明确文本依据：它把“放置后任务未完成”写成“对象类型不对或还需要另一个实例”的信号，没有充分考虑变换未完成、目的地等其他原因。Memory v3 虽没有加入这个两原因判断，却仍保留放置未完成就重新搜索的旧规则，因此也没有完全解决恢复问题。

R06 两版都利用历史失败认识细化搜索，没有仅用“扩展到单物体任务”解释多物体失败。Knowledge Only 的 reason 声称没有其他候选时不禁止返回，但 patch 的最近位置排除没有完整写出这个退路；Memory v3 将空容器视为当前搜索已耗尽，也仍有持续记忆边界问题。不能因为引用了历史，就认定历史约束已被完整落实。

## Replay

| 轮次 | 两版共同保留的核心认识 | 实质差异或问题 |
|---|---|---|
| R04 | 直接加热、错误类型限制、同容器多实例放置、CD/keychain 搜索失败、无关灯光任务 | 两版都错误地将未取得第二个 CD 推成无法知道它是否存在；Knowledge Only 实际修订 M3 并保留全部旧项 |
| R05 | mug 搜索改善、apple 搜索退步、bowl 取得对象后绕行、避免错拿 knife 但仍未找到目标、其他成功流程保留 | Knowledge Only 更明确指出灯光任务与 clean/transform/place 条款适用边界；Memory v3 将 P7/Q7 的搜索位置集合泛指双方，实际 P7 没有访问 cabinet |
| R06 | 避免反向热变换的改善、plate 从成功到失败、creditcard 从9步到27步、book 最后一步发现、apple 未找到 | Memory v3 把 Q4 的 tomato1 写成与 Parent 相同的 tomato2；Knowledge Only 的 Q1 叙述将错误动作放在 drawers 检查之前，实际顺序相反 |

R04 的共同错误尤其说明：P5:11 已显示 dresser1 上有 cd1、cd2、cd3，不能因为没有取得第二个就说其存在未知。这是对直接证据的概括失真，不能归因于 Knowledge Only 不提供历史原始轨迹。

以上为逐条阅读后的重点事实核查，没有统计完整事实准确率；不根据少数已定位错误给两版作总体准确率排名。条目多少也不代表覆盖或质量高低。

## 历史利用与知识保留

Preconditioner 两版都能利用历史条件与反例。R05/R06 Knowledge Only 明确调用了 M2/M3/M4/M5 中相关认识，并保留部分迁移不确定性；没有观察到必须读取历史原始轨迹才能形成核心判断的案例，但这不证明所有情境都不需要历史核查。

R04 Replay Knowledge Only 输出两个 entry：一个 revises M3，包含原有 5 条完整 text+evidence 和一条当前新增认识；另一个含 3 条当前新增认识。原有 5 条逐项精确保留。这是整体修订保留能力的一个正面案例。Memory v3 本轮只追加；R05/R06 两版也都只追加。因此只有一次修订案例，尚不能评价长期累积或两版修订能力孰优。

保留历史知识也会保留原有偏差。M3 原有的 R03 Q6 动作细节错误被 Knowledge Only 原样保留，属于输入旧知识的延续，不能记为本轮新编造或声称已重新核查。这同时说明知识保留与知识纠错是不同的能力。

## 单次输入规模

仅使用各原始单元第一次请求的 API prompt_tokens，不计失败重试累计成本；同消息的 API token 报告可能有轻微差异。

| 轮次 | 模块 | Memory v3 | Knowledge Only | 输入减少 |
|---|---|---:|---:|---:|
| R04 | preconditioner | 300,992 | 85,411 | 71.62% |
| R04 | replay | 333,048 | 116,590 | 64.99% |
| R05 | preconditioner | 346,975 | 55,618 | 83.97% |
| R05 | replay | 372,537 | 80,036 | 78.52% |
| R06 | preconditioner | 402,686 | 48,868 | 87.86% |
| R06 | replay | 447,064 | 91,841 | 79.46% |

## 判断边界与后续

目前可保留 Knowledge Only 的设计方向，没有证据要求恢复默认展开全部历史轨迹。优先处理已定位的规则范围、恢复原因及事实概括问题，并补齐 R04 Preconditioner 的引用识别缺口后再进行独立复核。后续若要判断长期知识累积，需要连续 Memory 回放；若要判断任务成功率，需要新的 Actor 实验。本次没有执行这两类实验。

## 可核查记录

- [单元状态、有效输出位置与单次输入统计](../results/R04_R06_comparison.json)
- [R04 语义审阅](../results/semantic_comparison.json)
- [R04 Preconditioner 引用定位](../results/preconditioner_reference_review.json)
- [R05 语义审阅](../../knowledge_only_single_round_008/results/semantic_comparison.json)
- [R06 语义审阅](../../knowledge_only_single_round_009/results/semantic_comparison.json)
- [R05 Memory v3 Preconditioner 补充协议](../../knowledge_only_single_round_010/PROTOCOL.md)

## 2026-10-27 材料整理说明

本文件保留原阶段的协议或结论，整理未重新执行命令、实验或测试。实际已运行单元、有效输出、失败证据及原始／追加批次关系见 [目录说明](../README.md)。
