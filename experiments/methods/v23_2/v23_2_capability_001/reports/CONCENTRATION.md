# 历史搜索进度问题的集中性核查（模型调用前冻结）

日期：2026-10-19。此核查只读历史真实输出，没有调用新的 LLM；下面的分类和判断先于本次新模板及请求。

## 范围与计数口径

读取 V23 R03／R05／R06 的 Diagnosis 和有效 Preconditioner、第一轮 V23.2 的三组固定 Plan 及 R05 串联、第二轮 V23.2 的 R03／R06。共 **13 份 Plan 记录：4 份 Original，9 份最终 Effective**；第二轮没有 R05 或串联结果，不虚构补齐。实际全文及路径见 [audit_corpus.json](../results/audit_corpus.json)。

计数单位是**去重后的缺失信息需求或错误历史推断类别**，不是出现次数、Update 数或失败 Episode 数。同一位置访问集合支持的“选未检查位置”“不回访旧位置”“全部位置穷尽”合并为一项；同一类别集合支持的“未访问类别”“类别全部检查完成”同样合并。跨类别返回时保存的局部游标单列，因为仅有已采样类别集合仍不能确定原类别剩余实例。状态到历史的错误推断单列。下表中的子表现及多个版本重复只提供证据，不再次计数。

“明确可执行性缺陷”仅指要求的决策信息不能由实际输入支持、且文本未给出可行恢复方式。可观察但不合理的动作限制、策略缺乏依据、过早停止另列；范围有两种合理解释的句子单列不确定，不据此增加已确认数量。reason 和 Checks 不计为 Actor 更新要求。

## 已确认的缺陷：四个去重类别

| 编号 | 隐含信息需求与合并表现 | 真实文本证据与跨材料复现 | 实际能力判断 |
|---|---|---|---|
| H1 | 全执行的位置访问／检查集合，包括单类全部检查、全候选穷尽后才准回访 | V23 R03 u1：`continue searching uninspected receptacles`，两轮 V23.2 均 Keep；V23 R05 u2：`a receptacle you have not yet inspected`；第一轮 R03 u3：`revisit a location only after exhausting the listed candidate receptacles`；R05 串联最终 u2：`inspect each unchecked instance once before returning to an already checked instance` | 候选列出可选动作，未标注全历史访问位；两组行动前记录不能保存整个已检查集合。当前编号可以支持局部下一步，但这些要求没有给出可从当前状态恢复的全局顺序。确认为历史进度缺陷。 |
| H2 | 类别是否未检查／已采样／已全部完成的累计状态，包括跨类别切换及全局终止 | V23 R05 u2：`different uninspected family`；V23 R06 u2：`genuinely uninspected family`；第二轮 R03 u3：`If the cabinets, fridge, and countertops have been checked`；第一轮 R05 串联 u2：`all plausible categories have been inspected once`；两轮 R06 同样要求类别采样完成 | 菜单可反映有哪些类别，不反映它们此前是否已经查过。近期看到某个空位置，不等于整类已穷尽；当前步数也不能推出类别进度。确认为历史进度缺陷。 |
| H3 | 离开某类后返回时，该类剩余实例／续行游标及与其他类别进度的对应 | 第一轮及第二轮 R06 u2：`return to ... remaining receptacles of the earlier family only after ... other ... families have been sampled` | 即便知道当前所在类别或编号，也不知道离开的多个类别各推进到哪里；文本没有定义足以恢复这些游标的完整固定调度。这里否定的是未给出的恢复依据，不是否定所有固定顺序。确认为历史进度缺陷；在 R06 两版重复，不伪称出现于其他轮次。 |
| H4 | 从当前开闭状态反推此前是否检查过 | 第二轮 R03 u3：`because a closed receptacle has not yet been searched` | 当前关闭可观察，但不证明从未打开检查。R03 的 C34 候选实际含 `close cabinet 2`，已经检查过的容器可以重新关闭。确认为错误历史推断；目前仅见于这一材料，不夸大复现次数。 |

来源路径通过 corpus 中 `label` 唯一定位（例如 `V23.2_2_R03`、`V23.2_1_chain_R05`），每项引文均核对对应 `updates[].text` 原文。H1/H2 在 R03、R05、R06 及 R05 串联跨材料重复，非只围绕一个例子。

## 不能全部归因于历史进度的其他问题

| 编号 | 材料及原文 | 分类与不计入分母的理由 |
|---|---|---|
| O1 | 第一轮固定 R05 u2：`no admissible candidate from a different family remains` 即结束搜索 | 当前菜单可判定其他类别候选是否存在，但同类别可能仍有可选位置。这是无依据的过早停止条件，不是缺少历史状态。 |
| O2 | 第一轮 R03 u3：`past the first third of the 50-step budget`；第一轮 R06 u2：`at most two consecutive empty receptacles`；第二轮 R06 u2：`after a small run` | 数值阈值缺少论证或切换尺度含糊；不能把“当前步数”误判为不可见。阈值的历史窗口依赖另由 H 类覆盖，不重复计数。 |
| O3 | 第一轮 R03 u2：`move the target in only when required, then take it back` | 插入／取回备用流程缺少必要性依据，“when required”没有明确判据。现有材料不足以证明该判据在所有情况下不可观察，因此列策略依据不足／操作条件欠明确，不硬归历史进度或新增一项已确认信息缺陷。 |
| O4 | 第一轮 R03 限制空手时 inventory／look；第一轮 R05 对近期空位置使用 `never move` | 条件可以绑定到当前／近期可见信息，主要风险是操作限制过强，不能由本次轨迹证明所有用途都不必要。不是历史进度原因。 |
| O5 | 第二轮 R03 固定柜子／冰箱／台面后换抽屉／架子的顺序；R05 串联要求检查所选类别各实例，又要求不穷尽单个系列 | 前者为实例化策略泛化，后者为执行顺序欠明确／冲突。即便增加记忆也不能自动解决其合理性。 |

不确定项另保留：第一轮 R05 的 `last two inspected receptacles` 可能只指当前窗口内出现的两次检查，也可能追溯更早的两次检查；因有“use current ... last two observations”的限定，不据此增加已确认缺陷。第二轮 R03 在一次 `Nothing happens` 后 `do not repeat that destination` 若仅指下一步，可由反馈支持；若理解为永久禁返，则需额外依据，文本作用范围未明确。两项均不作为集中性达标的新增计数。

温度动作候选、当前持有对象及任务目标标签的局部判断未发现同类全局搜索进度依赖。保留这些有效要求；不能把所有多步策略一概判错。

## 集中性判断与后续边界

**去重后已确认信息可执行性缺陷为 4 类，其中历史搜索进度／错误历史推断为 4 类：4/4（100%）。** H1/H2 在三个历史轮次及串联中反复出现；9 份最终 Plan 中，8 份至少有明确 H 类缺陷，第一轮固定 R05 留作范围不确定，不计为明确命中。后一个数字仅表示材料覆盖，不重复增加缺陷数。

该比率只描述这批已选历史材料中的明确信息缺陷，**不表示全部语义问题都来自历史进度，也不是独立随机样本发生率**。五组 O 类问题和两项不确定性另行保留。进一步将 H1/H2/H3 合并成一类“累计访问进度”、H4 保留为一类“错误历史推断”，结论仍为 2/2；不依靠细分相似症状凑高占比。

因此满足“至少约 2/3 且跨多个材料重复”的预设门槛，**允许开展唯一共享能力说明修改的两组验证**。这只是集中性门槛，不证明 LLM 内部一定误解了哪段话，也不证明澄清后必定改善。

后续只使用冻结 V23 Diagnosis／Preconditioner 原模板，不叠加前两轮修订。若两组最终文本未消除关键进度依赖或新增明显语义问题，不采纳为优先候选，不再改 Prompt 或追加调用。
