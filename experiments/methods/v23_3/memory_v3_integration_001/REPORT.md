# v23.3 Memory v3 接入与真实 A/B 结果

2026-10-21（Asia/Shanghai）

**已完成接入。v23.3 Preconditioner 默认使用已验收的 Memory v3 模型视图；正式 B 生成、编译和归档重载成功，随后完成同输入、同参数的 A/B。**

研究结果不等同于工程通过：**B 全部 Keep，没有实际 Patch；A 修改 u1/u2 并引用历史 Memory。当前不能认定 v23.3 的修改粒度或策略质量优于自由替换。** 两组理由/策略均存在限制，详见独立评价。

## 正式代码与归档

- [memory_view.py](../../../../src/skill_evolution/v23_3/memory_view.py)：从完整 Memory 确定性构建已验收视图。±2 历史证据窗口、完整动作反馈 trace、显式 before/after、按内容共享的全局菜单、完整来源步骤 ID 均保留。
- [preconditioner.py](../../../../src/skill_evolution/v23_3/preconditioner.py)：`messages_for` 默认使用 v3；`model_input` 提供实际模型视图。完整 `preconditioner_input` 仍供 Patch 编译，不用压缩视图替换完整校验数据。
- 新归档保留完整 `input.json`、`run.json.memory`，另存 `model_input.json`，记录 `run.json.memory_view`。加载时重新生成视图/消息、重解析原始输出并重新编译。
- 没有视图版本的旧归档按原 `entries_sources` 恢复；显式旧格式调用可传 `memory_view="entries_sources"`。不同视图不能静默复用同一目录。
- 原 V23 默认行为不变。实验 A 通过同一 `project_messages` 适配，与 B 的 user content 逐字符串相等。正式模块不导入实验目录。

通用说明：[memory_view_prompt.md](../../../../src/skill_evolution/v23_3/memory_view_prompt.md)；接口说明：[README](../../../../src/skill_evolution/v23_3/README.md)。修改前快照和 [implementation.diff](results/implementation.diff) 已保存。

## 离线验证

v23.3 **134 项通过**，包括五组已验收视图逐字段相等、输入不变、空 Memory、来源身份验证、A/B 同输入、真实旧归档及 Editor 归档恢复、新旧版本恢复、版本/视图篡改拒绝，以及各类合法 Patch、撤回、Keep、停点和失败保存。

V23 扩展回归为 **543 项通过、9 项 setup errors**。9 项全部来自 `test_formal_evaluation.py` 的旧正式评估冻结检查，当前旧 V23 代码与该历史冻结不一致。逐文件摘要确认，涉及的 editor/evolution/grouping/preconditioner/model_routing 五个文件与本轮开始时一致；本轮没有改动它们。没有绕过旧冻结，也没有把这 9 项报告为通过。

因此合计 **677 项通过，9 项已有冻结不匹配错误**。本次相关投影/编译/恢复门已通过，旧正式 Test 恢复问题单独保留。证据见 [offline_tests.json](results/offline_tests.json)。

## 实际生成配置与输入

复用首次 P3-A 已成功的真实 Diagnosis，不重新采样。Original 的 u1/u2/u3 仍分别为 3/3/2 行；Parent、当前 runs、完整 Memory 与当时一致。正式投影后的实际 payload 与已验收 P3A_B 样本逐字段相同，见 [input_equivalence.json](results/input_equivalence.json)。

A 为原 V23 自由替换 Prompt / `to.text`；B 为 v23.3 Prompt / `to.patch`。两组追加相同格式说明，user content 完全相等，模型与参数相同。

内网 deepseek-v4.1-flash，temperature=1、thinking enabled、reasoning_effort=medium、stream=false、timeout=(60,300)。**max_tokens 在发送前共同固定为 32768**，包括 reasoning 和最终输出；因为此前两次 16384 输出预算均被 reasoning 用尽。没有根据结果追加预算。

先冻结 A/B，再调用正式 B 并独立评价；B 的这一次结果直接成为 B 臂，随后只调用一次 A 并评价，不重复生成 B。B 允许合法 Keep 通过生产门，但不能把 Keep 当成真实 Patch 作用验证。协议与配置见 [PROTOCOL.md](PROTOCOL.md)、[freeze.json](config/freeze.json)。

## 两次实际调用

| 指标 | A 自由替换 | B v23.3 |
|---|---:|---:|
| 调用顺序 | 第二次 | 第一次 |
| HTTP / finish_reason | 200 / stop | 200 / stop |
| 正文大小，字节 | 961,087 | 963,910 |
| 耗时，含本地编译/重载 | 61.20 秒 | 67.58 秒 |
| 实际 prompt_tokens | 277,951 | 278,659 |
| 实际 completion_tokens | 17,369 | 14,107 |
| 其中 reasoning_tokens | 16,116 | 13,365 |
| 实际 total_tokens | 295,320 | 292,766 |
| 编译与重载 | 通过 | 通过，正式加载器 |
| 决策 / 调整数 | ready / 2 | ready / 0 |

总计 **2 次逻辑调用、2 次 HTTP，0 重试；588,086 tokens**。输入 556,610，输出 31,476，其中 reasoning 29,481 已包含在输出内。货币费用未返回，未知。正文发送时 socket timeout 均为 60 秒。

相比此前相应完整 Memory 请求，实际输入 A 从 474,697 降到 277,951（减少 **41.45%**），B 从 475,369 降到 278,659（减少 **41.38%**）。压缩节省明显，但仍有约 28 万输入 tokens。

当前与早先失败调用同时改变了输入表示和预设输出上限，不能把完整生成成功单独归因于压缩。A 的输出 17,369 也超过旧 16,384 上限。此次 A/B 之间配置一致。

## 独立评价与比较

B 评价在 A 调用前落盘：[B_EVALUATION.md](results/B_EVALUATION.md)。A 随后独立评价：[A_EVALUATION.md](results/A_EVALUATION.md)。评价者为同一当前分析者，不是盲评、双评或额外模型 Judge；未使用内部 reasoning 文本评分。

| 维度 | A | B |
|---|---|---|
| 实际 Update 变化 | u1 三行替换为三行，u2 三行替换为四行，u3 不变；三个 checks 改写 | 全部 Keep，Effective 与 Original 相等 |
| 变换动机 | 精确类别例子、同类别不同位置覆盖，明确引用 M8/M3/M6 | 主要据当前 runs 保留原要求，承认重复规则收益未知 |
| 历史参与 | 有可追溯引用及历史案例对应，但不证明逐条核查原始轨迹 | 最终回答无 M 或历史来源引用，未观察到可追溯参与 |
| 新增风险 | 加强所有未检查位置的覆盖优先顺序；新导航兜底与 u3 direct-action 分支可能冲突 | 无新增文本承诺，但原 u2 对已检查位置的记忆边界未处理 |
| 事实与归因限制 | 把未执行的 Original 与 Parent 已执行近似条款混用；显式例子的单独因果效果未建立 | P8 从未检查 bathtubbasin 的断言错误；把导航回访描述成 reopen 等 |
| 实际行为收益 | 未验证 | 未验证 |

关键原始核查：

- B 称 P8 从未检查 bathtubbasin，实际 **P8:2 已到达 bathtubbasin 1 并观察为空**；这一当前 run 没有经过历史 Memory 压缩，不能据此断言压缩导致错误。
- B 的 P6:6/10/16 均是 `go to drawer 1`，并非重新开门；重复回访方向成立，具体动作表述不准确。
- A 所用同类位置覆盖例子可追溯至 S1_R03/P2:15/16 的 countertop 3 bread 与 Q2 的漏查，但不足以推出“所有剩余同类及异类都查完才允许任何返回”的普遍最优策略。
- P6:20→21、P8:5→6 展示了导航不可用而 direct open 可成功；A 新 u2 的“导航不可用则去别处”没有明确保留该分支，与未改的 u3 存在协调风险。

具体语义差异见 [A_effective.diff](results/A_effective.diff)；[B_effective.diff](results/B_effective.diff)为空是因为没有文本修改，不是缺少结果。所有原始输出与 Effective 均保存。

三个研究问题分别结论如下：

1. **更新粒度：无法判断 B 是否改善。** B 没有实际编辑样本，不能把零修改当作精准修改。真实 Patch 应用仍只有离线覆盖，当前真实 B 是 Keep。
2. **历史参与：A 有可追溯线索，B 未展示。** 没有 no-Memory 对照，不能断言因果增益，也不能证明 B 内部完全没用历史。
3. **策略质量：没有可证明的赢家。** A 有合理具体化也有新增强约束；B 保留风险并存在事实叙述错误。没有 Editor 或 Replay，不能给出成功率、效率或稳定性优越结论。

## 完成范围与后续边界

本轮目标已完成：正式接入、离线集成检查、一次真实 B 生成/编译/重载、复用 B 的同输入 A/B 对照。可在后续 v23.3 实验中使用这版 Memory 输入机制；不因本轮没有证明策略优越而撤销已验收的输入格式。

当前没有注册为全局默认方法，没有运行真实 Editor、Actor、Replay、Memory commit 或最终 Test。没有修改 Prompt 来追求更好结果，也没有因 B Keep 而追加采样。

若继续研究 v23.3 的效果，应将问题转向“为何已有历史反例未触发 B 的变换，以及原始要求是否能由 Actor 的局部记忆执行”，另行设计后续实验；本次不能通过挑选更多生成结果来证明优势。

本轮只改动计划内的三个既有文件，并新增 Memory 模块、格式说明、测试及本实验目录。4,137 个既有相关文件中没有非预期变更；冻结输入核验通过。见 [source_protection.json](results/source_protection.json)、[summary.json](results/summary.json)。
