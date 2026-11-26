# LiveMathematicianBench 主对照

三种方法共用[初始 Skill](initial_skill.md)，由 DeepSeek Flash 在同一组 124 道测试题上作答。指标为选项标签精确匹配率（EM）。最终值取同一份 Skill 的三次完整测试中位数。训练与选优题次按完整作答次数累计。

| 运行 | 保留节点 | 首测 | 复测 1 | 复测 2 | 中位数 EM | 训练与选优题次 |
|---|---|---:|---:|---:|---:|---:|
| [v27.19](../v27_19/v27_19_lmb53_20261126/README.md) | R04 | 91 | 96 | 89 | 91/124（73.39%） | 96 |
| [SkillAdam](../skilladam/lmb/lmb53_skilladam_v27_5_official_flash_20261120_0020/README.md) | R02 | 61 | 58 | 61 | 61/124（49.19%） | 159 |
| [SkillOpt](../skillopt/lmb/lmb_skillopt_native_feedback_20261124/README.md) | R04 普通更新 | 86 | 91 | 89 | 89/124（71.77%） | 404 |

[固定题目清单](splits.json)记录 35 Train、18 Selection、124 Test。v27.19 和 SkillAdam 使用 53 题优化池。SkillOpt 保留 Train 和 Selection 的用途。初始 Skill 的共享 [R00 完整测试](results/evaluations/shared_R00/summary.json)为 44/124，使用 v27.12 已有的 R00 回执和补测。

## 离线读回

从仓库根目录执行以下命令。验证器只依赖 Python 标准库和本地归档。

```sh
python3 scripts/verification/verify_lmb_comparison_archive.py
```

[对照清单](comparison.json)指向三条训练的归档清单。命令读回 18 次 Test124，按每题的预测与参考标签重算 EM，再从训练和选优回执统计题次。评测正文与保留 Skill 逐字节核对。SkillAdam 的个别补测文件通过合并回执中的 Skill SHA-256 绑定，合并时按题目 ID 核对覆盖。

长记录和轨迹存于本机 `artifacts/methods/`。共享字段与附件存于 `experiments/benchmark_record_refs/lmb/`。携带精简记录时需同时保留这两部分。冻结证据中的原路径与 SQLite 键保留，读取工具通过[历史路径映射](../canonical-paths.json)定位现址。共用 R00 由历史映射定位到 [v27.12 的归档](../v27_12/README.md)。[归档还原说明](../../benchmark_record_refs/README.md) · [实验日志](../../../docs/04_EXPERIMENT_LOG.md)

## 历史版本

[v27](../v27/README.md) · [v27.1](../v27_1/README.md) · [v27.2](../v27_2/README.md) · [v27.3](../v27_3/README.md) · [v27.4](../v27_4/README.md) · [v27.5](../v27_5/README.md)

[v27.6](../v27_6/README.md) · [v27.7](../v27_7/README.md) · [v27.8](../v27_8/README.md) · [v27.9](../v27_9/README.md) · [v27.10](../v27_10/README.md) · [v27.11](../v27_11/README.md)

[v27.12](../v27_12/README.md) · [v27.13](../v27_13/README.md) · [v27.14](../v27_14/README.md) · [v27.15](../v27_15/README.md) · [v27.16](../v27_16/README.md) · [v27.17](../v27_17/README.md) · [v27.18](../v27_18/README.md) · [v27.19](../v27_19/v27_19_lmb53_20261126/README.md)

从仓库根目录执行以下命令，读回[历史运行索引](history.json)。

```sh
python3 scripts/verification/verify_lmb_history_archive.py
```

读取训练与选优回执，按受测 Skill、Actor 和题目 ID 复算每项评测。结果同时列出计划题数、实际评分题数和缺题 ID。v27 的旧测试报告对 JSON 编码后的 Skill 字符串取哈希，归档清单对 Markdown 字节取哈希，读回分别验证。v27.19 的 GPT-5.4 mini 评测也在此读回，DeepSeek Flash 评测由主对照验证器读回。历史启动快照和冻结回放可从各版本页面定位。

## 基线历史归档

[SkillAdam 训练与评测索引](../skilladam/lmb/README.md)收录八次历史训练、官方 Flash 代表运行的跨 Actor 评测和上游 Skill 的 Test124 对照。

[SkillOpt 训练与评测索引](../skillopt/lmb/README.md)收录三次训练、各自的最佳 Skill、历史评测和上游 Skill 的 Meta53 对照。
