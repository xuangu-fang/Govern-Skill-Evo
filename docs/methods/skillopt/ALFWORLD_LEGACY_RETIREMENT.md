# 旧 ALFWorld SkillOpt 方案退役记录

2026-10-30：按用户要求清理旧 ALFWorld SkillOpt 专用方案，保留历史结果、共用代码以及其他 benchmark 的依赖。本记录不设计或实现替代方案。

旧 `alfworld_deepseek_v23_4` 和 `alfworld_current_actor_20261025` SkillOpt 方案不再作为新实验的配置、设计或启动依据。以下暂留文件是历史兼容依赖，不是推荐的运行入口。此次没有禁用这些脚本，也没有改写冻结清单。

## 已删除

| 文件 | 删除原因 | 删除前 SHA256 |
|---|---|---|
| `experiments/configs/skillopt_alfworld_deepseek_v23_4.md` | 旧专用方案说明及启动指南，无现行代码依赖 | `d28d4d56cb0177b26d1a67de909500b8d1f87283e68f2d131a243e9407f964bc` |
| `experiments/configs/skillopt_alfworld_deepseek_v23_4.patch` | 旧传输适配的补丁副本；删除副本不撤销上游工作区中的实现 | `baccbb712f7ea5a5e019a76e76580b31414cbd74cb2ab9812b51f19798ce2569` |

历史 V25 分析目录的 `before_sha256.json` / `after_sha256.json` 曾记录上述文件。它们作为当时的全仓快照保留，未改写或伪造历史哈希；被删除路径可通过本表解释。

## 退役时保留的依赖

下表使用退役时的路径。共用配置与三个运行入口的现址见[ALFWorld 共用 Actor 与对齐基线](../../../experiments/baselines/alfworld/alfworld_current_actor_20261025/README.md)。

| 文件或目录 | 保留依据 |
|---|---|
| `scripts/runs/run_alfworld_aligned.py`、`scripts/runs/start_skillopt_alfworld_formal.py` | SpreadsheetBench 的 `experiments/baselines/skillopt_spreadsheetbench_official_actor48k_20261029/manifest.json` 冻结了这两个文件；预检逐文件验证存在性及 SHA256，删除会使其他 benchmark 预检失败。前者还提供旧 No Skill 入口。 |
| `scripts/runs/run_skillopt_alfworld_deepseek.sh`、`experiments/configs/skillopt_alfworld_deepseek_v23_4.yaml` | `scripts/runs/prepare_v23_5_alfworld.py` 读取它们并计算 provenance 哈希；旧正式启动器也依赖它们。 |
| `scripts/runs/alfworld_aligned_common.py` | SkillAdam 的多个入口继续使用其中的 Actor 执行、轨迹转换、运行时及读写函数；共用检查仍读取旧配置包。 |
| `experiments/baselines/alfworld_current_actor_20261025/` | Actor 和 Initial Skill 被 SkillAdam 的检查读取；配置包、README、补丁副本和任务清单在旧 manifest 中相互绑定，共用检查仍依赖它们。整个目录按历史兼容包保留，不作为新方案。 |
| `tests/adapters/alfworld/test_aligned_baselines.py` | 同时覆盖共享 Actor、No Skill 和共享上游 Final Test 开关，且被旧配置包冻结；不能作为纯 SkillOpt 专用测试整份删除。 |
| `scripts/runs/launch_alfworld_overnight.py` 及原 schedule | 同时包含 SkillAdam 调度及历史运行记录，不属于 SkillOpt 独占入口。 |
| `external/SkillOpt/` 的源码、配置及本地改动 | 开源实现及其传输适配、Final Test 开关也供其他 benchmark 使用；未重置工作区、撤销补丁或改变版本。 |
| `benchmarks/alfworld/editions/skillopt_39_18_134/`、共享 Actor 与相关测试 | 名称包含 SkillOpt，但承载多个已完成方法共用的数据划分和执行协议。 |

## 保护范围与验证

历史 SkillOpt / No Skill 的结果、日志、轨迹、launch 记录保持原样。v24.1 和 SkillAdam 已完成实验的配置、训练产物、测试结果及自动化记录保持原样。SpreadsheetBench、OfficeQA、SearchQA 等其他 benchmark 的实现与冻结清单未修改。

删除前建立了 32,751 个受保护文件的 SHA256 快照，覆盖上述历史结果、v24.1 / SkillAdam 实验、ALFWorld 共享实现、运行脚本、相关测试、SkillOpt 上游源码与配置，以及 SpreadsheetBench SkillOpt 实验。清理后逐文件复核，结果记录在本文件末尾。

未启动训练、测试集评估、真实环境 episode 或模型请求。没有新方案配置、适配器或实现。

验证结果：32,751 个受保护文件全部存在且 SHA256 与清理前一致（缺失 0、变化 0）；两个删除目标均不存在；SpreadsheetBench 冻结清单中的两个旧启动器仍与原记录哈希一致。此次仅删除上述两个文件并新增本记录，未运行需要启动实验的检查入口。
