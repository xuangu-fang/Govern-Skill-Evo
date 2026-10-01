# v19 第 6 步：Memory 影响下一轮 Diagnosis 和 Skill 生成

本步接通独立的 v19 生成阶段：读取当前 Parent 训练经验与已提交 Memory，重新 Diagnosis，经过 Compiler/Editor 生成完整 Candidate，并将历史来源写入新 edit 账本。本阶段不执行 Candidate 回放、Monitor、记忆提交或多轮 campaign。

实现文件：

- `src/skill_evolution/memory_diagnosis_v19.py`：输入拼接、历史复查验收、gap 到跨轮关系的映射。
- `src/skill_evolution/memory_generation_prompt_v19.py`：v19 Diagnosis 与 Editor Prompt。
- `src/skill_evolution/memory_generation_v19.py`：阶段运行、模型响应检查点和恢复。
- `src/skill_evolution/edit_tracking_v19.py`：构建/恢复账本时再次校验 v19 复查来源和跨轮关系。

v18 文件不变。v19 只读复用已有的 Diagnosis 语义/引用校验、确定性 Compiler、Editor 打包和文本应用函数；没有替换 v18 调度器或全局 monkeypatch。

## Memory 如何影响生成

1. 从一个已提交 Memory 快照取得当前 Parent 和历史链；核对当前 Parent Evolution 的完整检查点及 manifest。
2. 校验现有 Grouper 输出的全量分组。保留每个当前组（包括成功组），再按 v19.6 的唯一审阅归属分配历史 Memory；无法唯一匹配的历史 edit 进入历史专用审阅组。
3. 把历史两侧观察加入可引用证据目录，同时保留历史轮次、Parent/Candidate 角色、当时部署的 Skill 和原始 pair/evidence 引用。当前观察使用 `CURRENT/<run-round-digest>/...` 命名空间。
4. Diagnosis 对选中的每条历史 edit 显式给出 USE 或 DEFER。USE 必须关联本轮新 gap，引用历史配对两侧实际事件，并结合当前 Parent 重新授权。
5. Compiler 依据这些新 gap 生成完整计划；Editor 只获得本 edit unit 的新 gap、分析、证据和被重新授权的历史来源。
6. 确定性应用产生 Candidate 后，将新 edit 对历史 edit 的 REVISES/RETRIES/REVERTS 意图及证据写入账本。

历史归因、建议、Gate 决策和当前文本 binding 都不会变成 policy 或轨迹事实。Gate 只解释部署历史，不作为效果标签。引用旧观察不表示旧问题在本轮再次出现；Prompt 要求比较当前适用条件与反证。当前标签全为成功不能自动跳过历史复查，但旧问题也不强制产生新 gap。

## Diagnosis 输出与重新授权

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

### 跨轮关系的结构条件

| relation | 本轮重新授权条件 |
|---|---|
| REVISES | 历史 ADD/REPLACE 内容存在可靠当前规则绑定或结构后代；新 NEEDS_REVISION 指向这些当前目标 |
| RETRIES：ADD/REPLACE | 提议文本当前为 ABSENT；新 MISSING 授权添加。历史 REPLACE 也可由 NEEDS_REVISION 重新修改与原目标原文匹配的当前规则 |
| RETRIES：DELETE | 被删目标仍有当前绑定，新 SHOULD_REMOVE 独立授权再次删除 |
| REVERTS：DELETE | 被删内容当前为 ABSENT，新 MISSING 授权恢复指导 |
| REVERTS：ADD/REPLACE | 新 NEEDS_REVISION 或 SHOULD_REMOVE 重新授权修改可靠绑定的当前内容 |

这些条件校验身份、目标和来源关联，不证明自然语言意义上确实修好了旧问题。无法可靠绑定时应 DEFER，不能猜坐标。SHOULD_REMOVE 继续要求独立的整块删除理由；部分内容有害但还有有效内容时应考虑 NEEDS_REVISION。程序仍只做结构/引用验收，不宣称自动验证语义上的删除优于修订。

## Editor 与账本来源

Editor 不接收整个历史记忆仓库。每个 ADD/REPLACE unit 只增加该 unit 的 `memory_lineage`：新 gap 引用、对应复查记录、相关历史 edit 原文，以及明确的“历史意图不是额外授权”标记。可见证据目录保留来源轮次、角色、Skill 和历史/当前标识。

旧 Skill 文本只是背景，不自动复制成新规则；Editor 仍必须逐 unit 完成确定性计划，不能新增操作、借用其他 unit 或修改未授权内容。纯 DELETE 不调用 Editor 模型，由程序应用。

新账本的 `source_gap_refs` 保留本轮重新诊断来源；`related_history` 保留历史 edit ID、关系和精确证据 ID。模型包装响应及摘要保存在 Diagnosis provenance 中。v19 账本构建和恢复会重新验证包装响应、gap 与历史来源映射；删除或篡改这些复查来源不能绕过校验。内层 Compiler DTO 与验证 envelope 复用已有格式，这是兼容实现细节，不代表运行了 v18 生成流程。

## 调用接口

```python
from src.skill_evolution.memory_generation_v19 import (
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

## 审计与恢复

输出根目录保存 `input.json`、逐组 `diagnosis-NNN/`、可选 `editor/`、`generation.json` 和最终 `validation.json`。每次模型响应单独绑定请求与响应摘要；根 manifest 绑定全部 JSON 产物。

- 默认新目录；`resume=True` 显式恢复。
- 已完成响应不重复调用，恢复会重验 Diagnosis、历史复查、计划、Editor 应用及最终账本。
- 尚未开始的组可继续运行；已发出但没有完整响应检查点的调用不得自动重试，需显式新尝试目录。
- 格式错误或拒答的响应不自动修复，也不会在恢复时换一个响应采样。
- `load_memory_generation` 只读重建结果，不调用模型、不修改产物；输入、Prompt 或已记录结果变化会拒绝。
- 生成期间 Memory 头变化会使结果不能发布。阶段结束后仍需下一阶段核对预期 head；本步不锁住整个 Memory 跨模型调用，也不负责提交。
- 当前轮已提交后，不可用当前 head 重新运行这个旧轮次的生成。历史账本由第 2/5 步档案恢复；此生成加载接口面向仍待执行/提交的当前轮。

默认模型参数沿用前序 v19 的 deepseek-v4-pro、temperature=0、high reasoning、24,000 输出 token、300 秒超时、零自动重试。测试通过注入 diagnosis_transport/editor_transport 完成，没有真实模型请求。

## 验证与未完成范围

新增 **41 项专项测试**，连同前序 v19 及相关 v18/v4 回归合计 **271 项通过**。重点覆盖：

- 已接受 edit 的修订、未晋升 ADD/REPLACE/DELETE 的重新授权重试、恢复已删指导。
- 当前全成功仍复查历史、显式 DEFER/NO_UPDATE、空 Memory 正常生成。
- 历史/当前引用隔离、缺失复查拒绝、旧目标拒绝、Editor unit 范围。
- 多组同目标合并仍保留全部来源、完整响应恢复、篡改与版本漂移拒绝。
- 新账本在新进程恢复，并与既有回放、归因和记忆提交接口兼容；这些是构造数据集成测试，不是正式 campaign。

测试证明接口和证据链可执行，不能证明模型会作出正确的历史解释或 Memory 提升了 Skill 效果。真实语义质量及多轮收益仍需第 7 步独立调度与实验评估。本步没有运行真实模型、Monitor 或真实多轮实验。

## v19.5：引用闭合与一次契约修复

Diagnosis 每个 gap 的 evidence_refs 必须属于声明来源分析引用集合的并集；每个声明维度还必须与 gap 共享至少一条轨迹事件（仅共享政策不够）。v19 在保留 v18 原始校验的基础上增强 LINKAGE 报错，输出 gap_index、source_dimensions、missing_from_declared_analyses 和 analyses_without_shared_event。正文提及事实不替代结构化引用。真实 Pilot 第六组漏列的两条用户确认事件已作为回归 fixture 保存。

新批次绑定 `memory_generation_input_v19.2` / `v19.5-single-contract-repair`，每组最多一次修复：

1. 完整原始响应经过所有 Diagnosis 与 Memory review 校验。
2. 本地输出契约拒绝时，保存 `diagnosis-NNN/contract_rejection.json`；将完整原输入、原始响应字符串和精确错误反馈给模型。
3. 修复调用保存在 `diagnosis-NNN-repair-001/`，包含 request、response、response_complete；请求经过同样的输入预算检查。
4. 对修复响应重新执行所有校验，只有合法结果可进入 Compiler。仍不合法时保存该修复的 contract_rejection 并停止；程序不补引用、不删证据、不改结论。

无效 JSON、Diagnosis 和 Memory 输出契约错误允许使用这一次修复机会；网络异常、不完整响应、拒答、截断、检查点损坏和预算超限不触发自动修复或 transport 重试。resume 复用已保存响应并重新校验；已完成且失败的修复会再次报错，绝不会产生第三次请求。修复调用结果不确定时停止等待显式处理。

修复成功只证明契约合法，不证明结论正确、因果归因有效或 Gate 将接受。原始与修复记录均保留在 generation 清单中。旧批次缺少新协议绑定时拒绝普通 resume，不原地套用新规则；本次实现未改写或重跑旧 Pilot 产物。


## v19.6：历史 Memory 的唯一审阅归属

实现位于 `memory_allocation_v19.py`。本次更改仅涉及 v19，不修改已完成 Pilot、原始持久化证据和 v18。

1. 全局检索仍选择完整轮次及关系闭包；分配是其后的输入视图，不修改存储。
2. 将联合归因、显式跨轮关联和结构化修订关联的 edits 合为不可拆分单元。
3. 使用归因所引原始事件中的工具调用与可见 policy/tools 内容指纹，匹配当前组的工具行为。工具按其出现在当前组中的频率取倒数权重；只有唯一正分最高组获得该单元。任务别名、Gate、成功率、effect 标签、历史建议文字均不参与打分。这只是审阅调度，不是相关性或因果结论。
4. 无匹配、并列匹配或没有可用工具证据的单元进入额外的历史专用组；该组没有 CURRENT_PARENT 轨迹，须重新判断当前适用性，可以 DEFER。
5. 当前组只收到自己负责的 edits、对应归因（保留反证、不确定性和替代解释）、来源证据、当前绑定和完整的相关 Parent–Candidate pairs。若该组负责源轮全部 edits，或归因没有 observations，保留整轮回放供复查。共享 pair 保留同一身份，不成为多份独立支持。原轮摘要显式标记为整轮范围。
6. 分配清单、精确分数、理由和检索内容摘要写入请求 provenance；输入包含自己的归属及清单摘要。模型调用前检查完整覆盖和唯一归属。当前组仍可基于自己的新轨迹提出不带历史关联的新 gap。
7. 协议标识为 `v19.6-single-owner-memory` / `memory-diagnosis-v19.6`。恢复时按新输入精确绑定；不能将旧分配协议的部分响应混入新批次。旧账本的证据校验保持可读，不自动重写历史结果。

限制：工具/公开上下文匹配无法识别所有语义相关性，宽泛工具可能造成并列并增加历史专用审阅。完整证据超出预算仍显式停止，不自动截断。此机制保证审阅分配和来源可审计，不保证生成质量提升；需要新的真实 Pilot 观察效果。
