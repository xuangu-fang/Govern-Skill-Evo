# OfficeQA 整理盘点与路径映射

盘点日期为 2026-11-26。基线为 `wyy/day57-tau-autonomous-gse-v25` 的 `6135f2eb398`，盘点纳入该分支当前工作树中的未跟踪和忽略材料。覆盖 v26–v26.9、SkillAdam、SkillOpt、共用对照、运行入口、数据和归档。

登记 **26 条训练、准备及历史运行记录，79 条评测、补测及专项记录，744 条路径规则**。其中 18 条训练有完成记录。评测包含 42 次完整 Test172、8 条合并后覆盖 172 题的记录，以及限定题集、部分评测和补测材料。合并报告与其原测可以分别出现在清单中，计数单位是证据记录。

[结构化清单与拟议路径](officeqa-inventory.json)包含实验 ID、冻结配置、状态证据、已有受测 Skill 和哈希、评测分母、待评 UID、旧路径和拟议位置。

## 版本与基线

| 版本／方法 | 训练、准备或历史引用 | 完成训练 | 评测记录 | 完整 Test172 | 合并补齐 172 题 |
| --- | ---: | ---: | ---: | ---: | ---: |
| v26 | 5 | 2 | 2 | 0 | 1 |
| v26.1 | 1 | 1 | 5 | 2 | 1 |
| v26.2 | 1 | 1 | 2 | 0 | 0 |
| v26.3 | 1 | 0 | 0 | 0 | 0 |
| v26.4 | 1 | 0 | 0 | 0 | 0 |
| v26.5 | 1 | 1 | 4 | 0 | 0 |
| v26.6 | 1 | 1 | 2 | 0 | 0 |
| v26.7 | 1 | 1 | 4 | 0 | 0 |
| v26.8 | 1 | 1 | 2 | 0 | 0 |
| v26.9 | 1 | 1 | 7 | 5 | 1 |
| SkillAdam | 10 | 7 | 39 | 23 | 5 |
| SkillOpt | 2 | 2 | 11 | 11 | 0 |
| 共用 | 0 | 0 | 1 | 1 | 0 |

- **v26.3** 的设计、配置和实现仍可定位。v26.4 实现文档引用了历史训练 ID `v26_3_officeqa_train74_20261117_125845`。当前工作树、Git 历史及 OfficeQA 压缩清单均未定位到该实验目录，路径映射标为「缺失待找」。[v26.3 实现](../methods/v26_3/IMPLEMENTATION.md) · [历史训练引用](../methods/v26_4/IMPLEMENTATION.md:7)
- **v26.4** 的启动记录显示训练暂停，训练状态指向 R03 Selected，R04 已建目录。**v26.2** 首测和复测都评了 171 题，各为 120 和 118 题 EM，均缺 UID0111。v26.1 的 124/172 使用独立补测，相同配置的比较需要对齐题目交集。[v26.4 启动状态](../../experiments/launches/v26_4_officeqa_train74_20261117_151911/status.json) · [v26.4 训练状态](../../experiments/campaigns/v26_4_officeqa_train74_20261117_151911/state.json) · [v26.2 分母口径](../methods/v26_3/README.md:55)
- **早期运行与续跑**分开登记原 ID。v26 的 10 题 Pilot、正式 74 题运行和 UID0007 扩预算续跑各有原配置或状态回执。SkillAdam 的 10 月 29 日准备、启动失败、无完成回执及预算续跑也各有证据。11 月 20 日两次 SkillAdam 和 11 月 22／23 日两次 SkillOpt 各自独立归档。[v26 Pilot](../methods/v26/DEEPSEEK_PILOT.md) · [SkillAdam 预算续跑](../benchmarks/officeqa/SKILLADAM_UID0007_BUDGET.md)
- **共用对照**有两份已定位的初始 Skill 成绩。早期 v26.1 对照为 85/172，现有 v26.9 主对照为 93/172，来源分别为早期 R00 和 v26.9 R01 的现场。五组评测入口中的 No Skill 配置有文档，当前盘点未定位到该臂独立评分回执。[早期 R00](../../experiments/evaluations/officeqa_checkpoints_20261111/R00/summary.json) · [现有主对照 R00](../../experiments/evaluations/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/R01/summary.json) · [共用评测入口](../benchmarks/officeqa/NATIVE_LAUNCHERS.md)

## 现有主对照的原始证据

| 方法 | 训练记录 | 最终 Skill 三次 EM | 现有图取值 |
| --- | --- | --- | ---: |
| v26.9 | [2026-11-18 训练](../../experiments/campaigns/v26_9_officeqa_train74_20261118_180409) | [122](../../experiments/evaluations/v26_9_officeqa_UID0111_65536_20261118_194128/combined_report.json)、[123](../../experiments/evaluations/v26_9_officeqa_selected_serial_test172_w20_20261118_200526/final/summary.json)、[122](../../experiments/evaluations/v26_9_officeqa_final_test172_w20_repeat2_20261120_134237/summary.json) | 122/172 |
| SkillAdam | [2026-11-20 晚间第二次训练](../../experiments/baselines/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937/result.json) | [121](../../experiments/evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_test172/report.json)、[117](../../experiments/evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat1_20261121_000620/report.json)、[118](../../experiments/evaluations/skilladam_officeqa_deepseek_flash_7rounds_20261120_215937_R04_final_test172_repeat2_20261121_001928/report.json) | 118/172 |
| SkillOpt | [2026-11-23 重试版训练](../../experiments/baselines/skillopt_officeqa_retry_20261123_183232/result.json) | [118](../../experiments/evaluations/skillopt_officeqa_retry_20261123_183232_best_test172/report.json)、[119](../../experiments/evaluations/skillopt_officeqa_retry_20261123_183232_best_test172_repeat2/report.json)、[117](../../experiments/evaluations/skillopt_officeqa_retry_20261123_183232_best_test172_repeat3/report.json) | 118/172 |

v26.9 首测逐题日志有 171 份评分，121 题 EM。UID0111 单题补测答对，合并为 122/172。清单记录各次受测 Skill 的文件 SHA-256，也记录部分历史报告使用的规范 JSON 字符串哈希。两种口径按各自定义核对。[主对照取值](../../experiments/methods/OFFICEQA.md)

主对照三组配置指向同一数据发布目录 `763a8366abf2a3605c381d53586d844dc60fa756`，Test 划分为 172 题。v26.9 和两次 11 月 20 日的 SkillAdam 用 74 题优化池。SkillOpt 使用 50 道 Train 和独立的 24 道 Selection。早期解析修订和不同数据根以各次配置为准。[数据发布清单](../../data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756/dataset_config.json) · [正式基线配置说明](../benchmarks/officeqa/NATIVE_LAUNCHERS.md)

## 拟议路径

精确文件行优先。目录规则覆盖其余后代，后代沿用相对后缀。下表记录盘点时的拟议范围。已落地的实验见 [OfficeQA 实验索引](../../experiments/methods/OFFICEQA.md)。实际提取路径记录在[三组主实验验收清单](../../experiments/benchmarks/officeqa/main-comparison.json)、[v26.1／v26.2 验收清单](../../experiments/benchmarks/officeqa/v26_1-v26_2.json)、[v26、v26.3–v26.8 验收清单](../../experiments/benchmarks/officeqa/v26-remaining.json)、[SkillAdam 历史验收清单](../../experiments/benchmarks/officeqa/skilladam-history.json)和 [SkillOpt 历史验收清单](../../experiments/benchmarks/officeqa/skillopt-history.json)。

| 操作 | 行数 | 用途 |
| --- | ---: | --- |
| 拟提取精选 | 507 | 从校验过的原档提取冻结配置、状态、结果或 Skill 到实验目录。 |
| 拟迁移配置 | 22 | v26 各版训练模板和 OfficeQA 基线模板归各自 `profiles/`。落地时检查启动参数、代码引用和冻结清单。 |
| 拟迁移报告 | 1 | SkillOpt 11 月 22 日逐步评测说明归入原实验的 `reports/`。 |
| 原位保留 | 213 | 方法包、共享 Actor、测试、数据、完整运行、源文档和压缩归档按当前路径访问。 |
| 缺失待找 | 1 | v26.3 历史训练目录只有引用。 |

v26 系列拟归 `experiments/methods/<版本>/<原实验 ID>/`。SkillAdam 拟归 `experiments/methods/skilladam/officeqa/<配置>/<原实验 ID>/`。SkillOpt 拟归 `experiments/methods/skillopt/officeqa/<原实验 ID>/`。共用配置和历史比较入口拟归 `experiments/benchmarks/officeqa/`。各训练的独立评测在其 `results/` 下保留原评测 ID。源码继续使用现有包名。清单列出了 35 个直接跨包或上游 import，其中本地可解析的模块有 2 个尚未被 Git 跟踪。

## 核验边界

- 运行 `restore.py officeqa --verify`，归档的 37,157 条记录、526 个附件均通过原字节 SHA-256 校验。全部 37,683 个归档键在路径映射中有归属。逐题日志回算覆盖 65 条评测记录、10,401 份评分，另核对合并报告中的逐题表和专项评分。完整日志中的 UID 集合与 Test172 一致。[归档校验入口](../../experiments/benchmark_record_refs/README.md)
- 盘点时的路径校验检查旧键唯一、非缺失源可达，以及当时的拟议目标冲突。代码、配置和文档中的静态路径命中有 128 条普通记录。冻结验收快照按源文件和旧路径汇总，保留命中数量和行号范围。各实验页的离线核验入口可读回对应评分。
