# 经验生成、存储与消费

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v19 局部核验闭环（第三步）](#v19-local-generation)
- [v19 第 5 步：持续记忆的保存、更新和检索](#v19-persistent-memory)
- [v19 第 6 步：Memory 影响下一轮 Diagnosis 和 Skill 生成](#v19-memory-generation)
- [共享 Memory 消费边界 v19.1](#v19-memory-consumption)

<a id="v19-local-generation"></a>

## v19 局部核验闭环（第三步）

> 目录整理提示（2026-09-27）：下文旧 Pilot 的命令保留为历史说明，不代表搬迁后可直接 resume。当前产物入口见 [v19 实验索引](../../../experiments/methods/v19/README.md)，原始路径见 [迁移映射](../../../experiments/methods/canonical-paths.json)。

> 当前新运行已切换为 [单次 Evidence Review v19.3](EVIDENCE_REVIEW.md#v19-one-pass-evidence-review)，下文补充上下文协议保留作为历史说明。

`local_generation_v19.1` 接通 Current Diagnosis → Memory Review → Issue Fusion → 逐提案 Evidence Review → 确定性编译 → Bounded Editor → Candidate Replay → Attribution → 私有 Monitor/Gate → Memory 提交。旧 `legacy` / `separated` 协议与既有实验目录保留；不迁移旧 Reconciliation 检查点。

### 编译与来源边界

每个 PROPOSE 必须有独立、完整且重新通过校验的 Evidence Review。任何未完成提案阻止本轮编译，但其他提案的检查点继续独立保存。NO_EDIT 不进入计划；全部 NO_EDIT 返回 NO_UPDATE，无伪造 Candidate 或 Memory 提交。

VERIFIED gap 的 MISSING / NEEDS_REVISION / SHOULD_REMOVE 对应 ADD / REPLACE / DELETE。v19 适配器移植 v18 的确定性编译和局部文本应用规则，复用其严格 Editor 输出解析/Schema；**不伪造 v18 Diagnosis 的分析段，不修改冻结 v18，不直接把局部结果塞进旧 Diagnosis Compiler 接口**。

同操作、重叠目标按连通分量合并并保留全部来源；REPLACE/DELETE 重叠拒绝整批计划。ADD 不做语义去重。Editor 只获取已核验来源，未指定的 Parent 文本逐字保留；DELETE 由程序执行。

账本沿用既有 edit ID、效果归因和原子 Memory 提交机制。新审计保存完整 Current Findings、历史审阅、Fusion、每个 Review 的补充请求和结果；纯函数重建输入并验证全部来源。`source_gap_refs.diagnosis_ref` 是为账本兼容保留的字段名，新协议中其值是实际 `ISSUE/...` 提案 ID，`gap_index=0`，不是伪造 Diagnosis。Memory 保存 issues 与 evidence_reviews，并以 REVISES/RETRIES/REVERTS 表达可验证的结构关系；不把此关系宣称为因果证明。

### 复用上游，停在 Editor 前

```bash
python scripts/runs/v19/run_v19_local_review.py run \
  --upstream artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --output artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_001
```

这个入口只复用已完成 Current Diagnosis / Memory Review，重新运行 Fusion 与局部 Review，完成确定性编译后停在 `BEFORE_EDITOR`。不会调用 Editor、Replay、Monitor 或提交 Memory。源产物原封不动，新调用与上游摘要写入独立目录。程序失败时查看 `status.json` 与 `review-summary.json`；失败不等于 NO_EDIT。

恢复相同代码和输入：

```bash
python scripts/runs/v19/run_v19_local_review.py resume \
  --upstream artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --output artifacts/methods/v19/archive/legacy/v19_v4_local_review_once_001
```

resume 复用已完成调用；无完整响应的调用不会自动重发。对明确无响应的单提案，可使用已有 `run_evidence_review(..., resume=True, retry_incomplete=True)`，归档该次尝试后再请求；完成但契约失败不能这样重试。Fusion 仍保持一次契约修复上限，不自动重发不确定网络调用。

### 完整闭环入口（本次不启动）

```bash
python scripts/runs/v19/run_v19_v4.py --generation-protocol local --pilot --run \
  --output artifacts/methods/v19/pilot/v19_v4_local_pilot_001
python scripts/runs/v19/run_v19_v4.py --generation-protocol local --pilot --run --resume \
  --output artifacts/methods/v19/pilot/v19_v4_local_pilot_001
```

正式实验去掉 `--pilot` 并使用新的输出目录。未指定 `--run` 时仅 preflight。旧命令的默认协议仍保留 separated，新协议必须显式选择 local，避免无意改变既有运行行为。

### 验证范围

工程测试覆盖两轮 ACCEPT/RETAIN、历史关联、MIXED/NOT_COVERED、源篡改拒绝、NO_EDIT、未完成核验禁止编译、Editor 前停止、恢复不重复模型调用与提交、Monitor 隔离，以及确定性操作映射/合并/冲突。工程构造用于验证机制，不能作为真实效果证据。真实单次运行仅用于观察新 Fusion/Review 行为，未进入 Editor，因此不产生 Skill 效果结论。

输入 v19.2 的预算分析、无损目录、输出截断分类及显式旧产物复用，见 [Evidence Review 预算修正](EVIDENCE_REVIEW.md#v19-review-budget-fix)。

#### 统一一次契约修复与扁平 Editor（2026-09-28）

v19 活跃路径共用 `contract_repair_v19.py` 请求构造：原输入一份、完整原响应一份、
错误类型／阶段／简短错误消息。错误消息最多 2000 字符，完整错误仍在原 rejection
记录；输入与响应不截断。沿用已声明的无损引用别名。最多一次模型修复并重新执行全部
校验；传输失败和 length 不属于契约修复，不自动补引用或修改结论。各阶段预算检查
仍生效。Pair Attribution 旧修复记录按旧请求精确重建，供归档校验。

新生成审计记录 `editor_policy=flat_task_rules_v19.1` 和 `candidate_layout_v19.2`。
Editor 不生成分类标题，也不将已知实验 provenance 标识写入规则；规则保留实际工具名、
参数和业务编号。校验拒绝新增 Markdown 标题及已知内部标识，走同一个一次修复路径。
内部编号从结构化来源提取，不按 G05/C002 等具体 Pilot 编号硬编码。

确定性排版删除继承 Parent 的二级及以下 ATX 标题行，保留规则正文、顶级标题和代码块。
删除作为 layout policy 和 source/candidate digest 记录，可由 ledger 重建；规则 provenance
不变，禁止排版删除模型新增的规则文本。旧审计无新 policy 时沿用旧应用行为。
没有自动迁移旧运行或重写历史 Skill。纯 NO_UPDATE 不生成新的排版候选。

<a id="v19-persistent-memory"></a>

## v19 第 5 步：持续记忆的保存、更新和检索

本步实现不可变轮次归档、原子提交链和可重建的学习侧 MemoryContext。没有接入第 6 步 Diagnosis，也没有启动第 7 步 campaign 或真实模型实验。v18 源码、Prompt、冻结配置和历史实验保持不变。

实现：

- `src/skill_evolution/v19/memory_store_v19.py`：初始化、完整证据归档、提交与恢复校验。
- `src/skill_evolution/v19/memory_retrieval_v19.py`：当前规则绑定、历史复查、关键词匹配与完整证据检索。
- `tests/skill_evolution/v19/test_memory_v19.py`：40 项专项验收。

### 保存与更新

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

### 接口

```python
from src.skill_evolution.v19.memory_store_v19 import (
    initialize_memory, load_memory, commit_round_memory,
)
from src.skill_evolution.v19.memory_retrieval_v19 import retrieve_memory

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

### 恢复与历史验收

- head 发布前中断：暂存目录或完整但未挂到 head 的轮次不进入消费链；重试可验证并复用同一完整轮次归档。
- head 发布后响应中断：相同提交重试幂等，不重复追加、不重复晋升 Skill。
- 部分拷贝：保留暂存文件用于审计；不自动把它们当作已提交记忆，也不自动清理失败记录。
- 加载时：从一个 head 快照沿引用链重建，校验所有归档摘要，重建账本、重新投影训练证据、重验归因引用与结果方向，并验证决策后的 Skill 连续性。
- 历史加载使用归档的 benchmark manifest 和 Prompt/config，不要求当前线上模型配置或源码与历史版本一致，不调用模型。它验证历史产物一致性，不重新跑历史环境，也不把旧归因升级成因果事实。
- 同一运行内追加新轮次仍要求 Evolution manifest 一致，避免任务别名或运行配置漂移。旧轮次归因由当前确定性结构校验器重验；未来若契约不兼容，应显式迁移，不能忽略错误。
- 原实验目录删除后，读取已提交历史完全独立。再次调用提交接口仍要求提供可验证的阶段输入；仅需恢复当前状态时使用 `load_memory`。

摘要与检查点用于一致性审计，不是针对能够同时改写所有文件者的数字签名。NO_UPDATE / UNABLE 不伪造记忆轮次；保留已有 head，阶段停止记录由后续调度器负责。

### 检索与跨轮修正入口

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

### 验证结果与范围

新增 **40 项专项测试**；连同前序 v19 及相关 v18/v4 回归，合计 **230 项通过**。覆盖：

- ACCEPT/RETAIN 的完整保存和同头 Skill 绑定、幂等/冲突/过期提交。
- 拷贝中断、head 发布前后中断、进程锁、新进程加载及脱离原实验目录读取。
- 完成回执边界、未完成归因拒绝提交、归档/头部篡改拒绝。
- 完整反证、查询匹配、预算选择和显式排除。
- 已接受 edit 后续部分删除、未晋升 edit 重试、跨轮关系闭包和空 Skill DELETE。

全部使用构造轨迹与注入模型 transport，真实模型调用为 0。本步完成保存、追加更新和检索基础，不验证真实记忆能否提升后续 Skill 质量；Diagnosis 消费与多轮实验仍分别属于第 6、7 步。

<a id="v19-memory-generation"></a>

## v19 第 6 步：Memory 影响下一轮 Diagnosis 和 Skill 生成

本步接通独立的 v19 生成阶段：读取当前 Parent 训练经验与已提交 Memory，重新 Diagnosis，经过 Compiler/Editor 生成完整 Candidate，并将历史来源写入新 edit 账本。本阶段不执行 Candidate 回放、Monitor、记忆提交或多轮 campaign。

实现文件：

- `src/skill_evolution/v19/memory_diagnosis_v19.py`：输入拼接、历史复查验收、gap 到跨轮关系的映射。
- `src/skill_evolution/v19/memory_generation_prompt_v19.py`：v19 Diagnosis 与 Editor Prompt。
- `src/skill_evolution/v19/memory_generation_v19.py`：阶段运行、模型响应检查点和恢复。
- `src/skill_evolution/v19/edit_tracking_v19.py`：构建/恢复账本时再次校验 v19 复查来源和跨轮关系。

v18 文件不变。v19 只读复用已有的 Diagnosis 语义/引用校验、确定性 Compiler、Editor 打包和文本应用函数；没有替换 v18 调度器或全局 monkeypatch。

### Memory 如何影响生成

1. 从一个已提交 Memory 快照取得当前 Parent 和历史链；核对当前 Parent Evolution 的完整检查点及 manifest。
2. 校验现有 Grouper 输出的全量分组。保留每个当前组（包括成功组），再按 v19.6 的唯一审阅归属分配历史 Memory；无法唯一匹配的历史 edit 进入历史专用审阅组。
3. 把历史两侧观察加入可引用证据目录，同时保留历史轮次、Parent/Candidate 角色、当时部署的 Skill 和原始 pair/evidence 引用。当前观察使用 `CURRENT/<run-round-digest>/...` 命名空间。
4. Diagnosis 对选中的每条历史 edit 显式给出 USE 或 DEFER。USE 必须关联本轮新 gap，引用历史配对两侧实际事件，并结合当前 Parent 重新授权。
5. Compiler 依据这些新 gap 生成完整计划；Editor 只获得本 edit unit 的新 gap、分析、证据和被重新授权的历史来源。
6. 确定性应用产生 Candidate 后，将新 edit 对历史 edit 的 REVISES/RETRIES/REVERTS 意图及证据写入账本。

历史归因、建议、Gate 决策和当前文本 binding 都不会变成 policy 或轨迹事实。Gate 只解释部署历史，不作为效果标签。引用旧观察不表示旧问题在本轮再次出现；Prompt 要求比较当前适用条件与反证。当前标签全为成功不能自动跳过历史复查，但旧问题也不强制产生新 gap。

### Diagnosis 输出与重新授权

v19 在原 Diagnosis 结构外增加审计包装，不改变内部 MISSING / NEEDS_REVISION / SHOULD_REMOVE 语义：

```json
{
  "schema_version": "memory_diagnosis_response_v19.1",
  "diagnosis": {
    "success_analysis": {},
    "compliance_analysis": {},
    "skill_addressability": {},
    "parent_skill_gaps": []
  },
  "memory_review": [
    {
      "edit_id": "EDIT/...",
      "decision": "DEFER",
      "relation": "NONE",
      "gap_indices": [],
      "evidence_refs": [],
      "reason": "说明当前适用性、证据或可执行纠偏为何不足"
    }
  ]
}
```

上例只展示包装形状；内部 Diagnosis 的 analysis 等对象仍须满足原完整字段契约。

- 每条被检索的历史 edit 必须且只能复查一次；即使最终没有 gap 也不能省略。
- DEFER 要求 relation=NONE、gap_indices=[]，并给出原因。DEFER 不意味着问题已解决。
- USE 指向有效的本轮 gap 索引；必须引用该 edit 来源轮次至少一个 pair 的两侧事件，且这些引用全部出现在每个所关联 gap 和其来源分析中。
- 历史 attribution ID、Memory ID、Gate 决策、标签引用不能冒充轨迹引用；只有当前 Parent 规则目录能授予目标坐标。
- 任何引用历史观察的 gap 都必须有显式 USE 记录；纯当前观察支持的新 gap 可以不关联历史 edit。
- 所有组均完成并通过验证后才能编译。某组失败不能被省略后继续生成部分 Candidate。

#### 跨轮关系的结构条件

| relation | 本轮重新授权条件 |
|---|---|
| REVISES | 历史 ADD/REPLACE 内容存在可靠当前规则绑定或结构后代；新 NEEDS_REVISION 指向这些当前目标 |
| RETRIES：ADD/REPLACE | 提议文本当前为 ABSENT；新 MISSING 授权添加。历史 REPLACE 也可由 NEEDS_REVISION 重新修改与原目标原文匹配的当前规则 |
| RETRIES：DELETE | 被删目标仍有当前绑定，新 SHOULD_REMOVE 独立授权再次删除 |
| REVERTS：DELETE | 被删内容当前为 ABSENT，新 MISSING 授权恢复指导 |
| REVERTS：ADD/REPLACE | 新 NEEDS_REVISION 或 SHOULD_REMOVE 重新授权修改可靠绑定的当前内容 |

这些条件校验身份、目标和来源关联，不证明自然语言意义上确实修好了旧问题。无法可靠绑定时应 DEFER，不能猜坐标。SHOULD_REMOVE 继续要求独立的整块删除理由；部分内容有害但还有有效内容时应考虑 NEEDS_REVISION。程序仍只做结构/引用验收，不宣称自动验证语义上的删除优于修订。

### Editor 与账本来源

Editor 不接收整个历史记忆仓库。每个 ADD/REPLACE unit 只增加该 unit 的 `memory_lineage`：新 gap 引用、对应复查记录、相关历史 edit 原文，以及明确的“历史意图不是额外授权”标记。可见证据目录保留来源轮次、角色、Skill 和历史/当前标识。

旧 Skill 文本只是背景，不自动复制成新规则；Editor 仍必须逐 unit 完成确定性计划，不能新增操作、借用其他 unit 或修改未授权内容。纯 DELETE 不调用 Editor 模型，由程序应用。

新账本的 `source_gap_refs` 保留本轮重新诊断来源；`related_history` 保留历史 edit ID、关系和精确证据 ID。模型包装响应及摘要保存在 Diagnosis provenance 中。v19 账本构建和恢复会重新验证包装响应、gap 与历史来源映射；删除或篡改这些复查来源不能绕过校验。内层 Compiler DTO 与验证 envelope 复用已有格式，这是兼容实现细节，不代表运行了 v18 生成流程。

### 调用接口

```python
from src.skill_evolution.v19.memory_generation_v19 import (
    run_memory_generation, load_memory_generation,
)

result = run_memory_generation(
    store_dir=memory_dir,
    backend=backend,
    parent_dir=current_parent_evolution_dir,
    round_id=round_id,
    grouping_result=bound_grouping_result,
    artifact_dir=generation_dir,
    query='',
    edit_ids=(),
    max_rounds=None,
    max_memory_chars=None,
    max_input_chars=None,
)
```

`grouping_result` 是已有 Grouper 的已绑定结果，须完整覆盖当前 Parent Evolution；本步没有替换分组算法。后端 manifest 必须与当前 Memory 运行一致。第一轮空 Memory 仍支持普通当前经验生成。

返回 `MemoryGenerationResult`：

- `status=EDITED` 或 `APPLIED_DETERMINISTIC`：有完整 `candidate_skill` 与 v19 `ledger`。
- `status=NO_UPDATE`：所有选中历史已显式复查，但计划没有 edit；无 Candidate/账本。
- `status=UNABLE`：Editor 明确不能完成计划；无 Candidate/账本。
- 模型失败、截断、拒答、无效引用、缺失复查、预算不足或编译冲突：阶段失败，不转成 NO_UPDATE，不提交或晋升。

`build_memory_diagnosis_inputs(...)` 可单独构造输入而不调用模型。检索参数沿用第 5 步：完整轮次及关系闭包、保留反证、显式排除范围。入选历史 edit 在整个批次中恰好由一个组审阅；无匹配或并列匹配的历史问题仍进入历史专用审阅组，不会静默丢弃。`max_memory_chars` 限制 MemoryContext，`max_input_chars` 限制拼接后的规范 JSON 字符数，均不是 token 估算，不包含系统 Prompt/schema/output 预留量。超预算停止，不自动截断或偷偷丢掉历史证据。

### 审计与恢复

输出根目录保存 `input.json`、逐组 `diagnosis-NNN/`、可选 `editor/`、`generation.json` 和最终 `validation.json`。每次模型响应单独绑定请求与响应摘要；根 manifest 绑定全部 JSON 产物。

- 默认新目录；`resume=True` 显式恢复。
- 已完成响应不重复调用，恢复会重验 Diagnosis、历史复查、计划、Editor 应用及最终账本。
- 尚未开始的组可继续运行；已发出但没有完整响应检查点的调用不得自动重试，需显式新尝试目录。
- 格式错误或拒答的响应不自动修复，也不会在恢复时换一个响应采样。
- `load_memory_generation` 只读重建结果，不调用模型、不修改产物；输入、Prompt 或已记录结果变化会拒绝。
- 生成期间 Memory 头变化会使结果不能发布。阶段结束后仍需下一阶段核对预期 head；本步不锁住整个 Memory 跨模型调用，也不负责提交。
- 当前轮已提交后，不可用当前 head 重新运行这个旧轮次的生成。历史账本由第 2/5 步档案恢复；此生成加载接口面向仍待执行/提交的当前轮。

默认模型参数沿用前序 v19 的 deepseek-v4-pro、temperature=0、high reasoning、24,000 输出 token、300 秒超时、零自动重试。测试通过注入 diagnosis_transport/editor_transport 完成，没有真实模型请求。

### 验证与未完成范围

新增 **41 项专项测试**，连同前序 v19 及相关 v18/v4 回归合计 **271 项通过**。重点覆盖：

- 已接受 edit 的修订、未晋升 ADD/REPLACE/DELETE 的重新授权重试、恢复已删指导。
- 当前全成功仍复查历史、显式 DEFER/NO_UPDATE、空 Memory 正常生成。
- 历史/当前引用隔离、缺失复查拒绝、旧目标拒绝、Editor unit 范围。
- 多组同目标合并仍保留全部来源、完整响应恢复、篡改与版本漂移拒绝。
- 新账本在新进程恢复，并与既有回放、归因和记忆提交接口兼容；这些是构造数据集成测试，不是正式 campaign。

测试证明接口和证据链可执行，不能证明模型会作出正确的历史解释或 Memory 提升了 Skill 效果。真实语义质量及多轮收益仍需第 7 步独立调度与实验评估。本步没有运行真实模型、Monitor 或真实多轮实验。

### v19.5：引用闭合与一次契约修复

Diagnosis 每个 gap 的 evidence_refs 必须属于声明来源分析引用集合的并集；每个声明维度还必须与 gap 共享至少一条轨迹事件（仅共享政策不够）。v19 在保留 v18 原始校验的基础上增强 LINKAGE 报错，输出 gap_index、source_dimensions、missing_from_declared_analyses 和 analyses_without_shared_event。正文提及事实不替代结构化引用。真实 Pilot 第六组漏列的两条用户确认事件已作为回归 fixture 保存。

新批次绑定 `memory_generation_input_v19.2` / `v19.5-single-contract-repair`，每组最多一次修复：

1. 完整原始响应经过所有 Diagnosis 与 Memory review 校验。
2. 本地输出契约拒绝时，保存 `diagnosis-NNN/contract_rejection.json`；将完整原输入、原始响应字符串和精确错误反馈给模型。
3. 修复调用保存在 `diagnosis-NNN-repair-001/`，包含 request、response、response_complete；请求经过同样的输入预算检查。
4. 对修复响应重新执行所有校验，只有合法结果可进入 Compiler。仍不合法时保存该修复的 contract_rejection 并停止；程序不补引用、不删证据、不改结论。

无效 JSON、Diagnosis 和 Memory 输出契约错误允许使用这一次修复机会；网络异常、不完整响应、拒答、截断、检查点损坏和预算超限不触发自动修复或 transport 重试。resume 复用已保存响应并重新校验；已完成且失败的修复会再次报错，绝不会产生第三次请求。修复调用结果不确定时停止等待显式处理。

修复成功只证明契约合法，不证明结论正确、因果归因有效或 Gate 将接受。原始与修复记录均保留在 generation 清单中。旧批次缺少新协议绑定时拒绝普通 resume，不原地套用新规则；本次实现未改写或重跑旧 Pilot 产物。


### v19.6：历史 Memory 的唯一审阅归属

实现位于 `memory_allocation_v19.py`。本次更改仅涉及 v19，不修改已完成 Pilot、原始持久化证据和 v18。

1. 全局检索仍选择完整轮次及关系闭包；分配是其后的输入视图，不修改存储。
2. 将联合归因、显式跨轮关联和结构化修订关联的 edits 合为不可拆分单元。
3. 使用归因所引原始事件中的工具调用与可见 policy/tools 内容指纹，匹配当前组的工具行为。工具按其出现在当前组中的频率取倒数权重；只有唯一正分最高组获得该单元。任务别名、Gate、成功率、effect 标签、历史建议文字均不参与打分。这只是审阅调度，不是相关性或因果结论。
4. 无匹配、并列匹配或没有可用工具证据的单元进入额外的历史专用组；该组没有 CURRENT_PARENT 轨迹，须重新判断当前适用性，可以 DEFER。
5. 当前组只收到自己负责的 edits、对应归因（保留反证、不确定性和替代解释）、来源证据、当前绑定和完整的相关 Parent–Candidate pairs。若该组负责源轮全部 edits，或归因没有 observations，保留整轮回放供复查。共享 pair 保留同一身份，不成为多份独立支持。原轮摘要显式标记为整轮范围。
6. 分配清单、精确分数、理由和检索内容摘要写入请求 provenance；输入包含自己的归属及清单摘要。模型调用前检查完整覆盖和唯一归属。当前组仍可基于自己的新轨迹提出不带历史关联的新 gap。
7. 协议标识为 `v19.6-single-owner-memory` / `memory-diagnosis-v19.6`。恢复时按新输入精确绑定；不能将旧分配协议的部分响应混入新批次。旧账本的证据校验保持可读，不自动重写历史结果。

限制：工具/公开上下文匹配无法识别所有语义相关性，宽泛工具可能造成并列并增加历史专用审阅。完整证据超出预算仍显式停止，不自动截断。此机制保证审阅分配和来源可审计，不保证生成质量提升；需要新的真实 Pilot 观察效果。

<a id="v19-memory-consumption"></a>

## 共享 Memory 消费边界 v19.1

Memory Review 与 Evidence Review 共用 `memory_consumption_v19.py`，不增加模型阶段。
档案保持完整；消费视图是派生对象，不覆盖已提交 Memory。

### 契约与状态

`state_view` 读取已有历史判断和 edit 状态，去除完全相同的重复记录；保留不同或
矛盾判断、Gate、联合归因、不确定性和未归因上下文。它不是新的 LLM 总结器，
不把不同 edit 或不同适用范围凭文本相似性合并，不以最新记录覆盖旧反证。
目前尚未实现语义上的“同一问题历轮摘要合并”。不同经验持续增加时，摘要可能
达到上限并停止；因此这是有界消费与安全停止，不是无限轮次自动推进的保证。

来源引用是溯源关系，不自动要求加载全文。两个消费者共用 10,000 个本地代理
summary token 上限；成本基于已有可逆表示测量。单条/总摘要无法容纳时明确失败，
不切字符串、不把未知结论转为 NO_EDIT。完整请求另受原有总预算约束。

### 原文选择

`select_originals` 使用完整 pair/trajectory 单元：保留已引用事件及其可识别调用/
结果。已知反证单元优先，其余按稳定来源顺序选择，历史原文上限 6,000 代理
 token。不将 outcome 正负当作 edit 因果效果，不切断单元以填满预算。

选择记录保存 source digest、加载引用、遗漏数量及遗漏引用摘要。完整来源保留
在 canonical case，可以离线重建全部未加载项，未加载列表不会随历史增长进入
 prompt。遗漏已知反证原文时，Evidence Review 校验禁止 VERIFIED。其他必要
证据不足仍由审阅返回 NO_EDIT；自动选择不保证语义覆盖所有适用条件。

Memory Review 使用摘要及来源索引，不读取历史原文；Evidence Review 使用同一
摘要边界并通过原文选择器加载局部证据。当前 Finding 证据不被历史预算裁剪。
旧 source_findings 正文不重复传入，来源仍保留在档案与引用中。

### 验证与恢复

增长测试覆盖 10,000 条重复记录、2/20/200 个历史证据单元、不同新判断超限、
超大反证、原始档案不变、未加载反证禁止 VERIFIED；相关测试合计 78 项通过。

离线实际数据报告：
- `artifacts/methods/v19/v19_shared_memory_review_001/profile.json`：7 个 edit Memory Review。
- `artifacts/methods/v19/v19_shared_memory_002.json`：8 个 Evidence Review。
- `artifacts/methods/v19/v19_shared_memory_migration_readiness.json`：原始 3 个完成结果复验与阻塞项。

当前 3 个完整 Evidence Review 输入仍超过 32,000，不能恢复。旧结果按原始输入
校验通过，但不得将它们称为按新协议重审的结果。尚未修改正式运行检查点或执行
迁移；后续迁移需显式记录协议混用的复用边界。全部检查离线执行，模型调用为零。

### 真实观察入口（2026-09-28）

Evidence Review 的 32,000 改为观察阈值，默认工程保护上限为 64,000，
不代表 API 硬上限。首次请求及唯一修复共用该检查，不增加 Budget Manager。
已有可逆引用、正文去重和共享消费边界保持不变，不针对具体议题裁剪。

`retry_v19_evidence_reviews.py` 在独立目录完整复制并校验原 local-reviews，
保存代码/来源摘要；复验并保留已完成结果，只请求从未发送的剩余议题。
使用 --execute 才发送请求，结束停在 Compiler/Editor 前。它不是正式 campaign
的 resume 替代品；新结果回接完整闭环需要后续明确迁移。

### 摘要观察阈值修正

10,000 summary token 仅作日志观察阈值，不再阻断；默认摘要工程保护上限
为 64,000，可通过现有 limit 参数配置。没有按本次 10,353 样本裁剪，也没有
新增 Budget Manager。完整请求仍受各阶段已有请求预算限制，因此这项修改
不等于自动放宽 Memory Review 完整请求的 28,800/32,000 检查。

本次没有迁移正式运行检查点或启动请求；源码绑定变化后不能直接原样 resume。

### 完整 Memory Review 请求预算简化

首次请求和唯一一次 repair 统一使用 64,000 本地估算 token 工程保护上限。
取消首次 28,800 限制及固定 3,200 修复预留。32,000 仅为观察阈值，
请求与 profile 记录是否超过，不因此停止，也不追加压缩/检索调用。
摘要仍按上节使用 10,000 观察阈值与 64,000 工程保护。
这些均不是模型/API 硬上限；原始证据、校验契约及最多一次 repair 不变。

第三轮离线复算见 artifacts/methods/v19/v19_round03_relaxed_memory_budget_001/profile.json。
本次没有更改正式实验检查点，没有启动模型。恢复前仍需显式迁移源码绑定。
