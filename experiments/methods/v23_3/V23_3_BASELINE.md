# V23.3 P0：基线与接口

2026-10-20。本阶段只读核查与设计，不调用模型、不执行 Actor/ALFWorld/Replay，不实现正式 Preconditioner。

## 1. Git 冻结

| 项目 | 核查结果 |
|---|---|
| 当前分支 | `wyy/day52-tau-autonomous-gse-v23.2`；未切换、重置或提交 |
| 当前 HEAD | `daa2068498fe94f89d2be0c4e743fea1c63a8341`，`feat: preserve v23.2 research experiments` |
| 正式 V23 基线 | `08c442f202f05a25a0c30412ef89f8312df0c0f0`，`feat: add v23 method and experiment` |
| V23 与 HEAD 的差异 | 对 `src/skill_evolution/v23/`、`tests/skill_evolution/v23/`、`experiments/methods/v23/` 执行 `git diff 08c442f2 HEAD`，结果为空 |
| 开始时工作区 | 仅 `docs/04_EXPERIMENT_LOG.md` 已修改：0 行新增、16 行删除。属于既有变更，未触碰 |
| 新版本隔离 | `src/skill_evolution/v23_3/README.md` 与本目录七份文档；无代码复制、默认路由修改或历史覆盖 |

这里的“冻结”是以已有不可变 commit 和 Git Diff 明确基点，不创建额外哈希体系或声称整个工作区干净。V23.2 研究材料取当前 HEAD 的归档；运行原始数据另从已有 `artifacts/` 只读核验。Git 不管理的运行文件不冒称受 Git 保护。

## 2. 实际数据流

入口：[evolution.py](../../../src/skill_evolution/v23/evolution.py) 的 `run_round`。冻结 Parent、任务和 Active Memory → Parent 执行 → Grouping → Diagnosis → Preconditioner → 编译 Effective Plan → Editor → Candidate 执行 → 配对/Gate/Replay → Memory 提交 → 下一轮。

| 模块与函数 | 实际输入、输出及约束 | V23.3 决定 |
|---|---|---|
| [facts.py](../../../src/skill_evolution/v23/facts.py) `build_facts`；[grouping.py](../../../src/skill_evolution/v23/grouping.py) | facts 为 `parent/command_sets/runs`；Grouping 每组 `group_id/members/decision_problem/shared_basis/important_differences`，完整覆盖执行 | 原样复用，以 `decision_problem` 组织可比较行为，不新建分类器 |
| [diagnosis.py](../../../src/skill_evolution/v23/diagnosis.py) `diagnosis_input` | 当前全部 facts + grouping；没有 Memory，也不传私有 sources | 原样复用 |
| Diagnosis 输出 | `decision/reason/plan`；Plan=`goal/updates/checks`；Update=`id/text/basis`；Check=`id/update_ids/question`。Update basis 必含直接执行引用 | 保持接口；Goal 不锁实现是现有 Prompt 要求，不是程序保证 |
| [preconditioner.py](../../../src/skill_evolution/v23/preconditioner.py) `preconditioner_input` | `parent/plan/command_sets/runs/grouping/memory`；Plan 内 P 引用选整条执行，G 不反向展开全部成员；Diagnosis 顶层 reason 不进入输入 | P2 先复用选择规则和完整 Memory；不得声称含当前整个批次 |
| Preconditioner 输出 | `decision/reason/adjustments/checks`；Adjustment=`from/to/basis/reason`，to 项=`id/text` | 语义决策改为响应条件化；模型侧以现有 Unified Diff 代替完整 text，程序恢复原契约，见集成设计 |
| `compile_effective_plan` | 同时应用；Goal 不变；未消费 Update 原样保留；支持一对一、拆合、撤回；Checks 可保留或整表替换 | 原样调用，不重写编译器 |
| [editor.py](../../../src/skill_evolution/v23/editor.py) | 模型只读 `parent/plan=Effective Plan` 和 Actor 背景，输出 `patch/reason`；程序生成 Candidate 与 actual.diff | 模型接口、Prompt、补丁引擎与校验复用；磁盘加载入口需薄适配 |
| [replay.py](../../../src/skill_evolution/v23/replay.py) | `build_replay` 核对 Parent/Candidate、配对身份、执行协议等；输入含 actual.diff、有效 Plan、双方执行、pairs、Memory | 闭环保留；本次不运行 |
| [memory.py](../../../src/skill_evolution/v23/memory.py) | Replay 提议 `revises/knowledge/evidence`；Active entry=`id/knowledge/evidence`；view=`entries/sources` | 结构、提交和展开机制复用 |
| [gate.py](../../../src/skill_evolution/v23/gate.py) 与 `run_round` | Gate 决定 Parent 晋升；成功构建 Replay 后的 Memory 提交不以 ACCEPT 为唯一条件 | 保留混合反馈；RETAIN 不能抹掉局部收益，ACCEPT 不能证明每个子句正确 |

Effective Update 的 basis 是被消费 Original Update 的 basis 按原顺序去重继承；Adjustment 的历史 basis/reason **不会复制到 Effective Update**。Editor 不看历史解释，所以操作条件必须写进最终 text。

Memory `context/diff` 实际含 `parent/diff/execution_context`；`context/Pn`、`context/Qn` 含 `run/command_sets`。引用一步会展开该完整 run。仅选 Active entry 引用的来源，不是全部档案；也不自动补齐每条被引用 run 的另一侧配对。配对完整性应从现有 archive context 的 `pairs/pair_audit` 核查，不能只由 P/Q 编号推断。先冻结现有 view，缺配对时限制归因，不暗中增加输入。

## 3. 不能被“复用”掩盖的边界

- [execution_context.md](../../../src/skill_evolution/v23/execution_context.md)：Actor 只有当前观察、动作候选、最近两组行动前观察/动作；无全程访问集合、持久笔记或隐藏评估状态。分析器看全轨迹不等于 Actor 看全轨迹。
- Goal 中不合理的实现承诺不能通过 Update Patch 消除。局部兼容修正仍可做；若目标变换与 Goal 无法相容，须停在上游澄清/修订，不能悄悄删 Goal。
- 编译器只检结构、引用和来源；可执行性、证据支持及策略收益不是已有确定性保证。
- `editor.run_editor` 直接绑定 V23 `load_preconditioner`；它不能直接加载新 Patch 响应。详见 [集成设计](V23_3_PATCH_INTEGRATION.md)，不能以“Editor 无需改动”省略这一工作。

## 4. 研究证据入口及本次复核

| 证据 | 用途 |
|---|---|
| [P1-C 接口](../v23_2/v23_2_diagnosis_interface_audit_001/reports/P1C_INTERFACE_AUDIT.md)、[案例矩阵](../v23_2/v23_2_diagnosis_interface_audit_001/reports/P1C_CASE_MATRIX.md) | Goal 权限、证据选取、Original 与正式历史结果的区分 |
| [P2 Memory 审计](../v23_2/v23_2_memory_evidence_audit_001/reports/P2_MEMORY_AUDIT.md)、[R05 选取](../v23_2/v23_2_memory_evidence_audit_001/reports/P2_R05_EVIDENCE_SELECTION.md) | M6 混合响应；M10 类别/实例、未发现/不存在的混淆 |
| [P3-B 最终对照](../v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_UPDATE_COMPARISON.md)、[结论](../v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_DECISION.md) | 使用最终同 Prompt A_format/B_format，不能与旧 B 混用 |
| [P3-C1 边界](../v23_2/v23_2_preconditioner_commitment_analysis_001/reports/P3C1_TRANSFORMATION_BOUNDARY.md)、[机制建议](../v23_2/v23_2_preconditioner_commitment_analysis_001/reports/P3C1_MECHANISM_PROPOSAL.md) | 方向依据不自动授权出口变化；配套的反事实检验 |
| [P3-C2 实现](../v23_2/v23_2_commitment_anchored_001/reports/P3C2_IMPLEMENTATION_REPORT.md)、[测试](../v23_2/v23_2_commitment_anchored_001/reports/P3C2_TEST_REPORT.md) | 仅证明确定性原型；不移植 hash/role/depends_on/字节锚点协议 |

本次还直接读取 P1-B R04/R06 原始 diagnosis/input、R05 重试 diagnosis、正式 R04/R05/R06 Preconditioner input/result；复核 R04/R06 heat 行动前菜单、回源步骤，以及 M6/M10 sources 的 Diff 与关键执行。原始文件入口见[算法走查](V23_3_PRECONDITIONING_ALGORITHM.md)。没有重跑历史实验，也未用最终 Test 成绩选择方案。正式 V23 README 已含旧 Test 汇总，因此不把旧 Test 宣称为从未暴露的新验证数据。
