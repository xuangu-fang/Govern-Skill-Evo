# Pair Attribution v19.2

这是独立新版，不修改 `attribution_v19.py` / `attribution_prompt_v19.py` 的单次全局 Attribution，也不改 v18。新实现位于 `src/skill_evolution/attribution_pairs_v19.py`，版本分派位于 `attribution_dispatch_v19.py`。

## 1. 逐 pair 输入和观察

从原有经过账本与 Replay 重验的 learner projection 构造输入；不接受 Monitor 数据。每个请求只包含一对完整 Parent/Candidate 事件、本轮全部 edit 的 before/after、Parent Skill 和这对轨迹的完整公开领域 policy/tools。其他 pair、其他领域 context、edit 的 Diagnosis 来源全文与历史关系不进入模型。

不通过关键词筛选 edit，不丢弃持平 pair，不截断原始事件。`P1` / `C1` 是精确事件引用别名，只在引用字段展开，不替换自由文本。原始 Replay 和原始响应完整保留。

模型输出：

```json
{
  "schema_version": "pair_attribution_response_v19.2",
  "observations": [{
    "status": "ATTRIBUTED",
    "edit_ids": ["EDIT/..."],
    "parent_evidence_refs": ["P2"],
    "candidate_evidence_refs": ["C3"],
    "behavior_comparison": "具体行为比较",
    "reason": "关联依据及必要限制或反证"
  }]
}
```

- `ATTRIBUTED`：必须指定 edit，并引用双侧至少一条 assistant/tool 行为证据。多个 edit 难以分开时作为联合集合。
- `UNATTRIBUTED`：观察到变化，但不能可信关联到 edit；`edit_ids=[]`，仅解释为何不足，不细分原因类别。仍需双侧事件引用。
- 没有相关观察时允许 `observations=[]`。同一个 pair 可以同时保留 ATTRIBUTED 和 UNATTRIBUTED。
- 不让模型输出效果标签、分数、修改建议或后续操作；没有 MORE_CONTEXT。

引用验收只证明结构和来源有效，不证明自然语言关联正确，也不把任务结果变化当成因果效应。

## 2. 逐 pair 保存、预算与恢复

默认并发 2（API 可设 1–8）；单次输入代理预算 32,000，输出上限 24,000，超时 300 秒，SDK 重试 0。输入计数使用 cl100k_base，不能等同网关实际 token。首请求和修复均检查预算，超预算不发送、不截断。

每个 pair 保存 input、initial/request、response、response_complete、result、status。契约失败至多一次修复，原响应、精确错误、修复请求与响应都保存。超时、截断、拒答不进入契约修复，也不转成 UNATTRIBUTED。

单个 pair 失败不会重跑其他 pair；所有 pair 有效后才发布 `attributions.json`，否则整批 INCOMPLETE，不能提交 Memory。`resume=True` 复用已完成响应，并重验输入、Prompt、配置与当前实现摘要；不能混用新旧契约。

无完整响应的调用需显式执行 `archive_uncertain_call(directory, pair_id=..., phase='initial'|'repair')` 后恢复。它保留失败请求和归档 receipt，不替换已完成结果或无限重试无效响应。进程被杀后可先 resume，让不完整调用被识别为 INCOMPLETE；再显式归档。改变协议/预算使用新目录。

完成包使用固定文件清单：input、config、protocol、profile、pair-audit、attributions，以及 validation。`pair-audit.json` 汇集成功调用路径上的原始请求、原响应、修复响应和错误，是 Memory 可独立重验的审计副本；失败尝试继续保存在运行目录。Memory 不必依赖原运行目录存在。

## 3. 确定性聚合、Memory 与调度

按**精确 edit 集合**汇总 ATTRIBUTED 观察，不再调用全局模型。联合证据不转成各成员独立信用。一个集合中同一 pair 的多条观察合成一项 pair 观察，保留 observation IDs，标签只统计一次。

程序按关联 pair 的 success/compliant 两个维度保留正负方向：

| 关联结果 | effect |
|---|---|
| 有正有负，含同一 pair 两维方向冲突 | MIXED |
| 仅正向变化 | BENEFICIAL |
| 仅负向变化 | HARMFUL |
| 有行为关联，但标签均不变 | NO_OBSERVED_EFFECT |
| edit 没有任何可信关联观察 | UNKNOWN |

这些仍是**行为关联范围内的结果标签摘要**，不是隔离单个 edit 后测得的因果效应。无观察不生成 NOT_EXERCISED。UNATTRIBUTED 仅留在 pair 审计结果中，不给 edit 分配效果证据。单独未知记录不会覆盖已有联合记录；只有完全未被关联的 edit 才补 UNKNOWN。

新版不生成 `suggested_followup`。局部比较和理由随 observation 保留；后续如何处理仍由 Memory Review、Fusion、Evidence Review 决定。旧 Memory 的该字段继续可读，检索兼容字段缺省。旧/新归因可在同一 Memory 链上提交、读取、幂等恢复，Gate 与保留 Skill 的原子提交逻辑不变。

新 `campaign_config()` 默认 `attribution_protocol='pair'`；新 CLI 默认 pair：

```bash
# 只做新 campaign 预检，不调用模型
python scripts/run_v19_v4.py --generation-protocol local --attribution-protocol pair --pilot
```

旧版可显式选择 `--attribution-protocol legacy`。原实验脚本若直接导入 `attribution_v19.run_attribution`，仍执行旧版，不会暗中切换。当前 Pilot 的源码/协议绑定未迁移；不能直接拿旧 resume 脚本当成新版调用。

已有经过验证的 ledger、backend、Replay 可按下面调用新版（不会重新 rollout）：

```python
from src.skill_evolution.attribution_pairs_v19 import run_attribution

batch = run_attribution(
    ledger, backend=backend, parent_dir=parent_dir,
    replay_dir=candidate_replay_dir, history=history,
    artifact_dir=new_attribution_dir, max_workers=2,
)
```

当前 Pilot 后续切换时，应先记录源码/协议迁移、验证原账本及双侧 Replay 摘要，使用新的 Attribution 目录。无需重跑 Diagnosis、Editor 或 Replay；三次旧超时尝试保留。本次实现没有启动真实模型或 Monitor/Gate。

## 输入统计与验证范围

两轮现有完整 learner input 的只读统计见 `artifacts/v19_pair_attribution_profile_001/`。第一轮 36 对输入最大 24,287 token；第二轮 36 对最大 20,904；均未超预算。第二轮同口径旧版单次约 31.5 万（仅 user 正文约 28 万），新版单次约 1.21–2.09 万；逐 pair 重复公共上下文使整轮累计输入约 54.2 万，不能声称总 token 成本下降。

工程验证覆盖：完整双侧证据与私有数据隔离、引用角色和状态校验、联合归因不拆功劳、持平/冲突维度/UNKNOWN、一次修复、预算与截断、超时隔离和显式恢复、Memory 新旧混合链与两轮调度。构造测试只验证机制，真实语义质量、实际用量和延迟仍需新 Pilot 检验。

## 汇总 v19.3：行为关联与结果分离

逐 pair 模型协议仍为 attribution_pairs_v19.2；ATTRIBUTED / UNATTRIBUTED
输出契约不变。新确定性汇总为 attribution_batch_v19.3，不生成 effect。
associated_pair_outcome_counts 仅记录关联 pair 的成功/合规变化，不能作为
edit 的有益、有害、混合或无效果结论。不同 edit 集合的统计可能重叠，不可相加为贡献。

unattributed_context 保留相同 pair 的 UNATTRIBUTED 观察、解释及原始引用；
edit_ids 仍为空，不转为 edit 归因。旧 relation 以 legacy_relation 保存作溯源，
不能将 SUPPORT 理解为有效性支持。行为相同或结果不变不证明无作用。
旧 v19.2 汇总仍按旧算法恢复与校验；新算法不覆盖历史文件。

Memory 输入 issue_memory_v19.2 对旧历史作事实投影，去掉效果标签，保留原
attribution_id 用于追溯归档。原 Memory 持久化内容不变。Memory Review 四状态
判断具体行为观察或适用条件；reason 需说明具体支持/反驳什么，不判断 edit 好坏。
Issue Fusion / Evidence Review 继续沿用现有输出契约，局部证据包加载相关未归因
观察的原始证据。旧 issue_memory_v19.1 输入按原方式恢复，不能混用检查点。

离线重新汇总（不提交 Memory、不启动实验）：

```bash
python scripts/reaggregate_v19_attribution.py --source OLD_ATTRIBUTION --output NEW_ATTRIBUTION
```

新目录保存旧调用审计、事实汇总、完成校验及 semantics-migration.json。
已有输出拒绝覆盖。正式运行已提交的 Memory 与代码绑定不能原地改摘要后 resume；
需另行显式迁移运行绑定和 Memory 消费协议。Gate、Replay 和原始逐 pair 响应保持不变。
