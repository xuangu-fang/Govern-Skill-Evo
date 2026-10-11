# v19 edit-level Memory Review

> 2026-09-27 更新：当前逐 edit 输入协议为 `edit_memory_review_v19.2`。历史部分使用已有 Attribution 记录（完整局部比较、理由、反证、不确定性和联合 edit 关系）及原始证据引用，不再默认展开历史事件正文；程序补充被引用 pair 的监督标签和结果变化。当前 Findings 路由、当前事件组装及四类 Evidence Status 不变。以下 v19.1 的事件正文选择说明属于历史设计。
>
> `historical_evidence_refs` 是经过归档存在性检查的来源目录，`historical_evidence` 为空；模型可通过引用追溯摘要，但不能声称已阅读历史原文，也不能增加摘要未支持的历史事实。无需新增模型压缩调用、MORE_CONTEXT 或提高 32,000 输入预算。
>
> 离线统计见 `artifacts/v19_memory_summary_profile_001/report.md`。正式实验失败包由 44,381 降至 14,233 token。由于输入/Prompt 协议变更，既有实验不能直接 resume；需显式迁移并统一重新生成六份 Review，旧结果保留。此修改未执行迁移或模型调用；零当前关联问题尚未调整。

The local generation protocol now uses one deterministic packet and checkpoint per historical edit. The legacy separated protocol and historical audit restoration remain supported. No model calls are made by profiling.

## Input boundary

Full `memory-review-input.json`, committed Memory, and Replay remain immutable audit archives. They are not the model input. A packet contains the edit, its deployed rule bindings and Gate decision, attribution judgments including observations/counterevidence/uncertainty, attribution-cited historical events with identifiable tool call/result pairs, linked current Findings, their cited current events with call/result pairs, cited supervision, and relevant contexts. Tools are limited to those used in selected events. Applicable context policy remains intact.

Current Findings link only by exact overlap with the edit's current or descendant rule references. Possible/ambiguous bindings, keyword similarity, task-level coincidence and broad policy overlap do not establish links. Unmatched Findings remain in Issue Fusion. No linkage means no evidence in this packet, not that the full round contains no relevant behavior. In particular rejected/absent edits may remain uncovered with this conservative association method.

Evidence bodies stay unmodified. Repeated trajectory metadata is stored once. Compact CURRENT and PAIR references are lossless aliases, expanded before validation. Historical observations shared by edits retain their original IDs and are not independent confirmations. No complete historical Replay, prior review transcript, or recursive generation history is fed into the packet.

## Execution

`run_edit_reviews` in `edit_memory_review_v19.py` profiles every packet, then runs each edit independently. All historical objects for the same edit share one call. Input budget: 32,000 cl100k_base proxy tokens; output cap: 24,000 tokens. Both initial and optional repair requests must pass the input cap. These are local proxy counts, not gateway billing tokens.

Output states remain SUPPORTED / CONTRADICTED / MIXED / NOT_COVERED. The existing polarity, finding linkage and reference validation runs against the scoped packet. No MORE_CONTEXT branch exists. A local contract rejection permits at most one audited repair. Network/truncation/budget failures remain INCOMPLETE; they are not converted into NO_EDIT or NOT_COVERED. Unknown-response attempts require explicit recovery; resume does not silently resend them.

Each edit stores input, original request/response, optional repair, validated result and status. Resume revalidates checkpoints and only calls missing edits. Batch aggregation requires every edit to finish and validates the union against the original audit input. Issue Fusion receives the existing HistoricalReviews format and all current Findings. No downstream schema change is required.

## Profiling

```
/Users/didi/miniforge3/bin/python scripts/profile_v19_edit_memory_review.py \
  --input experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-02/generation/memory-review-input.json \
  --output artifacts/new_edit_memory_profile
```

The output directory must be new. `profile.json` records per-edit input sizes, linked Findings, edit coverage and unmatched Findings. Per-edit input JSON files preserve exact source references for inspection.

## Existing Pilot

The round-02 7 completed Current Diagnosis groups, full Memory review input and round-01 committed Memory are preserved. The implementation change intentionally does not rewrite existing run source bindings. Before resuming that Pilot, create an explicit source/protocol migration receipt that reuses those upstream checkpoints; blindly rerunning the old launcher will fail source validation. No real review or Pilot restart is performed by this implementation task.

## v19.3：问题与尝试关联

新运行的完整审计输入带 `memory_protocol=issue_memory_v19.1`。确定性投影
`edit_attempts` 从已有 generation issues、source findings、edit 和 Attribution 提取
问题来源、尝试内容、Gate 结果及正反/联合结果；不改写持久化原始证据，不新增图谱。
旧档案缺少来源时明确标为 LEGACY_EDIT_SOURCE_ONLY，不生成虚构问题摘要。

每个 edit 的既有 Memory Review 调用读取当前全部**精简 Finding 摘要**及事件引用目录，
不加载当前或历史原始 trajectory、工具定义或完整 Review 历史。规则引用只作关联提示，
不是资格条件，所以 RETAIN 后 ABSENT 的 ADD 也可关联当前问题。模型在既有
current_finding_refs 中选择关联；当前事件引用必须属于所选 Findings，保留原有四种状态。
这里判断的是 Findings 所报告的证据，不声称直接核查过原始事件。

这不是把全部 Findings 的原始证据送给每个 edit。32,000 输入预算不变，超限明确停止，
不截断、不新增 MORE_CONTEXT。规模增长后仍需监控预算，本次正式样本最大接近上限。
profile 的 available_finding_count 表示可见范围，linked_finding_count 仅表示规则提示，
二者都不等于模型实际建立的语义关联。

Issue Fusion 按问题合并历史与当前发现，相关 edit_attempt 随既有 historical_objects
进入局部 Evidence Review；只有此处加载相关原始证据并核验修改。局部审阅比较旧尝试：
拒绝不等于单 edit 无效，接受不等于单 edit 有效；重复负向尝试应在既有 reason 中说明
新证据或实质变化，无支持则 NO_EDIT，历史并非永久禁令。这是模型判断要求，不是代码
已经证明的因果关系或语义防重保证。Compiler/Editor 和输出状态不变。

旧输入无协议字段时按旧方式重建，保留旧审计哈希的可验证性。新旧请求不可混入同一
检查点批次。恢复现有正式实验需另行记录迁移并重建 Memory Review 及其下游；可以复用
已完成 Current Diagnosis。本次实现不启动实验，也不修改旧运行目录。

## v19.4：引用闭合错误与契约修复预算

输出契约不变。错误报告包含 review 索引、historical_object_id、未共享证据的 Finding
及其可引用事件、实际已引用事件。仍由模型决定修复，不由程序补引用或删 Finding。

输入采用无损共享 JSON 值表（repeated_text/shared_text_ref）及显式 ID 别名；
原始证据包和响应不截断。修复只携带一份原输入，原响应/错误中的引用可以用同一
别名表示，原响应文件保持原文。修复不再嵌套另一张共享值表。

总输入上限仍为 32,000；首次请求上限为 28,800，为唯一一次修复预留 3,200。
修复发送前仍按实际请求计数；余量不能保证任意长度输出都能修复，超限继续停止。
不是扩大总预算，也不增加修复次数。profile 的 within_budget 按首次上限判断。

本次离线回归：失败 edit 首次 31,075 → 28,730，带详细错误的修复为 31,051。
完整拒绝响应和输入包的压缩测试夹具保存在 tests/skill_evolution/fixtures 中。
旧运行未更改。新 prompt/错误协议与旧绑定不兼容，不直接 resume 原目录；后续迁移
需保留 6 个完整 Review 以及该 edit 原始响应，归档已确认未发送的修复请求，
只为失败 edit 生成新的修复请求。不得通过改哈希或整批重跑绕过版本校验。

### 历史判断与问题复发（claim-comparison-1）

不增加状态或输出字段。Review 在现有 `reason` 中明确被检验的历史主张，并区分：

- 问题仍存在：未采用旧方案的 Parent 再次犯错，只说明需求仍存在，不证明旧方案有效或无效。
- 旧方案的行为／适用性主张：只有相关证据能够支持或反驳；ABSENT 不禁止独立的能力或适用性反证。
- 已部署的规则：存在不等于被执行；不遵守与遵守后的后果必须区分。

只有相关问题复发、未检验方案主张时，沿用 `NOT_COVERED / INSUFFICIENT_EVIDENCE`，
保留 `context_current_refs` 和 `current_finding_refs`。这些关联仍交给 Fusion，不丢失重试机会。
不按 ABSENT、Gate 或结果分数由程序自动改写 Evidence Status。

共享语义在 `memory_consumption_v19.py` 中定义。新 prompt 记录 `-claim-comparison-1`；
输入数据、状态枚举及验证 schema 不变。历史判断不被覆盖，已保存结果不会自动转换为新语义结果。
