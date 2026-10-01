# v19 数据契约：构造示例与验收映射

配套规范：[V19_DATA_CONTRACT_AND_FLOW.md](V19_DATA_CONTRACT_AND_FLOW.md)。

以下均为人工构造的说明例，不是实际运行结果。S0、CA、A/e0、A/p1/P/E1 等是便于阅读的引用简写，正式产物必须补齐规范要求的运行 ID、版本摘要、完整可见轨迹、合法引用与私有绑定。本文件不是可直接输入运行器的 fixture。

## 例 A：整包接受，但保留了一条有局部负面证据的修改

本轮 Parent=S0，Candidate=CA，包含两个 ADD：

| edit_id | target_blocks | after_text（示意） | 来源 |
|---|---|---|---|
| A/e0 | 空 | 在用户授权范围内分别处理可独立完成的事项。 | DA/gap0 |
| A/e1 | 空 | 任一事项信息不完整时暂停全部事项。 | DA/gap1 |

两个修改均有来源 gap 和原始支持证据；有来源不保证推断正确。假设回放得到：

| pair_id | Parent 证据 | Candidate 证据 | 标签变化 | 确定性 delta(S,C) |
|---|---|---|---|---|
| A/p1 | P/E1：因一个无关事项未完成而遗漏已授权事项 | C/E1：分别处理并完成可独立办理的事项 | CF → CS | (+1,0) |
| A/p2 | P/E1：成功完成一个独立、已授权事项 | C/E1：因另一事项缺信息，暂停所有事项 | CS → CF | (-1,0) |

两个 pair 各有 P/S、C/S 标签引用及完整上下文。表格没有显示的观察不得被归因模块补造。

归因记录示意：

| attribution_id | edit_ids | effect / evidence_level | observations | uncertainty / suggested_followup |
|---|---|---|---|---|
| A/a0 | [A/e0] | BENEFICIAL / BEHAVIOR_SUPPORTED | A/p1 的 P/E1、C/E1 及 P/S、C/S 为 SUPPORT | 整包执行未隔离 e1 的影响；PRESERVE |
| A/a1 | [A/e1] | HARMFUL / BEHAVIOR_SUPPORTED | A/p2 的 P/E1、C/E1 及 P/S、C/S 为 SUPPORT | 行为与暂停指令一致，但尚无单 edit 干预证据；REVISE |

两条归因的 applicability 都只覆盖各自观察到的任务条件。这里的 BENEFICIAL / HARMFUL 是局部假设，不是全局因果结论。

**Monitor 独立返回 ACCEPT。** 这是构造例给定的整包决策，不能由上面两个训练 pair 推导；本例不提供任何 Monitor 逐题内容或分数。

提交的 RoundMemoryRecord：

- parent=S0，candidate=CA，edit_refs=[A/e0,A/e1]。
- replay_pair_refs=[A/p1,A/p2]，attribution_refs=[A/a0,A/a1]。
- gate_decision=ACCEPT，retained=CA；两条 edit 都随整包进入 CA。

**下一轮可以如何消费：**

1. 当前 Parent=CA，检索出 A/e1 的负面证据，绑定它在 CA 中的当前规则引用。
2. Diagnosis 判断能否把暂停范围限制在确实缺信息的事项；若证据支持，产生 NEEDS_REVISION。
3. 新 edit B/e0 使用 REPLACE，`related_history=[{prior_edit_id:A/e1, relation:REVISES, basis_refs:[A/a1]}]`。其 source_evidence_refs 仍引用 A/p2 的实际观察，不能只引用 A/a1 的解释。
4. 这一关联只表示正在修正。是否有效由 B 轮及后续的真实证据说明，不能在生成 B/e0 时把 A/e1 标为“已解决”。

这表达了：A/e1 的整包部署事实是 ACCEPT，它的局部效果假设仍可为 HARMFUL。

## 例 B：整包拒绝，但保留了可能有效的修改方向

这是独立于例 A 的另一条构造运行。Parent=S0，Candidate=CX，有两个 ADD：

| edit_id | target_blocks | after_text（示意） | 来源 |
|---|---|---|---|
| X/e0 | 空 | 执行有条件的操作前，先查询工具可直接提供的当前状态。 | DX/gap0 |
| X/e1 | 空 | 未经观察验证的条件下，固定选择方案甲。 | DX/gap1 |

训练配对观测：

| pair_id | Parent 证据 | Candidate 证据 | 标签变化 | delta(S,C) |
|---|---|---|---|---|
| X/p1 | P/E1：未查询状态而遗漏应完成的后续动作 | C/E1：查询状态后完成动作 | CF → CS | (+1,0) |
| X/p2 | P/E1：按可见条件选择方案乙并完成任务 | C/E1：固定选择甲，任务失败 | CS → CF | (-1,0) |

归因 X/a0 将 X/e0 与 X/p1 关联为 BENEFICIAL / BEHAVIOR_SUPPORTED，建议 RETRY；归因 X/a1 将 X/e1 与 X/p2 关联为 HARMFUL / BEHAVIOR_SUPPORTED，建议 REVISE。两者均保留其他 edit 和对话变化的可能影响，引用两侧事件及标签，不声称独立因果效果。

**Monitor 独立返回 RETAIN。** 提交记录仍包含全部两个 edit、两个 pair 和两个 attribution；retained=S0，不是 CX。

**下一轮可以如何消费：**

1. 当前 Parent=S0，X/e0 在当前 Skill 中为 ABSENT；Memory 仍保存其文本、来源和 X/p1 的正面证据。
2. Diagnosis 检查该查询步骤在当前场景是否仍适用、Parent 是否仍缺少它；若支持，产生 MISSING。
3. 新 edit Y/e0 是绑定 S0 的 ADD，以 RETRIES 关联 X/e0。不能把 X/e0 误认为已经部署，也不能对 CX 的旧坐标直接做 REPLACE。
4. 新 Candidate 必须重新经过完整回放和 Monitor；重试有历史依据，不等于预先批准。

这表达了：X/e0 的整包晋升事实是 RETAIN，它的局部效果假设仍可为 BENEFICIAL。

## 例 C：混合证据、未触发与不确定性

- 若同一个 edit 对 p1 的两个标签方向为 (+1,0)，对 p2 为 (-1,0)，归因应保存两组证据并使用 MIXED。不能用净变化为零把负面证据删掉。
- 若某 pair 为 CF → VS，其 delta 为 (+1,-1)，同一任务内已经存在成功与合规的权衡，不得直接记成“改善”。
- 两侧均 CS 不代表 edit 没有效果。可以记录行为变化和 NO_OBSERVED_EFFECT；该范围内没有测得标签变化不证明规则无用。
- 若受检任务明确都不满足规则触发条件，NOT_EXERCISED 应引用这些上下文并说明覆盖范围。没有足够观察判定是否触发时使用 UNKNOWN。
- 若 e0 与 e1 都涉及同一决策且无法拆分，应写 `edit_ids=[e0,e1]` 的联合归因，不给每条分别复制同一个独立收益。
- 若用户在两侧提供的关键事实不同，记录 alternative_explanations，保留原标签；不能仅凭失败标签把 edit 判为 HARMFUL，也不能事后把失败改为成功。
- 若模型调用失败，这属于阶段 INCOMPLETE，不是成功生成了一条 UNKNOWN 归因。

## 本步验收映射

| 检查项 | 对应示例 / 规范 |
|---|---|
| 整包接受与局部伤害能同时表达 | 例 A 的 gate_decision 与 A/a1 分开 |
| 整包拒绝后有效方向不丢失 | 例 B 的完整记忆提交与 Y/e0 重试 |
| 后续新修改绑定当前 Parent | 例 A 的 CA、例 B 的 S0，均不使用旧 Candidate 坐标 |
| 归因能追溯到两侧行为和结果 | 两例的事件引用与 supervision 引用 |
| 原始观测与解释分开 | ReplayPair 保存事实，AttributionRecord 保存解释 |
| 保留反证和维度权衡 | 例 C 的 MIXED 与 (+1,-1) |
| 不制造逐 edit 因果结论 | 证据等级、联合归因及不确定性 |
| 不使用 Monitor 私有证据生成修改 | 两例只给定整包决策，归因证据均来自 Evolution |
| 记忆不是编辑权限 | 后续修改必须重新经过 Diagnosis 授权和整包验证 |
| 不宣称已完成运行时实现 | 本文件全部数据为说明性构造，后续第 2–7 步尚待实现 |
