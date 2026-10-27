# V24 候选基线 RC1

版本：`v24_alfworld_verified_feedback_001_rc1`。状态：已保存，离线验收通过，真实实验未启动。
来源为 v23.5 的 `alfworld_verified_feedback_001` 最终配置。

| 材料 | 位置 |
|---|---|
| 代码副本与运行任务清单 | [code](code/) |
| 正式配置（57 个优化任务、六批） | [campaign.json](config/campaign.json) |
| 任务数据 | [data](data/) |
| 本次离线结果：100 项通过 | [report.json](validation/report.json) |
| 各项测试结果 | [tests.xml](validation/tests.xml) |
| 测试代码副本 | [tests](tests/) |
| 后续真实实验方案 | [NEXT_EXPERIMENTS.md](documents/NEXT_EXPERIMENTS.md) |
| 单轮计划配置（原第一批 10 任务） | [smoke_campaign.json](plans/smoke_campaign.json) |
| 效果对照共同参数 | [comparison_parameters.json](plans/comparison_parameters.json) |

保存采用版本名称、代码副本、配置文件和普通文件清单，不增加额外身份校验。
运行记录已按用户要求简化；prompt 原文、任务事实、预算和自进化方法保留。
核验/修复输入的运行元数据有明确删减，因此不把本次结论描述为全输入字节相同。

代码副本可恢复 v24 的正常运行实现；仍需本地 ALFWorld 数据、相应 Python 环境
和模型凭据。这里不包含凭据，也不打包整个环境。离线对照测试仍依赖原项目中的
历史实验档案及旧版测试夹具，不能将本目录视为包含全部历史数据的独立测试环境。

未来变更请使用下一个候选版本，不覆盖本目录。单轮配置只是计划输入，未创建
训练或 Test 运行。后续执行需要用户另行明确授权。
