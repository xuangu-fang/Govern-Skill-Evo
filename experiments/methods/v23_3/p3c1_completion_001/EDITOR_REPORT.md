# P3-C1 Editor 最终审计

A、B 均一次真实生成有效 Candidate；离线严格重载、解析、应用和 actual.diff 比对通过。两份 Candidate 不相同，B 也不等于 Parent。没有新 Editor 调用或人工修补。

| 项目 | A：自由替换结果 | B：全部 Keep 结果 |
|---|---|---|
| Preconditioner | u1/u2 修改，u3 Keep | u1/u2/u3 Keep，无 Update Patch |
| Editor 结果 | candidate，finish_reason=stop | candidate，finish_reason=stop |
| 请求正文 | 15,179 bytes | 14,230 bytes |
| input / completion / total tokens | 3,033 / 7,419 / 10,452 | 2,827 / 7,573 / 10,400 |
| reasoning tokens（已含于 completion） | 6,531 | 6,831 |
| 调用耗时（归档起止） | 36.42 秒 | 32.14 秒 |

两个请求除 messages 内 Effective Plan 外，模型和采样参数相同，timeout 均 (60,300)，transport_retries=0；Editor payload 唯一差异字段为 `plan`。请求完整记录分别在 [A HTTP request](../../../../artifacts/methods/v23_3/p3c1_r05_replay_001/editors/A/http/001/request.json)、[B HTTP request](../../../../artifacts/methods/v23_3/p3c1_r05_replay_001/editors/B/http/001/request.json)。金额未返回，未知。

## Effective → Skill 的落实

| 原要求及 A/B 差别 | 实际 Skill 修改 | 审计结论与风险 |
|---|---|---|
| u1：精确目标、禁止近似物替代；A 增加 knife/butterknife、pot/pan、cup/mug，并把适用对象扩至 surface | 两组改写 general step 2，均保留旧 soapbottle/dishsponge 示例；A 带入新增例子和 surface | 主要差异可追溯到 Effective，未发现 Editor 独立发明新的目标替换策略 |
| u2 A：未检查位置优先；扩充开放表面；保留同类实例覆盖，并要求回访前检查该类剩余未查实例及另一类 | A general step 1 包含 “still inspect the remaining unexamined receptacles of that type, as well as a different type, before returning to any location…” | 强回访前置条件来自 A Effective，不是 Editor 新增。历史支持防遗漏，不自动证明这种全称前置条件合理 |
| u2 B：检查某类 several 个仍未找到时，先扩展到另一类至少一个 still-unexamined 位置，再回查旧位置 | B general step 1 基本逐项落实 Original | B Keep 把原策略实施到 Skill；没有证明该策略满足 Actor 的有限历史条件 |
| u2 A：期望导航缺席时转向其他未查可执行位置，不重查当前点 | A general step 1 落实；与 step 5 的适当 direct action 优先条件并列 | 可能存在条件重叠和优先级不清。Editor 未解决，但不是擅自新增禁令；本轮未观察到可证明由此跳过必要 direct action 的实例 |
| u3 两组一致：核对当前 admissible；导航缺席但适当 direct action 可用时直接执行 | 两组新增 general step 5；仅 “that/the direct action” 等措辞差异 | 基本忠实落实。文本校验通过不能保证 Actor 标签输出或动作合法性 |

原位置级结束条件 “Continue until the exact target is found or all plausible candidate receptacles have been inspected once” 在两组均保留。**没有**改成“每类采样一次即可结束”。两组保留 lamp 段落、general step 3 的必要清洁、step 4 的交付和尾部成功能力保留要求。旧 Parent 没有独立的正向 cool/heat 流程，因此不能把两组未新加该流程误记为删除旧能力；本轮 P10 的必要 cooling 仍需按真实执行验证。

检查未发现明显独立于 Effective 的大幅策略新增或必要段落删除。这个判断是文本对应审计，不是对所有语义等价的形式证明；Checks 的实际达成也只能看 Replay。没有照明/多实例任务，文本未变不足以证明这些能力在行为上无退化。

完整依据：[A Effective](../p3c1_r05_replay_001/inputs/A_effective.json)、[B Effective / Original](../p3c1_r05_replay_001/inputs/B_effective.json)、[A actual.diff](../p3c1_r05_replay_001/editors/A/actual.diff)、[B actual.diff](../p3c1_r05_replay_001/editors/B/actual.diff)、[A Candidate](../p3c1_r05_replay_001/editors/A/candidate.md)、[B Candidate](../p3c1_r05_replay_001/editors/B/candidate.md)、[重载审计数据](editor_audit.json)。
