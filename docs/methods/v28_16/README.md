# SearchQA v28.16

v28.16 的实现基于 v28.15，写作要求以 v28.14 为准。规则按解题先后直接写在主标题下，用无序列表呈现；每条以简短动作开头，通常用一到两句交代做法和判断依据。每条规则回答一个具体问题。比如“哪些词可以删”和“删掉哪些词会使答案指向另一个对象”应写在同一条中；“题面问容纳地却答成了资源本身”有自己的触发条件、错误选择和纠正动作，可以独立成条。条目的位置和拆合由实际判断决定。

## 初始 Skill

以 SkillAdam 第二次训练的冻结配置中 `initial_skill` 的 UTF-8 原文为准。本地已有逐字节一致的模板，共 104 字节，末行有一个 LF。v28.16 的独立配置直接引用该模板。[冻结配置](../../../experiments/baselines/searchqa_skilladam/v28_11_aligned_batch60_20261109_010205/frozen.json) · [模板](../../../experiments/configs/v28_searchqa_initial_skill.md)

```markdown
# Question Answering Skill

(No learned rules yet. Rules will be added through the reflection process.)
```

## 两个模块分别改什么

| 模块 | 相对 v28.15 的修改 |
| --- | --- |
| [Preconditioner Prompt](prompts/preconditioner.md) | 将“分配章节、必要时跨节迁移”替换为“指出这项更新回答哪个问题、由哪条旧规则负责”。同一选择的新条件、例外、例子优先就地修订。不同判断即使属于同一题型，也可以是两条规则。继续在有效 Update 的 text 中明确写入位置、替换范围和需要保留的区别。 |
| [Editor Prompt](prompts/editor.md) | 保留主标题。每条规则以 `- **简短动作。**` 起头，紧随适用条件和必要例外，已授权的例子缩进放在下方。规则直接写在标题下，版式示例也使用这一结构。首次补丁以原占位句作只读定位，只追加本 Update 的规则。 |

原来的“五条独立 safeguards”随章节分类一起移除。整份 Skill 继续使用 3,000–4,000 字符软预算，每条默认 1–2 个有区别价值的例子；每轮最多四条有效 Update 是训练预算，继续独立适用。

## 首次部分采纳

设计选择是**由 Editor 的确定性文本组合逻辑负责占位句**。v28.16 沿用两个入口，`construct_candidate` 组合全体修改，`construct_selected` 组合选中子集。两者在 v28.16 调用同一条初始模板规则；Gate 仍只决定选哪些 ID。[Candidate 入口](../../../src/skill_evolution/v28_16/editor.py) · [子集入口](../../../src/skill_evolution/v28_16/editor.py) · [Gate](../../../src/skill_evolution/v28_16/gate.py#L116)

1. **按 Parent 内容识别初始状态。** 仅在原始 Parent 与上述 104 字节完全一致时启用。即使前几轮全部暂缓，首次成功采纳发生在后续轮次，也按同一规则处理。
2. **每个模型补丁只拥有自己的内容。** 非空补丁在真实 Parent 的 EOF 插入本 Update 的规则块。以占位句作为只读上下文，首个新增行以 `- ` 开头，块末保留换行。对初始模板的删除、替换、仅空白插入或重写标题均视作无效补丁，进入已有验证与重试路径。已有的空补丁和阻塞语义继续适用。
3. **组合时只移除固定的原始行一次。** 先按原 Parent 的位置验证各个补丁。当前组合中有有效规则新增时，将“删除原占位句所在行（含末尾 LF）”作为一次模板操作，与同一原始 EOF 的规则插入一起组合。保留标题后的空行，相同插入位置按 Effective Update 顺序排列。模板操作不占 Update ID。它只对那个已识别的原始位置有效，不对整份 Skill 搜索替换。
4. **同一结果用于执行、记录和恢复。** 联合 Candidate 在 Actor 执行前已完成组合；选中子集从同一 Parent 和原始补丁重建。保存原补丁及 Parent 到组合结果的真实 `actual_diff`。Gate 的每项 `delta_chars` 继续记录补丁自身的字符变化，共享占位句的删除只在整份文本的 diff 中体现。执行来源按实际文本比较；部分组合没有对应执行时沿用 `selected_execution_source=null`。

假设 u1 至 u4 都提交有效规则补丁：

| 取哪些补丁 | Actor 或下一轮看到的文本 |
| --- | --- |
| Candidate 取全部 | 主标题、空行、四条规则；占位句已退出。 |
| Gate 零采纳 | 原始 104 字节模板，包含占位句。 |
| Gate 只采纳 u3 | 主标题、空行、u3 的规则及其例子。 |
| Gate 采纳 u2、u4 | 主标题、空行、u2 和 u4 各自的规则及例子。 |
| Gate 全采纳 | 与实际执行的 Candidate 逐字节相同。 |

空补丁不触发模板操作。全为空补丁时沿用 `no_change`，有阻塞补丁时沿用 `needs_revision`。一旦 Parent 已包含规则，后续轮次使用常规增删改与子集组合。

## 版本范围与验收计划

独立方法标识为 `v28_16_campaign_v1`，两个新 Prompt 分别绑定 `v28_16_searchqa_preconditioner_rule_ownership_v2`、`v28_16_searchqa_editor_title_bullets_v2`。Editor 的文本组合合同为 `v28_16_editor_initial_rule_composition_v1`，保持原有请求及输出字段。Diagnosis、Replay 复用 v28.15 所用 Prompt 与合同。沿用逐 Update 的 Gate：归因净改善 N ≥ 2 为 Retain，N 为 0 或 1 为 Defer，N < 0 为 Reject。Parent/Candidate 同批执行、Replay 归因、Memory 发布、恢复、数据和调用预算均沿用 v28.15。

离线验收覆盖以下场景：

- 核对新配置加载的模板与冻结文本逐字节相等；检查实际发送的两份新 Prompt 与草案一致。
- 给四个首次追加的补丁穷举 16 个选择子集，按字节比对标题、空行、规则顺序、所属例子和占位句；全选应等于执行的 Candidate，零选应等于 Parent。交换模型返回的 edits 数组顺序，结果依旧服从 Effective Update 顺序。
- 模拟第一轮全暂缓、下一轮只采纳 u3，以及首次采纳后再修订旧规则。核对恢复后重建的 Candidate、Selected、实际 diff 和下一轮 Parent；覆盖空补丁、阻塞补丁和模型误删占位句。

## 运行入口与验收记录

[独立入口](../../../scripts/runs/run_v28_16_campaign.py) · [正式配置](../../../experiments/configs/v28_16_searchqa_train600_batch60.json) · [v28.16 验收用例](../../../tests/skill_evolution/v28_16/test_acceptance.py)

2026-11-12 离线验收通过，含 v28.16 的 5 项测试和 v28.15 的 4 项回归。四个补丁的 16 个子集同时覆盖正常和逆序返回。在三轮模拟执行中，第一轮全部暂缓，第二轮只采纳 u3，在 Gate 记录写入后中断并恢复，第三轮成功修订已采纳的规则。测试比对了各轮的 Parent、Candidate、Selected、完整 diff 和最终导出文本。正式配置通过只读预检。真实模型调用与正式训练、Test 均未启动。[验收报告](../../../artifacts/verification/v28_16_prompt_alignment_20261112/validation.json) · [测试日志](../../../artifacts/verification/v28_16_prompt_alignment_20261112/unittest.log)
