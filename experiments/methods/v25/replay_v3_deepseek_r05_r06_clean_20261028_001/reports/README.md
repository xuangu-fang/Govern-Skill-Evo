# Replay v3：DeepSeek R05 / R06 单模块筛查

2026-10-28。**v3 对部分概括和日志使用有改善，但两项关键程序差异仍遗漏；R05 还丢掉了原已保留的竞争解释，归因变得更确定。因此本轮未通过“准确比较关键行为差异”的主要目标，不能认定学习质量整体改善。**

## 实验与完整性

- 主对照：上一轮真实 **Replay prompt v2 + 输入视图 v4** 输出，与本次 **prompt v3 + 同一输入视图 v4** 输出。没有重新采样 v2，也没有使用离线复用输出夹具作为实验回答。
- 两轮各第一次请求即返回有效输出，合计 **2 次真实 DeepSeek API 请求**；无技术重试、无格式修正、无语义重采样。保留原生格式错误反馈机制，但本次没有触发。
- 起始请求仅有 system/user 两条消息，`feedback_from=null`，不含旧回答或旧修正反馈。user 内容逐字相同，system 除学习模板外的执行上下文、共享和代码解码说明完全相同。
- 原始 bundle、Memory、配对、调用参数不变。模型 `deepseek-v4.1-flash`；原内网 endpoint、`max_tokens=49152`、`temperature=1.0`、`reasoning_effort=medium`、`thinking.type=enabled`、`stream=false`、300 秒超时、最多 6 次请求均保持原值。
- R06 继续使用原 Memory（包含旧 M9），没有接入本次 R05 输出。
- 原生归档重载和逐请求重建通过。生产源码/Prompt、旧实验与原 campaign 的冻结哈希保持不变。
- 没有 Actor、Verifier、Repair、Memory 发布、完整链路、训练或测试集评估。本文所有任务评分均来自原始输入，不是本次新增任务执行成绩。

预先固定的 [review_criteria.json](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/review_criteria.json)、[manifest.json](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/manifest.json)，事后 [validation.json](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/validation.json)、[input_comparison.json](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/input_comparison.json) 保存实验边界和核对结果。

## 四项目标的结果

| 目标 | v2 + v4 | v3 + v4 | 判断 |
| --- | --- | --- | --- |
| 补回 R05 残差符号到加减动作的反转 | 未记录 | E2/K4 仍未记录 | 未改善 |
| 补回 R06 item 名称/代码优先级 | 未记录 | E1/K4 仍只比较订单号前缀和完整标识符 | 未改善 |
| R05 实际边界与条件查找区分 | 把查找写成已读到边界 | E2/K4 仍写 read the actual minimum and maximum bound rows | 未改善 |
| R06 追加行数的日志证据 | 称行数未独立验证，未保留报告值 | E1/K3 明确 reported appending 3998 rows | 改善；来源强度准确 |
| R05 Parent 全部直接值的概括 | 错把 P7 包括在内 | E1/K3 只归纳五个 Candidate 的公式缓存路线及配对同分，不再断言 Parent 全部直接值 | 有效收窄原错误主张 |
| R06 全部同分的概括 | 错把 Q7/Q14 包括在内，与改善条目矛盾 | E1/K5 正确列出其余 11 个同分成功配对，排除 Q7/Q14 | 改善 |
| 保留竞争解释和收益 | R05 文本项仍保留数值判断也变了 | E2/K2 删除数值判断变化，称收益 localized to the label predicate | 新退步；不是整体过度保守 |
| 合理假设与历史经验 | 保留邮编碰撞假设；不修订已有 Memory | 保留邮编假设，并在建议替换 M1 时保留旧正反对照 | 局部保留良好，未发布 |

新旧完整回答见 [outputs.md](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/outputs.md)。编号 E1/K3 表示第一个 Entry 的第三条 Knowledge，原 JSON pointer 为 `/entries/0/knowledge/2/text`；R05 v3 含两个 Entry，不能仅按 K 编号跨条目定位。

## R05：最重要的程序比较没有改善，文本归因更窄

### 数值任务：保留了一个分支条件，却仍遗漏方向反转

v3 E2/K4 正确限定了 Parent 在**负残差**时向首个非零单元格一次加入全部量，这比不区分分支的概括更具体。但最终仍只把重要差异写成边界来源和跨单元格传播，没有记录：

| 条件 | Parent | Candidate |
| --- | --- | --- |
| 正残差 | unit5 → unit1 减少，原本已有剩余量传播 | unit1 → unit5 增加 |
| 负残差 | unit1 → unit5 增加，首个非零格一次加入全部量 | unit5 → unit1 减少 |

它还写“programs differ precisely in bound source and cross-cell continuation”，将解释收窄到符合条款的两项变化；末尾不再像 v2 那样明确保留边界读取的独立贡献尚未隔离。

实际代码中的 min/max 查找仍带有标签/数值行识别与 `0/inf` 回退，输入没有选中行号和边界值。v3 将它写成已读到实际边界，仍超出了证据。135/189 → 189/189 的改善保留正确，但原因描述不可靠。

证据：[输出 E2/K4](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 111 起；[R05 输入](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) P3 `/runs/4/attempts/0` 行 325 起、Q3 `/runs/5/attempts/0` 行 509 起，回退 619–638、正负分支约 650–690。相同 user 消息哈希证明这些代码没有因 prompt 更换被删除。

### 文本任务：旧有竞争解释被删掉

v2 E1/K2 保留了 Candidate 的 companion numeric test 也发生变化。v3 E2/K2 则称改善“localized to the label predicate”，并声称错误集合恰好是两种文本谓词会发生分歧的两格，同时又承认 E10/E11 原文本不可见。

输入只给出这两格判错，不能确定两种文本谓词在这两格上的实际真假，更不能排除数值分支。代码明确显示 Candidate 新增括号负数处理，而且无法解析数值时返回 None 并跳过写入；Parent 相应返回 False 并走 Sales Tax 分支。这些差异均可能影响最终 E 列值，实际贡献仍未确定。

证据：[旧 E1/K2 / 新 E2/K2](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 19 / 99 起；[Parent 数值判断](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 63 起、[Candidate 数值判断与跳过分支](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R05_evidence.md) 行 198 起。该问题属于已见竞争差异丢失并收紧归因，不是缺少新输入。

### 公式概括：错误主张确实被收窄

v3 E1/K3 保留五个 Candidate 的公式缓存路线、回退条件及同分结果，但不再将 Parent 统一写为直接值。因此原先 P7 这个明确反例不再与其主张冲突。它没有逐一解释 Parent 的实现区别，但当前已不主张这些区别相同，不应因为少写实现详情而继续判错。

邮编 E2/K3 仍保留“去掉空格可能合并键”的机制假设，并承认来源选择也改变；没有为了避免错误而删除有依据的探索。旧 Sheet1 误写不再出现，但新文只列格地址，不能说它已明确重新核对并写对工作表名称。

## R06：结果分组和运行证据改善，item 键差异仍未进入经验

E1/K3 现在明确写“reported appending 3998 rows”，与 Q14 stdout 一致，既使用了实际日志，也没有把程序自报提升为独立金标准。E1/K5 正确列出 11 个双边 hard 1 配对，Q7、Q14 保留在改善条目中，原先同一回答的同分/改善矛盾消失。

但 E1/K4 仍只比较订单数字前缀与完整标识符，没有记录 Parent 优先 item 名称、Candidate 优先 item code 匹配并在找不到时回退名称。两边同为 15/17、H12/H13 判错不能排除这个变化的作用，也不能把程序差异缩成仅有后缀处理。

证据：[新 K3/K4/K5](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/outputs.md) 行 179 / 185 / 191 起；[R06 输入](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R06_evidence.md) Q14 stdout 行 1621、P15 名称优先行 1809/1825、Q15 代码优先及回退行 2114 起。

其他边界：

- `val:80-42`、`val:2768` 的 split 前缀已写对，但 K1/K2 仍将 `val:560-12` 写作 `train:560-12`。身份核对只部分改善。
- Q4 再次仅以 every-nth-row 任务出现在同分列表，没有解释可见公式所确定的分支；不再说未知并不等于完成分支核对。
- 新 K5 还把 Q1 的归一化称为 harmless “because no suffixed identifier is involved”。任务涉及型号键，预览只覆盖前五行；可见内容不足以证明全表不存在相关标识符条件，也不足以据同分确定这一因果解释。更合适的范围仍是本次未测得评分退步。证据见 [Q1 已见输入](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R06_evidence.md) 行 7 起。这是仍需核对的额外概括风险，未作为本轮预设主目标。

## R05 的 M1 替换建议：主要历史对照得到保留

这是本次相对前一轮新增的行为：v3 提出一个 `revises=["M1"]` 的完整替换条目，再新增一个当前批次条目；R06 仍只新增。

只依据模型当次已见的 M1 两条 Knowledge 核对后，主要正反对照保留：三个历史成功配对、一个 Parent 公式缓存成功而 Candidate 缓存不可读失败的配对、另外两个 Parent 直接值成功而 Candidate 失败的配对。前两条新 Knowledge 的历史 evidence 数组与旧两条逐项一致，后两条加入当前公式成功及文件系统中断经验。

旧成功经验中的具体答案区域和任务简称被压缩，但没有发现实质对照、结果方向或重要机制区别被抹掉。没有回读模型未收到的历史原始程序来替其补证据。详见 [M1_review.md](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/M1_review.md)。这是对这一份替换建议的核对，不能推广为历史修订已稳定可靠；本轮未实际发布或替换 Memory。

## 用量与输出规模

| 指标 | R05：v2 → v3 | R06：v2 → v3 |
| --- | ---: | ---: |
| user 字符 | 246,975 → 246,975 | 288,772 → 288,772 |
| API prompt tokens | 81,974 → 82,153 | 96,373 → 96,552 |
| API completion tokens（含 reasoning） | 24,019 → 26,576 | 20,057 → 26,344 |
| 请求耗时 | 147.9 → 160.3 秒 | 140.3 → 181.0 秒 |
| Entry / Knowledge 数 | 1/8 → 2/9 | 1/5 → 1/5 |
| Knowledge 正文空白分词数 | 972 → 823 | 575 → 688 |

数据来自保存的 API usage 和 attempt.json，见 [metrics.json](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/metrics.json)。R05 新输出含历史替换内容，与旧输出全为新增经验的组成不同；条目数或总字数不能作为学习质量指标。单次耗时和输出用量变化也不证明稳定成本趋势。

## 判断及下一步

没有出现整体过度保守：主要收益、机制假设、历史反例和同分案例都在。更突出的问题仍是已见程序差异未进入最终经验，以及 R05 用更确定的措辞收窄到条款对应解释。概括检查在两处目标上有效，但不能抵消关键解释遗漏。

本轮是 temperature=1 下各一次有效输出，且 R05/R06 已参与 prompt 设计。它既不能证明 v3 稳定改善，也不能把所有变化确定归因于 prompt。两项首要目标都未改善，尚不满足此前提出的“明显改善后再做稳定性与迁移验证”的条件，因此本轮没有自动扩展重复运行或完整训练。

下一步应先定位**程序差异提取与 Knowledge 概括之间的丢失环节**，不直接再追加一版 prompt。若另行授权，可以设计保留可核对行为比较结果的诊断性单模块对照，区分尚未识别差异和概括时遗漏；那会改变当前输出/处理方式，需要独立设计，不能用本次最终文本反推模型内部过程。

本次没有继续修改默认 prompt 或生产实现，也没有因语义问题重采样回答。所有新产物仅在本实验目录。
