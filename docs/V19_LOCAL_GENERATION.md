# v19 局部核验闭环（第三步）

> 目录整理提示（2026-09-27）：下文旧 Pilot 的命令保留为历史说明，不代表搬迁后可直接 resume。当前产物入口见 [v19 实验索引](../experiments/v19/INDEX.md)，原始路径见 [迁移映射](../experiments/v19/path-map.json)。

> 当前新运行已切换为 [单次 Evidence Review v19.3](V19_ONE_PASS_EVIDENCE_REVIEW.md)，下文补充上下文协议保留作为历史说明。

`local_generation_v19.1` 接通 Current Diagnosis → Memory Review → Issue Fusion → 逐提案 Evidence Review → 确定性编译 → Bounded Editor → Candidate Replay → Attribution → 私有 Monitor/Gate → Memory 提交。旧 `legacy` / `separated` 协议与既有实验目录保留；不迁移旧 Reconciliation 检查点。

## 编译与来源边界

每个 PROPOSE 必须有独立、完整且重新通过校验的 Evidence Review。任何未完成提案阻止本轮编译，但其他提案的检查点继续独立保存。NO_EDIT 不进入计划；全部 NO_EDIT 返回 NO_UPDATE，无伪造 Candidate 或 Memory 提交。

VERIFIED gap 的 MISSING / NEEDS_REVISION / SHOULD_REMOVE 对应 ADD / REPLACE / DELETE。v19 适配器移植 v18 的确定性编译和局部文本应用规则，复用其严格 Editor 输出解析/Schema；**不伪造 v18 Diagnosis 的分析段，不修改冻结 v18，不直接把局部结果塞进旧 Diagnosis Compiler 接口**。

同操作、重叠目标按连通分量合并并保留全部来源；REPLACE/DELETE 重叠拒绝整批计划。ADD 不做语义去重。Editor 只获取已核验来源，未指定的 Parent 文本逐字保留；DELETE 由程序执行。

账本沿用既有 edit ID、效果归因和原子 Memory 提交机制。新审计保存完整 Current Findings、历史审阅、Fusion、每个 Review 的补充请求和结果；纯函数重建输入并验证全部来源。`source_gap_refs.diagnosis_ref` 是为账本兼容保留的字段名，新协议中其值是实际 `ISSUE/...` 提案 ID，`gap_index=0`，不是伪造 Diagnosis。Memory 保存 issues 与 evidence_reviews，并以 REVISES/RETRIES/REVERTS 表达可验证的结构关系；不把此关系宣称为因果证明。

## 复用上游，停在 Editor 前

```bash
python scripts/run_v19_local_review.py run \
  --upstream experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --output experiments/archive/v19/v19_v4_local_review_once_001
```

这个入口只复用已完成 Current Diagnosis / Memory Review，重新运行 Fusion 与局部 Review，完成确定性编译后停在 `BEFORE_EDITOR`。不会调用 Editor、Replay、Monitor 或提交 Memory。源产物原封不动，新调用与上游摘要写入独立目录。程序失败时查看 `status.json` 与 `review-summary.json`；失败不等于 NO_EDIT。

恢复相同代码和输入：

```bash
python scripts/run_v19_local_review.py resume \
  --upstream experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign/round-01/generation \
  --output experiments/archive/v19/v19_v4_local_review_once_001
```

resume 复用已完成调用；无完整响应的调用不会自动重发。对明确无响应的单提案，可使用已有 `run_evidence_review(..., resume=True, retry_incomplete=True)`，归档该次尝试后再请求；完成但契约失败不能这样重试。Fusion 仍保持一次契约修复上限，不自动重发不确定网络调用。

## 完整闭环入口（本次不启动）

```bash
python scripts/run_v19_v4.py --generation-protocol local --pilot --run \
  --output experiments/v19/pilot/v19_v4_local_pilot_001
python scripts/run_v19_v4.py --generation-protocol local --pilot --run --resume \
  --output experiments/v19/pilot/v19_v4_local_pilot_001
```

正式实验去掉 `--pilot` 并使用新的输出目录。未指定 `--run` 时仅 preflight。旧命令的默认协议仍保留 separated，新协议必须显式选择 local，避免无意改变既有运行行为。

## 验证范围

工程测试覆盖两轮 ACCEPT/RETAIN、历史关联、MIXED/NOT_COVERED、源篡改拒绝、NO_EDIT、未完成核验禁止编译、Editor 前停止、恢复不重复模型调用与提交、Monitor 隔离，以及确定性操作映射/合并/冲突。工程构造用于验证机制，不能作为真实效果证据。真实单次运行仅用于观察新 Fusion/Review 行为，未进入 Editor，因此不产生 Skill 效果结论。

输入 v19.2 的预算分析、无损目录、输出截断分类及显式旧产物复用，见 [Evidence Review 预算修正](V19_REVIEW_BUDGET_FIX.md)。

### 统一一次契约修复与扁平 Editor（2026-09-28）

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
