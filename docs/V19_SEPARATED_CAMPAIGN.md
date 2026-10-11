# v19 职责拆分第 3 步：独立闭环与 Pilot

> 目录整理提示（2026-09-27）：下文旧 Pilot 的命令保留为历史说明，不代表搬迁后可直接 resume。当前产物入口见 [v19 实验索引](../experiments/v19/INDEX.md)，原始路径见 [迁移映射](../experiments/v19/path-map.json)。

日期：2026-09-24。

新 CLI 默认 `--generation-protocol separated`，在新目录执行：

```text
Parent Evolution → 当前经验分组 → Current Diagnosis → Current Findings
→ Memory Review → Historical Reviews
→ Reconciliation → 确定性 Compiler → Editor
→ Candidate Evolution → edit-level Attribution → 私有 Monitor/Gate
→ 原子提交 Memory/保留 Skill → 下一轮
```

原 v18、原 Pilot 不改写。Python `campaign_config` 保留 legacy 默认以兼容已有调用；新 CLI 显式选择 separated。协议写入 campaign binding，不能把旧目录原地改成新协议。

## run / resume

```bash
# 新流程无模型预检
python scripts/run_v19_v4.py --pilot \
  --preflight-output artifacts/v19_separated_preflight_manual_001

# 最多两轮独立 Pilot：输出目录必须尚不存在
python scripts/run_v19_v4.py --run --pilot \
  --output experiments/v19/pilot/v19_v4_separated_pilot_002

# 同一 Pilot 原配置恢复
python scripts/run_v19_v4.py --run --pilot --resume \
  --output experiments/v19/pilot/v19_v4_separated_pilot_002

# 完整实验仅提供命令，由用户自行启动；本次未启动
python scripts/run_v19_v4.py --run \
  --output experiments/v19/formal/v19_v4_separated_formal_001

python scripts/run_v19_v4.py --run --resume \
  --output experiments/v19/formal/v19_v4_separated_formal_001
```

默认并发 8，Pilot 最多 2 轮（与原 Pilot 同一 Evolution 36 / Monitor 45 划分，最多 324 条 rollout）；正式最多 4 轮。若首次指定不同并发，resume 保持相同值。NO_UPDATE/UNABLE 提前结束，不为了跑满轮数制造 Candidate。

## 检查点和一次修复

`generation/` 保存：

- input.json：Parent、Memory head、当前完整分组输入、协议和 v19 源文件摘要。
- current-NNN/：当前 Diagnosis 请求、完整响应标记；对应 current-NNN-findings.json。
- memory-review-input.json、memory-review/、historical-reviews.json。
- reconciliation-input.json、reconciliation/、reconciliation-result.json。
- editor/、generation.json、validation.json。

每个 Current Diagnosis、Memory Review、Reconciliation 和 Editor 调用在本地契约失败时最多允许一次 `-repair-001` 修复，保存原响应、精确拒绝、修复请求和修复响应。仍失败则停止，resume 不产生第三次调用。网络异常、未完成响应、拒答、截断或发送前超预算不属于契约修复；不自动补引用、删除证据或改变结论。

完成响应重验后复用。没有完成响应标记的请求保持不确定，普通 resume 不会悄悄重发；需要明确归档失败尝试后继续。协议、源码、Parent/Memory 或输入改变都会拒绝恢复。空历史不请求 Memory Review 模型；空 findings 加空历史不请求 Reconciliation/Editor。

## 持久化及跨轮来源

新 edit ledger 的可选 generation_audit 保存完整 Current 输入/发现、Memory Review 输入/输出、Reconciliation 输出；其 SHA-256 进入 ledger payload。旧 ledger 无该字段，继续按旧契约验证。恢复新 ledger 时从原始响应重验全部新阶段，重建相同 Compiler/Editor 来源；source snapshots 仅保留提案涉及的完整轨迹，完整审阅证据仍在 generation_audit 中。

Memory 仍通过既有原子提交保存 ledger_input、回放、归因及 Gate 回执。load/retrieve 额外暴露 generation_reviews：历史审阅状态、Current Findings 和全部决策，不覆盖旧记录。不传入 Monitor 轨迹、分数、评分理由。NO_UPDATE/UNABLE 的审阅记录保留在阶段目录，不伪造 Memory 提交。

跨轮链首先由 HR→HO→edit 和 RC→CF/HR 明确保存。仅有结构化关系可核对时，再产生原有关系标签：绑定当前内容的替换为 REVISES，删除为 REVERTS；对未部署内容重新 ADD 为 RETRIES；恢复已删除内容为 REVERTS；重试未生效删除为 RETRIES。仅提供背景、没有匹配目标的历史 review 不强行建立这些 mutation links。标签表达声明来源和结构化动作之间的关系，不证明语义恢复或因果改善。

最后一轮原子提交已完成但 round_result/campaign 报告尚未发布时，resume 从已验证 Memory/Gate 重建报告，避免重复提交或因 INCOMPLETE 报告无法收尾。

## 发送表示

`evidence_projection_v19` 按内容对事件正文和长文本建立引用，原事件 evidence_ref 不变；发送前自动无损还原并核对摘要。模型通过 event_bodies/text_bodies 读取完整内容。原始请求 DTO、证据和审阅输出按原文持久化；不做摘要截断，不按当前组路由历史。发送前沿用带余量的 token 预算检查，超限停止而非删减证据。

## 工程与真实观察边界

工程 fixture 验证两轮 ACCEPT→REVISES、RETAIN→RETRIES、MIXED/NOT_COVERED 保存、阶段中断、末轮提交后恢复、审阅/账本篡改拒绝、一次修复、无完成响应不重发、空发现无虚假提交、Monitor 隔离和无损发送表示。预设状态只验证机制，不是方法有效性的证据。

无模型预检：`artifacts/v19_separated_preflight_001/preflight.json`，243 个环境实例，模型调用 0。真实 Pilot 进展另行记录，不能将工程 fixture 结果当成真实纠偏效果。

最终工程验证：`tests/skill_evolution/*v19.py` **331 项通过**（含 14 项新闭环专项）。992 个 v18 冻结文件哈希一致。真实 Pilot 已在 `experiments/v19/pilot/benchmark_v4_rounds_01_02/campaign` 启动；启动信息在 `artifacts/v19_separated_pilot_001_process.json`，独立日志在 `artifacts/v19_separated_pilot_001.launch.log`。启动成功不等于 Pilot 完成，须以实际状态为准。
