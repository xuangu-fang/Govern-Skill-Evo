# v28.1 实验边界

确认日期：2026-11-03（Asia/Shanghai）。状态：第一至第五步已完成。两个 Prompt 保持第四步审查后的文本，已接入独立 v28.1 配置；145 项离线测试全部通过。见 [第五步交付与验收](OFFLINE_ACCEPTANCE.md)、[审查报告](PROMPT_REVIEW.md)、[Diagnosis](prompts/diagnosis.md) 和 [Preconditioner](prompts/preconditioner.md)。离线验收后，用户已授权启动正式训练，训练完成后自动接最终固定 Skill Test；每 20 分钟监督，训练与 Test 累计最多恢复三次。当前状态见 [运行控制目录](../../../experiments/comparisons/v28_1_searchqa_batch30_20261103/README.md)。

## 目的与待验证假设

v28.1 通过改进 Diagnosis 与 Preconditioner 的 Prompt，提高规则的泛化质量。

待验证假设：v28 的部分负迁移来自把局部纠正方向提升为适用范围过广、优先级过强的规则。改善规则提出与审核，可能在保留学习能力的同时减少这种负迁移。不预设修改后测试成绩一定提高，也不将单次测试差距视为因果证明。

本轮主要算法变量仅为两个 Prompt。按用户本次补充，不设置哈希或 SHA256 校验门槛；这项运行校验简化单独记录，不改变学习、评分或选择算法。

## 唯一主基线与归档来源

使用已完成 20 轮训练及 1,400 题 Test 的 v28 Replay v3：

- Train：`experiments/campaigns/v28_searchqa600_replayv3_batch30_20261102_175059/`
- Test：`experiments/evaluations/v28_searchqa1400_replayv3_batch30_20261102_175059/`
- 控制目录：`experiments/comparisons/v28_searchqa_replayv3_batch30_20261102_175059/`
- 实际配置：`experiments/configs/v28_searchqa_train600_replayv3_batch30_20261102_175059.json`
- 主基线 Test：1164 / 1400，EM 0.8314285714285714，F1 0.9037074829931973。

SkillAdam 的 `batch30_20261102_022539` 完整实验作为外部方法对照，Test 为 1174 / 1400，EM 0.8385714285714285，F1 0.9046423933209647。它的 Momentum、编辑预算、阈值 Gate 等均不引入 v28.1。此前中断的 v28 实验不混入主基线。

参数以已完成运行的实际归档为准。早期文档中的 40×15、Actor 49,152、旧阶段预算和源码哈希门槛不适用于本边界。

## 允许改变的内容

| 模块 | 允许改变的语义 | 必须保持的接口 |
|---|---|---|
| Diagnosis | 区分对象／关系错误、答案边界与参考形式差异；明确相对 Parent／基础协议的决策增量；用 Actor 可见且能支持拟改变行为的条件约束范围与强度 | 原有 `decision/reason/plan`；Update 的 `id/text/basis`；原有 Checks；允许 `no_change` |
| Preconditioner | 分别审核方向、范围与强度；以相关历史证据决定保留、实际修改或撤回；有依据地协调旧规则与优先级 | 原有 Direction／Scope／Coordination、`adjustments/checks`、KEEP／精确 patch／撤回及 Effective Plan 编译 |

执行要求：

- 不能仅凭裸标题、口号、作品列表等题面形状决定回答关系。
- 不能仅凭当前参考答案的形式偏好建立通用措辞规则。
- 条件来自 Actor 可见信息还不够，应说明它为何支持拟改变的对象、关系或粒度；不要求预先完成因果证明。
- 支持尝试一个方向，不自动支持扩展到整个题型，更不自动支持最高优先级。
- 行为条件、强度、例外及必要协调必须进入 Update 文本，不能只写在理由或 Checks 中。
- 已有规则范围不当时，明确提出修订相关条款，避免只追加例外。
- 允许尚未验证但合理的更新；不设置撤回比例，也不要求每项提案必须修改。

第五步已增加独立 Prompt 的选择接线和版本标识；模块输入、输出字段、执行阶段及优化算法保持原样。第二、三步完成独立 Diagnosis 与 Preconditioner 文本，第四步完成联合差异审查，第五步完成独立配置和离线验收。

## 保持一致的执行链路

| 部分 | 边界 |
|---|---|
| Grouping | 分组与证据组织方式不变 |
| Editor | 忠实实现 Effective Plan，不增加独立有效性判断 |
| Replay | 保持 `v28_searchqa_replay_v3`，记录收益、退化、未改善及不确定性 |
| 输入展示 | 保持 `v28_searchqa_pairs_shared_initial_v2` Replay 展示和 `v28_searchqa_pairs_content_v1` 模型视图 |
| Memory | 保持 Knowledge 视图、更新、修订、引用和发布机制；初始为空 |
| Gate | 同批次 Candidate 的 EM 成功数严格大于 Parent 才 ACCEPT，否则 RETAIN；F1 仅记录 |
| 评分与输出解析 | 保持 SearchQA 原有答案抽取、归一化、EM／F1；不增加别名或参考答案 |
| 执行与恢复 | 保持阶段顺序、解析反馈、持久化尝试额度和已完成结果复用；哈希门槛按下文取消 |
| 额外能力 | 不新增工具、Actor 调用、评分反馈补答、Verifier／Repair 或新阶段 |

不限制每轮 Update 数量，不要求固定数量，不设置 Skill 字符数上限。有效 `no_change` 继续后续批次；多个独立且合理的更新可以同时提出。

## 数据、初始化与实验参数

| 项目 | 固定值 |
|---|---|
| 初始 Skill | [baseline/initial_skill.md](baseline/initial_skill.md)，原文 104 字符（含换行） |
| 初始历史 | 空 Memory；不继承 v28 最终 Skill、Memory、checkpoint 或执行缓存；不运行 Stage0 |
| 优化数据 | 原 Train 400 + Validation 200，共 600 题；正文、采样及顺序保持一致 |
| 训练调度 | 30 题／step，20 轮，单遍，无重复无遗漏、不打乱；以保存的实际批次为准 |
| Actor | `deepseek-flash`，thinking enabled，reasoning_effort medium，temperature 1.0 |
| Actor 输入 | 同一基础 Prompt、完整 question/context 和当前 Skill；单轮、无工具 |
| Actor 输出预算 | `max_tokens=32768`，包括服务商计入的推理 token |
| 并发 | Train / Test = 15 / 15 |
| 最终 Test | 同一 1,400 题及顺序；训练完成后只评估最终保留 Skill，不按 Test 选择 checkpoint |
| 输入保护 | 不设置 `context_window_tokens`；沿用 4,000,000 字符／6,000,000 UTF-8 字节输入保护，不截断证据；这是请求保护，不是 Skill 长度上限 |

| 阶段 | max_tokens | 请求超时 |
|---|---:|---:|
| Actor | 32,768 | 300 秒 |
| Grouping | 32,768 | 600 秒 |
| Diagnosis | 65,536 | 600 秒 |
| Preconditioner | 65,536 | 600 秒 |
| Editor | 16,384 | 600 秒 |
| Replay | 65,536 | 600 秒 |

五模块继续使用相同 DeepSeek 模型、thinking、reasoning_effort 和 temperature。Actor 连接超时 10 秒，SDK 重试为 0，技术错误与 length 共用六次总尝试（含首次），等待 1×尝试序号秒。方法阶段最多六次尝试，等待 2×尝试序号秒；解析校验反馈沿用现有机制。正常 stop 的答错不重采样；耗尽不补零分；恢复不重置额度。

如后续沿用原运行监督器，训练与 Test 累计最多 3 次外层恢复，与单任务六次尝试是两种不同额度。本步不创建、启用或修改监督任务及自动化。

正式配置、控制目录和 Train 已独立建立，训练已按用户授权启动；Test 使用 [run_plan.json](run_plan.json) 中的独立路径，在训练结束后由控制器自动创建并运行，不复用或改写 v28 的原始目录。

## 不采用哈希防御

按用户明确要求，v28.1 不需要哈希或 SHA256 防御：

- 不新增哈希清单，不以源码、Prompt、配置或数据的哈希匹配作为启动、恢复或验收条件。
- 使用运行路径、配置值、Prompt 原文和任务 ID／顺序记录实验边界与来源。
- 保留必要的字段完整性、任务唯一性、Parent／Candidate 配对和结果对应关系检查；无完整结果不能冒充完成。
- 不为取消哈希而重写 v28 历史归档。历史文件中已有的相关字段仅是历史记录，不构成 v28.1 的门槛。
- 第五步已解除 v28.1 分支继承的哈希校验，并完成相关兼容接线；尝试额度、原子发布、结果复用及必要的损坏记录处理继续保留。原 v28 分支及历史归档保持原样。

本目录没有新增哈希清单。归档副本用于阅读、差异审查及离线直接内容比较；已选定的 Prompt 文本同时作为运行资源，不使用源码或 Prompt 哈希作为恢复门槛。

## 验收与解释边界

启动前检查两个 Prompt 与原输入输出契约兼容，必要条件能传递给 Editor，无额外调用或工具依赖，不含测试题答案和具体测试补丁。合成输出可验证链路，不能证明真实模型的规则质量改善。

训练后比较 Test EM／F1 与逐题变化、训练错转对／对转错及已接受轮次中的收益与退化，审核 Original Update → Effective Update → 最终 Skill 的方向、范围、强度和重复指导。Skill 长度和 Update 数量只作辅助观察，不作成功标准。

保持以下解释边界：

- 整包 Gate 仍可能保留没有显示收益的 Update；本轮不解决更新级因果归因或细粒度选择。
- Preconditioner 仍围绕当前 Original Updates 工作，不变成任意修复历史规则的独立阶段。
- 同时修改两个 Prompt 只能检验组合效果，不能分离各自贡献。
- 该 1,400 题已被用于设计分析，后续同集结果属于探索性复评；测试内容仍不得进入演化、Memory 或 Prompt。新的独立留出评估不纳入本轮新增工作。

## 本步交付与核对范围

- [baseline/run_identity.json](baseline/run_identity.json)：实际运行路径、完成状态、对照结果及快照来源。
- [baseline/campaign_config.json](baseline/campaign_config.json)：主基线实际配置原文；这是历史副本，不是 v28.1 可运行配置。
- [baseline/runtime_settings.json](baseline/runtime_settings.json)：实际 Actor 和并发参数。
- [baseline/schedule.json](baseline/schedule.json)：20×30 优化批次和 1,400 个 Test ID，无测试题正文或答案。
- `baseline/prompts/`：五个模块实际发送的 system Prompt 原文，运行说明已是 Actor 32,768；不使用源模板中尚未渲染的旧预算。
- `baseline/actor/`：从启动时源码归档提取的 Actor 模板及基础协议。
- [boundary_checks.json](boundary_checks.json)：20 项本地核对结果，全部通过。

核对使用直接内容比较、计数和 ID 对应关系，确认完整训练／测试状态、初始化、批次和测试顺序、数据集间无 ID 交集、实际配置与启动配置一致，以及五模块 Prompt 在 20 轮及保存的尝试中一致。它不是完整运行器恢复审计，也不是 v28.1 的效果验收。

第一步的边界约定及 baseline 副本保持原样。第二、三步分别新增独立 Diagnosis／Preconditioner Prompt、对照差异和核对说明；第四步完成联合审查及三处澄清；第五步完成独立配置、运行接线与离线验收，见 [OFFLINE_ACCEPTANCE.md](OFFLINE_ACCEPTANCE.md)。第五步没有启动实验；随后已按用户明确授权启动正式训练，并启用每 20 分钟监督及累计三次恢复上限。
