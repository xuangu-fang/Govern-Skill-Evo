# V22 实验与源码引用导航

[方法文档](../../../docs/methods/v22/README.md) · [五轮最终报告](../../../docs/methods/v22/ALFWORLD_57_FIVE_ROUND_EXPERIMENT.md) · [目录整理说明](../../../docs/repository/V22_CLEANUP.md)

V22 包含以下 18 个实际材料目录。编号是实验阶段，不要求连续；其中
`23_alfworld57_five_round` 是 **v22 的第 23 阶段**，不是方法版本 v23。

| 目录 | 用途 |
|---|---|
| [01_no_history](01_no_history/) | 无历史更新的配置和报告 |
| [02_behavior_feedback](02_behavior_feedback/) | 早期行为反馈验证 |
| [03_compact_cycle](03_compact_cycle/) | 紧凑学习与跨轮构造 |
| [04_fixed_consumption](04_fixed_consumption/) | 固定初稿的历史消费 |
| [05_conditional_trial](05_conditional_trial/) | 条件化试验 |
| [06_failure_trial](06_failure_trial/) | 失败反馈同信息对照 |
| [07_train_response](07_train_response/) | Train 响应与后续更新 |
| [08_grouped_continual](08_grouped_continual/README.md) | 两轮主线及恢复报告 |
| [11_unified_dsc_stream](11_unified_dsc_stream/) | 流式协议、计划和任务输入 |
| [12_contract_alignment](12_contract_alignment/README.md) | 历史契约公共实现 |
| [16_input_scalability](16_input_scalability/README.md) | 输入容量审计与原型 |
| [17_p1_input](17_p1_input/README.md) | P1 编码及验证 |
| [18_endpoint_model_routing](18_endpoint_model_routing/README.md) | Evolution 模型路由 |
| [19_endpoint_actor_evolution_routing](19_endpoint_actor_evolution_routing/README.md) | Actor 与 Evolution 模型路由 |
| [20_memory_contract_fix](20_memory_contract_fix/README.md) | Memory 字段说明与示例 |
| [21_memory_contract_minimal](21_memory_contract_minimal/README.md) | Memory 最小字段说明 |
| [22_reference_consistency](22_reference_consistency/README.md) | 类型化引用规则 |
| [23_alfworld57_five_round](23_alfworld57_five_round/README.md) | 57 项五轮运行及容量修订 |

## 引用关系

各修订先使用自身文件，再沿下列顺序查找公共内容：

- 12 → 仓库公共源码。
- 17、18、19 → 12 → 仓库公共源码；三者互不替换。
- 20 → 17 → 12 → 仓库公共源码。
- 21 → 20 → 17 → 12 → 仓库公共源码。
- 22 → 21 → 20 → 17 → 12 → 仓库公共源码。
- 五轮实验 → 22 → 21 → 20 → 17 → 12 → 仓库公共源码。
- 容量修订 → 五轮实验 → 22 → 21 → 20 → 17 → 12 → 仓库公共源码。

五轮实验的 `model_routing.py` 单独以相对链接引用 19 的完全相同实现。
12 中供旧审计直接读取的三个文件也保留相对链接。各修订本地的
`bounded_evaluation.py` 虽有相同文本，其所在目录决定 Actor 子进程的版本，
因此保留本地入口。

## 文件与运行产物

源码、测试、计划、提示词、任务清单、人工分析和正式报告进入版本管理。
`results/` 中精选的状态、成本、分析与来源摘要继续保留；自动校验输出、
旧源码清单及测试日志由 `.gitignore` 忽略，并保留本地原文件。
历史报告中指向这些生成记录的链接需要本地归档才能打开。

完整轨迹、请求、响应、状态、中间结果和运行目录位于
`artifacts/methods/v22/`，已被忽略。部分离线验证需要这些历史材料；
仅获取源码不代表已经获取全部实验数据。公共任务划分位于
[benchmarks/alfworld](../../../benchmarks/alfworld/README.md)，应继续保留。

使用各目录 README 中的 `offline_tests.py` 或明确测试命令选择修订；
不要用默认仓库入口代替历史修订，也不要为检查目录而重跑历史控制器。
