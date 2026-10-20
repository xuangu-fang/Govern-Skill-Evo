# V22 08：Fusion 单次续行、第二轮 Replay 与 Memory 截断

日期：2026-10-15。**第二轮实际更新、十项 Replay 和 Gate 已完成：Parent 7/10 → Candidate 8/10，Gate ACCEPT。最后的 Memory 调用输出截断，尚未产生有效 Memory 或第二轮发布状态；不能称两轮持续更新已全部完成。** 第一轮仍是最后正式发布的 Skill／Memory。

[原运行报告](REPORT.md) · [分类恢复报告](RECOVERY_REPORT.md) · [本次结构化结果](../results/fusion_resume_summary.json) · [档案核验](../results/fusion_resume_verification.json) · [已执行阶段重建](../results/fusion_resume_stage_verification.json) · [本次授权与预算](../config/fusion_resume_r2.json)

## 接续关系与实际范围

用户在首次恢复的 Fusion 失败后明确授权：单独归档该失败，保持输入与提示不变，仅重新调用 Fusion 一次，再继续剩余流程。本次没有修改分类、Diagnosis、Fusion／Compiler、Editor、Replay、Gate 或 Memory 的方法提示和契约，没有人工补写模型决定。

原运行与首次恢复的全部 208／123 个文件绑定为只读来源。保留原分类截断和第一次 Fusion 无效输出；本次在新目录 `artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015` 执行。R1 正式状态、R2 十条 Parent 轨迹、已经成功的 Classification／Diagnosis 均复用。复用调用的原始记录逐字相同，不再请求模型；新的 Fusion 完整 messages 与旧失败请求相同，不加入错误反馈或研究者分析。

本次最多新增 Fusion、Editor、Memory 各一次以及十条 Candidate episode。包含两次失败恢复后，总上限为 40 episodes／11 Pro。没有 Direct、Selection／Test、跨轮重复 Train、候选返工或按表现重跑。第一轮及旧轨迹保持原有混合调度历史；本次第二轮 Replay 实测并行峰值为 8。

## 有效更新构造：发生了什么，尚未证明什么

复用的独立 Diagnosis 提出三项要求：持物后所需工具未见、请求类型与观察对象不符、交付第一件后第二件未见。新的 Fusion 返回有效 `ready`，实际执行两项替换：

- u1 → u4：将缺失工具／目的地的搜索，从全局“已访问／未访问”判断改为当前可用动作和最近两步中的重复模式。
- u3 → u5：将第二件未见时的搜索同样限制在当前动作及最近两步可见信息中；保留不拿取无关物体、重新观察等要求。
- u2 原样保留，限制将 Pot 等其他观察类型当作请求的 Pan 加工交付。

这是实际要求变化，`requirements_changed=true`。Fusion 总体理由提到历史 m3 中“最近两步搜索尚非已证明解决方案”的限制，但两项 `changes.basis` 只引用当前轨迹、分组和 capabilities，正式 `history_cited=[]`。因此，可以确认历史被提供、理由提到历史限制、实际要求发生变化；**不能据此断言历史 Effect 独立导致了变化，或把全部改进归因预条件化**。当前能力约束也能解释这些替换，本轮未设置独立对照。

Editor 在实际 R1 Parent 上扩展双物体条款，并新增类型约束和持物后缺失工具条款，得到统一七段 Skill；没有分别生成十份 Skill。它返回空 issues，通过现有结构／引用／文本映射核验；这不等于语义可执行性被证明。初稿中“distinct 候选耗尽”和自然语言 stop 的能力边界仍需结合执行解释，未在本次人工改写。

Parent SHA256：`6ead6e278eddfb70cb00d71ecb6987dc5d59396cfb0bd8e39cfab7797a1862fa`。Candidate SHA256：`528c86f23bf4e49e40406f0451a5f1f5693036278a9b1f6a6f271cd66ff5d9ad`。

[有效要求](../../../../../artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2/effective_plan.json) · [Fusion 原始决定](../../../../../artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2/outputs/fusion.json) · [实际 Candidate](../../../../../artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2/candidate/SKILL.md) · [实际 diff](../../../../../artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2/candidate/actual.diff)

## 第二轮配对 Replay

| Train | Parent 步数／结果 | Candidate 步数／结果 |
|---|---|---|
| train:0002 | 50／失败 | 50／失败 |
| train:0008 | 4／成功 | 4／成功 |
| train:0009 | 5／成功 | 4／成功 |
| train:0014 | 15／成功 | 10／成功 |
| train:0023 | 8／成功 | 33／成功 |
| train:0024 | 50／失败 | 50／失败 |
| train:0029 | 36／成功 | 33／成功 |
| train:0036 | 50／失败 | 28／成功 |
| train:0037 | 8／成功 | 17／成功 |
| train:0038 | 9／成功 | 10／成功 |

原七项成功全部保持，0036 新增成功，0002／0024 仍失败。完整批次 Parent 235 步、Candidate 239 步；非法动作分别 2／3 次。统一 Candidate 的联合观察如下：

- **Keychain 修复。** Parent 第23步交付第一件后循环搜索，50步失败；Candidate 第22步交付第一件，24步访问 tvstand 看到第二件，25步拿取，28步完成交付。Candidate 没有先返回第一件的实际来源 sidetable 2，不能把这一成功写成“严格验证返回原来源为空后才转移搜索”的单条因果证据。
- **另一处搜索分支有执行机会。** 0038 Parent 从同一 cabinet 拿两件；Candidate 先从 countertop 拿第一件，交付后第5步返回发现已无目标，第6／7步前往并打开 cabinet，拿第二件后成功。这支持一个不同来源的联合行为观察；Parent 本来已成功，不属于新增修复。
- **Pan 的局部变化未转成成功。** Parent 多次取 Pot、冷却和交付；Candidate 未再加工或交付其他类型，但始终未找到 Pan。它有两次非法导航字符串，不能将全部未成功归因于目标类型约束。
- **CD 找灯仍未解决。** Candidate 始终没有执行 use，继续在桌面、架子和 CD 检查中循环，50步失败。第38步的一次空动作来自响应中示例空 action 标签先被解析，末尾另有 look 标签；这是输出／解析边界问题，不应全归为搜索策略。原始响应未修改。
- **成功保留不代表没有干扰。** Bread 从8步增至33步，先在柜子／台面间搜索，27步才到 diningtable 发现 Bread，之后完成冷却交付；双 Newspaper 从8步增至17步，Saltshaker 从9步增至10步。清洁从15步降至10步，Mug从36步降至33步。这里只记录行为与预算变化，不另设效率优化目标，也不从单次配对证明变化由某条编辑造成。

八并行峰值由轨迹起止时间计算。本次 Replay 批次约 1714.04 秒（28.57 分钟），由最后的 CD 长轨迹决定结束时间；任务内仍顺序执行。不能以不同任务或不同生成耗时的批次直接计算固定并行加速倍数。

## Gate 已 ACCEPT，Memory 未完成，状态未发布

[Gate](../../../../../artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2/gate.json) 根据完整同批原生成功数判定 `ACCEPT / success_rate_increased`，7/10 → 8/10，没有增加零退化否决条件。Gate 决定已保存，但按当前协议仍须 Memory 有效处理后共同发布 Skill／Memory。

最后一次 `post_gate_learning` 输入 398,816 Unicode 字符，未超过 400,000 上限，但仅剩 1,184 字符余量。服务报告输入 119,314 tokens、输出 16,384 tokens，其中 reasoning 14,913，`finish_reason=length`；调用约263.79秒，输出 JSON 在 `memory_delta` 的 limits 字符串中截断。它不是输入超限，也不是此次调用发生传输超时。

[失败 Memory 调用](../../../../../artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2/calls/post_gate_learning.json) 保留原始部分输出及用量。部分 findings／memory_delta 只是未完成草稿，没有通过校验、没有成为正式 Effect，也没有更新 R1 Memory。不存在 R2 `memory_after.json`、`memory_receipt.json` 或 `state.json`；最后有效状态仍为 [R1 继承副本](../../../../../artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/checkpoint/state.json)。不能将失败后无发布写成 RETAIN，也不能仅凭已保存 Gate 宣称第二轮正式采用已经完成。

## 调用成本与核验

| 本次新语义阶段 | 输入 tokens | 输出 tokens | reasoning | 结果 |
|---|---:|---:|---:|---|
| Fusion | 75,663 | 8,396 | 7,679 | 有效要求替换 |
| Editor | 75,228 | 6,975 | 5,648 | 一份有效 Candidate |
| Gate 后 Memory | 119,314 | 16,384 | 14,913 | 输出截断，未学习／发布 |

本次新增10 episodes、239次Actor逻辑请求、3次Pro、242次逻辑请求、243次HTTP尝试；输入594,874／输出229,838，共824,712已报告tokens。Bread第2步遇到一次HTTP429，按原有同内容传输重试策略成功；这不是episode重跑，其首次尝试用量未知。

包含原运行、分类恢复与本次续行，累计40 episodes、889次Actor请求、11次Pro、900次逻辑请求、905次HTTP尝试；输入1,612,140／输出715,135，共**2,327,275已报告tokens**，另有5次HTTP尝试用量未知。两个旧失败和本次Memory失败均计入；缓存复用的分类／Diagnosis／Parent未重复计费。服务报告的输入包含缓存命中，不直接等于现金计费输入。

模型仍为Actor `deepseek-v4-flash`、语义 `deepseek-v4-pro`；记录参数temperature1、thinking enabled、reasoning medium、stream false；本次三次Pro均max_tokens16384／timeout300秒，Actor每episode最多50步、seed42。Git HEAD `7d4749541dab04397ea146e56dc762a26ba81a3b`，实际身份由运行源码、配置和恢复控制脚本快照绑定。新control只编排复用／单次续行，不改方法实现或提示。

此前V22共325项离线测试通过；本次续行另外用合成数据验证成功发布与Fusion再次失败两条出口，核对不重新请求分类／Diagnosis、不重跑Parent、新调用数及累计成本去重。真实结束后档案核验为 `artifact_valid=true`、`campaign_complete=false`、`published_rounds=1`，确认原两份失败档案未变，复用来源一致。另外独立重建了本轮分类、Diagnosis、Fusion、Editor、20条配对轨迹、Gate及冻结Memory输入，结果一致；确认没有Memory后状态或R2发布文件。核验只认证来源、预算和确定性衔接，不认证语义解释或因果收益。复核入口为 `artifacts/methods/v22/08_fusion_resume_control_20261015/verify_executed.py`，合成续行测试保存在同目录 `test_resume_offline.py`。

## 剩余工作

真实数据已经回答了本批次的Skill修复与保留能力问题，并展示了初稿到实际要求及Skill的变换；历史响应的具体作用仍需严谨区分，不能因最终8/10就宣称预条件化优势。两轮当前只剩第二轮Memory有效处理及Skill／Memory共同发布未完成。

本次授权的额外Fusion调用和后续预算已用尽，按照预声明停点没有自动重试Memory、人工拼接部分输出或增加新实验。后续若恢复，应从已冻结的同一Memory输入及Gate继续，单独记录输出预算修订和累计失败成本；不需要重新执行分类、Diagnosis、Fusion、Editor或40条已有轨迹。输入已逼近上限，也提示后续扩大轮数前需要检查历史上下文增长，避免继续堆叠重复材料。
