# Phase 12S — Global GSE Information Boundary & Oracle-Leakage Audit

**PHASE12S_INFORMATION_BOUNDARY_VERDICT = MAJOR_ORACLE_LEAKAGE_REDESIGN_REQUIRED**

当前实际 learner 数据边界：**NO**，不满足 experience privilege only。既有 ID 匿名化和 holdout 隔离有效，但没有隔离 hidden policy、额外工具真值、evaluator solution 和高带宽反馈。此结论来自源码与保存的最终模型输入，不是对模型使用这些信息的因果归因。

## Execution

model calls = 0；rollouts = 0；Judge calls = 0；benchmark modifications = 0；runtime modifications = 0。没有修复、task generation、Skill Evolution、历史重跑或 Phase 13。

正式 benchmark `PHASE_A_UNIFIED_BENCHMARK_MANIFESTATION_EXPANDED_V1`：54 tasks，unchanged = true。3407 个受保护 source/benchmark/native 文件哈希前后一致；历史结果保留。只生成本目录七份产物。

## Global contract

Oracle 可读完整 benchmark truth 用于评判。Base 只读部署可见 context、Skill、用户消息、正常工具及观察。Learner 遵守与 Base 相同的 latent-knowledge 边界，只增加历史经验、多轨迹和最多 LEVEL 2 的反馈。**Learner = experience privilege, not oracle privilege.**

- Any truth hidden from Base must also be hidden from every Learner component unless the run explicitly declares privileged mode.
- Learner advantage comes from accumulated experience, not hidden-answer access.
- ORACLE_ONLY fields must not enter Diagnosis, Compiler, Proposal or Editor directly.
- ORACLE_DERIVED fields require explicit semantic learner-safety review before transfer; aliases and paraphrase do not declassify them.
- Judge uses full truth internally; learner-facing supervision must remain at most LEVEL 2 relative to the focal hidden truth.
- Benchmark provenance, mechanism labels, protection rationale and expected answers must not become learner hints.

ORACLE_DERIVED 不是自动安全：匿名 ID、摘要、target_behavior 都可能保留完整答案。相反，真实执行后可见的工具错误和状态属于允许的经验，不因揭示 backend behavior 而被禁止。

## Confirmed routes

| ID | Type | Severity | Source → Destination | Finding |
|---|---|---|---|---|
| IBS001 | DIRECT_ORACLE_LEAKAGE | CRITICAL | canonical domain loader → Diagnosis | Full hidden canonical clauses; CONFIRMED_CURRENT |
| IBS002 | DIRECT_ORACLE_LEAKAGE | CRITICAL | AST authoritative tool-contract loader → Diagnosis | Unmasked cancellation gift-card balance effect; non-Base Raises such as payment-history multiplicity; CONFIRMED_CURRENT |
| IBS003 | DIRECT_ORACLE_LEAKAGE | CRITICAL | Success evaluator detailed results → Diagnosis | Expected tool names/arguments and NL assertions; CONFIRMED_CURRENT |
| IBS004 | DIRECT_ORACLE_LEAKAGE | HIGH | UserSimulator scenario metadata → Diagnosis | task_instructions and unknown_info beyond revealed user messages; CONFIRMED_CURRENT |
| IBS005 | SUPERVISION_LEAKAGE | CRITICAL | Canonical Judge → Diagnosis through process/compliance feedback | Exact policy_clause/requirement and potentially exact fix in reason; CONFIRMED_CURRENT |
| IBS006 | INDIRECT_ORACLE_LEAKAGE | HIGH | Oracle-exposed Diagnosis → _signal → Editor → prospective Skill | target_behavior decision_boundary/repair_operator/expected_behavior; provenance retained; CONFIRMED_CURRENT |
| IBS007 | INDIRECT_ORACLE_LEAKAGE | MEDIUM | Nested evaluator action IDs / construction metadata → Legacy Diagnosis attempt1 | lga01 in nested action.action_id; CONFIRMED_LEGACY_ALREADY_REPAIRED |

全部 7 条路径：DIRECT=4，INDIRECT=2，SUPERVISION=1；severity={'CRITICAL': 4, 'HIGH': 2, 'MEDIUM': 1}。当前未修复路径 6 条：DIRECT=4、INDIRECT=1、SUPERVISION=1；IBS007 为已修复的历史标签路径。按路径计数，不重复计算同一条款的多个拷贝。

## Actual serialized evidence

遍历 attempt_3_clean_adapter 保存的全部 34 份 request/model_input：34 份含完整 policy；33 份含 expected action records；18 份含 NL assertions；17 份含 clause feedback。这些是“包含字段的 request 数”，不等于 34 个任务都含相同 latent truth。

- T001：完整 Retail policy 恢复 item modification 后不能再修改的隐藏段落；反馈也引用该段；authoritative tool Raises 直接给出 payment history >1 限制。
- T003：Success action_checks 给出 FQ8APE 正确 Economy 更新的工具、航段及付款参数，即使该 rollout Success=false。
- T005：NL assertion 指定 Trip A 用 gift card、Trip B 用 certificate 的正确分配，不能用“只是 Success 反馈”解释其安全性。
- Editor 保存输入有 17 条 eligible signals；首条 target_behavior 明确要求先 payment/address、最后 item modification。没有证据表明 Editor 能独立重新获得 canonical policy，但间接答案路径已存在。

精确 JSON path、示例值及源码行号见 end_to_end_information_flow_audit.json。

## Component conclusions

**Diagnosis：YES。** 完整 canonical policy + unmasked/augmented tool contracts + evaluator expectations + full clause feedback 均能越过 Base 边界。task_context 还含未揭露的 UserSimulator 脚本。

**Compiler：有上游污染传递，没有发现独立 Oracle 查询。** compile_semantic_diagnosis 只从 semantic feasibility/evidence/coverage 决定 eligibility/operation。_signal 把 target_behavior/expected_behavior/repair_operator 原样复制到 Editor。schema-valid 与引用存在不证明 learner-safe。

**Provenance / repair_policy_ids：** Unified C/P/E 匿名化有用，不能去除其旁边语义答案。generic resolver 会恢复原 policy IDs；不能仅因字段存在就认定完整答案泄漏，需要看含义及可访问映射。

**Editor：间接获得答案。** 输入仅 Parent + eligible_diagnoses，不直接接收 full policy。其系统提示要求保留 mechanism-defining condition，使污染的 Diagnosis 很容易进入 Skill。verification_target 是 Editor 生成的输出；未发现它是另一路 Oracle 预先注入的答案。

**Selection / regression：未确认反向泄漏。** reviewed v14 路径冻结分析、禁止向 learner 反馈、拒绝 monitor/test 证据。没有发现 live protected_rule_ids 字段；Parent related_rule_ids 是正常 Skill 索引。不要把所有 metadata 一概判为泄漏。

## Supervision ceiling

当前 canonical Judge 输出并保留精确 policy_clause / policy_requirement、evidence_steps、reason，已观察到隐藏条款，因此为 **LEVEL 3**，超过新 contract 的 LEVEL 2。

LEVEL 0 binary；LEVEL 1 经审查的粗类别；LEVEL 2 实际轨迹中的问题步骤/观察关系；LEVEL 3 完整 hidden rule 或等价修复答案。判断必须相对于隐藏信息：对于只有两步的 ordering，指出哪个前置状态缺失也可能等价于答案，不能因句子非命令式就视作安全。必要时退回更低带宽并承认 learnability 不足。

**本轮收紧并取代 Phase 12R 的反馈假设。** 当时允许用完整条款反馈支持 STRONG learnability；新用户 contract 明确禁止此类 LEVEL 3，所以不得沿用该结论。

## Legacy classifications

| Primary classification | Family/setting rows |
|---|---:|
| CLEAN_EXPERIENCE_GROUNDED | 0 |
| DIRECT_ORACLE_LEAKAGE | 8 |
| INDIRECT_ORACLE_LEAKAGE | 4 |
| SUPERVISION_LEAKAGE | 0 |
| PRIVILEGED_LEARNER_SETTING | 1 |
| NOT_APPLICABLE | 1 |
| UNCERTAIN | 8 |

22 family/setting audit rows; overlapping families/settings, not task prevalence. Primary label counts; secondary leakage channels retained.

| Unit | Primary classification | Key qualification |
|---|---|---|
| P1 | DIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| P2 | DIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| P3 | DIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| P4 | INDIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| P5 | INDIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| P6 | INDIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| LGA01 | DIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| LGA03 | DIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| LGA04 | DIRECT_ORACLE_LEAKAGE | Classification concerns the audited Unified learner route, not every historical trial. For P4-P6 the learned hidden backend law is not proved directly present in full policy; evaluator-selected solution/branch is an indirect answer surrogate. LGA04 destination is hidden in frozen context; trip-type rule is visible there and must not be labelled hidden merely by family tag. |
| UNIFIED_STEP1_DECLARED_SETTING | PRIVILEGED_LEARNER_SETTING | Report explicitly preserves canonical policy/raw semantic feedback. Interpret completed Diagnoses/Editor attempt as oracle-assisted. Pilot invalid; zero valid Candidate, no Skill gains, replay or Gate to reinterpret. This setting-level row overlaps family rows and is not a task count. |
| STEP4V_TRANSITION | DIRECT_ORACLE_LEAKAGE | Important exception: learner uses partial policy, so no IBS001 here. But authoritative Raises gives exact single-payment guard absent from Base standard schema. Traces also show real error; causal dependence on privilege is not established. |
| STEP4U_OPERATIONAL_ABLATION | UNCERTAIN | Learning gate not met; Skill recovery NOT_TESTED. Base ablation evidence remains valid; cannot certify an unexecuted learner clean. |
| STEP4W_O1_TRANSFER | DIRECT_ORACLE_LEAKAGE | Uses Step4V S_A_transition Skill; inherits its source-contract privilege. Do not treat reuse as new independent clean learning. |
| STEP4W_O2_O3 | UNCERTAIN | Partial Base views and oracle good_order known; dedicated learner input for these probes not established. Oracle registry existence alone is not leakage. |
| CERTIFICATE_S3_ABLATION | UNCERTAIN | Full/partial calibration construction; no separate learner input established here. Later P4 Unified classification recorded separately. |
| LATENT_GOVERNANCE_CALIBRATION_V1 | UNCERTAIN | Calibration/realization artifacts are not proof of a learner run. Risk under reused v14 route is confirmed, actual per-run learning classification not established. |
| BOUNDARY_LATENT_TEMPLATES | UNCERTAIN | Templates/oracle predicates are construction-side. Not every use of word latent means Base/learner masking; no blanket direct-flow allegation. |
| STATE_EXPANSION_PHASE1_7R | UNCERTAIN | State mining/calibration/admission inherit frozen context; no evidence that all expanded tasks were trained through learner. 34-task pilot must not be represented as 54-task learning. |
| MANIFESTATION_PHASE8_11 | UNCERTAIN | Admission/preflight is not semantic information-boundary certification or a recorded evolution run. Trip-type scope is explicit in current Final Context. |
| CONDITIONAL_GOVERNANCE | NOT_APPLICABLE | Manifest explicitly says Policy states WHAT, no normative clause hidden. This does not certify all evaluator metadata learner-safe. |
| CARDINALITY_PROPAGATION | UNCERTAIN | Construction metadata reviewed as index; source-to-learner realization not established; no unsupported CLEAN claim. |
| LEGACY_ATTEMPT1_METADATA | INDIRECT_ORACLE_LEAKAGE | Already invalidated and preserved. Do not count this resolved route as current attempt3 semantic mitigation. |

SUPERVISION_LEAKAGE 主分类计数可能为 0，不表示没有该路径：多渠道 family 以 direct 为主标签，IBS005 在 secondary channels 明确保留。没有未审计的 family 被算作 CLEAN。补充 discovery catalogue 只索引潜在材料，不把索引当成逐实验学习认证。

已有 Unified pilot 的 canonical policy/raw feedback 是明确保留设置，应解释为 privileged / oracle-assisted diagnosis 和 distillation attempt。原报告已标 PILOT_INVALID：Editor 输出截断，无有效 Candidate、无 replay/Gate；不能制造不存在的学习增益。Step4V partial policy 是真实隔离措施，但工具 Raises 提供额外知识；其已保存结果保留，仅调整解释。完全可见 baseline、静态 mining、calibration 本身不因为 learner 漏洞失效。

## CSG12_002 / CSG12_003

两者业务 VS/CF/CS 拓扑保持。当前 Final Context 仍显式披露它们的 focal rule；若未来 mask 但沿用现有 learner，就会通过 canonical policy、反馈和 target_behavior 泄漏答案。002 可提供已观察身份属性/查询结果/订单归属，但不能告诉 exact sufficient credential recipe。003 可提供实际取消结果和补偿事件，但不可由反馈直接给出 cancel-before-compensation 的完整规范边。

**目前均不推荐进入 Phase 13 latent realization。** Phase 12T 后需重新做 bounded-feedback learnability audit；002/003 仅保留为条件候选，不能自动 admission。

## Required repairs — not implemented

- **P0** One Base/learner visible-context projection, with explicit privileged mode only；涉及 domain loader, Diagnosis request, Editor lineage。
- **P0** Whitelist scalar and bounded evidence supervision; remove expected actions/assertions and unrevealed simulator scripts from learner channels；涉及 Success adapter, task context adapter, Judge-to-learner adapter。
- **P1** Taint/provenance review for Diagnosis → compiler → proposal → Editor and prior Skills；涉及 Diagnosis contract, _signal, Editor input, verification targets。
- **P1** Reclassify historical interpretation and re-audit CSG learnability under bounded feedback；涉及 experiment documentation, Phase13 admission。
- **P2** Retain and extend metadata/holdout isolation checks；涉及 preflight, provenance aliasing, selection/regression。

需要下一阶段 **Phase 12T — Learner-Safe Information Boundary Repair**。本轮仅给出 contract 和修复要求，没有编辑 Diagnosis / Compiler / Editor / Judge / runtime / Final Context。

七份产物：global_visibility_matrix.json；end_to_end_information_flow_audit.json；oracle_leakage_inventory.json；learner_safe_supervision_contract.json；legacy_latent_benchmark_audit.json；global_information_boundary_contract.json；本报告。

**PHASE12S_INFORMATION_BOUNDARY_VERDICT = MAJOR_ORACLE_LEAKAGE_REDESIGN_REQUIRED**
