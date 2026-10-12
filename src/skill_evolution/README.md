# 方法源码

`v01/` 至 `v21/` 中实际存在的版本目录保存对应方法实现；没有独立实现的版本不创建空包。文件名暂保留版本后缀，方便搜索和与历史记录对应。

| 目录 | 归属 |
| --- | --- |
| `v01/`—`v15/` | 各版 Autonomous GSE、诊断、门控及试验实现 |
| `v17/` | 经验分组、诊断、编译、编辑、Monitor |
| `v18/` | V18 方法及 benchmark V4 运行适配 |
| `v19/` | 演化、归因、记忆、评审、恢复 |
| `v20/` | V20 运行、分组、问题记忆、融合 |
| `v21/` | V21 证据、理解、记忆消费和更新 |
| `shared/` | 通用经验表示、诊断格式、演化决策、二维门控及文件定位 |

某版本被后续版本复用时，直接导入原版本包，不复制实现，也不因此把版本专属逻辑改称通用工具。例如 V19 的经验卡实现仍归 V17。

源码在这里；命令入口见 [scripts](../../scripts/README.md)，方法配置见 [experiments/methods](../../experiments/methods/README.md)，测试见 [tests](../../tests/README.md)。

新导入示例：`from src.skill_evolution.v19.campaign_v19 import run_campaign_v19`。旧的顶层模块已移除，不提供旧模块别名。
