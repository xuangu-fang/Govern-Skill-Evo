# ALFWorld 全量核对结果与拟提交范围

2026-11-11，在分支 `wyy/day56-tau-autonomous-gse-v24` 对照当前 HEAD 和工作树核对。该分支比本地记录的上游领先 1 个提交，内容为 v24.2 试整理。以下数量均为相对当前 HEAD 的待处理路径，暂存区为空。

**v24 的跨版本依赖已通过隔离验证，并纳入拟提交主体。** 28 项实验或材料入口和 26 项评测结果位置全部可达。25 次完整评测各 134 题，v24.4 retained 有 116 份有效回执。逐步轨迹反馈的上游源码也已通过独立目录预检。

本机核对依据为两份工作簿及当前仓库导航。工作簿位于 Git 忽略的 `outputs/`。[整理盘点表](../../outputs/01a1c560-90a0-7620-9047-3f7313b7b194/ALFWorld%20整理盘点表.xlsx) · [旧路径到新路径映射表](../../outputs/01a1c560-90a0-7620-9047-3f7313b7b194/ALFWorld%20旧路径到新路径映射表.xlsx) · [自进化索引](../../experiments/methods/ALFWORLD.md) · [SkillAdam 索引](../../experiments/methods/skilladam/alfworld/README.md)

## 实验和评测

下表按工作簿中的实验或材料身份计数，准备配置、候选、暂停或停止的运行均按原状态登记。成功数来自本次离线归档读取，首测、复测、消融各用自己的归档和实际受测 Skill。

| 方法或配置 | 登记项 | 评测读回结果（每次完整评测 134 题） |
|---|---:|---|
| [v24](../../experiments/methods/v24/README.md) | 6 | 首测 121 |
| [v24.1](../../experiments/methods/v24_1/README.md) | 2 | 首测 121，复测 119 |
| [v24.2](../../experiments/methods/v24_2/README.md) | 1 | 首测 118，复测 115 |
| [v24.3](../../experiments/methods/v24_3/README.md) | 1 | 首测 109 |
| [v24.4](../../experiments/methods/v24_4/README.md) | 5 | progress_decision 首测 108，retained 有 116 份回执，无最终成绩 |
| [v24.5](../../experiments/methods/v24_5/README.md) | 1 | 首测 109 |
| [v24.6](../../experiments/methods/v24_6/README.md) | 1 | 首测 104，消融 118 |
| [v24.7](../../experiments/methods/v24_7/README.md) | 1 | 首测 115，复测 116，消融 123 |
| [v24.8](../../experiments/methods/v24_8/README.md) | 1 | 首测 115 |
| [v24.9](../../experiments/methods/v24_9/README.md) | 2 | general 首测 114，withdraw 首测 119，withdraw 复测 121 |
| [v24.10](../../experiments/methods/v24_10/README.md) | 1 | 首测 119，复测 121 |
| [SkillAdam · 共享 Actor](../../experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/README.md) | 1 | 首测 120 |
| [SkillAdam · 上游原生重试](../../experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/README.md) | 1 | 仅准备，配置预检通过 |
| [SkillAdam · 官方优化器路由](../../experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/README.md) | 1 | 仅准备，配置预检通过 |
| [SkillAdam · 双官方模型路由](../../experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/README.md) | 1 | 首测 117，复测 116 |
| [SkillAdam · 逐步轨迹反馈](../../experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/README.md) | 2 | 首次训练首测 120，首次训练复测 121，独立重训首测 110 |

自进化共 11 个版本、22 项登记；SkillAdam 共 5 种配置、6 项登记，其中逐步轨迹反馈有两次独立训练。v24.6 和 v24.7 的消融使用单独归档的受测文本。v24.9 的两次训练属于 general 系列；基础搜索专项只登记已找到的设计与入口。共享 Actor 的 smoke 只找到配置。

从两个方法索引沿当前导航能找到全部 28 个实验或材料 README 和全部 26 份精选评测记录。对 25 次完整评测，已用归档读取器复核结果，并逐份比对精选受测 Skill 与原始评测文本。另从逐题轨迹验收同一共用 Actor 的三组基线：No Skill 101/134、Initial Skill 108/134、SkillOpt Best 112/134。两种夜间调度目标的离线预检、原生重试及两种官方模型配置的三个离线预检均通过。[共用配置和运行入口](../../experiments/baselines/alfworld/alfworld_current_actor_20261025/README.md)

## 路径、引用与需要关注的例外

| 核对项 | 结果 |
|---|---|
| 241 项材料、77 项子路径、187 项精选或提取 | 旧材料集合与盘点表一致。按表中原拟定的新址逐项检查，分别有 237、72、182 项直接存在。其余 4 项材料与 5 项精选来自已取消的联合对照目录；5 项子路径实际保留在版本目录原位。 |
| 5 项保留原位 | v24 的 `alfworld_history_and_plan_v3_no_review_workers10_20261029_001/data/`，以及 v24.1 两个配置各自根目录的 `data/` 和 `manifest.sha256.json` 均能找到。配置读取器和历史计划仍有引用。 |
| 126 行既有依赖、706 行引用调整 | 126 行的依赖位置和对应引用文件均存在。706 行中，682 行的引用文件在原拟定新址，其余 24 行按实际目录或旧路径映射核对，仅 3 行的来源是已删除的同一份 10 月 30 日终报。目标端仍无实体的 4 行是两项准备配置的训练输出、v24.4 两项停止或暂停训练的预定测试输出。此项核对的是位置，动态行为仅以实际运行的离线入口为准。 |
| 运行时旧路径映射 | 相对 HEAD 新增 228 条，既有映射无删除或改写。全部 8,210 个旧键唯一且解析到登记目标；9 个目标未生成，分别是共享 Actor smoke、原生重试准备配置、官方优化器准备配置各自的输出及两份启动文件。 |
| Markdown 导航 | 对 117 份方法索引、实验 README、报告和相关说明的 884 处本地链接逐条检查。883 处可达，其中 285 处直接依赖本机 `artifacts/`。一处为 RC1 冻结说明保留的历史相对链接。 |

**RC1 历史链接无需改动冻结副本。** 候选 README 第 12 行的 `validation/tests.xml` 已随日志移至本机归档。现行候选导航已指向实际文件，可从那里查看。[候选导航](../../experiments/methods/v24/candidates/README.md) · [测试日志](../../artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/tests.xml)

10 月 25 日的两份汇总和 10 月 30 日的终报已在上批删除。三个旧文件均不在当前 HEAD，不产生待提交的 Git 删除。v24.1 和双官方模型 SkillAdam 的首测执行记录均处于未跟踪状态，已计入各自的拟提交范围。[运行记录归档与清理记录](ALFWORLD_RUN_RECORDS.md)

## 拟提交范围

**主体共 1,183 个路径**，含本报告。1,103 个为未跟踪文件，21 个为已跟踪修改，59 个为旧路径删除。同一个文件移动时，工作树可同时显示一条删除和一条未跟踪；数字按路径计。附件式明细在文末按目录列出每个文件名。

| 归属 | 待新增 | 已修改 | 旧路径删除 |
|---|---:|---:|---:|
| 自进化 v24 | 98 | 13 | 59 |
| 自进化 v24.1 | 187 | 0 | 0 |
| 自进化 v24.2 | 1 | 4 | 0 |
| 自进化 v24.3 | 24 | 0 | 0 |
| 自进化 v24.4 | 127 | 0 | 0 |
| 自进化 v24.5 | 16 | 0 | 0 |
| 自进化 v24.6 | 25 | 0 | 0 |
| 自进化 v24.7 | 26 | 0 | 0 |
| 自进化 v24.8 | 28 | 0 | 0 |
| 自进化 v24.9 | 52 | 0 | 0 |
| 自进化 v24.10 | 20 | 0 | 0 |
| v24 跨版本源码依赖 | 27 | 0 | 0 |
| SkillAdam | 420 | 0 | 0 |
| 共用 Actor 与调度 | 49 | 0 | 0 |
| 导航与路径 | 3 | 4 | 0 |

这份范围覆盖方法实现、测试、版本文档、配置、精选结果、历史调度及导航。v24 的 59 条删除都有对应的新文件，其中 55 份与 HEAD 旧文件逐字节相同。另 4 份是 smoke 报告、重放 README、`archive_io.py` 和 `run_replay.py`，迁移时同时更新了文档或代码。v24.2 试整理的既有提交已从统计中扣除，本轮仅列 5 个后续变更。

**主体建议按性质拆开审阅。** v24 的 `src/skill_evolution/v24/{benchmark,config,evolution,feedback_retry,verifier_retry}.py` 与相应测试包括 Python 3.9 兼容、关闭 review 和恢复策略等实验行为。其他版本也包含首次纳入 Git 的方法实现。提交时应把实现和测试作为方法改动说明，目录移动与导航可另作整理提交。

### v24 的跨版本源码依赖（已计入主体）

**交付方式**：按原包路径纳入以下 27 个 Python 文件。当前均未跟踪且可被 Git 收录。隔离导入 v24.2 至 v24.10 的 campaign 时，Python 实际加载了表内全部 27 个文件。v24 原版和 v24.1 的演化模块可独立导入。v24.5 复用 v24.4 实现，v24.9 分别检查搜索专项和 general 入口。

| 来源目录 | 文件 | ALFWorld 使用关系 |
|---|---|---|
| `src/skill_evolution/v27/` | `__init__.py`、`benchmark.py`、`facts.py`、`json_response.py`、`storage.py`、`transport.py` | v24.2 及后续方法的 campaign 或 stages 直接使用校验、JSON 解析和传输接口；包初始化及其余模块随导入加载。 |
| `src/skill_evolution/v27/contracts/` | `__init__.py`、`diagnosis.py`、`editor.py`、`grouping.py` | v24.2 的 method 和 v24.4 的 success_memory 直接用诊断字段；editor 也列在 v24.2 的配置契约里，grouping 为引用解析提供支持。 |
| `src/skill_evolution/v28_5/` | `__init__.py`、`diagnosis.py`、`editor.py`、`execution_input_view.py`、`execution_references.py`、`explicit_references.py`、`facts.py`、`preconditioner.py` | v24.2 method、v24.6 gate、v24.9 search_scope 和 general/pick_two 直接使用 editor 的候选编辑函数，其余文件随这条导入链加载。 |
| `src/skill_evolution/v28/` | `__init__.py`、`validation.py` | 由 v28.5 引用的 SearchQA 协议间接加载。 |
| `src/skill_evolution/v28/benchmarks/` | `__init__.py` | 上述协议的父包。 |
| `src/skill_evolution/v28/benchmarks/searchqa/` | `__init__.py`、`facts.py`、`protocol.py` | v28.5 的诊断和预条件模块导入协议及事实读取函数。 |
| `src/skill_evolution/v29_2/` | `__init__.py`、`execution_references.py`、`explicit_references.py` | v24.2 method 和 v24.6 gate 直接使用 execution_references；explicit_references 由它间接加载。 |

**仅使用分支文件。** 在临时目录复制当前已跟踪文件及拟提交文件，在本机已有 Python 环境中禁用网络并禁止读取原工作区。未挂载运行归档时，v24.2、.3、.4、.6、.7、.8、.9（搜索专项及 general）、.10 的 `prepare` 均成功；v24.5 用自己的冻结配置、四份 Prompt 及 v24.4 的 prepare 完成准备。v24.2 至 v24.9 现有离线测试连同新增回归用例共 64 项通过。v24.10 通过实际入口验证。临时目录没有 `docs/methods/v28_5/prompts/` 或 `src/skill_evolution/v28/benchmarks/searchqa/context/`，这些资源不列入本批。

**额外挂载历史归档。** 在上述临时目录的 `artifacts/methods/` 下接入 33 个历史训练和评测目录的独立副本。v24.2、v24.5 和 v24.10 的常规 Test 入口通过 `--validate-only` 检查各自的 134 题输入；v24 至 v24.10 的 19 次完整评测均逐题读回，与上表成功数一致，包括两次消融。v24.4 retained 的 116 份回执都能定位到轨迹。该阶段使用本机已有的 ALFWorld 数据和 Actor Python 环境，全程没有发起模型调用。

历史回执会记录生成它们的工作区绝对路径。只读入口现按回执中的仓库相对位置和现有迁移映射，在当前检出定位训练、消融来源和逐题轨迹；回归用例覆盖旧训练路径、归档路径和无关外部路径。[归档读取入口](../../scripts/runs/v24/read_archived_test.py) · [v24.2 及后续评测入口](../../scripts/runs/v24_2/run_v24_2_test.py) · [路径回归用例](../../tests/skill_evolution/v24_2/test_final_evaluation.py)

**逐步轨迹反馈的上游源码已归位。** 新增 284 个拟提交文件，含固定提交 `b6c9640` 的 281 个包文件、原版 LICENSE 和 NOTICE，以及来源说明。在独立目录排除历史对照工作区、本机外部仓库和本地运行归档后，训练入口的离线预检通过，加载的 44 个 SkillAdam 模块全部来自新目录。预检按当前仓库位置读取训练输入，并检查原清单记录的 Python 版本和依赖包版本。历史实验原件仍在原处。[上游来源](../../src/skill_evolution/skilladam/upstream/README.md) · [逐步反馈实现](../../src/skill_evolution/skilladam/alfworld/trajectory_feedback/backend.py)

### ALFWorld SkillOpt 的 6 个文件：本批纳入 1 个，另外 5 个归原生 SkillOpt

六个文件目前均未跟踪。v24 和 SkillAdam 的运行及归档读取入口均可独立使用。本批建议带上共用 Actor 的迁移导航。原生 SkillOpt 的正式启动器、Actor、传输模块及实验 manifest 均在拟提交主体之外，只提交原生项目和测试的部分文件无法在独立检出中使用它们。

| 文件 | 本次提交 | 核对依据 |
|---|---|---|
| [ALFWORLD_LEGACY_RETIREMENT.md](../methods/skillopt/ALFWORLD_LEGACY_RETIREMENT.md) | **纳入，归到共用 Actor 文档** | 相对搬迁前版本，调整了旧路径表的标题，新增指向共用 Actor 配置和三个运行入口现址的导航。链接目标随本批提交。 |
| [ALFWORLD_NATIVE.md](../methods/skillopt/ALFWORLD_NATIVE.md) | 留给原生 SkillOpt | 文中已更新双官方模型 SkillAdam 配置的读取位置；其余内容是原生 SkillOpt 方法和启动说明，适合随其可运行入口交付。 |
| [当前 project.py](../../src/skillopt_alfworld_native/project.py) | 留给原生 SkillOpt | 为 SkillOpt 读取迁移后的 SkillAdam 配置及首测，在检查旧实验清单时还要读取下面两份历史源码。 |
| [当前 test_skillopt_native.py](../../tests/adapters/alfworld/test_skillopt_native.py) | 留给原生 SkillOpt | 轨迹复用测试已从新首测目录取样；整份测试还需要原生 SkillOpt 的 Actor、传输实现、启动器和本机实验材料。 |
| [历史 project.py](../../experiments/baselines/skillopt_alfworld_native_best_only_20261030_001/configuration_revisions/before_native_retry_layout/src/skillopt_alfworld_native/project.py) | 与原生 SkillOpt 实现一同保留 | 与迁移前实现逐字节相同，旧实验清单登记了该实现；当前检查器按旧清单读取此副本。 |
| [历史 test_skillopt_native.py](../../experiments/baselines/skillopt_alfworld_native_best_only_20261030_001/configuration_revisions/before_native_retry_layout/tests/adapters/alfworld/test_skillopt_native.py) | 与原生 SkillOpt 测试一同保留 | 与迁移前测试逐字节相同，旧实验清单也登记了该测试；保留当时的路径属于其历史用途。 |

本机原生 SkillOpt 的离线预检通过，模型请求和环境执行均为 0；上述测试模块的 11 项测试全部通过。此次只更新提交范围。SpreadsheetBench 的 `scripts/runs/run_skillopt_spreadsheetbench_aligned.py` 已明确排除。

### 本地归档和范围外改动

- 完整训练与评测轨迹、请求响应、日志、锁与恢复材料位于 `artifacts/methods/v24*/`、`artifacts/methods/skilladam/alfworld/` 及 `artifacts/baselines/`。受查方法和两组基线的原始目录由 Git 忽略。四个实验拆分的 40 份原始文件也在这里。独立备份状态不在本次核对范围。
- 两份步骤 1～3 工作簿位于 `outputs/`，也由 Git 忽略；本报告及两份首测执行 JSON 均可正常纳入 Git。
- `.gitignore` 的当前修改删除 38 行 v23.3 规则；`docs/04_EXPERIMENT_LOG.md` 有 925 行新增、19 行删除，与整理前已有的实验叙述混合，两者不在主体内。全仓 `git diff --check` 报告该实验日志四处行尾空白。
- 工作区在生成本报告前显示 502,967 个未跟踪路径，主要积累于其他 campaign、评测、基线和比较目录。SearchQA、OfficeQA、SpreadsheetBench、v25 及以后方法的整包实验、演示稿、跨基准成本分析等均不属于本批。27 个跨版本源码依赖及已纳入的共用 Actor 文档均列入文末逐文件明细。Git 扫描还提示一个范围外 SpreadsheetBench 冻结工作区的 `.gitignore` 存在符号链接循环；该目录的文件数量不作为提交依据。

**建议的实施顺序**

1. 将已验证的 27 个跨版本源码文件随 v24 使用方一起审阅，按上表保留原路径。
2. 审阅方法实现与测试，再按自进化、SkillAdam、共用 Actor 与导航分别审阅归档改动；59 对旧路径与新文件一起处理。
3. 依照最终选中的路径核对 Git 差异，在独立检出中复验可随分支提供的配置和入口；历史评测读回另需挂载本地归档。

## 主体逐文件明细

每行以目录为前缀，同行列出的名称均为该目录的直接子文件。新增、修改、删除按核对时的工作树状态区分。

<details>
<summary>方法和共用实验材料（557 个路径）</summary>

| 目录 | 状态 | 文件 |
|---|---|---|
| `experiments/` | 修改 | `README.md` |
| `experiments/automations/alfworld_v24_1_skilladam_20261030_001/` | 新增 | `OFFICIAL_MODELS.md`、`automation.json`、`check_official_models.py`、`evaluate_skilladam.py`、`layout.py`、`official_models_checks.json`、`offline_checks.json`、`offline_checks.py`、`plan.json`、`pre_test_training_snapshot.json`、`recover_iteration0_patch.py`、`test_patch_recovery.py`、`test_start_condition.json`、`test_worker.py`、`training_worker.py`、`with_official_credentials.py` |
| `experiments/automations/alfworld_v24_1_skilladam_20261030_001/execution/` | 新增 | `final_monitor_report.json`、`monitor_state.json` |
| `experiments/automations/alfworld_v24_1_skilladam_20261030_001/revisions/before_native_retry_layout/` | 新增 | `evaluate_skilladam.py`、`recover_iteration0_patch.py`、`test_patch_recovery.py`、`with_official_credentials.py` |
| `experiments/automations/alfworld_v24_1_skilladam_20261030_001/revisions/before_official_models/` | 新增 | `automation.json`、`automation.toml`、`offline_checks.json`、`plan.json` |
| `experiments/baselines/alfworld/alfworld_current_actor_20261025/` | 新增 | `README.md`、`actor.json`、`initial_skill.md`、`manifest.json`、`noskill.json`、`offline_validation.json`、`skillopt.yaml`、`skillopt_optional_final_test.patch` |
| `experiments/baselines/alfworld/alfworld_current_actor_20261025/provenance/before_layout/experiments/baselines/alfworld_current_actor_20261025/` | 新增 | `README.md`、`skillopt.yaml` |
| `experiments/baselines/alfworld/alfworld_current_actor_20261025/provenance/before_layout/scripts/runs/` | 新增 | `alfworld_aligned_common.py`、`run_alfworld_aligned.py` |
| `experiments/baselines/alfworld/alfworld_current_actor_20261025/provenance/before_layout/tests/adapters/alfworld/` | 新增 | `test_aligned_baselines.py` |
| `experiments/baselines/alfworld/alfworld_current_actor_20261025/splits/test/` | 新增 | `items.json` |
| `experiments/baselines/alfworld/alfworld_current_actor_20261025/splits/train/` | 新增 | `items.json` |
| `experiments/baselines/alfworld/alfworld_current_actor_20261025/splits/val/` | 新增 | `items.json` |
| `experiments/baselines/overnight_20261025/` | 新增 | `manifest.json`、`schedule.json` |
| `experiments/methods/` | 新增 | `ALFWORLD.md` |
| `experiments/methods/` | 修改 | `README.md`、`canonical-paths.json` |
| `experiments/methods/skilladam/alfworld/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config/` | 新增 | `actor.json`、`actor_runtime.json`、`alignment.json`、`initial_skill.md`、`manifest.json`、`optimization_items.json`、`preserved_results.json`、`requirements.lock`、`skilladam.json`、`source_config.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config/configuration_revisions/001_official_workers/` | 新增 | `README.md`、`actor.json`、`actor_runtime.json`、`alignment.json`、`initial_skill.md`、`manifest.json`、`optimization_items.json`、`preflight.json`、`preserved_results.json`、`reaudit.json`、`requirements.lock`、`run_skilladam_alfworld_native_retry.py`、`skilladam.json`、`source_config.json`、`test_skilladam_native_retry.py`、`verification.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config/provenance/` | 新增 | `README.before-layout.md` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config/splits/test/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config/splits/train/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/config/splits/val/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_native_retry_20261029_001/results/` | 新增 | `official_settings_verification.json`、`preflight.json`、`reaudit.json`、`verification.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config/` | 新增 | `actor.json`、`actor_runtime.json`、`alignment.json`、`initial_skill.md`、`manifest.json`、`optimization_items.json`、`preserved_results.json`、`requirements.lock`、`skilladam.json`、`source_config.json`、`source_files.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config/splits/test/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config/splits/train/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config/splits/val/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/results/` | 新增 | `final_skill.md`、`preflight.json`、`training_summary.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/results/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134/` | 新增 | `execution.json`、`summary.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/results/skilladam_alfworld_retest134_20261107_231301/` | 新增 | `summary.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/config/` | 新增 | `actor.json`、`actor_runtime.json`、`alignment.json`、`initial_skill.md`、`launcher.diff`、`manifest.json`、`optimization_items.json`、`preserved_results.json`、`requirements.lock`、`skilladam.json`、`source_config.json`、`source_files.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/config/provenance/` | 新增 | `README.before-layout.md` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/config/splits/test/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/config/splits/train/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/config/splits/val/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001/results/` | 新增 | `preflight.json`、`verification.json` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/` | 新增 | `actor.json`、`initial_skill.md`、`manifest.json`、`optimization_items.json`、`pip_freeze.txt`、`skilladam.json`、`smoke.json` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/provenance/before_layout/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/provenance/before_layout/experiments/baselines/skilladam_alfworld_native_retry_20261029_001/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/provenance/before_layout/scripts/runs/` | 新增 | `launch_alfworld_overnight.py`、`run_skilladam_alfworld_native_retry.py`、`run_skilladam_alfworld_official_models.py`、`run_skilladam_alfworld_official_optimizer.py`、`run_skilladam_aligned.py` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/provenance/before_layout/tests/adapters/alfworld/` | 新增 | `test_skilladam_aligned.py`、`test_skilladam_native_retry.py`、`test_skilladam_official_optimizer.py` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/splits/test/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/splits/train/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/config/splits/val/` | 新增 | `items.json` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/results/skilladam_current_actor_20261025_test134/` | 新增 | `summary.json` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/config/` | 新增 | `baseline_reference.json` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/config/provenance/` | 新增 | `run_alfworld_skilladam_v24_9_feedback.py` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/results/skilladam_alfworld_v24_9_feedback_20261109_001507_retest_20261109_012307_test134/` | 新增 | `summary.json` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_20261109_001507/results/skilladam_alfworld_v24_9_feedback_20261109_001507_test134/` | 新增 | `summary.json` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/` | 新增 | `README.md` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/config/` | 新增 | `baseline_reference.json` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/skilladam/alfworld/trajectory_feedback/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648/results/skilladam_alfworld_v24_9_feedback_rerun_20261109_125648_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24/` | 修改 | `README.md` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_20261027_001/` | 新增 | `README.md` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_20261027_001/config/` | 新增 | `baseline_manifest.json`、`budget.json`、`campaign.json`、`initial_baseline_reference.json`、`preparation.json`、`runtime.json` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_20261027_001/data/` | 新增 | `batches.json`、`optimization_pool.json`、`test.json`、`train.json`、`val.json` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_20261027_001/reports/` | 新增 | `REPORT.md` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_20261027_001/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_20261027_001/results/alfworld_history_and_plan_v3_20261027_001_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/` | 新增 | `README.md` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/config/` | 新增 | `budget.json`、`campaign.json`、`initial_baseline_reference.json`、`runtime.json`、`source_config.json`、`source_contract.json` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/config/provenance/` | 新增 | `alignment.json`、`manifest.json`、`preserved_source_results.json` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/data/` | 新增 | `batches.json`、`optimization_pool.json`、`test.json`、`train.json`、`val.json` |
| `experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/results/` | 新增 | `preflight.json`、`validation_report.json`、`verification.json` |
| `experiments/methods/v24/alfworld_rc1_smoke_001/` | 修改 | `README.md` |
| `experiments/methods/v24/alfworld_rc1_smoke_001/` | 删除 | `REPORT.md`、`summary.json`、`task_comparison.csv` |
| `experiments/methods/v24/alfworld_rc1_smoke_001/reports/` | 新增 | `REPORT.md` |
| `experiments/methods/v24/alfworld_rc1_smoke_001/results/` | 新增 | `summary.json`、`task_comparison.csv` |
| `experiments/methods/v24/alfworld_verified_feedback_001/` | 修改 | `README.md` |
| `experiments/methods/v24/analysis/` | 修改 | `README.md` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/` | 删除 | `.gitignore`、`README.md`、`analysis.json`、`archive_io.py`、`completion.json`、`manifest.json`、`run_replay.py` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/` | 删除 | `baseline_output.json`、`summary.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/preconditioner/` | 删除 | `result.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/preconditioner/attempts/001/` | 删除 | `actual_diffs.json`、`attempt.json`、`effective_plan.json`、`http_status.json`、`parsed.json`、`preconditioner.json`、`raw_output.txt`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/` | 删除 | `baseline_output.json`、`summary.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/preconditioner/` | 删除 | `result.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/preconditioner/attempts/001/` | 删除 | `error.json`、`http_status.json`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/preconditioner/attempts/002/` | 删除 | `actual_diffs.json`、`attempt.json`、`effective_plan.json`、`http_status.json`、`parsed.json`、`preconditioner.json`、`raw_output.txt`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/prompts/` | 删除 | `preconditioner_prompt.md` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/` | 删除 | `baseline_output.json`、`summary.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/preconditioner/` | 删除 | `result.json` |
| `experiments/methods/v24/analysis/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/preconditioner/attempts/001/` | 删除 | `actual_diffs.json`、`attempt.json`、`effective_plan.json`、`http_status.json`、`parsed.json`、`preconditioner.json`、`raw_output.txt`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/` | 新增 | `.gitignore`、`README.md`、`archive_io.py`、`manifest.json`、`run_replay.py` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/` | 新增 | `baseline_output.json`、`summary.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/preconditioner/` | 新增 | `result.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R03/preconditioner/attempts/001/` | 新增 | `actual_diffs.json`、`attempt.json`、`effective_plan.json`、`http_status.json`、`parsed.json`、`preconditioner.json`、`raw_output.txt`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/` | 新增 | `baseline_output.json`、`summary.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/preconditioner/` | 新增 | `result.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/preconditioner/attempts/001/` | 新增 | `error.json`、`http_status.json`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/inherited_v23_5_R06/preconditioner/attempts/002/` | 新增 | `actual_diffs.json`、`attempt.json`、`effective_plan.json`、`http_status.json`、`parsed.json`、`preconditioner.json`、`raw_output.txt`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/prompts/` | 新增 | `preconditioner_prompt.md` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/results/` | 新增 | `analysis.json`、`completion.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/` | 新增 | `baseline_output.json`、`summary.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/preconditioner/` | 新增 | `result.json` |
| `experiments/methods/v24/preconditioner_history_and_plan_v3_20261026_231243/v24_smoke_R01/preconditioner/attempts/001/` | 新增 | `actual_diffs.json`、`attempt.json`、`effective_plan.json`、`http_status.json`、`parsed.json`、`preconditioner.json`、`raw_output.txt`、`request_context.json`、`request_started.json`、`response.json`、`validation.json` |
| `experiments/methods/v24_1/` | 新增 | `README.md` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/` | 新增 | `README.md`、`manifest.sha256.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/config/` | 新增 | `budget.json`、`campaign.json`、`initial_baseline_reference.json`、`runtime.json`、`source_config.json`、`source_contract.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/config/provenance/` | 新增 | `alignment.json`、`implementation_changes.patch`、`preservation.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/data/` | 新增 | `batches.json`、`optimization_pool.json`、`test.json`、`train.json`、`val.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/results/` | 新增 | `acceptance.json`、`implementation_audit.json`、`preflight.json`、`recheck.json`、`verification_report.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/` | 新增 | `README.md`、`manifest.sha256.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/config/` | 新增 | `budget.json`、`campaign.json`、`initial_baseline_reference.json`、`runtime.json`、`source_config.json`、`source_contract.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/config/provenance/` | 新增 | `alignment.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/data/` | 新增 | `batches.json`、`optimization_pool.json`、`test.json`、`train.json`、`val.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/reports/` | 新增 | `REPORT.md` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134/` | 新增 | `execution.json`、`summary.json` |
| `experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/v24_1_alfworld_retest134_20261107_231217/` | 新增 | `summary.json` |
| `experiments/methods/v24_1/v24_1_cost_estimate_20261106/results/` | 新增 | `v24_1_cost_estimate_20261106.json` |
| `experiments/methods/v24_1/v24_1_recheck_20261030_001/results/` | 新增 | `report.json` |
| `experiments/methods/v24_10/` | 新增 | `README.md`、`layout-change.json` |
| `experiments/methods/v24_10/v24_10_alfworld_20261109_235409/` | 新增 | `README.md` |
| `experiments/methods/v24_10/v24_10_alfworld_20261109_235409/config/` | 新增 | `config.json`、`contract.json`、`runtime.json` |
| `experiments/methods/v24_10/v24_10_alfworld_20261109_235409/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_10/v24_10_alfworld_20261109_235409/results/v24_10_alfworld_20261109_235409_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_10/v24_10_alfworld_20261109_235409/results/v24_10_alfworld_20261109_235409_test134_retest_20261110_011255/` | 新增 | `summary.json` |
| `experiments/methods/v24_2/` | 新增 | `README.md` |
| `experiments/methods/v24_2/` | 修改 | `layout-change.json` |
| `experiments/methods/v24_3/` | 新增 | `README.md`、`layout-change.json` |
| `experiments/methods/v24_3/v24_3_alfworld_20261106_223712/` | 新增 | `README.md` |
| `experiments/methods/v24_3/v24_3_alfworld_20261106_223712/config/` | 新增 | `config.json`、`contract.json`、`runtime.json` |
| `experiments/methods/v24_3/v24_3_alfworld_20261106_223712/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_3/v24_3_alfworld_20261106_223712/results/v24_3_alfworld_20261106_223712_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_222610/` | 新增 | `README.md` |
| `experiments/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_222610/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_222610/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_223146/` | 新增 | `README.md` |
| `experiments/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_223146/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_3/v24_3_alfworld_r02_quickcheck_20261106_223146/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/` | 新增 | `README.md`、`layout-change.json` |
| `experiments/methods/v24_4/v24_4_alfworld_20261107_013300/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_20261107_013300/config/` | 新增 | `config.json`、`contract.json`、`runtime.json` |
| `experiments/methods/v24_4/v24_4_alfworld_20261107_013300/results/` | 新增 | `training_summary.json` |
| `experiments/methods/v24_4/v24_4_alfworld_keep_after_regression_20261107_172806/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_keep_after_regression_20261107_172806/config/` | 新增 | `config.json`、`runtime.json` |
| `experiments/methods/v24_4/v24_4_alfworld_keep_after_regression_20261107_172806/results/` | 新增 | `training_summary.json` |
| `experiments/methods/v24_4/v24_4_alfworld_keep_after_regression_repeat_20261107_174810/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_keep_after_regression_repeat_20261107_174810/config/` | 新增 | `config.json`、`runtime.json` |
| `experiments/methods/v24_4/v24_4_alfworld_keep_after_regression_repeat_20261107_174810/results/` | 新增 | `training_summary.json` |
| `experiments/methods/v24_4/v24_4_alfworld_progress_decision_20261107_202453/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_progress_decision_20261107_202453/config/` | 新增 | `config.json`、`runtime.json` |
| `experiments/methods/v24_4/v24_4_alfworld_progress_decision_20261107_202453/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_4/v24_4_alfworld_progress_decision_20261107_202453/results/v24_4_alfworld_progress_decision_20261107_202453_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r01_success_memory_20261107_025441/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_choice_check_20261107_031328/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_choice_check_20261107_031328/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_choice_check_20261107_031328/reports/` | 新增 | `COMPARISON.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_choice_check_20261107_031328/results/` | 新增 | `gate.json`、`pair_audit.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_memory_control_20261107_030544/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_memory_control_20261107_030544/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_memory_control_20261107_030544/reports/` | 新增 | `COMPARISON.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_memory_control_20261107_030544/results/` | 新增 | `gate.json`、`pair_audit.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_preconditioner_20261107_022149/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_preconditioner_20261107_022149/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_preconditioner_20261107_022149/reports/` | 新增 | `COMPARISON.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_preconditioner_20261107_022149/results/` | 新增 | `gate.json`、`pair_audit.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_quickcheck_20261107_021324/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_quickcheck_20261107_021324/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_quickcheck_20261107_021324/reports/` | 新增 | `COMPARISON.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_quickcheck_20261107_021324/results/` | 新增 | `gate.json`、`pair_audit.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_search_type_20261107_022906/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_search_type_20261107_022906/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_search_type_20261107_022906/reports/` | 新增 | `COMPARISON.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r02_search_type_20261107_022906/results/` | 新增 | `gate.json`、`pair_audit.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_gain_regression_20261107_1637/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_gain_regression_20261107_1637/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/reports/` | 新增 | `CANDIDATE_REVIEW.md`、`REVIEW.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/results/` | 新增 | `gate.json`、`pair_audit.json`、`r05_comparison.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_quickcheck_20261107_012031/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_quickcheck_20261107_012031/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_quickcheck_20261107_012031/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_quickcheck_20261107_012534/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_quickcheck_20261107_012534/config/` | 新增 | `provenance.json` |
| `experiments/methods/v24_4/v24_4_alfworld_r05_quickcheck_20261107_012534/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_alfworld_retained_20261107_135247/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_retained_20261107_135247/config/` | 新增 | `config.json`、`runtime.json` |
| `experiments/methods/v24_4/v24_4_alfworld_retained_20261107_135247/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_4/v24_4_alfworld_retained_20261107_135247/results/v24_4_alfworld_retained_20261107_135247_test134/` | 新增 | `progress.json` |
| `experiments/methods/v24_4/v24_4_alfworld_test11_search_audit/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_alfworld_test11_search_audit/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_decision_evidence_checks/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_decision_evidence_checks/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_parent_choice_checks/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_parent_choice_checks/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_r02_p8_editor_trigger_quickcheck/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_r02_p8_editor_trigger_quickcheck/results/` | 新增 | `gate.json`、`pair_audit.json`、`r02_comparison.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_r02_repeat_add_p8_20261107_1815/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_r02_repeat_add_p8_20261107_1815/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_r02_repeat_add_p8_20261107_1815/results/` | 新增 | `gate.json`、`pair_audit.json`、`r02_comparison.json`、`selected.md` |
| `experiments/methods/v24_4/v24_4_r04_r05_search_pair_20261107_213553/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_r04_r05_search_pair_20261107_213553/config/` | 新增 | `manifest.json` |
| `experiments/methods/v24_4/v24_4_r05_progress_decision/` | 新增 | `README.md` |
| `experiments/methods/v24_4/v24_4_r05_progress_decision/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_4/v24_4_r05_success_priority/` | 新增 | `README.md` |
| `experiments/methods/v24_5/` | 新增 | `README.md` |
| `experiments/methods/v24_5/v24_5_alfworld_20261107_220520/` | 新增 | `README.md` |
| `experiments/methods/v24_5/v24_5_alfworld_20261107_220520/config/` | 新增 | `config.json`、`runtime.json` |
| `experiments/methods/v24_5/v24_5_alfworld_20261107_220520/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_5/v24_5_alfworld_20261107_220520/results/v24_5_alfworld_20261107_220520_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_5/v24_5_r05_original_effective/` | 新增 | `README.md` |
| `experiments/methods/v24_5/v24_5_r05_original_effective/reports/` | 新增 | `REVIEW.md` |
| `experiments/methods/v24_6/` | 新增 | `README.md`、`layout-change.json` |
| `experiments/methods/v24_6/v24_6_alfworld_20261108_000609/` | 新增 | `README.md` |
| `experiments/methods/v24_6/v24_6_alfworld_20261108_000609/config/` | 新增 | `config.json`、`contract.json`、`runtime.json` |
| `experiments/methods/v24_6/v24_6_alfworld_20261108_000609/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_6/v24_6_alfworld_20261108_000609/results/v24_6_alfworld_20261108_000609_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_6/v24_6_alfworld_20261108_000609/results/v24_6_alfworld_v24_1_search_swap_test134_20261108_012501/` | 新增 | `evaluated_skill.md`、`summary.json` |
| `experiments/methods/v24_6/v24_6_offline_verification/results/` | 新增 | `offline.json` |
| `experiments/methods/v24_7/` | 新增 | `README.md`、`layout-change.json` |
| `experiments/methods/v24_7/v24_7_alfworld_20261108_020254/` | 新增 | `README.md` |
| `experiments/methods/v24_7/v24_7_alfworld_20261108_020254/config/` | 新增 | `config.json`、`contract.json`、`runtime.json` |
| `experiments/methods/v24_7/v24_7_alfworld_20261108_020254/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_7/v24_7_alfworld_20261108_020254/results/v24_7_alfworld_20261108_020254_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_7/v24_7_alfworld_20261108_020254/results/v24_7_alfworld_20261108_020254_test134_retest_20261108_032120/` | 新增 | `summary.json` |
| `experiments/methods/v24_7/v24_7_alfworld_20261108_020254/results/v24_7_search_continuation_only_test134_20261108_102755/` | 新增 | `evaluated_skill.md`、`summary.json` |
| `experiments/methods/v24_7/v24_7_offline_verification/results/` | 新增 | `offline.json` |
| `experiments/methods/v24_8/` | 新增 | `README.md`、`layout-change.json` |
| `experiments/methods/v24_8/v24_8_alfworld_20261108_034407/` | 新增 | `README.md` |
| `experiments/methods/v24_8/v24_8_alfworld_20261108_034407/config/` | 新增 | `config.json`、`contract.json`、`runtime.json` |
| `experiments/methods/v24_8/v24_8_alfworld_20261108_034407/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_8/v24_8_alfworld_20261108_034407/results/v24_8_alfworld_20261108_034407_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_8/v24_8_search_continuation_01/` | 新增 | `README.md` |
| `experiments/methods/v24_8/v24_8_search_continuation_02/` | 新增 | `README.md` |
| `experiments/methods/v24_8/v24_8_search_continuation_03/` | 新增 | `README.md` |
| `experiments/methods/v24_8/v24_8_search_continuation_04/` | 新增 | `README.md` |
| `experiments/methods/v24_8/v24_8_search_continuation_05/` | 新增 | `README.md` |
| `experiments/methods/v24_9/` | 新增 | `README.md`、`layout-change.json` |
| `experiments/methods/v24_9/v24_9_general_alfworld_20261108_125258/` | 新增 | `README.md` |
| `experiments/methods/v24_9/v24_9_general_alfworld_20261108_125258/config/` | 新增 | `config.json`、`contract.json`、`preconditioner.md`、`runtime.json` |
| `experiments/methods/v24_9/v24_9_general_alfworld_20261108_125258/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_9/v24_9_general_alfworld_20261108_125258/results/v24_9_general_alfworld_20261108_125258_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_9/v24_9_general_archive_01/` | 新增 | `README.md` |
| `experiments/methods/v24_9/v24_9_general_archive_01/config/` | 新增 | `sources.json` |
| `experiments/methods/v24_9/v24_9_general_archive_01/reports/` | 新增 | `REPORT.md` |
| `experiments/methods/v24_9/v24_9_general_archive_01/results/` | 新增 | `learning_gate.json`、`paired_results.json`、`window_results.json` |
| `experiments/methods/v24_9/v24_9_general_withdraw_alfworld_20261108_141622/` | 新增 | `README.md` |
| `experiments/methods/v24_9/v24_9_general_withdraw_alfworld_20261108_141622/config/` | 新增 | `config.json`、`contract.json`、`preconditioner.md`、`runtime.json` |
| `experiments/methods/v24_9/v24_9_general_withdraw_alfworld_20261108_141622/results/` | 新增 | `final_skill.md`、`training_summary.json` |
| `experiments/methods/v24_9/v24_9_general_withdraw_alfworld_20261108_141622/results/v24_9_general_withdraw_alfworld_20261108_141622_test134/` | 新增 | `summary.json` |
| `experiments/methods/v24_9/v24_9_general_withdraw_alfworld_20261108_141622/results/v24_9_general_withdraw_alfworld_20261108_141622_test134_retest_20261108_152517/` | 新增 | `summary.json` |

</details>

<details>
<summary>源码（520 个路径）</summary>

| 目录 | 状态 | 文件 |
|---|---|---|
| `src/skill_evolution/skilladam/alfworld/` | 新增 | `archive.py` |
| `src/skill_evolution/skilladam/alfworld/native_retry/` | 新增 | `archive.py`、`backend.py`、`layout.py`、`official_models.py`、`official_optimizer.py` |
| `src/skill_evolution/skilladam/alfworld/shared_actor/` | 新增 | `archive.py`、`backend.py`、`paths.py` |
| `src/skill_evolution/skilladam/alfworld/trajectory_feedback/` | 新增 | `archive.py`、`backend.py` |
| `src/skill_evolution/skilladam/upstream/` | 新增 | `LICENSE`、`NOTICE`、`README.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/` | 新增 | `__init__.py`、`__main__.py`、`cli.py`、`codex_product_mcp.py`、`codex_review_app.py`、`environment.py`、`product_cli.py`、`product_mcp.py`、`product_review_mcp.py`、`registry.py`、`review_app.py`、`types.py`、`usage.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/` | 新增 | `__init__.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/` | 新增 | `manifest.json` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/alfworld/` | 新增 | `best_skill.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/deepplanning/` | 新增 | `shopping_level1.md`、`shopping_level2.md`、`shopping_level3.md`、`travel_en.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/docvqa/` | 新增 | `best_skill.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/lmb/` | 新增 | `best_skill.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/officeqa/` | 新增 | `best_skill.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/searchqa/` | 新增 | `best_skill.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/artifacts/skills/spreadsheetbench/` | 新增 | `best_skill.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/backends/` | 新增 | `__init__.py`、`deepplanning_bridge.py`、`deepplanning_official.py`、`openai_compatible.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/` | 新增 | `__init__.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/` | 新增 | `LICENSE`、`NOTICE`、`__init__.py`、`contracts.py`、`gate.py`、`reflection_trace.py`、`report.py`、`runner.py`、`scheduler.py`、`slow_update.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/prompts/` | 新增 | `memory.md`、`merge.md`、`reflection.md`、`select.md`、`slow_update.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/prompts/benchmarks/alfworld/` | 新增 | `analyst_error.md`、`analyst_success.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/prompts/benchmarks/docvqa/` | 新增 | `analyst_error.md`、`analyst_success.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/prompts/benchmarks/lmb/` | 新增 | `analyst_error.md`、`analyst_success.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/prompts/benchmarks/officeqa/` | 新增 | `analyst_error.md`、`analyst_success.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/prompts/benchmarks/searchqa/` | 新增 | `analyst_error.md`、`analyst_success.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/baselines/skillopt/prompts/benchmarks/spreadsheetbench/` | 新增 | `analyst_error.md`、`analyst_success.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/` | 新增 | `__init__.py`、`base.py`、`registry.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/alfworld/` | 新增 | `__init__.py`、`adapter.py`、`evaluation.py`、`gate.py`、`manifest.py`、`requirements.txt`、`rollout.py`、`runtime.py`、`stage0.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/alfworld/prompts/` | 新增 | `failure_types.md`、`iteration_example.md`、`metric_interpretation.md`、`skill_writing_policy.md`、`stage0_example.md`、`stage0_extra_section.md`、`stage0_system_prompt.md`、`success_types.md`、`trajectory_compress_example.md`、`trajectory_compress_system.md`、`trajectory_label_format.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/deepplanning/` | 新增 | `__init__.py`、`adapter.py`、`evaluation.py`、`gate.py`、`manifest.py`、`requirements.txt`、`rollout.py`、`runtime.py`、`stage0.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/deepplanning/prompts/` | 新增 | `failure_types.md`、`iteration_example.md`、`iteration_example_v2.md`、`iteration_system_prompt_v2_r2_baseline.md`、`metric_interpretation.md`、`metric_interpretation_shopping_level1.md`、`metric_interpretation_shopping_level2.md`、`metric_interpretation_shopping_level3.md`、`metric_interpretation_travel_en.md`、`skill_writing_policy.md`、`skill_writing_policy_v2_r2_baseline.md`、`stage0_example.md`、`stage0_extra_section.md`、`success_types.md`、`trajectory_compress_example_shopping.md`、`trajectory_compress_example_travel.md`、`trajectory_label_format.md`、`trajectory_label_format_shopping_level1.md`、`trajectory_label_format_shopping_level2.md`、`trajectory_label_format_shopping_level3.md`、`trajectory_label_format_travel_en.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/docvqa/` | 新增 | `__init__.py`、`adapter.py`、`evaluation.py`、`gate.py`、`manifest.py`、`requirements.txt`、`rollout.py`、`stage0.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/docvqa/prompts/` | 新增 | `failure_types.md`、`iteration_example.md`、`metric_interpretation.md`、`rollout_system.md`、`skill_writing_policy.md`、`stage0_example.md`、`stage0_extra_section.md`、`stage0_system_prompt.md`、`success_types.md`、`trajectory_label_format.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/lmb/` | 新增 | `__init__.py`、`adapter.py`、`choices.py`、`evaluation.py`、`gate.py`、`manifest.py`、`requirements.txt`、`rollout.py`、`stage0.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/lmb/prompts/` | 新增 | `failure_types.md`、`iteration_example.md`、`metric_interpretation.md`、`skill_writing_policy.md`、`stage0_example.md`、`stage0_extra_section.md`、`success_types.md`、`trajectory_label_format.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/officeqa/` | 新增 | `__init__.py`、`adapter.py`、`evaluation.py`、`gate.py`、`manifest.py`、`requirements.txt`、`rollout.py`、`stage0.py`、`tool_runtime.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/officeqa/prompts/` | 新增 | `failure_types.md`、`iteration_example.md`、`metric_interpretation.md`、`skill_writing_policy.md`、`stage0_example.md`、`stage0_extra_section.md`、`stage0_system_prompt.md`、`success_types.md`、`trajectory_compress_example.md`、`trajectory_compress_system.md`、`trajectory_label_format.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/searchqa/` | 新增 | `__init__.py`、`adapter.py`、`evaluation.py`、`gate.py`、`manifest.py`、`requirements.txt`、`rollout.py`、`stage0.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/searchqa/prompts/` | 新增 | `failure_types.md`、`iteration_example.md`、`metric_interpretation.md`、`stage0_example.md`、`stage0_extra_section.md`、`success_types.md`、`trajectory_label_format.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/spreadsheetbench/` | 新增 | `__init__.py`、`adapter.py`、`evaluation.py`、`gate.py`、`manifest.py`、`requirements.txt`、`rollout.py`、`runtime.py`、`stage0.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/benchmarks/spreadsheetbench/prompts/` | 新增 | `failure_types.md`、`iteration_example.md`、`metric_interpretation.md`、`skill_writing_policy.md`、`stage0_example.md`、`stage0_extra_section.md`、`stage0_system_prompt.md`、`success_types.md`、`trajectory_compress_example.md`、`trajectory_compress_system.md`、`trajectory_label_format.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/core/` | 新增 | `__init__.py`、`acceptance_gate.py`、`case_sampler.py`、`diff_apply.py`、`edit_budget.py`、`feedback_loop.py`、`momentum.py`、`stage0.py`、`trajectory_condenser.py`、`type_taxonomy.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/core/prompts/` | 新增 | `iteration_system_prompt.md`、`momentum_update_system.md`、`skill_writing_policy.md`、`stage0_example_default.md`、`stage0_system_prompt.md`、`stage0_user_prompt.md`、`trajectory_compress_system.md` |
| `src/skill_evolution/skilladam/upstream/skilladam/cost/` | 新增 | `__init__.py`、`ledger.py`、`pricing.py`、`report.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/data/` | 新增 | `__init__.py`、`download.py`、`materialize.py`、`prepare.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/data/profiles/` | 新增 | `__init__.py`、`alfworld_main_results.json`、`docvqa_main_results.json`、`lmb_main_results.json`、`officeqa_main_results.json`、`searchqa_main_results.json`、`spreadsheetbench_main_results.json` |
| `src/skill_evolution/skilladam/upstream/skilladam/execution/` | 新增 | `__init__.py`、`aggregation.py`、`backend.py`、`contracts.py`、`evaluate.py`、`fixture_backend.py`、`planning.py`、`selection.py`、`skills.py`、`store.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/experiments/` | 新增 | `__init__.py`、`api_preflight.py`、`api_smoke.py`、`main_results.json`、`main_results.py`、`planning.py`、`prompt_resources.json`、`prompt_resources.py`、`result_verification.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/methods/` | 新增 | `__init__.py`、`skilladam.py`、`skilladam_prompts.py`、`skillopt.py`、`skillopt_prompts.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/product/` | 新增 | `__init__.py`、`cli_model.py`、`commands.py`、`evaluation.py`、`evaluation_planning.py`、`evaluation_semantics.py`、`evaluators.py`、`feedback.py`、`history_adapters.py`、`history_discovery.py`、`jobs.py`、`model.py`、`models.py`、`patch_review.py`、`project.py`、`runtime.py`、`service.py`、`session_codec.py`、`session_store.py`、`task_manifest.py`、`tasking.py`、`workflow.py`、`workflow_support.py` |
| `src/skill_evolution/skilladam/upstream/skilladam/ui/` | 新增 | `__init__.py`、`codex_review.html` |
| `src/skill_evolution/v24/` | 修改 | `README.md`、`benchmark.py`、`config.py`、`evolution.py`、`feedback_retry.py` |
| `src/skill_evolution/v24/` | 新增 | `verifier_retry.py` |
| `src/skill_evolution/v24_1/` | 新增 | `README.md`、`__init__.py`、`__main__.py`、`baseline.py`、`benchmark.py`、`cli.py`、`config.py`、`diagnosis.py`、`editor.py`、`evaluation.py`、`evolution.py`、`facts.py`、`feedback_retry.py`、`grouping.py`、`json_response.py`、`knowledge_evidence.py`、`knowledge_repair.py`、`knowledge_review.py`、`knowledge_verifier.py`、`memory_view.py`、`output_feedback.py`、`plan.py`、`preconditioner.py`、`prompts.py`、`replay.py`、`replay_view.py`、`resources.py`、`storage.py`、`unnumbered_patch.py`、`update_patch.py`、`verifier_retry.py` |
| `src/skill_evolution/v24_1/benchmarks/` | 新增 | `__init__.py` |
| `src/skill_evolution/v24_1/benchmarks/alfworld/` | 新增 | `__init__.py`、`adapter.py`、`context.py`、`evaluation.py`、`evidence_contracts_diagnosis.py`、`evidence_contracts_grouping.py`、`evidence_contracts_memory.py`、`evidence_contracts_memory_view.py`、`evidence_contracts_preconditioner.py`、`evidence_contracts_replay.py`、`evidence_contracts_replay_view.py`、`evidence_knowledge_evidence.py`、`evidence_registry.json`、`evidence_replay.py`、`evidence_replay_view.py`、`facts.py`、`gate.py`、`runtime.py` |
| `src/skill_evolution/v24_1/benchmarks/alfworld/actor/` | 新增 | `__init__.py`、`actor_prompt.py`、`eval_test.py`、`response_archive.py`、`run_task.py`、`run_task_skill.py`、`run_task_upstream.py`、`skill_runtime.py`、`verify_skill_run.py`、`verify_upstream_run.py` |
| `src/skill_evolution/v24_1/benchmarks/alfworld/prompts/v23/` | 新增 | `diagnosis_prompt.md`、`editor_prompt.md`、`execution_context.md`、`grouping_prompt.md`、`preconditioner_prompt.md`、`replay_prompt.md` |
| `src/skill_evolution/v24_1/benchmarks/alfworld/prompts/v23_3/` | 新增 | `diagnosis_prompt.md`、`memory_view_prompt.md`、`multi_knowledge_view_prompt.md`、`preconditioner_prompt.md` |
| `src/skill_evolution/v24_1/benchmarks/alfworld/prompts/v23_4/` | 新增 | `diagnosis_prompt.md`、`preconditioner_prompt.md`、`replay_multi_knowledge_contract_prompt.md`、`replay_multi_knowledge_learning_prompt_v1.md`、`replay_multi_knowledge_view_prompt.md`、`replay_prompt.md`、`replay_view_prompt.md` |
| `src/skill_evolution/v24_1/benchmarks/alfworld/prompts/v23_5/` | 新增 | `diagnosis_prompt.md`、`diagnosis_prompt_feedback.md`、`editor_prompt.md`、`editor_prompt_feedback.md`、`knowledge_only_view_prompt.md`、`knowledge_repair_prompt.md`、`knowledge_verifier_prompt.md`、`preconditioner_knowledge_only_prompt.md`、`preconditioner_knowledge_only_prompt_feedback.md`、`preconditioner_prompt.md`、`preconditioner_prompt_feedback.md`、`replay_knowledge_only_prompt.md`、`replay_knowledge_only_prompt_feedback.md`、`replay_multi_knowledge_learning_prompt_v1_feedback.md` |
| `src/skill_evolution/v24_1/benchmarks/alfworld/protocol/` | 新增 | `LICENSE`、`rollout_no_history.md`、`rollout_with_history.md`、`source.json` |
| `src/skill_evolution/v24_1/contracts/` | 新增 | `__init__.py`、`diagnosis.py`、`editor.py`、`gate.py`、`grouping.py`、`memory.py`、`memory_view.py`、`model_routing.py`、`preconditioner.py`、`replay.py`、`replay_view.py` |
| `src/skill_evolution/v24_10/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`stages.py` |
| `src/skill_evolution/v24_10/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `src/skill_evolution/v24_2/` | 修改 | `storage.py` |
| `src/skill_evolution/v24_3/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`stages.py` |
| `src/skill_evolution/v24_3/prompts/` | 新增 | `diagnosis.md`、`preconditioner.md` |
| `src/skill_evolution/v24_4/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`episodes.py`、`stages.py` |
| `src/skill_evolution/v24_4/prompts/` | 新增 | `diagnosis.md`、`preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/decision_evidence/prompts/` | 新增 | `diagnosis.md`、`preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/decision_priority/prompts/` | 新增 | `diagnosis.md`、`preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/gain_regression_decisions/prompts/` | 新增 | `preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/historical_attempt/prompts/` | 新增 | `preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/historical_choice_check/prompts/` | 新增 | `preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/keep_after_regression/prompts/` | 新增 | `preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/parent_choice/prompts/` | 新增 | `preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/progress_decision/prompts/` | 新增 | `diagnosis.md` |
| `src/skill_evolution/v24_4/revisions/search_type_choice/prompts/` | 新增 | `preconditioner.md` |
| `src/skill_evolution/v24_4/revisions/success_memory/prompts/` | 新增 | `replay_success.md` |
| `src/skill_evolution/v24_4/success_memory/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`observations.py`、`stages.py` |
| `src/skill_evolution/v24_5/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `src/skill_evolution/v24_6/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`gate.py`、`stages.py` |
| `src/skill_evolution/v24_6/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `src/skill_evolution/v24_7/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`stages.py` |
| `src/skill_evolution/v24_7/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `src/skill_evolution/v24_8/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`stages.py` |
| `src/skill_evolution/v24_8/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `src/skill_evolution/v24_9/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`search_scope.py`、`stages.py` |
| `src/skill_evolution/v24_9/general/` | 新增 | `__init__.py`、`__main__.py`、`campaign.py`、`pick_two.py`、`stages.py` |
| `src/skill_evolution/v24_9/general/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `src/skill_evolution/v24_9/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `src/skill_evolution/v27/` | 新增 | `__init__.py`、`benchmark.py`、`facts.py`、`json_response.py`、`storage.py`、`transport.py` |
| `src/skill_evolution/v27/contracts/` | 新增 | `__init__.py`、`diagnosis.py`、`editor.py`、`grouping.py` |
| `src/skill_evolution/v28/` | 新增 | `__init__.py`、`validation.py` |
| `src/skill_evolution/v28/benchmarks/` | 新增 | `__init__.py` |
| `src/skill_evolution/v28/benchmarks/searchqa/` | 新增 | `__init__.py`、`facts.py`、`protocol.py` |
| `src/skill_evolution/v28_5/` | 新增 | `__init__.py`、`diagnosis.py`、`editor.py`、`execution_input_view.py`、`execution_references.py`、`explicit_references.py`、`facts.py`、`preconditioner.py` |
| `src/skill_evolution/v29_2/` | 新增 | `__init__.py`、`execution_references.py`、`explicit_references.py` |

</details>

<details>
<summary>运行和分析入口（28 个路径）</summary>

| 目录 | 状态 | 文件 |
|---|---|---|
| `scripts/analysis/v24_9/` | 新增 | `v24_9_general_windows.py` |
| `scripts/runs/` | 修改 | `verify_v24_offline.py` |
| `scripts/runs/alfworld/` | 新增 | `alfworld_aligned_common.py`、`launch_alfworld_overnight.py`、`run_alfworld_aligned.py` |
| `scripts/runs/skilladam/alfworld/native_retry/` | 新增 | `run_skilladam_alfworld_native_retry.py`、`run_skilladam_alfworld_official_models.py`、`run_skilladam_alfworld_official_optimizer.py` |
| `scripts/runs/skilladam/alfworld/shared_actor/` | 新增 | `run_skilladam_aligned.py` |
| `scripts/runs/skilladam/alfworld/trajectory_feedback/` | 新增 | `run_alfworld_skilladam_v24_9_feedback.py`、`verify_alfworld_skilladam_v24_9_feedback.py` |
| `scripts/runs/v24/` | 新增 | `read_archived_test.py`、`verify_v24_offline.py` |
| `scripts/runs/v24_1/` | 新增 | `verify_v24_1_offline.py` |
| `scripts/runs/v24_10/` | 新增 | `run_v24_10_test.py` |
| `scripts/runs/v24_2/` | 修改 | `run_v24_2_test.py` |
| `scripts/runs/v24_3/` | 新增 | `run_v24_3_test.py` |
| `scripts/runs/v24_4/` | 新增 | `run_v24_4_test.py` |
| `scripts/runs/v24_5/` | 新增 | `run_v24_5.py` |
| `scripts/runs/v24_6/` | 新增 | `run_v24_6_test.py`、`verify_v24_6_offline.py` |
| `scripts/runs/v24_7/` | 新增 | `run_v24_7_test.py`、`verify_v24_7_offline.py` |
| `scripts/runs/v24_8/` | 新增 | `run_v24_8_test.py`、`verify_v24_8_offline.py` |
| `scripts/runs/v24_9/` | 新增 | `run_v24_9_general_test.py`、`run_v24_9_test.py`、`verify_v24_9_general_offline.py` |

</details>

<details>
<summary>测试（24 个路径）</summary>

| 目录 | 状态 | 文件 |
|---|---|---|
| `tests/adapters/alfworld/` | 新增 | `test_aligned_baselines.py` |
| `tests/skill_evolution/skilladam/` | 新增 | `__init__.py` |
| `tests/skill_evolution/skilladam/alfworld/` | 新增 | `__init__.py` |
| `tests/skill_evolution/skilladam/alfworld/native_retry/` | 新增 | `__init__.py`、`test_skilladam_native_retry.py`、`test_skilladam_official_optimizer.py` |
| `tests/skill_evolution/skilladam/alfworld/shared_actor/` | 新增 | `__init__.py`、`test_skilladam_aligned.py` |
| `tests/skill_evolution/v24/` | 新增 | `test_no_review.py`、`test_verifier_retry.py` |
| `tests/skill_evolution/v24_1/` | 新增 | `__init__.py`、`conftest.py`、`support.py`、`test_implementation.py`、`test_no_review.py` |
| `tests/skill_evolution/v24_2/` | 修改 | `test_final_evaluation.py` |
| `tests/skill_evolution/v24_3/` | 新增 | `test_entrypoints.py` |
| `tests/skill_evolution/v24_4/` | 新增 | `test_success_memory.py` |
| `tests/skill_evolution/v24_5/` | 新增 | `test_entrypoint.py` |
| `tests/skill_evolution/v24_6/` | 新增 | `test_campaign.py` |
| `tests/skill_evolution/v24_7/` | 新增 | `test_search_handoff.py` |
| `tests/skill_evolution/v24_8/` | 新增 | `test_continuation_campaign.py` |
| `tests/skill_evolution/v24_9/` | 新增 | `test_general.py`、`test_search_scope.py` |

</details>

<details>
<summary>文档（54 个路径）</summary>

| 目录 | 状态 | 文件 |
|---|---|---|
| `docs/methods/skillopt/` | 新增 | `ALFWORLD_LEGACY_RETIREMENT.md` |
| `docs/methods/v24/` | 修改 | `NEXT_EXPERIMENTS.md`、`PRECONDITIONER_ROLE.md`、`README.md`、`VALIDATION.md` |
| `docs/methods/v24_1/` | 新增 | `README.md` |
| `docs/methods/v24_1/draft_20261030_001/` | 新增 | `CHANGES.md`、`README.md`、`REVIEW_CASES.md`、`SECOND_REVIEW.md`、`review_checks.json`、`source_manifest.json` |
| `docs/methods/v24_1/draft_20261030_001/baseline/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `docs/methods/v24_1/draft_20261030_001/context/` | 新增 | `execution_context.md`、`knowledge_only_view.md` |
| `docs/methods/v24_1/draft_20261030_001/diffs/` | 新增 | `diagnosis.diff`、`editor.diff`、`preconditioner.diff`、`replay.diff` |
| `docs/methods/v24_1/draft_20261030_001/prompts/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `docs/methods/v24_1/draft_20261030_001/review_02/` | 新增 | `before_review_checks.json`、`before_source_manifest.json` |
| `docs/methods/v24_1/draft_20261030_001/review_02/before/` | 新增 | `diagnosis.md`、`editor.md`、`preconditioner.md`、`replay.md` |
| `docs/methods/v24_1/draft_20261030_001/review_02/diffs/` | 新增 | `diagnosis.diff`、`editor.diff`、`preconditioner.diff`、`replay.diff` |
| `docs/methods/v24_10/` | 新增 | `README.md` |
| `docs/methods/v24_3/` | 新增 | `README.md` |
| `docs/methods/v24_4/` | 新增 | `README.md` |
| `docs/methods/v24_4/revisions/decision_evidence/` | 新增 | `DESIGN.md` |
| `docs/methods/v24_4/revisions/gain_regression_decisions/` | 新增 | `DESIGN.md` |
| `docs/methods/v24_4/revisions/parent_choice/` | 新增 | `AUDIT.md` |
| `docs/methods/v24_5/` | 新增 | `README.md` |
| `docs/methods/v24_6/` | 新增 | `README.md` |
| `docs/methods/v24_7/` | 新增 | `DESIGN.md`、`README.md` |
| `docs/methods/v24_8/` | 新增 | `DESIGN.md`、`README.md`、`verification.md` |
| `docs/methods/v24_9/` | 新增 | `DESIGN.md`、`README.md` |
| `docs/methods/v24_9/general/` | 新增 | `DESIGN.md` |
| `docs/repository/` | 新增 | `ALFWORLD_COMMIT_SCOPE.md`、`ALFWORLD_RUN_RECORDS.md` |

</details>
