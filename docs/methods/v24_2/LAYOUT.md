# v24.2 文件整理记录

2026-11-10。正式训练 ID 为 `v24_2_alfworld_20261106_195800`。目录中的配置、最终 Skill、训练摘要及两份 Test 摘要可从[实验入口](../../../experiments/methods/v24_2/v24_2_alfworld_20261106_195800/README.md)查阅。

| 材料 | 原位置 | 当前位置 |
|---|---|---|
| 活动 Prompt | `docs/methods/v24_2/prompts/` | [源码包的 prompts](../../../src/skill_evolution/v24_2/prompts/) |
| Test 命令 | `scripts/runs/run_v24_2_test.py` | [v24.2 运行脚本](../../../scripts/runs/v24_2/run_v24_2_test.py) |
| 正式训练 | `experiments/campaigns/<训练ID>/` | `artifacts/methods/v24_2/<训练ID>/` |
| 启动与两次测试日志 | `experiments/launches/<训练ID>/` | 完整训练目录的 `launch/` |
| 首测、复测 | `experiments/evaluations/<评测ID>/` | `artifacts/methods/v24_2/<评测ID>/`，两个 ID 分别保留 |
| 早期合成验收 | `artifacts/verification/v24_2_alfworld_offline_001/` | [离线运行归档](../../../artifacts/methods/v24_2/v24_2_alfworld_offline_001/) |

### 实际调整

- 运行时从 v24.2 源码包读取四份模块 Prompt 和领域说明。方法文档直接链接这些文件，历史修订差异保留原文。
- v24.3 的 R02 分析链接指向新的归档，v24.3、v24.4、v24.6 至 v24.10 的 Test 入口与相关单元测试改用 v24.2 的新导入路径。v24.1 的基线配置继续在原处读取。
- 正式训练的 `config.json`、`runtime.json`、`contract.json` 和 `final_skill.md` 原样选入实验目录。训练摘要列出各轮任务数和选中来源。两份评测摘要各自记录成功数、总题数、用量及原始报告位置。

### 映射表补充

启动材料位于训练目录的 `launch/`，训练准备入口现可识别这个子目录。历史契约中的 Prompt 路径和评测回执中的轨迹绝对路径都保留原文。读取旧数据时使用[仓库路径映射](../../../experiments/methods/canonical-paths.json)和[本次源码修订对照](../../../experiments/methods/v24_2/layout-change.json)。旧契约中的其他差异继续按原规则处理。

对这两次已经完成的 Test，使用新路径运行原有 `--resume` 命令会读取归档输入、回执及对应轨迹，返回已记录的结果。未完成的新 Test 继续使用原评测流程。对旧合成验收的解释以它自己的 `offline_report.json` 和当时的 Prompt 修订为准。

### 离线验收结果

迁移前 v24.2 的 12 项测试通过。迁移后覆盖 v24.2、v24.3、v24.4、v24.6 至 v24.9 的 61 项测试通过，其中含一项本次新增的旧契约读取回归。关闭网络后，通过新 Test 入口分别核对两份归档的 134 个任务、逐题轨迹和训练最终 Skill，读回首测 118/134、复测 115/134。
