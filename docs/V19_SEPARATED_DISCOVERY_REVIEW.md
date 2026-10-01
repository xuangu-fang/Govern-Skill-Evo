# v19 职责拆分：第 1 步数据契约与独立阶段

日期：2026-09-24。

本步完成 Current Diagnosis 与 Memory Review 的输入构造、严格响应 schema、本地校验、不可变 DTO、稳定来源 ID、独立 Prompt 和工程测试。没有实现 Reconciliation、模型调用/修复与阶段检查点、多轮新调度或新的真实 Pilot；这些在后两步接入。v18 和已完成 Pilot 保持不变。

## 阶段边界

```text
当前 Parent Evolution + 当前 Parent Skill + 当前分组
  → Current Diagnosis
  → Current Findings ──────────────────────────────┐
                                                 │
历史 Memory + Current Findings + 全部当前证据索引  │
  → Memory Review → Historical Reviews ────────────┤
                                                 ↓
                                  后续 Reconciliation（未实现）
```

新接口不调用 Memory Router，也不将历史 edit 分配给当前 Diagnosis 组。旧的 `memory_diagnosis_v19.py`、路由和生成入口暂时保留，用于现有产物验证和旧流程兼容。`run_v19_v4.py` 尚未切换到新流程，不应将运行旧入口当作本次拆分的真实验证。第 3 步统一接入时再切换；不提前拼接到缺少 Reconciliation 的旧 Compiler 路径。

## 1. Current Diagnosis

入口：`current_diagnosis_v19.build_current_diagnosis_inputs`。

显式传入 run_id、round_id、parent_skill、Evolution backend、完成的 Parent 目录和已绑定分组。不传入 Memory store。复用现有 learner-safe 当前轨迹投影、全量分组校验和 v18 policy/rule 引用索引；不复用旧 Diagnosis 的 gap 输出。

输出每组一个 `CurrentDiagnosisInput`，仅包含当前 Skill、当前组轨迹、可见 policy/tools、Level-0 监督和组织性分组提示。事件采用 run/round 作用域的 CURRENT 引用，附带原始轨迹身份、Parent Skill 身份及来源轮次。私有 Monitor 和 evaluator 内容不进入接口。

模型响应 schema：

```json
{
  "schema_version": "current_findings_response_v19.1",
  "summary": "对当前组的分析总结，也可解释没有充分 finding 的原因",
  "findings": [{
    "kind": "OBSERVED_PROBLEM",
    "statement": "可见条件、行为及观察结果",
    "applicability": "适用范围",
    "dimensions": ["SUCCESS"],
    "evidence_refs": ["CURRENT/.../E0001"],
    "supervision_refs": [],
    "policy_refs": [],
    "related_rule_refs": [],
    "uncertainty": ["可能的采样波动或其他解释"]
  }]
}
```

- kind：`OBSERVED_PROBLEM / EFFECTIVE_BEHAVIOR / COUNTEREVIDENCE / UNCERTAINTY`。不要求凑齐四种，不强迫成功观察生成 gap，允许 findings=[]。
- dimensions：SUCCESS / COMPLIANCE，至少一项。
- 每条 finding 必须有当前事件引用；policy、supervision、rule 分字段校验。监督引用必须属于所引轨迹，policy 必须属于所引事件的上下文。
- 不接受 Evidence Status、历史关系、Review Decision、Skill Gap、编辑操作或 Skill 正文等额外字段。
- 校验后由运行时生成 `CF/<hash(input_ref + finding)>`，保存 input_ref、batch、group_id 和精确原响应。相同输入及相同 finding 得到相同 ID，改变内容或来源则改变 ID。不让模型自行命名。
- DTO 用冻结 dataclass 保存规范 JSON；读取 payload 返回独立副本。Memory Review 构造前逐条从原响应重新校验，篡改、旧轮混入、重复组、漏组或漏响应都拒绝。

`Current Finding` 记录当前发现，不决定是否修改。没有历史关系的 finding 将来可直接进入 Reconciliation，不必构造 Evidence Status，也不默认等于 MISSING。

## 2. Memory Review

入口：`historical_review_v19.build_memory_review_input`。

输入为已校验的完整 Current Findings 批次及请求，以及已提交的 Memory。校验运行身份、当前 Parent、Evolution manifest、Memory head；不能审阅已提交为历史的“当前轮”。本步检索全部已提交历史，不使用按当前组路由或静默丢弃历史的预算裁剪。

可见内容包括：

- 全部 Current Findings（不可改写）；
- 当前原始事件索引、轨迹身份、上下文和监督，涵盖未出现在 Findings 中的事件；
- 完整历史 Memory，包括原 paired replay、支持与反证、归因不确定性、来源及当前绑定；
- 明确的 historical_objects 审阅清单。

`resolve_current_evidence(request, refs)` 按精确引用返回只读的当前原始事件和对应上下文。当前 Prompt 以全量事件索引提供这些材料，不假装已经实现动态工具检索。调用前使用既有 token 预算检查，超限停止，不截断原始证据；大规模分批执行和恢复属于后续调度工作。

### 历史对象

本步直接适配已有归因存储：一个对象是 `(edit_id, attribution_id)`，稳定 ID 为 `HO/<hash(identity)>`。它携带该归因的 interpretation、applicability、effect、uncertainty、alternative_explanations 和当前规则绑定。

同一 edit 的两个历史判断有两个对象；共同归因保留 joint_edit_ids 和同一 attribution_id，不能被当成独立证据。Review 必须覆盖全部对象，但不得因此将同一原始 pair/event 重复计为多份支持。没有添加自由生成的新历史 issue 或新的归因；将来的 issue 演进由后续持久化协议处理。

已有 interpretation 可能包含复合判断；MIXED 应解释分别支持和反对的部分。结构校验不能证明自然语言判断已经原子化或语义正确。

### 响应

```json
{
  "schema_version": "historical_review_response_v19.1",
  "reviews": [{
    "historical_object_id": "HO/...",
    "evidence_status": "NOT_COVERED",
    "supporting_current_refs": [],
    "contradicting_current_refs": [],
    "context_current_refs": [],
    "current_finding_refs": [],
    "historical_evidence_refs": [],
    "coverage_reason": "NO_RELEVANT_OBSERVATION",
    "reason": "本轮未观察到足够相关的行为",
    "uncertainty": ["不能由未覆盖推断历史问题已解决"]
  }]
}
```

| Evidence Status | 结构要求 |
|---|---|
| SUPPORTED | 有 supporting_current_refs，无 contradicting_current_refs |
| CONTRADICTED | 有 contradicting_current_refs，无 supporting_current_refs |
| MIXED | 两类引用都有，解释支持与反证各自的含义 |
| NOT_COVERED | 两类引用都没有，必须说明覆盖不足原因 |

NOT_COVERED 的 coverage_reason：

- NO_RELEVANT_OBSERVATION：没有相关当前事件引用。
- INSUFFICIENT_EVIDENCE：有 context_current_refs，说明为什么尚不能形成支持或反驳。

其他三种状态的 coverage_reason 为 ASSESSED。

支持、反证、上下文引用只接受当前原始事件，不接受历史事件、policy、rule、监督或 finding ID。current_finding_refs 可为空；如有，每条链接必须与该 review 共享至少一条当前事件。历史引用独立保存，必须属于对象对应的完整原始 pairs；无 observations 的历史判断保留其原轮完整回放供核查。

每个历史对象恰好一个 review，未知、重复或遗漏对象都拒绝。校验后分配 `HR/<hash(input_ref + review)>`，保存精确原响应与输入绑定。Memory Review 不接受 PROPOSE/KEEP/DEFER、mutation kind、操作或改写后的 findings。

空 Memory 的 historical_objects 和 reviews 均为空；已有 Current Findings 不受影响。Current Findings 为空时，历史审阅仍可查看全部当前事件，不能把没有 finding 当作没有新证据。

## 下一步的兼容接口

Reconciliation 将独立接收 CurrentFindings 与 HistoricalReviews，来源至少一侧非空，并逐项做 PROPOSE/KEEP/DEFER。只有 PROPOSE 产生 v18 风格的 MISSING/NEEDS_REVISION/SHOULD_REMOVE；Compiler 再映射为 ADD/REPLACE/DELETE。本步不提前确定这两层的响应 schema，也不自动把 evidence status 映射到编辑动作。

## 验证边界

本地校验保证 schema、引用类型/范围、来源绑定和历史覆盖，不保证因果归因、语义蕴含或模型真正重视当前证据。工程 fixture 的支持/反驳状态是预设输入，仅验证机制；尚无新流程真实模型效果结论。

测试：`python -m pytest tests/skill_evolution/test_separated_review_v19.py -q`。

本步最终验证：新增专项测试 27 项；`tests/skill_evolution/*v19.py` 全量 **293 项通过**。语法编译和 diff 空白检查通过；v18 冻结 manifest 的 **992 个文件全部哈希一致**。未运行真实模型或 Pilot。
