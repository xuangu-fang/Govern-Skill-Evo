# V23.2 实验材料与运行记录

[方法实验总索引](../README.md) · [方法说明](../../../docs/methods/v23_2/README.md)

2026-10-20 分两步整理。第一步新增一条精确忽略规则：
`/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/pytest_tmp/`。
测试临时文件仍留在本地；源码、测试、实验输入、正式报告和关键结果均未移动或删除。
第二步精确忽略 62 份辅助状态快照与日志，详见末节。
两步均没有执行实验、重生成结果或调整方法实现。

## 文件数量与用途

检查时，全仓库未追踪文件为 2,919 个，其中 V23.2 为 2,278 个。
忽略 1,598 个测试临时文件后，分别为 1,321 和 680 个。
这两个清理后数字不包含随后新增的本清单；其他工作继续产生文件时数量会变化。

第一步完成时，V23.2 剩余材料包括本目录内的 665 个文件，以及方法文档 4 个、
方法源码与提示词 4 个、测试 7 个。以下为检查时各实验目录的文件数，
均不包含当时已忽略的产物。以下数量保留为第一步的检查记录；
第二步完成后的总数见末节。

| 实验目录 | 文件数 | 用途 |
|---|---:|---|
| [v23_2_executability_001](v23_2_executability_001/) | 13 | 第一轮可执行性验证：输入、提示词差异、尝试摘要和报告 |
| [v23_2_executability_002](v23_2_executability_002/) | 15 | 第二轮可执行性验证及最终更新比较 |
| [v23_2_capability_001](v23_2_capability_001/) | 20 | 能力背景澄清、技术停点与证据核查 |
| [v23_2_memory_analysis_001](v23_2_memory_analysis_001/) | 6 | 历史 Memory 分析、来源索引和报告 |
| [v23_2_response_alignment_001](v23_2_response_alignment_001/) | 16 | 支持范围对齐的局部模型验证 |
| [v23_2_response_behavior_001](v23_2_response_behavior_001/) | 18 | R06 Candidate 的真实行为验证、实际差异、轨迹报告与成本 |
| [v23_2_response_construction_001](v23_2_response_construction_001/) | 23 | 证据约束的更新构造、技术失败说明与对比 |
| [v23_2_response_symmetric_001](v23_2_response_symmetric_001/) | 22 | 原始与替代更新的对称证据约束 |
| [v23_2_evidence_calibration_001](v23_2_evidence_calibration_001/) | 29 | 证据校准、历史比较及真实尝试记录 |
| [v23_2_response_grounded_001](v23_2_response_grounded_001/) | 28 | 有据构造的局部验证及历史对照 |
| [v23_2_response_inference_analysis_001](v23_2_response_inference_analysis_001/) | 10 | 离线读取既有响应、轨迹与推断分析 |
| [v23_2_diagnosis_boundary_001](v23_2_diagnosis_boundary_001/) | 25 | Diagnosis 边界实验、输入冻结与响应比较 |
| [v23_2_diagnosis_trace_001](v23_2_diagnosis_trace_001/) | 12 | Diagnosis 证据追溯与根因分析 |
| [v23_2_diagnosis_construction_001](v23_2_diagnosis_construction_001/) | 33 | Diagnosis 构造实验、历史漂移记录与输出 |
| [v23_2_diagnosis_construction_001_r05_retry_001](v23_2_diagnosis_construction_001_r05_retry_001/) | 11 | R05 独立重试及比较结果 |
| [v23_2_diagnosis_interface_audit_001](v23_2_diagnosis_interface_audit_001/) | 14 | 接口离线核查、案例矩阵和决策 |
| [v23_2_memory_evidence_audit_001](v23_2_memory_evidence_audit_001/) | 18 | Memory 证据核查及 R05 输入选择 |
| [v23_2_preconditioner_memory_ab_001](v23_2_preconditioner_memory_ab_001/) | 275 | A/B 输入、9 次真实调用、失败记录、报告修订与主对照 |
| [v23_2_preconditioner_commitment_analysis_001](v23_2_preconditioner_commitment_analysis_001/) | 12 | 读取 A/B 结果进行承诺追溯与机制分析 |
| [v23_2_commitment_anchored_001](v23_2_commitment_anchored_001/) | 65 | 独立原型源码、测试夹具、人工演示及实现报告 |

## 保留边界

| 类别 | 典型材料 | 本次处理 |
|---|---|---|
| 源码、测试 | `run.py`、分析与报告脚本、原型实现、测试代码 | 保留现有结构与内容 |
| 实验输入 | Prompt、配置、原始 Plan、Memory A/B、上下文、来源清单、`requests/*_UNSENT.json`、`fixtures/` | 保留；不能按 JSON、TXT 或目录名整体忽略 |
| 正式报告 | `reports/*.md`、实际修改差异、历史报告修订副本 | 保留；历史版本与当前结论分开读取 |
| 关键结果 | 比较与汇总、费用/用量、实际响应、Effective Plan、失败原因、证据索引 | 保留；同名 `verification.json` 也可能包含实质结果 |
| 人工演示 | 原型 `results/human_runs/` 的 31 个文件及 `human_demos.json` | 保留，标记为人工夹具演示，不能算模型调用结果 |
| 测试临时输出 | 原型 `results/pytest_tmp/` 的 1,598 个文件 | 已精确忽略，仍留本地 |
| 辅助状态快照与日志 | 25 份运行前快照、29 份 Git 状态、8 份测试通过日志 | 第二步按完整路径忽略，本地保留 |
| 其他检查结果 | 保护检查结论、失败诊断、结构化验证结果 | 继续保留 Git 可见性，不按名称批量忽略 |

## 真实运行记录

### 早期实验

已有 12 组实验将完整请求、响应、尝试和轨迹写入
[`artifacts/methods/v23_2/`](../../../artifacts/methods/v23_2/)。
检查时共 844 个文件、约 254 MB，已由根目录 `/artifacts/` 规则忽略，
不计入上述未追踪数。本次保留现状。

实验目录中的输入、精选结果和正式报告继续保留。历史读取脚本和部分测试
依赖这些本地原始归档，仅取得 Git 文件不能保证重放全部历史分析。
其中 `response_behavior_001` 包含真实 Editor 与七条环境任务的行为验证；
不能将其与仅进行 Diagnosis／Preconditioner 调用的实验混为一类。

### 新增 A/B 实验

`v23_2_preconditioner_memory_ab_001` 的真实记录目前位于实验目录内部，
九个运行目录合计 97 个文件，约 5.53 MB：

| 位置 | 文件数 | 记录性质 |
|---|---:|---|
| `p3b_results/runs/A/` | 6 | 初次 A 请求超时，没有合法输出 |
| `p3b_results/runs/B/` | 12 | 原 Prompt 的合法 B 输出，属于历史对照 |
| `p3b_A_retry_001/runs/A/` 至 `p3b_A_retry_005/runs/A/` | 55 | 五次技术失败；保留响应、解析/引用错误及用量 |
| `p3b_A_format_001/runs/A/` | 12 | 当前选用的合法 A：保留原始 Plan |
| `p3b_B_format_001/runs/B/` | 12 | 当前选用的合法 B：修改 u1 |

当前主对照是同 Prompt 的 A_format/B_format，见
[阶段结论](v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_DECISION.md)。
旧 B 与失败重试保留历史身份，不能替代当前配对或被当成重复文件删除。
主报告、`evaluation_filled.json`、调用账本、用量和失败诊断一并保留。

这 97 个文件本次继续保留在 Git 可见范围内。已确认的读取关系包括：

- [承诺分析](v23_2_preconditioner_commitment_analysis_001/analyze.py)读取 A_format/B_format 的请求、响应、原始输出、Preconditioner 结果、Effective Plan 与运行状态。
- [原型夹具准备](v23_2_commitment_anchored_001/prepare_fixtures.py)直接读取 B_format 请求，构造本地测试输入。
- [原型报告脚本](v23_2_commitment_anchored_001/finish_reports.py)读取两组请求及关键结果，核对夹具来源。
- [A 报告脚本](v23_2_preconditioner_memory_ab_001/p3b_A_format_001/finalize_offline.py)和 [B 报告脚本](v23_2_preconditioner_memory_ab_001/p3b_B_format_001/complete_reports.py)读取历史响应和用量，生成比较与累计记录。

因此不能直接对 `runs/`、`results/` 或整个 A/B 实验设置忽略规则。

### 原型人工演示

`commitment_anchored_001` 的七组 `human_runs` 来自人工测试夹具：
六组结构编译或合法停点、一组预期拒绝。其脚本禁止网络调用。
这些文件用于说明原型行为，不是七次真实 Preconditioner 调用，
也不是新的真实 Candidate；正式报告引用的演示结果继续保留。

## 第二步：辅助状态快照与日志清理

2026-10-20 已逐份读取以下 62 份辅助记录，根目录 `.gitignore`
新增对应的完整文件路径，没有使用覆盖整个 `config/`、`results/`、
`reports/` 或同名文件的通配规则。

| 文件类别 | 数量 | 用途与核对结果 |
|---|---:|---|
| `protected_before.json` | 25 | 运行前的文件状态清单；24 份为直接映射，Diagnosis Trace 一份另含时间与扫描范围；均不承载 Plan、Memory、Prompt 或调用响应 |
| `git_status_before.txt` | 17 | Git 运行前状态输出 |
| `git_status_after.txt` | 12 | Git 运行后状态输出 |
| `offline_tests.txt` | 8 | 测试通过摘要与控制台进度，没有失败诊断 |

这 62 份记录合计 503,014,847 字节（约 503 MB），全部保留在本地原位置。
全仓库未追踪文件由 1,322 降至 1,260；V23.2 由 681 降至 619，
其中包含本清单。V23.2 未追踪材料的文件大小合计由约 604 MB 降至约
101 MB；这是待纳入 Git 的材料减少，本地磁盘占用未减少。

### 历史读取依赖

快照被部分 `run.py`、`analyze.py`、`verify_freeze.py`、
`verify_protection.py`、报告生成及报告修订脚本用于比较运行前后文件状态。
部分调用入口还会检查快照是否存在。此次只改变 Git 可见性，
文件与读取路径均保留，不改写旧脚本或重新生成历史检查结果。

仅从 Git 获取仓库时，这些旧检查需要另外恢复本地快照与原始归档。
旧检查比较的是当时的文件状态，不能把其检查通过条件当成当前仓库的验收条件。

### 继续保留的材料

- 源码、测试、提示词、实验配置、Plan、Memory、夹具、待发送请求和来源清单。
- `freeze.json`、`implementation.json`、输入与来源索引等实验定义材料。
- 所有正式报告、报告修订副本、精选结果、用量、失败诊断及保护检查结论。
- A/B 实验的 97 份真实调用记录，包括失败尝试与当前选用的合法配对。
- 原型的 31 份人工演示文件，以及包含测试案例详情的结构化结果。

本次没有额外忽略其他 `verification`、`protection`、`tests` 或
`offline_checks` 文件；它们可能包含实质性结果，仍按原有边界保留。
