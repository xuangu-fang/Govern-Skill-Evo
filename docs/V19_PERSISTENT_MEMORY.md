# v19 第 5 步：持续记忆的保存、更新和检索

本步实现不可变轮次归档、原子提交链和可重建的学习侧 MemoryContext。没有接入第 6 步 Diagnosis，也没有启动第 7 步 campaign 或真实模型实验。v18 源码、Prompt、冻结配置和历史实验保持不变。

实现：

- `src/skill_evolution/memory_store_v19.py`：初始化、完整证据归档、提交与恢复校验。
- `src/skill_evolution/memory_retrieval_v19.py`：当前规则绑定、历史复查、关键词匹配与完整证据检索。
- `tests/skill_evolution/test_memory_v19.py`：40 项专项验收。

## 保存与更新

每轮保存完整 edit 账本、Parent/Candidate 配对回放、归因响应及验证产物，并接收可信 Monitor 调用方提供的完成回执。ACCEPT 和 RETAIN 保存相同范围的训练证据；只有 retained Skill 的选择不同。

`RoundMemoryRecord` 按第 1 步契约记录前一记忆引用、两侧 Skill 引用、全部 edit/pair/attribution 引用、整包决策和保留 Skill 引用，并增加私有归档清单的摘要绑定。记忆更新采用追加新轮次，不覆盖旧归因或将 RETAIN 自动改写为有害。当前规则对应关系在读取时根据全部已提交 edit 历史重建。

目录结构：

```text
memory/
  genesis.json
  head.json
  rounds/<record-sha256>/
    record.json
    audit.json
    backend.json
    gate.json
    ledger_input.json
    ledger.json
    parent/...
    candidate/...
    attribution/...
  pending/<attempt-id>/...
```

`rounds` 保存独立副本，不依赖原实验目录继续存在。私有归档包含检查点所需数据库、执行配置、simulator prompt 和原始评分，**不能整体提供给学习器**。学习侧只消费 `retrieve_memory` 的结果。

提交过程：校验旧记忆头和 Parent 连续性 → 验证账本、完整回放及归因 → 复制并重验归档 → 固化不可变轮次 → 一次原子替换 `head.json`。head 同时保存记忆头、revision、精确保留 Skill 原文及摘要，下一轮必须从该 head 获取 Skill，不能独立读取某个暂存 Candidate 文件作为当前 Skill。写入使用进程锁、同目录原子替换和 fsync。

`expected_head_ref` 提供比较并提交检查，拒绝基于过期头部的新轮次。同一 round/evidence/decision 重试返回原引用，不重复追加；即使后面已有新轮次，也不会回退头部。相同 round 的不同证据或决策被拒绝。

## 接口

```python
from src.skill_evolution.memory_store_v19 import (
    initialize_memory, load_memory, commit_round_memory,
)
from src.skill_evolution.memory_retrieval_v19 import retrieve_memory

snapshot = initialize_memory(
    store_dir=memory_dir, run_id=run_id, initial_skill=initial_skill,
)
# 下一轮构造账本时使用 snapshot.history。
# 当前执行 Skill 从同一快照的 head 读取。
current_skill = snapshot.head['retained_skill']

memory_ref = commit_round_memory(
    ledger,
    store_dir=memory_dir,
    expected_head_ref=snapshot.head['memory_ref'],
    backend=backend,
    parent_dir=parent_dir,
    replay_dir=candidate_replay_dir,
    attribution_dir=attribution_dir,
    gate_result=gate_receipt,
)

snapshot = load_memory(memory_dir)
context = retrieve_memory(
    store_dir=memory_dir,
    current_parent=snapshot.head['retained_skill'],
    query='当前可见的问题或行为描述',
    edit_ids=(),
    max_rounds=None,
    max_chars=None,
)
# context.payload 是后续 Diagnosis 可消费的学习侧投影。
```

Gate 回执字段严格限定为：

```json
{
  "status": "COMPLETE",
  "decision": "ACCEPT",
  "run_id": "run-id",
  "round_id": "round-id",
  "parent_skill_sha256": "exact-parent-digest",
  "candidate_skill_sha256": "exact-candidate-digest"
}
```

不接受 Monitor 分数、轨迹、标签或解释。上述回执不是模型输出；可信 Monitor 调用方负责提供真实完成结果。本模块检查回执的结构及 Candidate 绑定，不能单凭字典证明 Monitor 实际执行过。第 7 步调度器将负责连接这个信任边界。

初始化可幂等调用，但不同 run 或初始 Skill 被拒绝。`load_memory` 返回私有 `MemorySnapshot`：包含当前 head、完整轮次资料和可用于下一轮账本的 `history`；不要直接将其序列化给模型。

## 恢复与历史验收

- head 发布前中断：暂存目录或完整但未挂到 head 的轮次不进入消费链；重试可验证并复用同一完整轮次归档。
- head 发布后响应中断：相同提交重试幂等，不重复追加、不重复晋升 Skill。
- 部分拷贝：保留暂存文件用于审计；不自动把它们当作已提交记忆，也不自动清理失败记录。
- 加载时：从一个 head 快照沿引用链重建，校验所有归档摘要，重建账本、重新投影训练证据、重验归因引用与结果方向，并验证决策后的 Skill 连续性。
- 历史加载使用归档的 benchmark manifest 和 Prompt/config，不要求当前线上模型配置或源码与历史版本一致，不调用模型。它验证历史产物一致性，不重新跑历史环境，也不把旧归因升级成因果事实。
- 同一运行内追加新轮次仍要求 Evolution manifest 一致，避免任务别名或运行配置漂移。旧轮次归因由当前确定性结构校验器重验；未来若契约不兼容，应显式迁移，不能忽略错误。
- 原实验目录删除后，读取已提交历史完全独立。再次调用提交接口仍要求提供可验证的阶段输入；仅需恢复当前状态时使用 `load_memory`。

摘要与检查点用于一致性审计，不是针对能够同时改写所有文件者的数字签名。NO_UPDATE / UNABLE 不伪造记忆轮次；保留已有 head，阶段停止记录由后续调度器负责。

## 检索与跨轮修正入口

检索只读已提交轮次，并验证调用者的 `current_parent` 与当前 head 原文一致。MemoryContext 包含当前 Parent 引用及原文、当前规则、记忆头、选中的历史完整证据单元及来源/选择清单。

每个历史单元包含：来源轮次与 Gate 事实、精确 edit、来源可见证据、两侧历史 Skill、完整 ReplayPair、全部归因，以及重新计算的当前 binding。EXACT/PARTIAL/ABSENT/UNRESOLVED 继续使用第 2 步定义；DELETE 的 binding 指被删目标是否出现，不指空 after_text。历史决策、当前文本存在性和效果假设分开表达。

默认不设预算时返回全部历史。设置预算时采用确定性优先顺序：

1. 显式指定的 edit。
2. 当前仍有 EXACT/PARTIAL/UNRESOLVED 绑定且包含 HARMFUL/MIXED 的记录。
3. RETAIN 包中的 BENEFICIAL/MIXED 方向。
4. 历史未决效果或仍建议复查的记录。
5. 当前可见 query 的词项匹配，再按历史顺序补充。

query 由调用者保证只含学习侧可见内容。首版采用英文词项和中文相邻双字匹配，不引入 embedding 或模型；它只是检索排序，不证明语义等价。无需当前失败组或 query，负面和未决历史也会进入复查入口。

最小选择单元是完整轮次，保留所有 edit、配对和归因，避免只给收益摘要或遗漏同 edit 另一范围的反证。显式 REVISES/RETRIES/REVERTS 关系，以及已接受 edit 的结构祖先变化，会把相关轮次合并为不可拆分的证据单元。因此跨轮 followup 和 basis 引用有完整来源，不把新 edit 已生成或 Gate ACCEPT 当作旧问题已解决。

`max_rounds` 限制实际纳入的轮数；`max_chars` 计数整个规范 JSON 的字符数，不是 token 估算。预算不足时不截断轨迹/解释，而是跳过整个证据单元，并在 selection 中列出全部候选单元的来源、选择原因及排除原因。没有任何完整单元可容纳或基础上下文/选择清单超预算时，抛出 `MemoryBudgetExceeded`。显式请求的 edit 未能纳入时同样拒绝返回不完整替代结果。

此方案偏重证据完整性，历史链较长时可能需要更大输入预算。首版不实现细粒度语义检索、效果数值聚合、自动判定问题解决或记忆淘汰。

## 验证结果与范围

新增 **40 项专项测试**；连同前序 v19 及相关 v18/v4 回归，合计 **230 项通过**。覆盖：

- ACCEPT/RETAIN 的完整保存和同头 Skill 绑定、幂等/冲突/过期提交。
- 拷贝中断、head 发布前后中断、进程锁、新进程加载及脱离原实验目录读取。
- 完成回执边界、未完成归因拒绝提交、归档/头部篡改拒绝。
- 完整反证、查询匹配、预算选择和显式排除。
- 已接受 edit 后续部分删除、未晋升 edit 重试、跨轮关系闭包和空 Skill DELETE。

全部使用构造轨迹与注入模型 transport，真实模型调用为 0。本步完成保存、追加更新和检索基础，不验证真实记忆能否提升后续 Skill 质量；Diagnosis 消费与多轮实验仍分别属于第 6、7 步。
