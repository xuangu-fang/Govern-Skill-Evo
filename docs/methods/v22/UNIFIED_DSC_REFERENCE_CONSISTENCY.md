# V22 统一引用体系：最小整理与验证

## 边界与实现身份

新 profile：`v22.unified_dsc.v6`；引用契约：`v22.typed_references.v1`。基线为 `v22.unified_dsc.v5.minimal`。新实现位于 `experiments/methods/v22/22_reference_consistency/revision`，采用稀疏 Python package 覆盖：只保存改动模块，通过明确的 package 路径继承 21 目录其余实现，没有复制一套平行源码。必须将该 revision 置于 import path 首位。旧目录及冻结档案完全保留。

不修改 D/S/C 策略、Gate、模型阶段数、P1 codec、retire_limits 四字段和认识修订语义。没有自动接受别名、去掉 group 评价对象或修补模型输出。

## 核查结论

| 位置 | 旧情况 | v6 处理 |
|---|---|---|
| Finding.about / open.about | 裸 Requirement/Watch ID；来源字典是带类型 ID | 同一权威目录生成带类型对象集合；验证与模型输入使用同一目录 |
| Finding.refs | 当前 sources 键，含带类型 Requirement/Watch | 保持现有来源范围；历史事件不变成当前来源 |
| Plan.watch.about / open.about | 指向裸定义 ID | 模型输入输出使用带类型引用，解析边界转回原内部编译器表示 |
| Fusion changes.from / watch_changes.from | 裸 Requirement/Watch ID | 带类型引用；to.id 仍为对象定义 ID；原替换和 Watch 迁移校验继续执行 |
| Editor mappings.requirements / issues / 新 Watch | 裸引用 | 同一转换函数处理；已有文本和继承 Watch 格式整理在内部表示上运行后返回标准引用 |
| Requirement.basis / Fusion changes.basis | 当前证据键及阶段允许的 Effect ID | 不增加或削减合法证据范围，不因对象合法就让它成为证据 |
| Memory replace / retire_limits.effect_id | 已有全局 Effect ID | 保持原样，未发明 effect: 前缀 |
| Memory basis / 历史消费 | context_id + 原来源；Hn:: 为当前消费别名 | 保留旧档案和代际身份；新 Finding.about 与新 Editor 实现关联存储带类型引用 |
| P1 | 字典共享但来源身份独立 | codec 不变，编码还原保留每个引用 |

旧 `compact_learning.validate_learning` 使用裸对象集合；`build_learning_payload` 却生成 `requirement:<id>` / `watch:<id>` 来源。这确实是同一对象两种命名。相反，group/event 在 refs 合法、在 about 不合法，是有意的职责边界。

此前三个失败输出的原因不同：20/R2 同时使用 requirement:/watch: 前缀（旧 about 不接受）；20/R1 和 21/R2 将 group 放入 about（即使 v6 也不合法）。测试保留原文件并验证旧结果仍失败；没有将其改写为新实验成功。

## 唯一标准与实现位置

`reference_rules.py` 统一定义 `ref`、对象类型目录 `objects/learning_objects`、字段限定转换 `convert`、模型消费 `input_view` 及输出结构 `shape`。标准为：

- Requirement：`requirement:<原 ID>`；Watch：`watch:<原 ID>`。
- Intent：`intent`；Effect：已有完整唯一 ID（例如 context hash:m1），原样复用。
- Group 与执行事件：继续使用既有完整来源键。
- Finding ID 属于本次响应内部链接（memory_delta.findings/retire_limits.findings），不作为跨模块 Update 对象，保持原格式。
- 旧历史快照保持原契约，通过既有 context/Hn:: 身份与当前轮隔离；不将旧裸字段重写成当前引用。v6 新产生的跨模块引用使用新格式。

合法 about 目录由实际 Plan 和 Memory 确定性生成，作为 `reference_contract.about_objects` 传入模型。group/event 不入目录。裸 Requirement/Watch 引用在 v6 不作为兼容别名接受；不存在的对象、错误类型和来源仍被拒绝。

对象定义与内部编译器继续用局部 ID，因此需要一个显式的类型解析边界。它不是遍历全部字符串的替换器：只处理已声明的对象引用字段，不修改自然语言、实际轨迹、basis 来源、Effect ID 或历史别名。原编译器继续检查存在性、替换关系、Watch 覆盖、实际文本映射和更新条件。旧 profile 走原分支。

改动位置：

- `compact_update.py`：Diagnosis/Fusion/Editor 模型输出的统一边界；原内部校验保留。
- `grouped_update.py`：模型 view/shape 接线；Editor 实现与学习交接。
- `compact_learning.py`：about 校验、Watch 覆盖和来源闭包共用对象目录；新来源快照保留标准引用。
- `train_response_update.py`：将既有 Editor 格式整理放在同一边界内，避免原始 Watch 与标准 Watch 比较冲突。
- `effective_memory.py`：只登记新 profile，退休与应用函数未改。
- `grouped_representation.py`：新 profile 继续走原 P1 编码。
- `continual_runtime.py / continual_verify.py / continual_runner.py`：profile 路由、Editor 交接、覆盖层与继承源码冻结及引用版本绑定。

Prompt 只增加简短字段职责说明并使用同步生成的 shape，不追加任务案例、失败案例修补或退休规则。System 增加 417 字符；这包含通用类型说明、about 目录职责和形状文字变化。接口新增的是消费侧引用目录，不新增模型输出字段。

## 冻结探针

使用真实 08 R2，10 对执行、474 步、3 条历史 Effect；实际 Plan、Skill、diff、事件、合法动作、分组、Memory 与基线完全一致。仅 Editor 映射引用作为导入边界的确定性格式迁移，未改变编辑内容或历史执行。

官方 `deepseek-flash`，P1，temperature=1，thinking enabled，reasoning_effort=medium，max_tokens=65,536，超时 600 秒。授权上限 2 次，实际冻结 1 次；不自动重试。完整消息字符数从 184,687 增至 185,745（约 0.57%）。原始请求、响应、usage、契约结果和失败均独立归档。

## 离线结果与兼容性

最终 421 项 V22 继承回归（85.165 秒）、35 项 Adapter（0.285 秒）、12 项引用专项及 2 项零重试控制器测试（合计 14 项）全部通过。早期新测试中的夹具 ID 假设与测试启动目录错误已定位并修正；未删除旧测试、放宽校验或修改旧结果。

专项覆盖：相同 Requirement/Watch 在 about/refs 使用相同引用；合法与未知对象；group/event 与裸 ID 拒绝；相同局部 ID 的类型区分；来源闭包和 Watch 覆盖；Keep、策略替换、尺度扩大/收窄、关联协调的结构可表达性；Editor 到学习的完整交接及格式整理；历史继承和限制退休；P1 精确还原；原三个失败档案仍按原契约失败；v5.minimal 实际完整消息逐字重建；覆盖源码与继承源码同时进入冻结。

旧 8 份 v3/v4 真实消息精确重建由继承回归覆盖。旧 v5 长说明源码仍留在 20 目录；v5.minimal 留在 21 目录，未被覆盖。新旧规则由 profile 显式选择，旧调用不自动采用带类型 about。

这些离线测试验证引用、路由、来源保真和原行为规则的兼容性，不证明模型能理解自然语言策略或改善任务成功率。

## 真实 Replay／Memory 结果

**本次没有得到可验证的完整模型输出。** 唯一请求 HTTP 200，`finish_reason=length`；响应中可见 content 为空，严格 JSON 与生产解析均失败。模型用完冻结的 65,536 生成额度，服务报告这 65,536 Token 全部为 reasoning；因此不是 about 校验拒绝，而是尚未进入引用/Memory delta 验证。

| 实际输入 Token | 实际生成 Token | 其中推理 Token | 可见 JSON | 耗时 | 请求数 |
|---:|---:|---:|---|---:|---:|
| 61,095 | 65,536 | 65,536 | 无 | 312.31 秒 | 1 |

按此前归档价格口径估算费用约 0.646478 元（输入未缓存 2 元/百万、输出 8 元/百万）；不是账户账单确认。最大输出额度与实际消耗在这次请求中恰好相同，不能据此推断其他调用也会用满。

与此前 v5.minimal 同材料归档输入 60,806 Token 相比，本次增加 289 Token；字符数增加 1,058。没有证据将本次推理耗尽归因于新增引用目录或格式变化，单次调用也不能证明其没有影响。不能把“没有输出”解释为 about、refs、retire_limits 或行为解释已通过。

没有修补输出、提取推理中的片段充当 JSON、追加调用或临时提高预算。授权最多 2 次，本次冻结并消耗 1 次，另 1 次没有使用；不存在自动追加授权消耗。完整原响应和 usage 位于 `preparation/cases/r2_references/response.json`、`call.json` 和 `result.json`，失败成本纳入记录。

## 最终判断

- **已完成**：统一引用代码、模型消费与解析边界、严格字段权限、历史兼容和完整离线验证。此前裸 ID/带类型 ID 的确定性差异已经消除；group/event 仍不能进入 about。
- **没有完成实证确认**：真实模型此次未生成 JSON，故整个 Replay／Memory 契约的模型遵从性、事实理解及条件化学习质量仍待验证。没有观察到可据此定位的新增引用实现缺陷，本次不继续改 Prompt 或算法。
- **其他边界**：旧历史内部定义/旧快照仍按其生成版本解释并通过 context 身份隔离，未偷偷迁移；它们不是 v6 当前对象别名。内部局部 ID 与模型标准引用之间仍有一个必要、集中、受类型约束的转换边界；并非宣称所有历史表示都被统一重写。当前明确检查范围内未发现另一项必须修复的引用差异。
- **五轮准备**：可以继续离线协议准备，但尚不能确认已具备正式启动条件。需要获得一次完整的真实 Replay／Memory 输出来确认新契约；此前大规模输入容量边界仍需在协议中处理。本次生成预算耗尽属于真实调用稳定性未解决事项，尚不能判为 D/S/C 或引用算法缺口。

本阶段停止：0 次 ALFWorld episode，0 次正式 Skill/Memory 发布，未启动五轮实验。

## 证据入口

- 核心引用规则：`revision/src/skill_evolution/v22/reference_rules.py:23`（对象目录）、`:72`（解析边界）、`:110`（消费视图）。
- 学习验证与来源闭包：`compact_learning.py:129`、`:271`、`:285`；编译接口：`compact_update.py:201`、`:217`、`:284`。
- Editor 到学习：`grouped_update.py:192`、`:225`；既有格式整理适配：`train_response_update.py:24`。
- 上述源码均在 `experiments/methods/v22/22_reference_consistency` 下；完整相对 diff 见 `artifacts/methods/v22/22_reference_consistency/analysis/*.diff`。
- `offline/v22_final_tests.log`、`adapter_final_tests.log`、`reference_tests.log` 为最终离线结果。
- `preparation/protocol.json`、`freeze.json`、`input_audit.json` 为冻结预算与事实一致性记录。
- `analysis/model_result.json` 为真实失败、Token 和成本汇总。
