# Phase 12T — Fork v15 & Implement Experience-Grounded Learner

**PHASE12T_V15_VERDICT = READY_FOR_V15_RUNTIME_BOUNDARY_VALIDATION**

已新增独立 GSE-v15 实现，冻结所有 v14 与既有 benchmark/历史产物。v15 的 prior policy/tool knowledge 与 Base 使用同一投影；额外信息只来自三条已观察轨迹及安全监督。

## Execution

v14 modified = false；v15 created = true；model calls = 0；rollouts = 0；Judge calls = 0；benchmark modifications = 0；new tasks = 0；Skill Evolution = 0。单元测试使用合成 transport，并仅在内存创建合成 Candidate，属于用户允许的 no-model dry run，不是一次正式实验或持久化 Skill Evolution。

14,557 个既有受保护文件前后哈希一致，其中 3175 个路径含 v14 的文件/历史产物保存逐文件指纹。当前 54-task benchmark `PHASE_A_UNIFIED_BENCHMARK_MANIFESTATION_EXPANDED_V1` semantics unchanged = true。v14 标注为 PRIVILEGED_LEARNER / v14_legacy 仅写在本轮新增文档；没有改任何旧代码或旧结果。

## New implementation

- `src/learners/stwebagentbench/generate_governed_skill_v15.py`
- `src/skill_evolution/autonomous_gse_v15_benchmark_runtime.py`
- `src/skill_evolution/autonomous_gse_v15_proposal.py`
- `src/skill_evolution/diagnosis_compiler_v15.py`
- `src/skill_evolution/diagnosis_contract_v15.py`
- `src/skill_evolution/diagnosis_provenance_v15.py`
- `src/skill_evolution/diagnosis_schema_v15.py`
- `src/skill_evolution/diagnosis_v15.py`
- `src/skill_evolution/experience_grounded_runtime.py`
- `src/skill_evolution/information_boundary_v15.py`
- `src/skill_evolution/skill_text_v15.py`
- `tests/skill_evolution/test_experience_grounded_v15.py`

新实验入口：`src.skill_evolution.experience_grounded_runtime`，只导出 v15。旧 launcher/manifest 仍冻结；不得把旧 v14 启动器当成新 experience-grounded 默认入口。投影缺失时失败，不会退回 canonical truth。

## Information boundary

| Channel | v14 legacy | v15 |
|---|---|---|
| Policy prior | Full canonical for Diagnosis | Same bound Agent visible policy |
| Tool prior | Unmasked source contracts/Raises | Exact deployed public function schema |
| Success | Expected actions/assertions may be included | Explicit boolean only |
| Judge | Hidden clause/reason may be included | Separate sealed boolean projection |
| IDs | Canonical policy resolution | Local R/E/S/H experience references |
| Editor semantics | May contain Oracle-derived answer | Certified learner-inferred hypotheses |

Diagnosis_v15 直接看到 Base-hidden canonical policy：NO；private backend semantics：NO；evaluator expected answers：NO；raw Level3 Judge answer：NO（指受信任 capture/projection 正常路径）。真实 tool observations/errors 仍完整保留：Agent 执行后看到的操作事实不是 forbidden source knowledge。

Judge 未修改：raw maximum = LEVEL3；contract ceiling = LEVEL2；**当前实际 learner-facing maximum = LEVEL0**。它比上限更严格，避免用字符串黑名单或不可靠 paraphrase 来认定 Level2。并未声称实现了自由文本 Level2 安全降级器。未来若增加更细监督，需要独立验证。

## Learner hypotheses and preserved algorithm

v15 保留 Parent 三轨迹→Diagnosis→确定性 Compiler→Editor→Candidate 的骨架。Compiler 独立复制 v14 决策代码，版本 docstring 之外逐字一致。Diagnosis 仍有机制分析、反证、feasibility、coverage、dual-axis relation、target behavior 和 edit intent。多轨迹、正负标签、观测值、当前 Skill、E/S 证据均保留。没有新增 Oracle 纠正回路。

target_behavior / expected_behavior / repair_operator 是 LEARNER_INFERRED_HYPOTHESIS，可以推断错误。Editor 继续去重、归纳、规范措辞、选 section 并 bounded edit。verification_hypothesis 是 Editor 自己生成的可检验假设，不是 evaluator target。

## Provenance and fail closed

Oracle 与 Learner 使用不同数据通道。允许进入 Editor 的 hypothesis 在 safe request→model transport→schema validation 后由 runtime 签发，不接受外部 dict 自报 provenance。整个不可变 JSON envelope 有进程内签名，且 target_behavior 各字段、mechanism、source refs、supervision refs 都有来源标签。ORACLE_DERIVED、缺失标签、篡改 envelope 均拒绝。

**Can ORACLE_DERIVED semantic fields reach Editor_v15? NO**，在实现的受信任 runtime 路径及测试模型内。Signature 防止意外绕过，不保护进程免受任意恶意 Python，也不证明 learner 的规则在事实或语义上正确。

## Tests

**20 / 20 PASS**，命令 `python3 -m unittest tests.skill_evolution.test_experience_grounded_v15 -v`。

| Required test | Result |
|---|---|
| A — v14 frozen | PASS |
| B — hidden policy isolation | PASS |
| C — evaluator truth isolation | PASS |
| D — backend truth isolation | PASS |
| E — Judge Level3 blocking | PASS |
| F — Editor provenance | PASS |
| G — experience retained | PASS |
| H — no Oracle pointer | PASS |

另覆盖：完整合成 no-model proposal、Final Context/override 快照、无 v14/canonical loader import、缺失投影/标签失败、事件 Oracle 字段拒绝、context/rollout mismatch、未知 Diagnosis 字段拒绝、compiler snapshot 一致、字段级 provenance、无 eligible update 不调用 Editor、禁止修改 compiled operation、v15 默认新入口。所有新增模块编译通过。

## Remaining findings and limits

v15 current path 的已确认剩余泄漏：CRITICAL=0、HIGH=0、MEDIUM=0、LOW=0。这个计数只覆盖本轮静态/单元测试的可信输入路径，不覆盖未经验证的真实框架适配器。

- Runtime capture trusts the actually deployed bound Agent and genuine observed events. Typed schemas and seals do not prove that arbitrary Python callers supplied honest events. Phase12U must verify live normalization/capture provenance.
- Process-local signed immutable envelopes prevent accidental DTO forging/mutation; not a sandbox for malicious Python or a semantic proof of hypothesis correctness. Persisted envelopes cannot be resumed in another process; fail closed, then recapture/revalidate from allowed sources in a future explicit path.
- LEVEL0 is the only implemented declassification. LEVEL1/2 prose/localization is intentionally not accepted, because in small hypotheses such localization may encode a LEVEL3 answer.
- Current Skill is assumed to be the actually deployed Parent shared with Base. Historical privileged Skills are not automatically clean; no historical Skill was migrated this phase.
- No empirical learnability, improvement, semantic correctness of model hypotheses or Editor generalization was measured.
- No existing v14 launcher or benchmark manifest is redirected. NEW experience-grounded experiments use src.skill_evolution.experience_grounded_runtime, which exports only v15 and has no privileged fallback.

## CSG and next phase

CSG12_002 realized = false；CSG12_003 realized = false。v15 已提供在相同 visible prior 与 bounded feedback 下重新审计 learnability 的基础，但未证明它们在 binary supervision 下可学习，未修改它们的 context、生成任务或进行 rollout。

下一阶段建议 **Phase12U — v15 Information Boundary Runtime Validation**：验证真实 Agent binding、消息标准化/来源、实际序列化模型 payload、evaluator/Judge 投影和跨进程 fail-closed 行为。暂不做 Skill Evolution，不进入 Phase13。本轮完成后停止，未执行 Phase12U。

**PHASE12T_V15_VERDICT = READY_FOR_V15_RUNTIME_BOUNDARY_VALIDATION**
