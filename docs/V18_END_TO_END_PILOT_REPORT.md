# v18 单轮端到端 Pilot 报告

日期：2026-09-19  
输出：`experiments/v18_pilot_001/`  
模式：独立 `PILOT`，固定一轮，共用 v18 正式冻结任务、Prompt、模型与 seed 200。

## 结论

完整链路已跑通：32 个 Evolution → Grouping → 6 个 Diagnosis → Compiler → Editor → 41 组 Parent/Candidate Monitor → Four-Delta Gate。最终 campaign 状态为 `COMPLETE`，Gate 决策为 `ACCEPT`。

Pilot 证明 v18 调度、恢复、Compiler/Editor 接线和 Gate 可以在真实模型调用下完成一轮，也证明 Editor 基本能够保持 Diagnosis 的条件、范围和不确定性。但 Diagnosis 仍存在两个属于 learner 的通用语义问题，因此不建议立即启动正式四轮实验。下一步应针对“不可执行的隐藏机制”和“未知机制转新门槛”做 Prompt v3 的最小修订，再用本次固定输入回放验收；不得依据具体 Monitor 错题定向修改 Prompt。

## 运行结果

- 最终有效样本：32 个 Evolution，41 个 Monitor 任务 × Parent/Candidate，共 114 个完成 rollout。
- 当前有效 Grouping：6 组。
- Diagnosis：6/6 VALID；5 组 ADDRESSABLE，1 组 NO_ISSUE；共 6 个 gap，全部为 MISSING。
- Compiler：VALID；6 个 ADD，1 个 NOOP。
- Editor：VALID；1 次有效模型调用；Candidate SHA-256 为 `9c0d780422914696fbf195f162f6c0d8d0e571b790e3402a2201dbca37feab49`。
- 6 个有效 Diagnosis 合计 288,125 tokens；有效 Editor 调用 65,219 tokens。中断、空响应与受并发影响的调用保留在审计目录中，未混入最终 Gate。

Gate 的聚合计数：

| 指标 | Parent | Candidate | Δ |
|---|---:|---:|---:|
| Success | 28 | 34 | +6 |
| Compliant | 34 | 41 | +7 |
| Compliant + Success | 21 | 34 | +13 |
| Violating + Failure | 0 | 0 | 0 |

Candidate 的二维分布为 CS=34、CF=7、VS=0、VF=0。Gate 的 ACCEPT 仅说明聚合结果满足 Four-Delta 条件，不替代 learner 语义验收，也不作为针对具体 Monitor 任务修改 Prompt 的依据。

## learner 语义评估

按 Grouping 的 6 个当前有效组评估：4 组通过，1 组部分通过，1 组失败。

| 组 | 结果 | 说明 |
|---|---|---|
| G01 购买保护 | 通过 | 保留 partner_direct 条件、tentative 状态和 consolidated 未决分支，没有扩成普适规则。 |
| G02 双地址写入 | 通过，带风险 | 将 cedar 与写入顺序保持为局部候选假设，没有扩展到 orbit；替代顺序未被直接观察，但不确定性被保留。 |
| G03 多乘客与行李 | 部分通过 | 乘客数量规律保持为 C002 的候选边界；行李规律只证明“不能全部计为 nonfree”，却没有可执行的免费额度映射。Diagnosis 仍判 ADDRESSABLE，可能迫使 Agent 猜测隐藏合同。 |
| G04 结算渠道 | 通过 | 保留 horizon/summit 条件和 tentative 状态，明确可改变的是首次更新前的总价计算。 |
| G05 全部成功合规 | 通过 | 正确输出 NO_ISSUE，没有因 Parent 为空而制造 gap。 |
| G06 保险取消 | 失败 | 将内部保险覆盖不可见转成“没有可见的明确覆盖证明就拒绝”，新增 verification duty、prohibition 和 stopping outcome，正是 v18 要避免的未知机制→门槛转换。 |

Editor 对 6 个 gap 的改写整体忠实：条件、观察范围和 tentative/未决状态均保留；未发现 Editor 独立新增 transfer fallback 或把候选规律改写为普适确定规则。G06 的强门槛已经存在于 Diagnosis gap，不能归因于 Editor。

## 执行与恢复记录

第一次启动因 VPN 未连接发生模型服务连接错误。VPN 恢复后，Evolution 中一个任务及后续 Grouping、Diagnosis、Monitor 出现若干空响应；调度通过显式恢复复用完成产物，最终补齐全部样本。空响应属于运行完成性问题，没有作为 learner Prompt 证据。

调试期间发现工具等待返回后旧 Python 进程仍运行，造成两个恢复进程并发，并生成了不同 Editor Candidate。绑定校验阻止了不同 Candidate 的 Monitor 结果混用。受影响的 Monitor 目录完整归档为 `monitor_private.concurrent-1`，最终 Gate 使用当前 Editor Candidate 重新完成全部 82 个 Monitor 调用。旧 Grouping 的 Diagnosis 目录已隔离到 `diagnosis.stale-grouping-1`。

调度随后增加了非阻塞 campaign 文件锁，并在未完成 Grouping 被替换时自动隔离其 Diagnosis 目录。相关测试覆盖并发拒绝和旧 Diagnosis 隔离。

## 下一步验收标准

Prompt v3 只处理 learner 的通用转换问题：

1. ADDRESSABLE 必须给出由现有证据和可用信息决定的具体动作；只知道“当前动作错误”但不知道替代动作如何选择时，不应制造要求 Agent 猜测隐藏机制的 gap。
2. 不得把缺少隐藏合同、映射或机制信息改写为新的证明义务、默认拒绝、禁止执行、转人工或停止条件。
3. 如果证据支持一个局部经验结果，应直接保持为带范围与不确定性的候选规律；如果证据不足以决定替代行为，则判 NOT_ADDRESSABLE 或明确不产出执行规则。

使用本次 G03 行李和 G06 保险输入作为固定语义回归，同时保留 G01/G02/G04/G05 作为非退化样本。该回归只评价 Diagnosis/Editor 的语义保持，不使用具体 Monitor 错题或转移结果构造规则。
