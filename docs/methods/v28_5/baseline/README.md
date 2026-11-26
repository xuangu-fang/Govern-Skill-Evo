# v28.5 的冻结基线

冻结日期：2026-11-04（Asia/Shanghai）。来源是当前仓库 v28.3，不是 v28.4。所有快照按字节复制，源文件未修改；逐文件对应关系见 [source_map.json](../source_map.json)。

| 快照 | 内容 |
|---|---|
| `prompts/*_v28_3.md` | v28.3 四份完整 Prompt，作为 diff 的旧侧 |
| `CONTRACTS_v28_3.md` | v28.3 证据、字段、patch、Gate、Memory 和恢复合同 |
| `README_v28_3.md` | v28.3 方法、实验参数和运行背景 |
| `v28_3_config.json` | 原运行配置，包含全部 600 题批次 ID 与模型参数 |
| `initial_skill.md` | 原始未学习 Skill |
| `actor/*.md` | 当前 SearchQA Actor base/system/user/runtime 原文 |

原文中的状态、版本名和相对链接一并保留，代表源文件语境；复制后的文档不是新的运行记录，其内部相对链接应按源文件所在目录解释。配置里的原身份、绝对来源路径和文本保持不变，不将其伪装成可执行 v28.5 配置。

快照用于审阅和后续实现对照，不由旧 runner 加载为新 Prompt，不恢复或覆盖旧 campaign，不继承 v28.3 最终 Skill 或 Memory 作为未来新训练的初始状态。
