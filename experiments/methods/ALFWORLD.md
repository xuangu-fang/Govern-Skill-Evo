# ALFWorld 自进化实验索引

覆盖 v24 至 v24.10。表中每次完整 Test 均含 134 题，数字为成功题数。消融使用的 Skill 与对应训练的导出文本分别归档。

| 版本与实验材料 | 训练与归属 | Test |
|---|---|---|
| [v24](v24/README.md) | R04 发布最终 Skill。另有独立的 RC1 候选、单轮 smoke 和三例重放。 | 首测 121 |
| [v24.1](v24_1/README.md) | 官方模型配置完成训练；复审准备配置单独保留。 | 首测 121，复测 119 |
| [v24.2](v24_2/README.md) | 同一正式训练对应两次独立评测。 | 首测 118，复测 115 |
| [v24.3](v24_3/README.md) | 两次 R02 快检和正式训练分别归档。 | 首测 109 |
| [v24.4](v24_4/README.md) | 五次训练。progress_decision 和 retained 完成，另有两次停止、一次暂停。 | progress_decision 首测 108；retained 有 116 份回执，无终报 |
| [v24.5](v24_5/README.md) | 使用本版四份 Prompt，通过 v24.4 入口训练和评测。 | 首测 109 |
| [v24.6](v24_6/README.md) | 搜索段落替换消融使用独立的混合 Skill。 | 首测 104，消融 118 |
| [v24.7](v24_7/README.md) | 正式 Skill 首测与复测；搜索延续消融另存受测文本。 | 首测 115，复测 116，消融 123 |
| [v24.8](v24_8/README.md) | 正式训练与五组离线检查分别归档。 | 首测 115 |
| [v24.9](v24_9/README.md) | general 与 general_withdraw 各自完成六轮，分别保留实际使用的 Preconditioner。 | general 首测 114；general_withdraw 首测 119，复测 121 |
| [v24.10](v24_10/README.md) | 一份正式训练对应首测和复测。 | 首测 119，复测 121 |

## 从摘要定位原始记录

每个版本的实验页列出训练配置、已发布轮次、最终 Skill 和评测摘要。每次评测保留自己的 ID。精选材料在实验目录的 `config/`、`results/`、`reports/`，完整轨迹和回执在本机的 `artifacts/methods/<版本>/<运行 ID>/`。旧记录中的原始路径按[路径映射](canonical-paths.json)解析。

对 v24.6～v24.10 的已完成评测，可用相应版本的 Test 入口传入 `--read-archive --campaign <训练目录> --evaluation <评测目录>`，逐题读取当时实际使用的 Skill 和回执。早期 v24.9 general 的原始 Prompt 见对应训练的 `config/preconditioner.md`。
