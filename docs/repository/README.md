# 仓库文件归属总清单

当前进度：[第 3 步方法实验整理](METHOD_EXPERIMENT_LAYOUT.md)已执行，统一入口见 [v01–v21](../../experiments/methods/README.md)。原清单 JSON 保留盘点时点。

> 后续状态：第 2 步已执行，见 [benchmark 整理记录](BENCHMARK_LAYOUT.md)。本页表格、JSON 清单与路径计划保留第 1 步的历史快照；Markdown 链接跟随迁移更新，当前路径以 [实际迁移映射](../../benchmarks/path-map.json) 为准。

盘点日期：2026-10-12。范围：整理计划第 1 步，**只盘点、确定归属和拟议路径，没有移动或修改既有文件**。

## 从这里查阅

- [实验与材料单元索引](EXPERIMENTS.md)：逐项列出现有位置、归属、配置/报告候选与目标位置。
- [结构化清单](inventory.json)：benchmark、方法、材料单元、依赖引用、缺口和 Git 状态。
- [旧路径到目标路径计划](path-plan.json)：可查询的精确文件/目录规则；**不是迁移脚本**。
- [本机逐文件明细（压缩 JSONL）](../../artifacts/repository_inventory/20261012-001/files.jsonl.gz)：每个文件的路径、大小、Git 状态、归属、匹配规则和拟议目标。该文件在 artifacts 内，被 Git 忽略。
- [本机目录清单（含空目录）](../../artifacts/repository_inventory/20261012-001/directories.jsonl.gz) 与 [校验记录](../../artifacts/repository_inventory/20261012-001/validation.json)：保留目录覆盖范围及本轮验收结果。
- [本机静态路径引用](../../artifacts/repository_inventory/20261012-001/references.json) 与 [本机 Python 导入关系](../../artifacts/repository_inventory/20261012-001/imports.json)：为后续迁移提供依赖证据。

## 盘点口径与完成范围

- 覆盖 **140,459 个文件**，合计约 12.65 GiB；包括被 Git 忽略的本地实验产物。
- 其中 2,599 个在当前工作区实际存在且已跟踪，186 个未跟踪，137,674 个被忽略。数字不包含本次新建清单。
- 登记 8 个带 VERSION.json 的 τ² edition、1 个独立 v5 原型系列、21 个方法版本标签、394 个材料单元，以及 741 条归属/路径规则。
- 材料单元不等于实验次数：一个实验的配置、运行副本、分析、重试、日志可能分成多行；同名目录没有被自动合并。
- 不展开 `.git/` 和 `external/` 中第三方仓库内部文件；只登记外部依赖入口。不跟随符号链接。`.env` 仅登记路径/大小，不读取内容。
- 包含空目录的扫描记录。`data/`、`experiments/runs/` 等没有实际文件的目录不计入文件统计。
- 已完成的文档迁移和占位清理造成的 tracked-missing 列表保留在 inventory.json 中，不能误判为本次删除。

## 各类文件归属

| 文件类型 | 归属 | Git 策略 | 本轮处理 |
|---|---|---|---|
| 可复用实现、环境和评分器 | `src/`；基准内历史实现需先梳理调用关系 | 跟踪 | 只登记拟议位置，不重构 |
| 自动化测试及固定样例 | `tests/` | 跟踪必要 fixture | 双重用途样例列为 hold |
| 构建、启动、分析命令 | `scripts/`，历史构造脚本暂随原 edition 保存 | 跟踪可复现入口 | 不执行模型或实验 |
| benchmark 任务、划分、环境定义与版本证据 | `benchmarks/<系列>/editions/<版本>/` | 跟踪 | τ² 系列保留；v5 规划同层级 |
| 实验配置、冻结清单、精选结果和报告 | `experiments/methods/<版本>/<实验ID>/` 或 `experiments/benchmarks/<版本>/<实验ID>/` | 跟踪 | 配置和结果按实验关联，原哈希不改 |
| 早期 POC / 外部方法基线 | `experiments/baselines/<实验ID>/` | 跟踪精选输入和结论 | 不把 POC 的 v01 当方法 v01 |
| 完整轨迹、请求响应、运行快照、重试与日志 | `artifacts/methods/...` / `artifacts/benchmarks/...` | 忽略 | 保留全量，不删失败记录 |
| 人工标注及 gold | `experiments/annotations/` | 跟踪人工标注；运行生成结果按原规则忽略 | 保留原位，属于共用评价输入 |
| 研究说明与方法文档 | `docs/`，补充研究叙事在 `research/` | 跟踪 | 保持已整理的目录 |
| Policy、Schema、Skill 种子 | `policies/`、`schemas/`、`skills/` | 跟踪 | 本轮保持原位 |
| 第三方源码与本地凭据 | `external/`、`.env` | 原忽略规则 | 本轮不整理其内部 |

## Benchmark 清单

下列任务数来自 VERSION.json，并核对当前列出的任务 JSON 长度；只做数量与存在性核对，不表示重新验证 benchmark 难度或有效性。

| 标识 | 谱系 | 任务数 | 当前入口 | 拟议位置 |
|---|---|---:|---|---|
| governed_v1_day27 | tau_governed | 116 | [benchmarks/tau2_governed_evolution/editions/governed_v1_day27](../../benchmarks/tau2_governed_evolution/editions/governed_v1_day27) | `benchmarks/tau2_governed_evolution/editions/governed_v1_day27` |
| governed_v2_day28 | tau_governed | 28 | [benchmarks/tau2_governed_evolution/editions/governed_v2_day28](../../benchmarks/tau2_governed_evolution/editions/governed_v2_day28) | `benchmarks/tau2_governed_evolution/editions/governed_v2_day28` |
| governed_v3_day29 | tau_governed | 20 | [benchmarks/tau2_governed_evolution/editions/governed_v3_day29](../../benchmarks/tau2_governed_evolution/editions/governed_v3_day29) | `benchmarks/tau2_governed_evolution/editions/governed_v3_day29` |
| phase_final_candidate_day35 | tau_phase | 73 | [benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35](../../benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35) | `benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35` |
| phase_v1_day30 | tau_phase | 54 | [benchmarks/tau2_governed_evolution/editions/phase_v1_day30](../../benchmarks/tau2_governed_evolution/editions/phase_v1_day30) | `benchmarks/tau2_governed_evolution/editions/phase_v1_day30` |
| phase_v2_day30 | tau_phase | 72 | [benchmarks/tau2_governed_evolution/editions/phase_v2_day30](../../benchmarks/tau2_governed_evolution/editions/phase_v2_day30) | `benchmarks/tau2_governed_evolution/editions/phase_v2_day30` |
| phase_v3_day34 | tau_phase | 32 | [benchmarks/tau2_governed_evolution/editions/phase_v3_day34](../../benchmarks/tau2_governed_evolution/editions/phase_v3_day34) | `benchmarks/tau2_governed_evolution/editions/phase_v3_day34` |
| phase_v4_day36 | tau_phase | 81 | [benchmarks/tau2_governed_evolution/editions/phase_v4_day36](../../benchmarks/tau2_governed_evolution/editions/phase_v4_day36) | `benchmarks/tau2_governed_evolution/editions/phase_v4_day36` |
| standalone/v5 | independent_prototypes | 未冻结 | [benchmarks/standalone/editions/v5](../../benchmarks/standalone/editions/v5) | `benchmarks/standalone/editions/v5` |

**v5 的内容不能整目录机械搬运：** `prototypes/scenarios.json` 是任务定义；`calibration/`、`learning/`、`decision_probe/` 中的协议与精选结果属于实验材料；`prototypes/engineering_results.json` 属于工程验证结果。path-plan.json 为这些内容提供优先于 v5 根目录规则的例外。

你提到的 [calibration/results.json](../../experiments/benchmarks/v5/calibration/results.json)，本次快照实际状态是**未跟踪、未忽略**。它包含逐任务分数与统计汇总，归属“基准校准实验结果”，候选位置为 `experiments/benchmarks/v5/calibration/results.json`，可以作为可复现证据纳入 Git；完整请求响应与轨迹则归 artifacts。不能仅凭文件名含 results 就统一忽略。

τ² 的 `shared/`、跨版本 `audits/` 和根层 `final_candidate/construction/` 均登记为跨版本基准材料，不擅自归到某一个 edition。其余构造/校准子项目逐项见实验索引。

## 方法版本与实验入口

版本标签只用于导航，不代表每个版本都存在独立正式实验。源码和测试计数采用方法相关命名规则；未标版本的共用模块另由根目录规则覆盖。Prompt v3.1、benchmark v4、方法 v18 分别处理。

| 方法 | 相关源码/测试/脚本 | 材料单元数 | 主要现有入口与归属依据 |
|---|---|---:|---|
| v01 | 4/5/0 | 3 | [autonomous_gse_v01](../../experiments/methods/v01/autonomous_gse_v01/config)；ST-WebAgentBench |
| v02 | 5/6/0 | 2 | [autonomous_gse_v02](../../experiments/methods/v02/autonomous_gse_v02/config)；ST-WebAgentBench |
| v03 | 5/6/0 | 2 | [autonomous_gse_v03](../../experiments/methods/v03/autonomous_gse_v03/config)；ST-WebAgentBench |
| v04 | 1/1/0 | 6 | [autonomous_gse_v04_seed_100](../../experiments/methods/v04/autonomous_gse_v04_seed_100/config)、[autonomous_gse_v04_seed_150](../../experiments/methods/v04/autonomous_gse_v04_seed_150/config)、[autonomous_gse_v04_seed_200](../../experiments/methods/v04/autonomous_gse_v04_seed_200/config)；ST-WebAgentBench |
| v05 | 3/1/0 | 2 | [autonomous_gse_v05](../../experiments/methods/v05/autonomous_gse_v05/config)；ST-WebAgentBench |
| v06 | 1/1/0 | 2 | [autonomous_gse_v06](../../experiments/methods/v06/autonomous_gse_v06/config)；ST-WebAgentBench |
| v07 | 3/2/0 | 2 | [autonomous_gse_v07](../../experiments/methods/v07/autonomous_gse_v07/config)；ST-WebAgentBench |
| v08 | 1/1/0 | 2 | [autonomous_gse_v08](../../experiments/methods/v08/autonomous_gse_v08/config)；ST-WebAgentBench |
| v09 | 1/1/0 | 2 | [autonomous_gse_v09](../../experiments/methods/v09/autonomous_gse_v09/config)；tau3 Airline/Retail |
| v10 | 1/1/0 | 2 | [autonomous_gse_v10](../../experiments/methods/v10/autonomous_gse_v10/config)；tau3 Airline/Retail |
| v11 | 8/1/0 | 2 | [autonomous_gse_v11](../../experiments/methods/v11/autonomous_gse_v11/config)；tau3 Airline/Retail |
| v12 | 7/1/0 | 2 | [autonomous_gse_v12](../../experiments/methods/v12/autonomous_gse_v12/config)；tau3 Airline/Retail |
| v13 | 8/2/8 | 2 | [autonomous_gse_v13](../../experiments/methods/v13/autonomous_gse_v13/config)；tau3 Airline/Retail |
| v14 | 17/9/0 | 5 | [autonomous_gse_v14](../../experiments/methods/v14/autonomous_gse_v14/config)、[autonomous_gse_v14_tge_v1](../../experiments/methods/v14/autonomous_gse_v14_tge_v1/config)；另有 TGE 与 Phase-A 分支 |
| v15 | 10/1/0 | 1 | [v15 Pilot](../../scripts/benchmarks/v2/experiments/benchmark_v2_v15_pilot_001)；位于 Phase-v2 edition 内 |
| v16 | 4/0/0 | 1 | [v16 one-step](../../src/benchmark_v3/final/experiments/benchmark_v16_one_step_001)；源码被 v17/v18 导入 |
| v17 | 21/16/7 | 22 | [冻结配置](../../experiments/methods/v17/v17_formal_001/config)；[运行与索引](../../artifacts/methods/v17) |
| v18 | 22/23/19 | 34 | [v4 正式冻结](../../experiments/methods/v18/v18_formal_003/config)；另有早期冻结、Diagnosis Pilot、Joint Admission |
| v19 | 50/30/17 | 72 | [运行参数](../../experiments/methods/v19/v19_run/config)；[运行树](../../artifacts/methods/v19)；[入口](../../scripts/runs/v19/run_v19.py) |
| v20 | 12/6/6 | 11 | [独立配置](../../experiments/methods/v20/v20_pilot_001/config/config.json)；引用 V18 formal_003 冻结输入；运行在 artifacts |
| v21 | 6/10/7 | 29 | [证据/Memory/语义验证文档](../methods/v21/README.md)；[闭环验证](../../artifacts/methods/v21/v21_closed_loop_001)；没有凭空补建 Campaign 配置 |

早期 SearchQA、Trace2Skill、Schema/Verifier 验证和 SuiteCRM POC 单独登记为 baseline，不强行挂靠某个 Autonomous GSE 方法版本。

## 路径计划如何使用

规则采用“精确文件优先，否则最长目录前缀”。子规则覆盖父规则，保留未匹配的相对后缀。新路径目前只是计划，**不应直接拿规则批量执行 mv**。

| 处理标记 | 含义 |
|---|---|
| `keep` | 归属已明确，保留原位置 |
| `proposed_move` | 已给出候选位置；仍须更新引用、冻结兼容和运行入口后才能执行 |
| `hold` | 归属已登记，但具体迁移须等待共享依赖、生命周期或证据核查 |
| `split_required` | 同目录包含配置、源码、精选结果和运行产物，或其中实现被外部导入；不能整目录搬走 |

被忽略的 τ² 运行 payload 有显式运行产物例外，详见 path-plan.json 的 runtime_override 与逐文件明细；`.py`、`.md`、`.sh`、`.yaml` 不因此被当作原始 payload。此规则也只用于规划，不是丢弃文件的依据。

## 已确定的关键依赖与待核对项

1. **V15/V16 不是缺失版本。** 两者有内嵌实验入口。V16 的 `benchmark_runtime.py` 被 V17/V18 复用，不能当作普通旧实验附件迁移。
2. **V20 复用 V18 冻结输入。** `experiments/methods/v20/v20_pilot_001/config/config.json` 的 `benchmark_freeze` 明确指向 `experiments/methods/v18/v18_formal_003/config`；记录为显式依赖，不直接重命名旧冻结包或更改哈希。
3. **Prompt 版本不等于方法版本。** `v18_diagnosis_v31_pilot_*` 归属方法 v18；`v31` 是其 Diagnosis 子版本。`formal_v18_v4.py` 归属方法 v18，v4 是 benchmark。
4. **`editions/benchmark/` 不是第九个正式 edition。** 当前只有空目录层级，没有文件或 VERSION.json，登记为待处理空壳。
5. **人工标签不是方法 v01。** `transfer_scope_v01` 与 `write_confirmation_v01` 归属共用标注输入；不按后缀混入方法 v01。
6. **旧结果有测试依赖。** Day4/Day5 的 common trajectories 被测试读取，列为双重用途 fixture，暂缓搬迁；迁移时同步调整测试和历史引用。
7. **运行目录中还有代码。** 原始产物树里的 `run.py`、`verify.py` 等会随材料单元列出，不因其位于 artifacts 就判断可以删除。
8. **36 个材料单元含外部模块导入的实现。** 已标记 split_required；完整静态导入边在本机审计明细中。静态扫描不保证覆盖动态 import、shell 命令和配置拼接。
9. **隐藏 pending / 恢复目录不能自动合并。** 比如 v19 formal 下的 `.pending-*` 目录及恢复快照，保留原名、原位置和独立身份，待运行生命周期确认。
10. **222 个材料单元未发现邻近配置候选，108 个未发现邻近报告/结果候选。** 其中包含日志、构造子模块和分析目录，不能据此宣布实验缺失或失败。逐项 gaps 列明扫描范围；可能需要从继承配置、入口源码或父运行查找。

“归属已覆盖”不表示所有实验都具备完整独立复现包。登记不清楚的实际运行绑定、未执行项和继承配置，比为它们编造统一配置更可靠。

## 验收与后续边界

- 全部扫描文件具有唯一生效的归属规则；拟议目标没有文件覆盖冲突。
- 8 个正式 edition 的任务文件存在，任务数与各自 VERSION.json 一致。
- 各清单源路径与链接指向当前材料；目标路径可以尚不存在。
- 本轮不执行实验、不调用模型、不改变 Git 索引、不移动文件，不修改 `.gitignore`、现有文档、配置、源码、冻结清单、实验结果或两份实验日志。
- 新增文件仅位于 `docs/repository/` 与被忽略的 `artifacts/repository_inventory/20261012-001/`。
- 后续第 2 步先处理 benchmark 的系列/版本层级；遇到 hold/split_required 必须先按依赖拆分，不能把本清单当作已授权的批量迁移脚本。

本机逐文件清单与静态引用扫描只记录整理时点，不会自动更新；实际迁移前应重新核对文件状态。

## 第四步：运行产物已归位

[整理记录](RUNTIME_LAYOUT.md) · [当前运行导航](../../experiments/methods/RUNTIME.md)。本目录 inventory/path-plan JSON 保留盘点时点；当前实际状态以各步迁移收据为准。

## 全项目旧入口已移除

[直接路径整理记录](CANONICAL_PATHS.md)：删除 190 个兼容链接，源码、配置和默认输出统一引用当前目录。

## 第五步已完成

[源码、命令和测试归类](CODE_LAYOUT.md)：方法实现按版本分包，脚本按用途分类，测试与实现对应，旧平铺入口已移除。
