# Govern V23.3

状态：2026-10-21 已将通过用户验收的 Memory v3 视图接入 v23.3 Preconditioner 默认模型输入。未注册为全局默认方法；真实生成及 A/B 结果见 [本轮接入报告](../../../experiments/methods/v23_3/memory_v3_integration_001/REPORT.md)。

代码基线是正式 V23 commit `08c442f202f05a25a0c30412ef89f8312df0c0f0`，不是 V23.2。复用 V23 的事实输入、Schema 校验、Unified Diff 引擎、编译器和 Editor 策略；只增加本版 Prompt、转换器与必要加载入口。

核心研究问题：历史实际编辑及其条件化行为响应，能否改善当前 Update 的变换选择，并最终提高任务表现？Unified Diff 仅承担修改落实。

从 [P0/P1 决策](../../../experiments/methods/v23_3/P0_P1_DECISION.md)进入设计历史；当前实现与边界见 [P2 决策](../../../experiments/methods/v23_3/p2_offline_001/P2_FINAL_DECISION.md)。

调用入口：

- `diagnosis.run_diagnosis(grouping_directory, directory, generate=...)`
- `preconditioner.run_preconditioner(grouping_directory, diagnosis_directory, directory, generate=..., memory=...)`
- `editor.run_editor(preconditioner_directory, directory, generate=...)`

每个入口均有同模块 `load_*`，并沿版本匹配的上游链恢复验证。`generate(messages, directory)` 沿用已有注入式接口。恢复时必须传回相同 Memory、视图版本和调用配置。大体积历史输入需显式声明合适的 `max_input_chars`，不自动截断。

## Memory 模型输入

`memory_view.py` 在本地确定性构建 `memory_evidence_view_v3`，不增加模型调用：保留全部 active entries、原引用 sources、完整动作/反馈 trace 和结果；数字证据锚点取 ±2 详细状态窗口，无数字锚点的来源保留全部详细步骤。详细步骤显式包含 before/after；状态直接引用按完整内容及顺序共享的全局菜单；所有 trace 与详细步骤使用带历史来源的完整 ID。

`preconditioner_input(saved)` 仍返回完整原始数据供 Patch 编译校验；`model_input(saved)` 返回模型视图，`messages_for(saved)` 默认发送该视图并追加通用格式说明。新归档的 `input.json` 和 `run.json.memory` 保留完整 Memory，`model_input.json` 保存实际模型输入，`run.json.memory_view` 标识版本。加载时重新投影并验证消息，再重新解析、应用 Patch 和编译；Editor 接口不变。

旧归档没有 `memory_view` 时按 `entries_sources` 恢复。需要显式运行或恢复旧格式时传 `memory_view="entries_sources"`，不同版本的请求不能静默复用同一目录。原 V23 默认输入不变；A/B 的自由替换侧通过 `memory_view.project_messages(v23.messages_for(saved))` 适配，与 B 使用完全相同的 user 输入。

该视图省略窗口之外的详细状态，保留遗漏范围；完整归档可用于校验，不意味着模型看到了被省略状态。格式验收接受来源计数 16/17 的非阻断误差，不放宽来源、动作、状态、菜单或引用要求。

`normalize_update_patches(result, payload)` 返回 `(normalized, effective_plan)`；结构拆合和新 ID 暂不支持。旧单行 text 不迁移，合法停点不进入 Editor。

离线复现：

```sh
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_3/p2_offline_001/run_tests.py D
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_3/p2_offline_001/build_mock_archive.py
```

P2 当时最终回归 434 项通过，仅证明工程贯通。第二条命令使用明确标记的人工 Mock；其旧归档应使用旧视图恢复，当前加载器兼容这些历史结果。当前版本的回归可运行 `python -m pytest tests/skill_evolution/v23_3 tests/skill_evolution/v23`。真实模型调用、已知开发案例验证及费用分别保存在实验目录，不将离线 Mock 等同于行为收益。

## 运行产物与读取依赖

2026-10-27 已将原始运行数据迁至 `artifacts/methods/v23_3/<实验ID>/`，配置、报告与必要证据留在实验目录。入口见
[v23.3 实验导航](../../../experiments/methods/v23_3/README.md)。
归档读取工具在需要时临时拼合文件，历史结果与冻结记录保持原文；无永久兼容链接或迁移清单。

### Git 保留范围

- 方法与实验源码、测试代码、Prompt、协议、参数、任务清单、冻结定义及来源索引。
- P1R 的 `fixtures/`、测试问题与预期答案等小型夹具；不为历史复现复制完整数据集。
- 正式报告、评价与决策、最终指标、费用汇总、轻量核验结果及必要的证据摘录。
- 实际有效 Plan、Candidate Skill、Patch 与实际 Diff。
- 关键失败说明、结构化校验、错误堆栈和小型模型输出等足以解释失败原因的材料。
- 历史源码与报告修订仍保留，本次不做源码去重。

### 本地归档范围

| 材料 | 读取用途 | 当前边界 |
|---|---|---|
| 完整 `trajectory.json`、原始响应正文 | 行为重放、完整轨迹核验 | 本地保留；正式轨迹报告与结果摘要继续纳入 Git |
| `input.json`、展开的 Memory、payload、模型输入、消息和请求副本 | 真实输入重建、历史归档读取、Memory 视图比较 | 本地保留；任务、参数、Prompt、来源索引和小型预期答案保留 |
| 完整 `run.json` 及调用状态、HTTP 正文 | 历史恢复、实际调用校验 | 本地保留；最终结果、错误说明和小型解析输出保留 |
| 带逐次调用明细的 `analysis.json` | 费用重算与详细调用审计 | 本地保留；`final_metrics.json`、费用汇总和正式报告保留 |
| 生成的 Mock 归档与重复中间数据 | 离线实验重放 | 本地保留；构造脚本、人工夹具和测试代码保留 |
| 运行前状态、Git 状态、锁、原始归档清单及工作区补丁快照 | 辅助检查与运行控制 | 本地保留，运行锁不释放 |

归档范围按具体文件用途核对，不整体忽略任何实验目录，也不使用
通用 `*.json` 规则。只有辅助用途的展开输入副本被忽略，不能仅凭位于
`config/` 或 `results/` 判断文件用途。

### 历史读取与测试的边界

`diagnosis.load_diagnosis`、`preconditioner.load_preconditioner` 和
`editor.load_editor` 会沿 Grouping → Diagnosis → Preconditioner → Editor
读取完整历史链。它们需要本地原始归档；存在读取依赖不意味着这些归档必须进 Git。
`transport.py` 的请求复用与恢复，以及实验 `analyze.py` 的费用重算同样依赖本地材料。

`tests/skill_evolution/v23_3/helpers.py` 通过 P1R 的 `fixtures/sources.json`
读取既有 `artifacts/` 下的事实和 Memory，因此相关历史测试原本就不是仅靠
Git 文件即可复现。Memory compaction 的历史验证测试还读取 `cases/` 下生成的
payload 和消息；这些大体积副本作为本地测试数据保存在 artifacts 中，测试读取入口已适配。需要运行这些测试时，
应准备对应归档或按其原有构造脚本准备数据。本次没有修改测试或伪造替代输入。

### 2026-10-21 精确忽略整理的历史记录

第一轮后为 1,230 个未追踪文件、约 270 MB。第二轮新增精确忽略 411 份：
168 份展开输入、94 份调用记录、30 份 Mock 输出、9 份辅助清单、
5 份详细调用账本、102 份完整轨迹或原始响应、3 份历史 Memory 包。
剩余 819 个文件、约 5.6 MB，包含精确忽略规则本身；文件数随后续开发可能变化。

第一轮恢复可见的完整轨迹和 HTTP 原始响应现按新边界留在本地；
14 份重启实验的轻量 `audit.json` 仍显式保留，失败说明和报告也仍可见。
当时所有本地文件保持原位，磁盘占用不因忽略而减少；2026-10-27 的物理归档位置以实验导航为准。
本次没有执行模型、环境或历史测试，没有暂存、提交或切换分支。
