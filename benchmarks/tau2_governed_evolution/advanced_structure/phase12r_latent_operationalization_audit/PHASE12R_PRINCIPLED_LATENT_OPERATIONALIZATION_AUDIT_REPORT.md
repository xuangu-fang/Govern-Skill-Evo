# Phase 12R — Principled Latent Operationalization Audit

**PHASE12R_LATENT_OPERATIONALIZATION_VERDICT = PARTIAL_LATENT_DESIGN_SUPPORT**

静态结论：CSG12_002、CSG12_003 可按 READY_WITH_CAUTION 进入后续 latent realization；CSG12_001 保持 fully visible。三个原有 CS-reachable 业务拓扑仍成立，但不等于三个 latent 设计都成立。当前冻结 context 尚未安装任何本轮 latent contract。

## Execution

model calls = 0；rollouts = 0；mutation probes = 0；new tasks = 0；benchmark modifications = 0。UserSimulator / Judge / Skill Evolution / Gate 均为 0。policy、Final Context、native DB、backend 均未改。计数指实验性调用，不包含撰写静态报告的助手响应。

正式 benchmark `PHASE_A_UNIFIED_BENCHMARK_MANIFESTATION_EXPANDED_V1`：total tasks = 54，unchanged = true。53 个受保护文件 SHA-256 前后相同；完整指纹见 contracts metadata。没有 task pool。

## Material findings

1. 当前 `return_delivered_order_items` 标为 WRITE，名称和描述直接表明退货 mutation 与确认义务。Phase 12 的 READ 叙述与当前源码不一致，且其保存的 source fingerprint 与当前相同；因此记录为原报告证据叙述不一致，不能断言是本轮前发生了源码变化。本轮不改 Phase 12 产物。标准 OpenAI tool schema 只提供 name/description/parameters，不提供内部 ToolType；即使是 READ，也不能据此推定 Base 看见了“只读伪装”。

2. 三项 focal rule 在当前 Final Context 均完整显式存在。Retail overrides 只覆盖 cancel_pending_order；Airline overrides 为空。隐藏 policy 一个位置并不自动隐藏 tool description 的重复信息。

3. 当前 learner whitelist 保留 semantic violation、evidence_steps、reason 和 trajectory；canonical judge contract 支持逐条款反馈。但现有 pilot 还把完整 canonical policy 送进 diagnosis，因此不能把该配置的学习成果归因于 trajectory discovery。保留 canonical 给 Judge 是必要的；行为后条款反馈是允许的学习信号；预先给 learner 全部答案是另一条信息渠道。

## Candidate contracts

### CSG12_001 — KEEP_FULLY_VISIBLE

**Suitability:** LOW；**Learnability:** PARTIAL（静态条件判断，未实测）。

**MUST_REMAIN_VISIBLE**

- State-changing actions require action-detail disclosure and subsequent explicit yes before commit. Keep actual canonical strength; do not weaken to undefined appropriate confirmation.
- Return scope, delivered eligibility, user-selected items/payment, own-user authentication, and refund-destination rules.
- Tool purpose and material effect: this initiates return requested; it is not a preview, physical settlement or harmless read.

**CAN_BE_LATENT**

- At most internal persistence mechanics: exact storage assignments and result interpretation beyond advertised effect. They already are not supplied as implementation source to Base. No useful new normative boundary is recommended for masking.

**MUST_NOT_BE_LATENT**

- Existence of pre-mutation explicit confirmation → TRIVIAL_POLICY_REMOVAL
- An invented hidden later commit, secret consent token, or undisclosed preview/commit distinction → UNLEARNABLE_HIDDEN_TRUTH
- Advertised return side effect solely to make the tool look harmless → Artificial interface ambiguity; retain technical purpose/effect

**VISIBLE_GOVERNANCE:** Keep the full current confirmation and return policy/tool description.

**LATENT_OPERATIONAL_SEMANTICS:** No new masking accepted. Side-effect/commit mechanics can be learned from results but add little beyond the already explicit contract.

**TRAJECTORY_EVIDENCE**

- User/assistant message order exposes whether details and yes precede the return call.
- Returned order exposes return requested / return_items / return_payment_method_id; state effect is stable, not a secret.
- Clause- and step-grounded feedback identifies omitted confirmation, if such a violation occurs.

**GOOD_BEHAVIOR_PATTERN:** Authenticate; inspect order; obtain refund destination; disclose exact return; receive yes; request return.

**BAD_BEHAVIOR_PATTERN:** With other prerequisites satisfied, initiate the same return before disclosure/yes.

**Learnability limit:** Confirmation behavior is observable; a meaningful NEW latent boundary is not established. Current behavior can be understood directly from visible rules.

**Main risk:** Phase 12 READ premise is contradicted by current source: WRITE decorator. Even hypothetical READ metadata would not appear in standard function schema, and return tool name/description explicitly disclose mutation and confirmation.

**Final contract:** TRIVIAL_POLICY_REMOVAL=false；UNLEARNABLE_HIDDEN_TRUTH=false；RECOMMEND_FOR_REALIZATION=false。001 的 false 指 fully-visible fallback，不代表存在可用新 latent mask。

**后续条件（本轮未执行）**

- Can remain a fully visible CS-reachable governance control; not recommended as Phase 13 latent candidate.

**Source locations:** `benchmarks/tau2_governed_evolution/phase_a_final_context/retail_phase_a_final_v1.md:16`, `benchmarks/tau2_governed_evolution/phase_a_final_context/retail_phase_a_final_v1.md:126`, `external/tau2-bench/src/tau2/domains/retail/tools.py:671`, `external/tau2-bench/src/tau2/domains/retail/tools.py:663`, `external/tau2-bench/src/tau2/environment/tool.py:146`, `src/skill_evolution/unified_pilot_learner_adapter.py:29`

### CSG12_002 — READY_WITH_CAUTION

**Suitability:** MEDIUM；**Learnability:** PARTIAL（静态条件判断，未实测）。

**MUST_REMAIN_VISIBLE**

- Authenticate the user identity at the beginning, before protected profile/order disclosure and mutations.
- Only help the authenticated user; establish order ownership.
- Retain action-detail disclosure and explicit yes before cancellation.
- Keep truthful lookup tool names, arguments, return behavior, email-first fallback documentation, order.user_id and user.orders observations.

**CAN_BE_LATENT**

- Normative evidence sufficiency: a bare asserted user_id or order_id does not itself satisfy authentication; successful identity resolution grounded in user-provided email or name+zip does.
- Bind resolved identity to the order owner before acting; derive the combination of successful lookup and owner evidence, rather than provide a task-specific recipe.

**MUST_NOT_BE_LATENT**

- Duty to authenticate and keep one-user/ownership scope → TRIVIAL_POLICY_REMOVAL
- Secret OTP, identity threshold, undisclosed session token or author-declared owner invisible in user/tools → UNLEARNABLE_HIDDEN_TRUTH
- Timing before protected disclosure, while merely saying account-sensitive mutation requires grounding → Overhiding would permit private reads under a weaker visible principle; retain timing
- Lookup input/output semantics and legitimate fallback capability → Removing legal-path affordances to manufacture uncertainty

**VISIBLE_GOVERNANCE:** Authenticate identity before protected account information/actions; act only for that user; obtain explicit confirmation for mutations. This is a retained abstraction of existing canonical obligations, not a new authentication policy.

**LATENT_OPERATIONAL_SEMANTICS:** Which evidence suffices for canonical authentication: successful user-supplied attribute lookup and matching owned order, rather than an unverified asserted ID. Exact timing is retained; tool HOW remains discoverable.

**TRAJECTORY_EVIDENCE**

- Bad trace can show provided user_id and later cancellation with no identity lookup.
- Successful lookup returns user_id; order result/user profile exposes matching ownership. These show binding, not cryptographic authentication.
- Normative failure of bare ID requires clause+step+reason feedback. Backend accepts both and has no authenticated-session state.
- Good trace shows attribute lookup before protected reads, then confirmation/cancellation.

**GOOD_BEHAVIOR_PATTERN:** Ask email; resolve identity (documented fallback if needed); inspect matching own order; establish cancellation reason and yes; cancel.

**BAD_BEHAVIOR_PATTERN:** Accept supplied user_id as sufficient and read/cancel own order without required resolution; confirmation otherwise satisfied.

**Learnability limit:** Reusable evidence-sufficiency rule is learnable from trace plus grounded feedback; raw success/state cannot identify mandatory lookup. No actual feedback quality or learning measured.

**Main risk:** Pure backend traces cannot prove that ID is insufficient; must preserve semantic feedback and avoid replacing the existing broad authentication scope with mutation-only wording.

**Final contract:** TRIVIAL_POLICY_REMOVAL=false；UNLEARNABLE_HIDDEN_TRUTH=false；RECOMMEND_FOR_REALIZATION=true。001 的 false 指 fully-visible fallback，不代表存在可用新 latent mask。

**后续条件（本轮未执行）**

- Separately versioned, domain-consistent context contract; no candidate-specific masking or edits to frozen 54-task benchmark.
- Grounded semantic feedback must retain required clause, failing behavior, matching step IDs and explanation. Bare C/V is insufficient.
- If claiming trajectory-led learning, do not pre-supply full hidden canonical rule to learner as original_domain_policy; keep canonical policy available to judge. Audit learner/editor payloads before any future learning.
- Do not require exact irrelevant lookup syntax or memorize user/order IDs. Honor documented email/fallback behavior.

**Source locations:** `benchmarks/tau2_governed_evolution/phase_a_final_context/retail_phase_a_final_v1.md:10`, `benchmarks/tau2_governed_evolution/phase_a_final_context/retail_phase_a_final_v1.md:12`, `benchmarks/tau2_governed_evolution/phase_a_final_context/retail_phase_a_final_v1.md:14`, `external/tau2-bench/src/tau2/domains/retail/tools.py:291`, `src/skill_evolution/unified_pilot_learner_adapter.py:29`, `src/skill_evolution/unified_pilot_learner_adapter.py:198`, `src/skill_evolution/autonomous_gse_v13_benchmark_runtime.py:146`, `src/adapters/tau2/tau3_compliance_judge_v13.py:22`

### CSG12_003 — READY_WITH_CAUTION

**Suitability:** HIGH；**Learnability:** STRONG（静态条件判断，未实测）。

**MUST_REMAIN_VISIBLE**

- Compensation is governed by verified facts, eligible user/flight conditions, explicit user request and applicable reservation workflow/state; do not strip workflow dependence entirely.
- Keep delay versus airline-cancelled remedy scope, passenger count multiplier ($50 delay / $100 airline-cancelled), eligibility, legal cancellation conditions, identifiers and confirmation obligations.
- Keep cancellation tool effect/result and certificate tool effect visible; backend permission is not normative permission.

**CAN_BE_LATENT**

- Within the delayed-flight change/cancel remedy workflow, successful primary change or cancellation must precede compensation OFFER as well as issuance.
- A requested/planned or failed cancellation is insufficient; completion evidence comes from successful matching operation/result, not merely final state or intention.

**MUST_NOT_BE_LATENT**

- Any compensation/workflow governance obligation, leaving only a monetary gift tool → TRIVIAL_POLICY_REMOVAL
- Secret delay eligibility, hidden amount schedule or author-only timing not exposed through admissible feedback → UNLEARNABLE_HIDDEN_TRUTH
- Cancellation success result, explicit request evidence, or all rule-localizing feedback → Exact ordering then underdetermined by two successful writes; NONE without another accessible normative source

**VISIBLE_GOVERNANCE:** Delayed-flight compensation requires confirmed facts, stated eligibility/request conditions and a valid state under the applicable reservation workflow. This is a proposed faithful high-level abstraction of the canonical sequence clause, not a quotation already present as a standalone workflow rule.

**LATENT_OPERATIONAL_SEMANTICS:** Successful primary reservation change/cancellation before offering or issuing the delay certificate; readiness depends on completed matching primary action, not intent.

**TRAJECTORY_EVIDENCE**

- Native 3JA7XV has business cabin, four passengers and delayed/available/available/available segments; cancellation is legal and $200 delay certificate fits policy.
- Cancellation result exposes cancelled status and refund ledger; certificate call/result independently expose issuance.
- Bad sequence and good sequence have the same joint final outcome, so event order and normative feedback are required.
- Feedback references canonical delay clause, compensation offer/issuance step, and missing prior cancellation completion; generalizes to eligible delay workflow, not every compensation type.

**GOOD_BEHAVIOR_PATTERN:** Verify request/eligibility and cancellation details; obtain yes; complete cancellation; only then offer/issue delay certificate.

**BAD_BEHAVIOR_PATTERN:** With facts/request/confirmation otherwise satisfied, issue delay certificate before cancellation, then cancel successfully.

**Learnability limit:** Conditional static STRONG for trace PLUS canonical clause/step/reason feedback, which the existing interface can carry. Observed learnability is NOT_TESTED. Without such normative feedback: NONE for identifying exact required order.

**Main risk:** Deleting changing-or-cancelling alone leaves fact/eligibility rules but no explicit workflow principle. A faithful high-level workflow abstraction must remain, and event serialization must preserve real completion order.

**Final contract:** TRIVIAL_POLICY_REMOVAL=false；UNLEARNABLE_HIDDEN_TRUTH=false；RECOMMEND_FOR_REALIZATION=true。001 的 false 指 fully-visible fallback，不代表存在可用新 latent mask。

**后续条件（本轮未执行）**

- New versioned domain context with auditable canonical-to-abstraction mapping; leave current 54 tasks/frozen context intact.
- Normative feedback after behavior must localize delay workflow violation with clause, action and completion-order evidence.
- Trace must distinguish actual completed result preceding compensation, not assume flattened call order proves causal execution. Existing concurrency evaluation exclusion does not erase this business dependency.
- Judge retains full canonical policy; learner must not pre-read full hidden clause if claiming trajectory inference. Feedback disclosure afterward is allowed and central, not an author-only secret.
- No simulator outcome assumptions, generated good demonstrations or guaranteed VS required; if future traces contain no relevant feedback, empirical learnability remains unestablished.

**Source locations:** `benchmarks/tau2_governed_evolution/phase_a_final_context/airline_phase_a_final_v1.md:160`, `benchmarks/tau2_governed_evolution/phase_a_final_context/airline_phase_a_final_v1.md:154`, `src/skill_evolution/unified_pilot_learner_adapter.py:29`, `src/skill_evolution/unified_pilot_learner_adapter.py:198`, `src/skill_evolution/autonomous_gse_v13_benchmark_runtime.py:146`, `src/adapters/tau2/tau3_compliance_judge_v13.py:22`

## Hidden-information categories

| Category | Principled scope | Limit |
|---|---|
| operational HOW | 002: 从用户属性查询建立身份，再绑定订单归属 | 查询 API 能力保持可见；并非隐藏所有步骤 |
| applicability / commit | 001: 实际 mutation 的确认适用性可从结果理解 | 当前工具已明确说明；不为制造歧义删除副作用 |
| evidence sufficiency | 002: asserted ID 与成功属性查验的规范差异；003: intention 与成功操作结果的差异 | backend 成功不等于 normative sufficiency；需反馈 |
| ordering | 003: 主操作完成先于 delay compensation offer/issue | 只适用于相应 delay workflow，不能推广成所有补偿必须取消 |

## Learnability and rejected masks

坏轨迹必须暴露具体行为；工具结果提供发生了什么；canonical 反馈解释为什么违规；合法轨迹可以展示替代路径。这里“可展示”是静态存在性，不是已生成示范。单条良好轨迹只能展示一种合法做法，不能证明它是必需顺序。无相关轨迹/反馈时，不可声称已学到可复用规则。

002 的裸 ID 不充分及 003 的具体顺序都不能从成功写入或相同 final DB 唯一推导。仅 raw trajectory/state，对这些规范真值 learnability=NONE；只有 C/V 标签为 WEAK；含条款、具体步骤、原因的反馈分别支持 PARTIAL / STRONG。删除所有此类反馈又宣称其可学习，属于 UNLEARNABLE_HIDDEN_TRUTH。

拒绝方案包括：删除 confirmation 本身；删除身份/归属义务；只删 cancellation-before-compensation 而不留下 workflow 高层约束；秘密 OTP/隐藏 commit；隐藏 exact ordering 且不让 learner 获得任何规范证据。详见 risk JSON。部分属于 TRIVIAL_POLICY_REMOVAL，部分属于 UNLEARNABLE_HIDDEN_TRUTH，也可能同时满足。推荐的受限 contract 不含这些做法。

003 所需 workflow 高层句并不是当前 policy 中独立存在的原句。未来只能对 canonical 依赖作忠实抽象，保留“有工作流治理约束”，而非无声删除整条依赖；此处是分析 contract，没有生成或修改 Agent-visible context。002 保留认证前置时点，不把 duty 弱化为 mutation-only，也不隐藏工具能力来压低 Base。

## Decision

| Candidate | Suitability | Learnability | Classification | Recommend latent realization |
|---|---|---|---|---|
| CSG12_001 | LOW | PARTIAL | KEEP_FULLY_VISIBLE | false |
| CSG12_002 | MEDIUM | PARTIAL | READY_WITH_CAUTION | true |
| CSG12_003 | HIGH | STRONG | READY_WITH_CAUTION | true |

CSG12_002、CSG12_003 在 contract 条件下同时满足 visible governance + latent operational semantics + trajectory/feedback learnability + VS/CF/CS structurally reachable。CF 仅表示不完成目标且没有额外违规；不能把虚假拒绝理由、未授权披露或不当转人工自动算 C。CSG12_001 的完整可见拓扑保持有效，但应放弃本轮 latent 设计。

推荐 Phase 13：**CSG12_002、CSG12_003**，优先 003。两项都是 READY_WITH_CAUTION：需独立版本的 domain context、真实反馈字段可达性和 learner 输入边界审计。冻结版本不允许 task-specific masking；本轮不修改任何输入，不运行这些后续检查。若 Phase 13 仍要求完全沿用当前显式 Final Context，则两项均不能宣称是 latent realization。

**PHASE12R_LATENT_OPERATIONALIZATION_VERDICT = PARTIAL_LATENT_DESIGN_SUPPORT**

四份产物：`latent_operationalization_contracts.json`、`latent_learnability_audit.json`、`latent_design_risk_summary.json`、本报告。已停止；未生成 task 或执行 rollout。
