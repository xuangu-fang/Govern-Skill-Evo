# v29.6 固定实验边界与后续计划

最新运行状态：用户已授权当前新方案正式训练，并在训练成功后顺序运行最终 Test。已于 2026-11-05T03:35:25.223097+08:00 启动；[实时状态](../../../experiments/launches/v29_6_parent_memory_delta_v1_docvqa160_20261105_033511/status.json)。本次只运行新方案，实验参数不变，未设置定时任务。以下“未启动”表述记录此前设计/离线验收时点，原始成绩仍属于首次 v29.6。

当前生效的领域指南及 [parent_memory_delta_v1 修订](PARENT_MEMORY_DELTA_REVIEW.md) 均未启动实验。下列参数全部冻结；历史启动记录只描述首次 v29.6，不能视为当前修订已获启动授权。

状态：独立运行器、CLI 与配置已验收；正式训练已于 2026-11-05 01:22 启动，成功后顺序运行 Test。没有定时任务，状态见 [status.json](../../../experiments/launches/v29_6_docvqa160_20261105_012220/status.json)。以下参数在 v29.6 配置中保持 v29.5 基准，验收记录见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。

## 1. 逐项冻结

参数权威来源为 [v29.5 配置快照](baseline/v29_5_config.json)，并发来源为 v29.5 CLI 与共享 DocVQA adapter，数据身份来源为冻结 split/manifest。它们的原始路径和 SHA-256 均在 [source_map.json](source_map.json)。

| 项目 | v29.6 保持值 |
|---|---|
| 数据 revision | `539088ef8a8ada01ac8e2e6d4e372586748a265e` |
| 优化池 | `v29_docvqa_optimization160_v1`，原 train 107 + val 53，共 160 题 |
| 批次与顺序 | 原 train 顺序后接 val 顺序；10 批 × 15 + 最后 10 题，共 11 批；逐题 ID 与配置一致 |
| 独立 Test | 原 374 题与顺序，和优化池不相交；只在后续完整训练成功后另行评估 |
| 初始 Skill | [原 DocVQA Skill](baseline/actor/initial_skill.md)，逐字保持；不是空占位文本，不使用 v29.5 最终 Skill 热启动 |
| 初始 Memory | 模型视图 `{"rounds":[]}`；持久化初态为 head=null、memory={rounds:[]}、selection=null、selected_execution_source=null |
| Actor transport / endpoint / model | direct_http / `https://api.deepseek.com/chat/completions` / deepseek-flash |
| Actor sampling | thinking enabled，reasoning_effort=medium，temperature=1.0 |
| Actor 输出预算 | 32,768 tokens，含 provider 计入的 reasoning tokens |
| Actor 执行 | 单轮、无工具、原图；沿用 image_detail=auto 的现有运行约定 |
| Actor 超时 / 连接超时 | 300 / 10 秒 |
| Actor 请求预算 | 最多六次总请求（含首次），技术失败和 length 共用；SDK retries=0 |
| Actor 重试间隔 | 1 秒；length 使用相同消息与预算，不从中选可解析答案 |
| Diagnosis / Preconditioner / Editor / Replay | 同一 endpoint、deepseek-flash、thinking enabled、medium、temperature=1.0 |
| 四个模块输出预算 / 超时 | **每个均为 32,768 tokens / 300 秒** |
| 模块 max_attempts / 重试间隔 | 6 / 2 秒；沿用验证反馈策略，恢复不重置请求额度 |
| 训练 / Test 并发 | **15 / 60**；训练由 v29.5 CLI 显式设置，Test 沿用 adapter.test_workers |
| 输入字符 / 消息字节限制 | max_input_chars=4,000,000；max_message_utf8_bytes=6,000,000 |
| 评分 | `v29_docvqa_skilladam_scoring_v1`；hard=1 iff ANLS≥0.999 |
| Gate | `v29_2_gate_selective_hard_v1`；只按当前关联 hard 翻转计 G/L |
| continue_no_change | true |
| semantic_resampling | false |
| knowledge_review | disabled_v1 |
| retry_policy / memory_publication | previous_output_validation_error_v1 / append_only_head_selected_skill_v1 |

不迁移 v28.5 的 60 题批次、训练并发 60、Editor 65,536、模块 600 秒或 SearchQA 初始化。不能以“Prompt 迁移”为由改变 DocVQA Actor、预算、数据或归一化。

## 2. 实际身份差异

从 v29.5 配置生成的 [v29.6 配置](../../../experiments/configs/v29_6_docvqa_optimization160.json) 只替换 method.version、method.stage_contract 和四份 Prompt 版本为设计值。其余配置逐字段相同，包括全部 batches、initial_skill 和 module_calls。计划与实际身份见 [CONTRACTS.md](CONTRACTS.md) 第 7 节与 source_map.json 的 planned_method / bound_method。

独立运行时、最终评估归档及输出目录使用 v29.6 身份；旧 v29.5 文件和 campaign 保持原样，禁止交叉恢复。未修改的结构契约、输入共享编码、Memory 格式保留原标识。新 Replay 已显式绑定 v29.6 本地 Prompt，原 v29.2 Replay Prompt 不再是本版运行资源；Replay 结构合同及共享输入代码继续复用。

## 3. 静态核对与离线验收

设计静态检查 [validate_design.py](validate_design.py) 验证：验证基线和来源哈希、精确替换与统一 diff、保留的公共/接口段落、冻结参数和分区、四份 Prompt 的 JSON 示例、排除补丁的原段落，以及文档本地链接。脚本只使用标准库读文件并写本目录报告，不导入运行器，不读凭据，不发请求。

离线验收覆盖四份 Prompt 实际加载、独立身份、版本隔离、输出合同、冻结编译、patch 映射与空/null 分支、hard-only Replay、Gate/Memory 发布和恢复预算。复用既有检查并增加 v29.6 绑定检查；合成运行使用临时目录、微型数据和手写响应，禁止网络与子进程。完整真实数据仅用于只读配置及 CLI 预检查，不调用模型或评分运行。不把手写模型响应当作真实 Prompt 效果证据。本设计不增加独立模型评审、固定输入 Prompt 对照或额外训练前试验阶段。

训练与 Test 仍是显式分开的操作，不因文档完成而自动启动。后续若运行，应从原初始 Skill 与空 Memory 开始；训练完整成功后评估最终 Selected Skill，不能把某轮完整 Candidate 的成绩归给未经执行的 patch 子集。

## 4. 观察指标与解释范围

在后续真实实验中，记录 Original→adjustments→Effective→patch→Selected 的交接一致性，以及相关旧规则是否实际被修改、是否出现残留冲突或无授权行为。记录每轮 hard/ANLS、G/L、Gate 决定、Selected 执行来源、请求/token 用量及 Skill 的结构和长度。

最终 Test 使用相同 374 题做逐题配对，区分改善、退步和不变，报告 hard 正确数与 ANLS；不以更少 Update、更多 REPLACE 或更短 Skill 认定成功。最终评分只能支持本版整体效果判断，不能独立识别 Diagnosis、Preconditioner、Editor 或 Replay 的贡献。保留采样波动、联合修改与部分 patch 选择的限制。

设计阶段未读取 Test 问题/答案或加入专项规则；实现阶段的配置预检查由既有数据加载器读取分区和元数据，不将 Test 内容用于 Prompt 修改。既有结果参与过版本讨论，未来报告应保留该开发背景，不将重复使用的 Test 描述为完全未接触的盲测。本次没有产生任何新实验结果。
