# 单次 Evidence Review：v19.3 输入协议

当前流程：Issue Fusion → 确定性证据包 → Evidence Review → VERIFIED / NO_EDIT → 确定性 Compiler。

新运行不再允许 MORE_CONTEXT，没有补充次数、第二次上下文调用、上下文请求检查点或补充请求 Schema。正常每个议题一次模型调用；完整响应违反最终契约时，仍最多允许一次修复。修复只接收相同证据包，不能读取更多材料。超预算、连接失败、超时、截断仍是 INCOMPLETE，不由程序转成 NO_EDIT。

## 输入组装

- 原样保留每个议题的全部直接证据、已知反证、关联历史和目标规则。
- 补齐可识别的工具调用/结果配对。
- 对 Findings 引用的政策行，按原始行号连续性和 Markdown 标题边界展开到完整段落。空行形成段落边界，不按本次 Pilot 的规则名或行号特判。
- 若这些政策段落明确提到公开工具名，加入工具定义及该议题已限定轨迹中的对应调用/结果，核验执行条件。名称匹配使用实际工具目录，不硬编码某个业务工具。
- 不再向模型提供未加载内容的事件/政策/工具/规则检索目录；使用 input_scope 说明这是局部材料，未包含材料不能被当成不存在。
- 长 ID 继续采用可逆表示。原始归档完整保存，不裁剪事件、删除反证或按剩余 token 强行截断。

必要上下文仍可能不足：程序的确定性组装不能保证语义充分性。模型应在 reason 中说明不足并返回 NO_EDIT；这只意味着本轮材料不支持修改，不表示问题永久解决。

## 历史兼容

v19.1/v19.2 的纯输入重建和校验仍保留，以验证已有证据及账本；执行器只接受 v19.3。新审计行只保存 input_version 和 result，不再写 context_requests。旧实验目录不改写，旧产物不能在新代码下盲目 resume。

本轮建议继续只复用 Fusion，8 个议题统一按 v19.3 重新审阅：

```bash
python scripts/run_v19_local_review.py run \
  --upstream experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --reuse-local experiments/archive/v19/v19_v4_local_review_once_003 --fusion-only \
  --output experiments/archive/v19/v19_v4_local_review_once_004
```

相同代码下恢复新尝试时，将 `run` 改为 `resume`，保留其他参数。该入口仍停在 Editor 前，不提交 Memory 或启动完整实验。本文命令未在此次实现中执行。

## 离线重建

输入预算仍为 32,000 本地估算 token，输出预算仍为 24,000（包含 reasoning）。8 个 Pilot 议题新输入为 6,269～24,181 token，全部通过预算检查。移除检索目录后，即使增加政策段落和关联工具上下文，总输入仍下降。

明细见 `artifacts/v19_review_once_packet_001.json`。这是离线工程验证，不是方法效果证据。

## 引用类型与修改权限约束

新请求使用 `evidence_review-v19.3-typed-refs-1`，输入证据包与单次审阅流程不变。

- `events` 是事件证据；`policies` 是环境约束；只有 `rules` 中的 Parent Skill 条目可以作为编辑目标。政策中已有一条要求，不代表 Parent Skill 中存在同名规则。
- 根据实际加载的 Parent 规则生成响应 Schema。目标为空时，gap.kind 只允许 MISSING，related_rule_refs 必须为空；有目标时，目标引用只能取自实际规则目录。NO_EDIT 始终可选。规则是否值得新增/修改仍由模型判断。
- 本地校验仍独立执行，不依赖网关严格遵守 Schema。对结构合法响应，一次收集事件引用、反证引用、目标引用、可用操作和已知反证遗漏等可独立检查的错误。反馈包含字段位置、具体引用、实际类型与期望类型；唯一一次修复能看到这些错误，而不是只看到第一项。
- 不自动补引用、删除证据或把 NEEDS_REVISION 转成 MISSING。未知或未加载引用仍拒绝；程序不放宽编辑权限。

实现和测试不含业务案例、政策行号或工具名特判。旧结果和旧失败记录不改写；已完成结果仍可按原始输入重建校验。由于请求协议和源码绑定改变，不应直接 resume 旧未完成尝试。

## v19.4 历史证据边界（2026-09-28）

执行器仍是单次审阅，响应契约和 v18 Compiler 不变。新证据包标记
`packet_version=evidence_packet_v19.4`，请求版本为
`evidence_review-v19.4-scoped-history`。

- canonical case 保存完整证据档案；发送前从当前 Finding 引用、Memory Review 的明确引用及全部已知反证重新确定事件种子。仅关联历史 edit 不再自动展开它全部 Attribution 事件。
- 保留历史行为比较、归因判断、不确定性、联合归因和未归因上下文；这些是历史评估，不是已加载原始证据。只允许引用 events 中存在的原文。
- 历史 edit 正文、Review 结论各表示一次。旧 source_findings 全文不再重复输入，保留来源 ID；匹配的 Attribution 结果使用已有 historical_judgment，其他结果仍保留。
- 工具调用/结果闭合、政策段落和政策相关工具补充保持不变，但不会扩展到与明确证据种子无交集的历史轨迹。
- PAIR 引用采用已有可逆前缀表示；原始引用和归档原文不变。
- 预算仍为 32,000；没有按预算取前 N 条、删除反证、MORE_CONTEXT 或额外 LLM 阶段。材料不足时由模型判断 NO_EDIT；超预算仍为工程 INCOMPLETE。

离线报告：`artifacts/v19_evidence_review_scoped_history_001.json`。它复用 formal_004
第二轮的 8 个 canonical cases，只重建输入，不调用模型、不更新运行检查点。
该报告验证全部直接引用及已知反证都已加载。优化后仍有 3 个议题超预算；
其中价格议题上游 Review 明确引用了 63 条历史事件，不能为了达标静默移除。
因此本次实现不是“所有议题已经可运行”的声明。

旧完成结果、Fusion 和运行目录保持不变。源码绑定与包协议已变，更改后的代码
不能直接 resume formal_004；后续恢复须显式迁移并核验已完成结果，不整批重跑。

## v19.5 共享历史消费边界

后续请求改用 `evidence_packet_v19.5` / `evidence_review-v19.5-shared-memory`。
明确来源引用不再等于必须加载的全文列表；历史原文有独立预算，遗漏反证禁止
VERIFIED。具体契约、测试结果与尚未完成的迁移条件见 [共享 Memory 消费边界](V19_MEMORY_CONSUMPTION.md)。
