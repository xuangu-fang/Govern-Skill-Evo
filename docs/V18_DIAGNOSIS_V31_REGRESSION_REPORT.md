# v18 Diagnosis Prompt v3.1 回归报告

日期：2026-09-20。Prompt：`v18-group-diagnosis-3.1`，Prompt SHA-256 `5db3aabc070cbbdc20347fc912efe7c5d91b61cacd5fafc551a38b2ebf22ecf1`。

## 改动与冻结边界

本次只重写 Diagnosis Prompt 的可学习性判定段，Schema、引用校验、Compiler、Editor 和 Gate 均未修改。判定分为三步：识别有支持的选择关系、检查条件与动作是否可执行、检查输出是否依赖无来源的替代动作或信息。候选动作不要求已在成功轨迹中完整执行；有限动作集合加一次失败本身也不能选择其补集。可回答的澄清必须取得具体事实，且回答值能够映射到后续动作。明确 policy、用户约束、工具契约或观察关系支持的禁止不要求虚构替代动作。

Prompt 不包含 cedar、行李、保险、coverage 或任何组编号等专项规则。

原 G01–G06 输入和 v3 rubric 未改，rubric SHA-256 仍为 `261ad5ef144e8be4f6cb611e82d7a65b4920455197e77ba17d6b0f430165b4a4`。在修改 Prompt 前，另行冻结了五类通用边界样本与评分：机制未知但关系稳定、动作有限但无选择依据、有可回答的澄清、仅有负面结果、明确禁止依据。其 cases SHA-256 为 `b2b4da59bb444fbed706880ea2f02e6f483ffb42dc7b30d950a542036dce6fce`，rubric SHA-256 为 `f0f1e582e5449b864226cf994be24639d590c83fcdf9072f00387adfc9a69ee4`。两套评分均未使用 Monitor 逐题数据或 Gate 转移。

## 执行结果

第一次执行因未连接内网 VPN，11 次调用全部在 DNS/传输层失败，没有模型响应或 token 消耗，审计保留在 `artifacts/v18_diagnosis_v31_pilot_001/`。连接恢复后使用新目录执行：11/11 一次完成且结构与引用 VALID，0 重试；prompt tokens 247,423，completion tokens 75,676，总计 323,099 tokens。

原六组按未修改 rubric 为 5/6 通过：G01、G03、G04、G05、G06 PASS，G02 FAIL。G03 现在只保留人数 gap，将缺少额度映射的行李问题留在 unresolved，没有生成禁止、隐藏规则澄清或猜测参数。G06 和其余非退化组保持通过。

五个通用边界样本 5/5 通过：稳定但机制未知的关系被保留为局部候选；有限动作但无选择证据和仅有负面结果均为 NOT_ADDRESSABLE；可回答澄清被识别为可执行信息路径；有明确 policy 依据的禁止被保留。

完整人工评分见 `artifacts/v18_diagnosis_v31_pilot_002/semantic_assessment.json`。

## 剩余语义跳转

G02 的跳转发生在 Analysis → Addressability。Analysis 正确保留 cedar 与失败、orbit 与成功的可观察关联；Addressability 认为没有任何行为对照、查询结果、policy 或工具结果能够为 cedar 选择反向写入顺序，因此不生成 gap。v2 则把“反向顺序”作为失败顺序在二元动作空间中的未观察补集。

这与新增的通用“动作有限但没有选择依据”对照形成直接张力：该对照的预写标准明确要求不能因为一个动作失败、且只剩另一个动作，就推断补集动作。v3 的 G02 rubric 又要求保留同型的 tentative 替代顺序。此时继续增加 Prompt 条款，会把冲突隐藏在措辞里，并重新引入两端摇摆。

因此本轮不再修改 Prompt，v3.1 不进入正式 freeze，正式四轮实验仍不得启动。下一步应先在评估层明确一个统一原则：未观察的互补动作在什么额外证据下可以成为候选。确定后应先更新一套新的预写通用 rubric，再决定 Prompt 是否需要变化；原 rubric 和本次结果保持不动作为历史审计。

## 验证

相关 v17/v18 测试 543 项通过。正式四轮入口继续因冻结的 Prompt 摘要与 v3.1 不一致而拒绝启动。
