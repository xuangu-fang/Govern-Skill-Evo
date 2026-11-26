# Replay 单配对上下文消融

2026-10-28。两次实际 DeepSeek 调用均首次通过格式及引用校验，无格式修正、技术重试或语义重采样。生产 prompt、代码、旧实验和 Memory 未修改；没有运行下游链路或训练。

结论：缩小当轮上下文后，R05 的条件对照与信息保留明显更完整；R06 只部分改善，仍缺两侧回退条件对照，且可见比较中的 code 优先未进入 Knowledge，同时新增了等分排除因果的错误。结果不支持将遗漏全归为长上下文，也不支持直接将 Replay 改为逐配对调用。更准确的定位是：比较粒度、重要区别进入 Knowledge 时的保留、评分与因果关系的判断都仍需处理。

## 1. 实验设计与输入控制

对照使用[上次完整批次 B 组](../../replay_comparison_diagnostic_20261028_001/reports/README.md)的已归档输出；本次仅新增两个单配对请求，没有重新运行完整批次基线。

| 条件 | R05 | R06 |
|---|---|---|
| 目标配对 | P3/Q3，train:433-47 | P15/Q15，val:2768 |
| 当轮配对数 | 15 → 1 | 15 → 1 |
| 当轮 runs 数 | 30 → 2 | 30 → 2 |
| 共享消息数 | 17 → 3 | 17 → 3 |
| user 字符数 | 246,975 → 63,012 | 288,772 → 89,068 |

唯一干预是移除其他当轮 pairs/runs 及它们不再使用的共享初始消息。对应 Parent、Diff、Plan、原 Memory 逐字内容不变；B system prompt 逐字不变，未追加针对目标差异的提示；目标配对的代码、response、执行反馈、评分、任务输入、预览和共享 Actor system 均保留。原 P/Q 编号、配对记录、共享指针名称、配对邻接和 response/code 去重标记保留。选定初始消息和程序还原后与完整 v4 对应记录完全一致。

由于保留原共享指针名称，这是一份沿用 v4 编码的诊断裁剪视图，不是重新编号的标准生产归档；没有修改生产视图生成器。B 诊断 schema 和原生 entries validator 沿用上次实现，只允许选定当轮执行引用和原有历史引用。原 bundle 的配对审计及 record_paths 也仅保留对应配对，未把已删除轨迹留在模型请求里。

参数沿用：deepseek-v4.1-flash，max_tokens=49152，temperature=1.0，reasoning_effort=medium，thinking enabled，stream=false，timeout=300 秒，原内网 endpoint。初始请求仅 system/user；旧答案、人工评审标准、修正反馈未发送。格式修正沿用原机制，本次没有触发。

- [运行前判读标准](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/review_criteria.json)、[冻结清单与输入差异统计](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/manifest.json)。
- [R05 初始请求](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/R05/base_messages.json)、[R06 初始请求](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/R06/base_messages.json)。
- [完整与单配对的逐项输出](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/outputs.md)、[人工评审](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/semantic_review.json)。
- [R05 实际输出](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/R05/replay/attempts/001/diagnostic.json)、[R06 实际输出](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/R06/replay/attempts/001/diagnostic.json)。
- [最终校验](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/final_checks.json)、[调用统计](../../../../../artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/metrics.json)。

## 2. R05：从整体概括转向明确的分支对照

完整批次 B 已识别正负残差动作反转，但在 shared_and_different 中仍把 Parent 概括成“一格后停止”，抹去了 Parent 正残差分支已有的跨格延续。其最终 Knowledge 保留了反转，但没有保留这一已有能力。

单配对结果为 1 个 comparison、5 条 observations、1 个新增 Memory 提案、5 条 Knowledge，revises=[]。

- Observation 2 明确对齐：Parent 负残差从 unit1 向右加到第一个非零格；正残差从 unit5 向左逐格减到 0。Candidate 正残差按上限逐格加，负残差按下限逐格减。
- K1 明确保留 Parent 正残差分支本来就会 spilling；不再把所有跨格延续当作 Candidate 新能力。
- K2 单独保留正负动作映射反转，并说明该变化未由条款直接规定，不能把 135/189 → 189/189 的改善单独归因于边界处理。
- 54 个错误坐标均在 B–F，B2:B18 与 F2:F18 各 17 个的表述已核对原评分列表。表头/列定位到 row 1、B–F、I 可以由已给预览和程序确定，并不一律需要额外运行日志。

这次观察到的改善是条件对照与已有能力保留更完整，不是首次识别反转：上一轮原版 A 和完整 B 都已经提到反转。

仍然存在证据边界问题：输出继续将 Candidate 从工作簿读取实际 min/max 作为确定事实。虽然提到通过行和值排序识别边界行的 fallback，却没有保留找不到上下限时使用 0/∞ 的程序回退。当前预览没有边界行，stdout 未报告边界值，不能由评分通过单独证实实际分支。这项问题没有随上下文缩小而消失。

## 3. R06：部分识别改善，完整条件仍缺失，进入 Knowledge 时又丢失优先级

单配对结果为 1 个 comparison、3 条 observations、1 个新增 Memory 提案、2 条 Knowledge，revises=[]。

| 检查点 | 完整批次 B | 单配对 B |
|---|---|---|
| 比较中识别 Candidate code 优先 | 只描述两张库存表 | 明确 prefers the code key / code-first dual lookup |
| Parent name 优先及回退条件 | 没有完整对照 | 仍只写 name-or-code |
| 两侧回退判据对照 | 缺失 | 仍缺失 |
| Knowledge 中的优先级 | 提到 code-then-name，Parent 对照缺失 | 只保留双表，code 优先也省略 |
| 答案范围 | 错写 H2:H17 | 正确 H2:H18 |
| 相同评分与因果关系 | 保留原因未定 | 新增“键差异不解释错误”的过强排除 |

关键的完整语义仍应是：Parent 在名称为空时才用 code，名称非空但库存查不到不会再试 code；Candidate 则优先使用存在于 code 库存表的键，未命中才尝试 name。这些选择再决定分组和库存消耗池。单配对结果仍未将这条依赖关系写完整。

与上一轮不同，本次确实能在可见产物中定位到一项信息损失：比较明确写出了 Candidate code 优先，最终 K1 只剩 separate item-code-keyed and item-name-keyed stock lookups。但它不是“完整的双侧条件对照已经提取、随后全部丢失”：完整回退对照从未出现在比较里。这里同时存在提取/对齐不足和部分信息未保留，不能只选一个解释。也不能根据这些外部字段还原模型内部推理顺序。

新的因果错误在 comparison 和 K1 中均存在：两侧 H12/H13 都错，因此“their cause is not the keying difference”／“the key difference does not explain them”。相同错误坐标并不能排除键处理参与两侧错误：两者可能产生不同错值，也可能由不同机制共同导致失败。输出虽然同时承认错值可能不同，却没有把这个限制落实到因果排除句中。正确结论应限于：评分及错误位置未变，键变化是否触发、是否影响这些单元格及其因果贡献尚未确定。

## 4. 对原因的更新判断

1. **上下文或任务负担可能影响比较完整性，但本次不建立独立因果效应。** R05 同一 prompt 下保留了更多分支细节；R06 更明确地描述 code 优先。改变的同时包括长度、当轮任务数、位置和注意力分配，每条件一次且 temperature=1，不能拆分这些因素或宣称稳定收益。
2. **长上下文不是充分解释。** 当轮只剩一对后，R06 的 name/code 回退条件仍未对齐；R05 的边界实际激活仍被过度确认。继续单纯压缩输入不能保证解决这些问题。
3. **比较结果到 Knowledge 的保留值得单独处理。** R06 code 优先从可见比较进入 Knowledge 时被省略；R05 则成功保留了新增的分支信息，说明这不是所有比较都必然被压缩掉。
4. **事实理解与因果判断是不同问题。** R06 一方面承认等分不等于相同错值，另一方面又排除键差异，反映的是证据限制未作用于具体结论。仅增加字段或重复“保留不确定性”不够。
5. **仍未隔离条款牵引或 Memory 影响。** 单配对仍保留完整 Diff/Plan 和原 Memory；输出仍按三条新增 Skill 条款描述适用/未触发。不能因此断定 Memory 有问题，也不能把能力不足作为唯一解释。

本次均未修订旧 Memory 条目，也没有把单配对的当前结果写成 15 对的批次汇总；未发现引用已删除的当前执行。这些引用/范围校验通过不等于全部语义判断正确。

## 5. 资源变化与适用边界

| 指标 | R05 完整 B → 单配对 | R06 完整 B → 单配对 |
|---|---:|---:|
| Prompt tokens | 82,300 → 24,044（约 -71%） | 96,699 → 31,238（约 -68%） |
| Completion tokens（含 reasoning） | 29,396 → 13,035 | 37,053 → 13,377 |
| 请求耗时 | 202.8 → 82.1 秒 | 264.1 → 90.0 秒 |
| 实际 API 请求数 | 本次 1 | 本次 1 |

单配对完成的工作量更小，不能据此推断把全部 15 对拆成独立调用会更省；那会重复发送共享 prompt、Diff/Plan/Memory，且还需批次整合。缓存命中与服务时延也不同。对照来自上次归档，没有本轮新增的同期全批次重复控制。

## 6. 下一步建议（未执行）

不建议据此将 B 设为默认，也不立即上线逐配对流水线。下一版局部方案应优先解决：

- 用真正区分行为的条件比较关键操作：尤其键来源、选择顺序、回退触发、分组与消耗之间的关系；不要求穷举所有分支或固定数量。
- 将改变经验解释的重要区别保留到 Knowledge；可以合并表述，但不能把不同选择机制统一成无差别的 item，也不能只留下“双表”而丢掉决定选择的优先级。
- 将“评分未变”与“某机制不可能解释错误”分开；允许基于程序的机制假设，缺少贡献隔离时不作因果排除，不要求所有假设先得到实验确认。

之后再用相同输入条件的对照检验局部调整，并用匹配重复样本确认稳定性。当前默认仍为 Replay v3 / 生产输入视图 v4，Preconditioner v7。

离线复核（不会调用模型）：

```sh
/Users/didi/miniforge3/envs/spreadsheetbench/bin/python artifacts/methods/v25/analysis/replay_single_pair_diagnostic_20261028_001/summarize.py
```
