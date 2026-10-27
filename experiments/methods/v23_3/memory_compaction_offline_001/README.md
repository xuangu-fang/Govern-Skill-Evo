# Memory 紧凑输入离线原型

**结论：值得进入有限的新输入格式验证；目前不替换正式默认输入。** 已完成独立转换器、R04/R05/R06 及本次 P3-A/B 输入对照、离线测试与关键证据核查。模型调用、检索模型、环境运行、Editor、Replay 和 Memory 更新均为 **0**。

原型仅新增在本目录。没有改动 V23/V23.3 正式模块、既有 Prompt、Memory 存档或历史实验。输出仍拟由一次 Preconditioner 调用产生，没有选择证据的额外 LLM 阶段，也没有新增读取工具。

## 实现的规则

[compact.py](compact.py) 的 `compact_memory()` 从完整 Memory 构造独立的 `memory_evidence_view_v1`：

1. 原样保留全部活跃条目的 knowledge/evidence，以及全部既有来源身份；历史 Parent、实际 Diff 和 execution_context 原样保留。
2. 每条来源轨迹保留原始 task、initial、outcome，以及全部有序的 step/action/feedback。不能用缺失的 detailed observation 推断物体、状态或动作不可用。
3. 对所有条目的数字步骤引用取并集，固定展开前后两步，裁到轨迹边界；同源相邻或重叠窗口合并。不按任务、成功与否或知识文字筛选。
4. 每个窗口保存起点 before 及每步 after；窗口内下一步 before 从上一 after 恢复。窗口之间不推断状态；初始状态单独保留。
5. 没有数字步骤引用时保留整条轨迹。`:0` 是初始状态锚点，展开步骤 1～2。同时有精确与 outcome/整轨迹引用时按精确引用展开，完整动作序列与 outcome 仍保留。这条规则不是对 broad claim 的完整语义保证。
6. 完全相同的候选命令表共享；各来源的 C ID 仍使用独立命名空间。详细窗口、窗口起点和 initial 使用的命令表都保留。`null` 不转换成空命令列表。
7. 显式记录 `detail_coverage`、展开窗口和 `omitted_detail_ranges`。完整动作序列不冒充完整观察序列。

[MODEL_FORMAT.md](MODEL_FORMAT.md) 是对应模型格式说明。它已附在本次生成的 compact_messages 中，并计入成本；没有覆盖现有方法 Prompt。该原型属于输入表示与证据装配变更，不能追记为原来冻结的实验。

`validate_view()` 将紧凑视图逐字段与完整归档比较，包括引用窗口、起点、状态、菜单内容及命名空间、动作顺序、反馈、结果与省略范围。`restore_complete_memory()` 只恢复完整覆盖的视图；部分视图拒绝恢复，不编造缺失状态。

## 输入成本

以下紧凑值使用本地 `o200k_base` 计数，按**每个原请求实际返回的 prompt_tokens / 原请求本地计数**校准。包括格式说明，但不精确模拟服务端消息封装。它们是估算，不是 DeepSeek 精确 tokenizer 结果、计费结果或统计置信区间。`cl100k_base` 的独立对照计数也已归档。

| 案例 | 原始实际输入 | 去重复 before 的完整视图 | 再共享命令表的完整视图 | 再加引用窗口 | 总输入减少 |
|---|---:|---:|---:|---:|---:|
| V23 R04 | 356,103 | 307,220 | 265,239 | **201,694** | 43.36% |
| V23 R05 | 470,139 | 403,432 | 343,632 | **245,816** | 47.71% |
| V23 R06 | 432,863 | 373,556 | 317,450 | **219,300** | 49.34% |
| 本次 P3-A，自由替换 | 474,697 | 408,003 | 348,214 | **250,417** | 47.25% |
| 本次 P3-B，Patch | 475,369 | 408,675 | 348,886 | **251,090** | 47.18% |

另一 tokenizer 校准后的窗口估算依次为 202,355、246,983、220,313、251,542、252,215。完整计数、版本、来源请求路径和分项降幅见 [costs.json](results/costs.json)。

比前期简单去重试算多出的部分来自现在实际交付的显式窗口/轨迹结构、覆盖标记和模型说明。因此以前的约 29% 只能作为探索性估算；本表以当前可检查格式为准。两个完整视图均通过了**恢复后与原 Memory 逐字段相等**的检查；最终窗口视图是有损投影，不称为无损。

成本仍高于 10～15 万目标。本轮没有为了达到目标扩大半径调参、按案例手挑证据、裁剪 knowledge 或进一步删除反馈。

## 覆盖与完整性

| 案例 | 保留历史轨迹 | 保留全部动作/反馈步数 | 有详细状态与菜单的步骤 | 完整详细轨迹 | 窗口数 |
|---|---:|---:|---:|---:|---:|
| R04 | 52 | 1,201 | 329 | 5 | 67 |
| R05 | 70 | 1,716 | 416 | 5 | 88 |
| R06 | 58 | 1,586 | 393 | 2 | 79 |

本次 A/B 与 R05 使用相同 Memory，因此对应的覆盖也相同。所有真实来源都有数字锚点，没有触发“无法定位则全文”回退；回退由合成测试单独覆盖。所有精确引用均保留详细证据，三轮共检查 396 次数字步骤引用出现，未按来源去重计数。

完整性结论是**声明保留的材料与归档一致**，不是窗口外细节不重要的证明。人工检查覆盖 M6 正反响应、M7 温度处理前提、M10 概括偏差。具体事实、保留范围和省略限制见 [EVIDENCE_AUDIT.md](EVIDENCE_AUDIT.md) 与 [原始证据摘录](results/evidence_specimens.json)。

## 对照材料

| 案例 | 原始输入 | 紧凑输入 | 实际拟发送消息 | 展开/省略清单 |
|---|---|---|---|---|
| R04 | [原始](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R04/original_payload.json) | [紧凑](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R04/compact_payload.json) | [消息](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R04/compact_messages.json) | [覆盖](cases/R04/coverage.json) |
| R05 | [原始](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R05/original_payload.json) | [紧凑](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R05/compact_payload.json) | [消息](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R05/compact_messages.json) | [覆盖](cases/R05/coverage.json) |
| R06 | [原始](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R06/original_payload.json) | [紧凑](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R06/compact_payload.json) | [消息](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/R06/compact_messages.json) | [覆盖](cases/R06/coverage.json) |
| P3-A | [原始](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/P3A_A/original_payload.json) | [紧凑](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/P3A_A/compact_payload.json) | [消息](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/P3A_A/compact_messages.json) | [覆盖](cases/P3A_A/coverage.json) |
| P3-B | [原始](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/P3A_B/original_payload.json) | [紧凑](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/P3A_B/compact_payload.json) | [消息](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/cases/P3A_B/compact_messages.json) | [覆盖](cases/P3A_B/coverage.json) |

当前 Parent、Original、当前执行和当前命令表均未改变；只替换历史 Memory 的模型输入视图。本次 compact A/B 的 user message 逐字符串相等，系统 Prompt 分别保留各方法说明并附相同格式说明，见 [A/B 核查](results/ab_input_checks.json)。

## 验证与重现

在仓库根目录运行只读离线测试：

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \
  experiments/methods/v23_3/memory_compaction_offline_001/test_compact.py
```

**29 项测试通过。** 覆盖窗口边界/合并、初始状态与空轨迹、缺少精确引用的全文回退、同源引用合并、跨来源同名 C ID、完整视图无损往返、部分视图拒绝伪恢复、破坏引用材料后的拒绝，以及三轮真实归档。测试禁止 socket 网络连接。

[run.py](run.py) 是本次材料生成入口，禁止网络访问，使用本地已缓存 tokenizer；[audit.py](audit.py) 提取人工核查材料。生成入口采用排他写入，已有目录不能覆盖重跑。它们已执行完成；复核现有结果用上述测试，未来再生成应使用新的实验目录。没有运行与本改动无关的整套环境回归。

此前 3,913 个相关源码、测试及实验/正式运行文件的 size/mtime 保护检查通过，见 [保护结果](results/protection.json)。不把元数据核对描述成密码学内容证明。

## 下一阶段决策

离线结果满足“输入显著减少、所有精确引用和已抽查关键反例仍可检查”，**建议进入新输入格式的有限生成验证**；不宣称策略质量、模型理解或行为收益已经通过。

真实验证前须完成：

- 将独立 view 显式接入新实验入口，保存 full payload 与 compact view 两份记录。旧 `validate_memory`、loader 和 compiler 不能直接消费新 view；不应放松旧完整轨迹校验来迁就片段。编译所需原始 Plan/Memory 与实际送入的视图须保持可追溯关系。
- A/B 同时使用相同紧凑输入及格式说明，冻结半径 2 和原 Original。不要在一组中混入另外的 Memory 概括修正。
- 单独确定一致的输出/思考预算和调用上限。压缩输入不保证原 16,384 输出预算不再截断；不自动增加预算或启动请求。
- 首先检查模型是否正确理解窗口、菜单引用及证据边界，再评价 Update/Patch。两组均压缩只能比较压缩条件下 A/B，不能独立证明压缩相对全文无质量损失；若要作该结论，需要后续同方法全文/紧凑对照。

本轮在离线验收和建议处结束，没有真实调用、默认接入或正式算法晋升。

## 文件与归档

配置、任务定义、报告、精选结果、候选及必要失败证据保留在本目录；人工测试夹具与源码快照仍纳入 Git。

主要材料：

- [EVIDENCE_AUDIT](EVIDENCE_AUDIT.md)

完整模型输入、请求响应、运行元数据、轨迹、展开的 Memory、生成的 Mock 数据以及日志等已归入[本地原始归档](../../../../artifacts/methods/v23_3/memory_compaction_offline_001/)，不进入 Git。归档保留原相对层级；只需要日志归档的实验仍保留原配置和全部研究材料。

当前脚本通过 [v23.3 归档读取工具](../archive_io.py) 读取分开存放的文件，并同时枚举实验目录与归档中的轨迹。加载链需要合并文件时只创建系统临时读取目录，退出后删除；历史 JSON 中的路径和阶段结论保持原文。历史启动约束未重置，本次没有重新执行模型或环境。

返回 [v23.3 实验导航](../README.md)。
