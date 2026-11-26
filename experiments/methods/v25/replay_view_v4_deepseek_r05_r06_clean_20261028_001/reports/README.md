# Replay Prompt v2 / 输入视图 v4：DeepSeek R05、R06 单模块对照

2026-10-28。**输入显著缩短，但这两份输出没有达到“补回关键程序差异、稳定减少概括错误”的主要目标。部分旧错误消失，也有新的事实错误；不能据此认定 v4 整体提升了 Replay 质量。**

## 实验范围与完整性

- 主对照为此前 **Replay prompt v2 + 输入视图 v1** 的原始 Replay 输出，对比本次 **同一 prompt v2 + 输入视图 v4**。没有重新运行旧视图，也没有把发布后的 Memory 当成原始 Replay 基线。
- DeepSeek `deepseek-v4.1-flash`，原内网 endpoint；`max_tokens=49152`、`temperature=1.0`、`reasoning_effort=medium`、`thinking.type=enabled`、`stream=false`、300 秒超时、每轮最多 6 次请求不变。逐请求对比 request.json，除 messages 外完全相同。
- 两轮都从 system/user 两条消息开始，`feedback_from=null`，没有旧回答或旧校验反馈。各第一次请求即返回有效 JSON，合计 **2 次真实 API 请求**，没有技术重试或格式修正。原生格式反馈机制保留，但本次未触发。
- 原始 input.json 与此前完全相同。将 v4 的共享初始消息、代码标记展开，并恢复原 run 顺序后，模型已见事实与旧视图一致。pairs 前置、Parent/Candidate 邻接已检查。R06 保留原有 Memory（包括旧 M9），没有接入本次 R05 输出。
- 原生 `load_replay` 重读两份新结果成功；请求按归档版本重建一致。生产源码/Prompt 冻结契约、原 campaign 和此前 v2 实验哈希均未变化。Preconditioner 默认仍为 v7。
- 没有 Actor、Verifier、Repair、Memory 发布、完整链路、训练或测试集评估。下文分数均为原输入中的历史评分，不是本次新增执行成绩。

预先固定的 [review_criteria.json](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/review_criteria.json)、[manifest.json](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/manifest.json)、事后 [validation.json](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/validation.json) 保留完整实验边界。原始输出对照在 [outputs.md](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/outputs.md)，其中 K 是每个版本输出内的 Knowledge 序号，JSON pointer 为 `/entries/0/knowledge/(K-1)/text`。

## 输入压缩与运行结果

| 指标 | R05：旧视图 → v4 | R06：旧视图 → v4 |
| --- | ---: | ---: |
| user 字符 | 528,806 → 246,975 | 688,910 → 288,772 |
| API 报告 prompt tokens | 152,945 → 81,974（−46.4%） | 194,514 → 96,373（−50.5%） |
| 重点配对记录起点间距 | P3/Q3：220,586 → 3,315 字符 | P15/Q15：325,123 → 9,935 字符 |
| completion tokens（含 reasoning） | 19,632 → 24,019 | 41,571 → 20,057 |
| Knowledge 数 | 6 → 8 | 7 → 5 |
| Knowledge 正文空白分词数 | 767 → 972 | 1,165 → 575 |
| 选中成功请求耗时 | 140.0 → 147.9 秒 | 280.6 → 140.3 秒 |

此处 prompt tokens 为服务端实际 usage 报告，不是之前的 cl100k 代理估计；比较基线是旧 v1 视图，包含恢复邻接和所有已批准去重的联合变化，不是仅 v3 → v4 的代码去重。旧 R05 另有一次超时，服务端用量未知；表中仅列选中成功请求。旧 R05 报告了缓存命中，新请求未报告对应字段，因此这些数字不能直接解释为费用节省比例。

详见 [metrics.json](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/metrics.json) 和 [input_comparison.json](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/input_comparison.json)。

## 重点问题逐项对比

| 核对点 | 旧 prompt v2 / view v1 | 当前 prompt v2 / view v4 | 判断 |
| --- | --- | --- | --- |
| R05 正负残差与加减动作反转 | K5 未记录 | K3 仍未记录 | 关键遗漏未改善 |
| R05 Parent 两个残差分支 | K5 把整个程序写成只改首个单元格 | K3 区分一次性加法与向 0 扣减；但仍将多单元格传播笼统说成 Candidate 新增 | 局部改善，仍不完整 |
| R05 实际边界是否读到 | K5 将条件查找写成已读到实际边界 | K3 仍称读到了 minimum/maximum bound row | 未改善；依旧把实现可能性写成事件 |
| R05 材料汇总/hashtag 混为子串能力 | K4 混淆三类操作，虚构共同 case-fold/空白变化 | K6 按直接值路线归组，K8 的容错匹配只讨论 P4/Q4、P6/Q6 | 原错误不再出现，归类更合理 |
| R05 邮编 unmatched 与归因 | 旧 v2 已没有 v1 原始 unmatched 错误，但表选择差异表述不准 | K7 保留归一化与列选择的竞争解释，碰撞机制明确为假设；新增错误 sheet 名 | 机制范围较好，事实对应仍出错 |
| R06 item name/code 优先级 | K4 未记录 | K4 仍只比较订单数字前缀与完整标识符 | 关键遗漏未改善 |
| R06 同分与同值 | 旧 v2 已纠正 v1 的“未改变任何格值” | K4 没有再断言实际值相同，保留两格失败原因未解 | 原改善基本保留，不能算 v4 新增修复 |
| R06 锚点差异被空格状态否定 | K2 末句否定“不要写到 I3 上方”的区分机会 | K2 保留 I2 → I3 差异，删除矛盾末句 | 旧矛盾消失 |
| R06 Q4 已知分支被写成未知 | K7 将由可见公式确定的分支写成未确立 | 不再分析该分支，仅列作直接值答案 | 不再说错，但不能认定正确利用了该事实 |
| R06 合并行数的已知事实 | K3 正确记录 stdout 的 appended=3998 等 | K3 又称 appended row count 未独立验证 | 新的局部过度保守 |

没有把遗漏某个非核心例子直接判作错误，也没有把条目增减当成质量指标；以上判断针对预先固定的程序差异、归因范围和事实对应问题。

## R05：最关键的竞争解释仍未进入 Knowledge

新 K3 继续按“读取 min/max、遵守上下界”组织收益解释，没有保留输入代码里明确存在的反转：

| 条件 | Parent | Candidate |
| --- | --- | --- |
| residual < 0 | unit1 → unit5 加法，首个非零格一次加入全部量 | unit5 → unit1 减法，逐格受下界限制 |
| residual > 0 | unit5 → unit1 减法，原本就有剩余量传播 | unit1 → unit5 加法，逐格受上界限制 |

新 K3 的“Parent 加法只改首格、减法向 0 扣减”比旧 K5 的整段概括更准确；但没有符号条件，仍遗漏足以改变解释的差异，并且“Candidate also added ... multi-cell distribution”掩盖了 Parent 减法原本已有跨列传播。

与此同时，Candidate 的 min/max 代码有标签查找、数值行启发式及 `0/inf` 回退。输入没有给出选中行号和边界值；189/189 不能独立证明走了哪个边界分支。因此新 K3 “read both a minimum and a maximum bound row”仍过实。这里必须分开判断：**符号反转是已见事实未利用；实际边界值则是输入证据不足，应该保留条件或假设，而不是补成事实。**

证据：[当前输入摘录](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/R05_evidence.md)，P3 `/runs/4/attempts/0`（正文行 325 起，分支 348/359 附近），Q3 `/runs/5/attempts/0`（行 509 起，边界选择与回退 558–638、正负分支 650–690）。两边原 executed_code 都被精确标记引用，response 全文仍在；无损展开校验已证明该差异没有被去重删除。

文本案例新 K2 仍保留数值解析也变了，这点是好的；但用“错误发生在 E 文本格”突出文本谓词并不能排除 F 数值分支，因为两个分支都决定最终 E 值。它承认原单元格文本不可见，却又暗示容错测试确实捕获了某种文本形态。相比旧 K2 的“两项贡献无法分开”，这次仍需谨慎理解为解释假设。

邮编新 K7 对“去掉所有空格可能合并不同键”的解释明确加了假设边界，也保留 header 选择的竞争原因，合理泛化没有被压制。但它将原错误工作表 `Compiled and located schools da` 写成 `Sheet1`（[输入摘录](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 2031）。这是已有身份事实被错误抄写，不是缺输入。

## 新出现的两类明确概括错误

### 1. R05 把混合路线统一概括成 Parent 全部直接值

当前 K4 列举五个公式任务后称“in all five” Parent 都通过直接计算/查找值获得 hard 1。但 P7 原程序明确写入数组公式，再调用 `inject_cached_values(OUTPUT_PATH, "Sheet1", cached_values)`；两边在该任务都使用公式加缓存。旧 v2 K6 原本正确保留了这点。

因此“这五对全部是 Parent 直接值 versus Candidate 公式缓存”不成立，不能用它支持一个整齐的路线对照。证据：[当前输出 K4](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 73 起；[P7 代码](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 1252 起，写公式约 1490 起、缓存调用行 1560。

### 2. R06 把已改善的任务列进“全部与 Parent 同分”的集合

当前 K5 把 Q7、Q14 列入直接值任务后统一说这些任务 “all tied Parent at hard 1”。但 P7/Q7 是 4/12 → 12/12，P14/Q14 是 48,013/95,988 → 95,988/95,988；它们正是 K1–K3 已正确叙述的两项提升。这造成同一输出内的事实矛盾。

证据：[当前 K5](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 183 起；[R06 输入](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/R06_evidence.md) P7/Q7 行 401/563 起、P14/Q14 行 950/1281 起。K5 的 evidence 数组还没有引用 P7/Q7、P14/Q14 的 outcome，进一步说明“引用合法”不保证概括范围被逐项支持。

此外，当前 R06 K1–K4 将 `val:560-12`、`val:80-42`、`val:2768` 误写成 `train:...`。输入的 task_id 和 pairs 均正确，原生校验仍通过；本轮实际暴露了结构/引用校验与自然语言事实校验的区别。原始输出完整保存，未人工修正，也未把这些语义问题作为格式反馈重新采样。

## R06：仍未抓到另一项关键差异，且对已有日志过度保守

当前 K4 抓住了订单号截断 versus 完整标识符，但仍未记录：Parent 的 item 键是 `norm_item(item) or norm_item(icode)`，优先名称；Candidate 优先 `(order, item_code)` 的 stock 映射，找不到再用名称。这个差异不一定解释 H12/H13，却足以作为竞争解释保留，不能把程序变化缩成只有后缀。

证据：[当前输入](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/R06_evidence.md)，P15 `/runs/28/attempts/0`，名称优先行 1676/1692；Q15 `/runs/29/attempts/0`，代码优先及回退行 1981 起。这些代码现在相邻且完整可还原，仍未被使用。

当前合并 K3 说 appended row count 没有独立验证，但 Q14 execution.stdout 明确包含 `start_row=4000 appended=3998 end_row=7997`、首尾来源和 `verify_ok=True`（[输入摘录](../../../../../artifacts/methods/v25/analysis/replay_view_v4_deepseek_r05_r06_clean_20261028_001/R06_evidence.md) 行 1488）。这些是程序自报运行证据，不是外部金标准的独立证明；可以限定为“程序报告追加 3998 行”，没有必要把可用的运行事实整体降成未知。旧 K3 处理得更具体。

Q4 不再单独讨论，所以此前“由 C2/C3 公式已确定的分支仍被说成未知”的错误没有重现；但这不等于这次正确识别了该分支。Q3 的示例覆盖行为、Q11 的示例块条件也从新输出中省略，不能仅凭少写这些内容就声称不确定性校准改善。

## 是否过度保守，以及本次支持什么结论

没有整体过度保守：R05 保留三个提升、直接值/公式缓存路线和技术失败后恢复，R06 保留两个提升及标识符未测得评分收益；邮编碰撞机制仍作为有依据的待验证假设。R06 合并行数是局部的已知事实利用不足，和 R05 边界事件说得过实同时存在，统一要求“更加谨慎”不能同时解决这两端问题。

这次可以确认：

1. **v4 的表示层收益成立。** 无损还原、干净请求、原始事实/参数一致，并且服务端报告输入 tokens 约减少一半。
2. **可读性改善不是充分条件。** 两项预先指定的重要程序差异依旧遗漏，新增的“全部”概括又有明确反例；不能再只用配对距离大或重复文本多解释所有错误。
3. **下一步值得核对的是程序比较如何进入最终 Knowledge，以及跨任务概括是否保留反例。** 对已确定的符号分支、item 优先级不需要新增工作簿证据；对实际 min/max 边界应保留未知或待验证解释。重点应是已见事实的利用与主张核对，不是压制经验泛化。

这是 temperature=1 下两轮各一次新有效输出，且 v4 同时改变邻接、初始消息共享和代码去重。它不能证明某个输入改动导致了某个新错误，也不能区分三项输入优化的各自作用或据此给出模型能力上限。保留 v4 有明确的输入效率依据；输出质量的稳定改善仍未验证。

本次没有修改生产代码或 Prompt，未发布 Memory。所有新产物仅位于本实验目录。
