# 08 第二轮 Memory 独立恢复与共同发布

日期：2026-10-15。**第二轮已通过独立 Memory 恢复完成共同发布**，并通过来源、调用、认识增量、Gate 绑定、成本和状态重建核验。第一轮和第二轮均为 Parent 7/10 → Candidate 8/10、ACCEPT；两轮二十个 Train 不重复。此结果包含显式恢复，不能描述为原冻结协议无故障完成，也不证明历史预条件化具有独立收益。

- [恢复协议](../config/memory_recovery_r2.json)
- [正式状态（Skill 与 Memory）](../../../../../artifacts/methods/v22/08_grouped_continual_memory_recovered_20261015/state.json)
- [已采用 Skill](../../../../../artifacts/methods/v22/08_grouped_continual_memory_recovered_20261015/SKILL.md)
- [Memory](../../../../../artifacts/methods/v22/08_grouped_continual_memory_recovered_20261015/memory_after.json)、[学习原始输出](../../../../../artifacts/methods/v22/08_grouped_continual_memory_recovered_20261015/learning_output.json)、[发布凭据](../../../../../artifacts/methods/v22/08_grouped_continual_memory_recovered_20261015/memory_receipt.json)
- [结果与费用](../results/memory_recovery_summary.json)、[独立核验](../results/memory_recovery_verification.json)、[语义检查边界](../results/memory_recovery_semantic_review.json)、[离线检查](../results/memory_recovery_offline_checks.json)

## 恢复范围与预算

第二轮既有 Gate、候选正文与 diff、冻结分类、二十条 Parent/Candidate 轨迹均复用。没有重新执行环境，没有重新调用分类、Diagnosis、Fusion 或 Editor；本次只有一次 `deepseek-v4-pro` Memory 调用、一次 HTTP 请求。

原 Memory 在 16,384 输出 token 处截断，其中推理占 14,913。新声明在调用前把 `max_tokens` 提高到 **65,536**、读取超时提高到 **600 秒**，保留完整消息、模型、thinking enabled、reasoning_effort medium 及其他请求参数；没有输入裁剪、提示修订或拼接旧残缺输出。消息内容共 363,710 Unicode 字符，SHA256 为 `73806f43d32cde2d6ea0f9129dabb46a8c89f39ceb64b35780c6935afc24dc4f`，与失败请求一致。普通运行器默认预算保持不变。

本次请求北京时间 20:01:41 发出，20:06:08 完成恢复与发布，约 4 分 27 秒。输出 `finish_reason=stop`，实际完成 token 为 **16,694**，其中推理 14,585、正文 2,109；新上限是容纳推理与结果的空间，不要求模型耗尽预算。读取超时不等于整次调用墙钟上限。

第一次网络执行审批在启动进程前被拦截，理由是未确认向外部端点发送完整轨迹的授权。只读核对确认配置使用既有内部代理 `llm-proxy.intra.xiaojukeji.com`，再提交相同命令及证据后通过审批；被拦截的启动未发出模型请求，也未产生第二次 Memory 消费。

## Memory 学到了什么

正式 Memory 从 **3 条变为 5 条**：保留两条，修订一条，新增两条。输出包含三项观察和三项未决问题，没有强制给所有修改正面评价。

1. **修订双物体交付的作用认识。** 原先仅有同一来源、抽屉目的地的证据。当前 Keychain 候选转向另一表面，找到并交付第二件物体；Saltshaker 候选在原来源为空后打开另一橱柜并完成交付。Keychain 是本轮唯一失败转成功，另外两项同类任务原本也成功。记录保留联合候选归因边界，没有将增益单独归因于某条规则。尤其 Keychain 并未先回到真正原来源检查为空，不能声称它完整执行了字面条件分支。
2. **记录类型纪律的收益限制。** Pan 任务的 Candidate 没有继续处理 Pot，但仍未找到 Pan 并失败；Parent 也失败。避免错误替代与完成任务是两件事，当前反馈不能证明 Pot/Pan 是否为可接受别名，也不能把失败归因于新规则。
3. **记录停止分支的可执行性限制。** Parent 中实际 `stop` 命令不在可用动作中，返回 Nothing happens；当前候选缺失灯具时仍运行到步数上限。空动作也无效，但空动作不是一次字面 `stop` 尝试。此反馈限制“没有不同候选就停止”的可执行性，不证明该触发条件已满足。

第一轮的直接热／冷处理认识，以及有限历史搜索仍会失败的认识保留。两轮证据通过上下文编号区分；旧来源和退役理由仍可追溯。Gate ACCEPT 只代表整体版本晋级，不把各编辑标记为成功。

### 语义检查发现的边界

现有校验确认结构、来源引用、限制继承／退役格式和发布绑定，不能自动证明每项语义判断正确。本次有一条**复合旧限制退役范围偏宽**：旧句同时包含“其他来源”“目的地 move 不可用”“非抽屉目的地”三种未验证情况。新反馈覆盖了其他来源和非抽屉目的地，**没有验证目的地 move 不可用时如何完成任务**。模型将整句退役，不能据此把第三种情形也视为已验证。

该问题已单独保存于语义检查结果；未人工改写模型输出、未伪造证据、未追加模型调用。后续消费这条 Effect 时应保留上述未验证边界。正式发布表示既有校验和共同版本交接完成，并不表示 Memory 的每一句认识已经充分验证。

## 发布与费用

发布复用原冻结 Gate：Candidate 成功数 8 严格高于 Parent 的 7。此前成功的七项均继续成功；本次没有新增轨迹，也没有重新测量成功率。候选 Skill SHA256 为 `528c86f23bf4e49e40406f0451a5f1f5693036278a9b1f6a6f271cd66ff5d9ad`；正式状态 SHA256 为 `e2de4a15216702791403bb6f60f29972d890d191334bae52d2aa2096cf6e21d9`，`round_index=2`，包含二十个唯一已训练任务。

| 范围 | 环境 episode | Actor 请求 | Pro 调用 | HTTP 尝试 | 输入 token | 输出 token | 已报告总 token |
|---|---:|---:|---:|---:|---:|---:|---:|
| 本次 Memory 恢复 | 0 | 0 | 1 | 1 | 119,314 | 16,694 | 136,008 |
| 含全部失败与恢复的累计 | 40 | 889 | 12 | 906 | 1,731,454 | 731,829 | 2,463,283 |

累计另有五次 HTTP 尝试用量未知，未按零计算；原分类失败、首次恢复 Fusion 失败和本次之前的 Memory 截断均保留并计入。没有价格或货币账单可据以换算实际金额。复用轨迹和模型记录不重复计费。

三个旧运行档案保持不变，原来的未完成报告仍表示各自当时的停点。当前发布入口为本报告所链接的新 `state.json`；恢复报告的 `latest_state` 也指向它。离线 327 项 V22 测试通过，独立恢复成功／截断分支走查通过，新发布状态可从原始响应完整重建。

## 本次完成与未作结论

两轮持续执行、真实 Parent 继承、配对 Replay、Gate、跨轮 Memory 学习和共同发布链路已经完成；本次完成的是第二轮末尾学习与交接。第二轮初稿确实有两项要求被替换，但既有 Fusion 的变更依据未正式引用 Effect，仍不能把执行收益归因于历史预条件化。当前不新增 Selection／Test，不启动第三轮，不针对同批任务返工候选，也不在本次修复复合限制的表示或退役算法。
