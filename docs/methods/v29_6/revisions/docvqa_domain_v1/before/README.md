# DocVQA v29.6：结合 Parent 与 Memory 的更新预条件调整

状态：2026-11-05，正式训练与最终 Test 均已完成：训练于 01:54、374 题 Test 于 01:56（Asia/Shanghai）结束。Test hard 为 325/374（86.8984%），ANLS=0.941317；v29.5 为 331/374、0.947180，SkillAdam 为 325/374、0.940727。配对分析见 [analysis.json](../../../experiments/analysis/v29_6_docvqa160_20261105_012220_comparison/analysis.json)。实验参数保持 v29.5，未设置定时任务。实现与验收见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。

## 1. 基线、目标与范围

**唯一直接方法与实验基线为 v29.5。** 在保留其 DocVQA 证据边界、执行链路、接口和实验参数的前提下，迁移 v28.5 首次冻结设计中关于职责分配、Parent/Memory 联合调整和 Replay 事实忠实度的改动。

本版要检验的假设是：Diagnosis 聚焦当前执行支持的行为提案，Preconditioner 集中判断该提案进入当前 Skill 的必要性、范围与旧规则协调，能否减少重复指导、无依据分支和冲突，同时保留有效能力。Parent 提供当前规则状态，Memory 提供已报告的历史响应。较短 Skill 不是接受条件，也不能单独说明方法有效。

v28.4 与 v29.5 的完整修正策略思想相近，但不是逐字相同的实现；v28.5 的直接基线又是 v28.3。因此本版按职责替换 v29.5 的相关段落，不把 v28.5 全文覆盖到 DocVQA，也不在旧职责后叠加相反要求。

迁移来源固定为 `experiments/automations/v28_5_searchqa600_batch30_20261104_220800/frozen_prompts/`，本地副本见 [首次冻结 Prompt](sources/v28_5_initial/prompts/)。范围明确如下：

| 项目 | v29.6 决定 |
|---|---|
| Diagnosis 减轻 Parent 全面查重、旧规则整合职责 | 迁移；保留相关 Parent 作为执行背景，提案仍需具体完整 |
| Preconditioner 联合 Parent、当前证据与相关 Memory | 迁移；既有覆盖、真实增量、条件交互与旧指导处理由该模块集中判断 |
| Editor 落实旧文字修改及本次实施自查 | 迁移首次设计；不新增独立压缩阶段或行为策略 |
| Replay 同时变化、归一化及事件解释忠实度 | 迁移首次设计，按 DocVQA hard/ANLS 和不可见图片的边界改写 |
| Brutus / R03 分析后的 Preconditioner 支持案例回查补丁 | **不迁移** |
| 同次 Replay 决定性条件核实、未知/不一致强化补丁 | **不迁移** |
| 后续已撤回的 Editor 表达压缩微调 | **不迁移**；首次设计已有的简洁表达要求仍保留 |
| v28.5 逐行表达偏好、SearchQA 规则和运行参数 | 不迁移；保留 v29.5 的完整段落/列表表达与 DocVQA 参数 |

排除的是后续新增要求，不是撤销 v29.5 已有的证据约束，也不是删除首次 v28.5 的一般事实忠实度要求。准确来源、哈希及计划/实际版本身份见 [source_map.json](source_map.json)。

## 2. 完整链路与职责

```text
Parent 全批执行
  → Diagnosis：Original Plan
  → Preconditioner：逐 Original 的 KEEP / REPLACE / WITHDRAW
  → 程序编译 Effective Plan
  → Editor：逐 Update patch → 程序构造完整 Candidate
  → Candidate 全批执行
  → Replay：仅 hard 翻转事件 Knowledge
  → Gate：选择 Retain patches
  → 原子发布 Memory 与 Selected Skill
```

上图为有候选时的主路径；无修改、全部撤回、空/null patch 和无 hard 翻转分支仍沿用 v29.5，见 [接口合同](CONTRACTS.md)。没有 Grouping、额外 Reviewer、独立压缩器、组合复测或新增模型阶段。

| 模块 | v29.5 | v29.6 |
|---|---|---|
| Diagnosis | 在提案中同时选择完整修正策略与必要旧规则处理 | 提出当前证据支持的完整行为修正；Parent 全面整合留给 Preconditioner |
| Preconditioner | 审查、调整上游已提出的修正策略 | 集中识别当前 Parent 的覆盖与行为增量，结合历史响应形成完整可实施的修正 |
| Editor | 忠实实施修正、保留无关有效指导 | 保留上述职责；强调实际修改旧文字、避免重复复述，并检查本次实施造成的冲突 |
| Replay | 记录 hard 翻转并关联实际修改 | 进一步区分答案变化、Update 关联和分数解释，保留影响解释的同时变化 |
| Gate / Memory | 确定性选择、顺序存储与原子发布 | 不变 |

### Diagnosis：完整行为提案，不承担全面整合

Diagnosis 仍读取整个当前 Parent 批次及完整 Parent，考虑成功、失败和反例。对每项提案说明改变什么行为、适用条件、强度、必要行为依赖与保护边界，并在 basis 中引用决定这些边界的直接执行证据。

它可以指出当前可见的冲突，但不再要求完成所有相关旧规则的删改安排、跨段落去重或整体优先级设计。失败不自动说明缺规则，已有规则也不自动说明无需修改。提案仍按共同问题和修正方向组织，不按句子、任务数量或未来 Gate 去留机械拆分。保留 v29.5 的完整段落/列表表达；不恢复逐行独立要求。

### Preconditioner：决定提案如何进入当前 Skill

1. 理解 Original 的问题边界和拟改变的行为。
2. 阅读所有相关 Parent 指导，包括其他段落中的条件和例外，判断已有覆盖、真实增量与冲突。
3. 结合当前引用证据和相关 Memory，调整 Direction、Scope 与 Coordination；无相关历史不阻止合理提案，也不要求为了展示调整而 REPLACE。
4. 明确相关旧指导需替代、限定、整合或删除的部分，以及有依据的有效分支。
5. 检查 Parent 与存活 Updates 的预期共同含义，输出 KEEP、完整 REPLACE 或 WITHDRAW。

这些是职责说明，不增加输出清单或字段。KEEP 必须表示全文已足以作为当前 Parent 中的合理修正；必要旧规则处理只写在 reason 里时，应改为完整 REPLACE。整合旧 Skill 规则不等于合并 Update IDs。相关修正不能依赖另一 Update 未来必然被 Gate 保留。

Parent 已在 v29.5 输入中存在，本版改变的是使用职责，不新增 Parent 输入。Memory 的范围、未知信息解释和历史证据权限不变。

### Editor：忠实实施及局部自查

Editor 只收到 Parent 和 Effective Plan 的 goal、updates[id,text]。它负责措辞、位置和精确 patch，不重新决定行为策略。要求替代或删改旧指导时，应实际修改相应文字，不能靠新增平行警告保留旧冲突；确需新增时也不强行合并。

允许在授权范围内简洁表达、避免无意义复述，保留所有材料性条件、例外、强度、优先级和依赖。调用内检查实际修改引入的重复、残留旧要求和冲突；未获授权的关键策略选择仍按 patch=null 合同处理。这里没有迁入后续 Editor 表达压缩补丁。

### Replay：说明发生了什么，再解释关联

先完整比较可见答案差异，再区分哪些变化与实际 patch 相符、哪些同时变化限制对得分翻转的解释。答案选取、增删内容、转录、标点和空白变化均按实际材料判断，不只选取最符合 Update 意图的一项。

DocVQA 归一化仅小写、去首尾空白和合并空白，不删除标点、冠词、单位等。优化模块没有图片，不能根据答案或 reference 声称已看到字段、版面或文字；Actor 对图片的描述仍是 Actor 的报告。Knowledge 的条件和结论限于当前事件，一般因果免责声明不能替代具体事实。多项答案变化不自动要求 null，原有明确行为关联合同不变。

## 3. 保持不变的边界

- Actor 看原图；优化模块不看图片、OCR、独立 caption 或隐藏 reasoning。DocVQA 任务特征、完整文本投影、共享编码及原始归档不变。
- Original Goal、ID、顺序、basis 冻结；REPLACE 替换完整 text，WITHDRAW 删除对应项，不拆分/合并 IDs。
- 所有 patch 定位同一原始 Parent，保留精确匹配、多 hunk、逐 Update 映射、冲突校验、空 patch 与 null 的原语义。
- Replay 只看 hard 翻转；ANLS 仅诊断。Gate 不加入长度、净收益、历史投票或新兜底。
- Memory 仍只保存 Effective Updates、Gate 决定与事件 Knowledge；不追加未翻转执行、历史原图、patch 或新的归因字段。
- 完整 Candidate 被执行，不保证选择后的 patch 子集已执行或语义独立；保留 `selected_execution_source` 的真实来源标记。
- 数据、批次及顺序、初始化、模型、预算、超时、重试和并发全部保持 v29.5。具体值见 [实验计划](EXPERIMENT_PLAN.md)。

## 4. 交付与验证边界

| 文件 | 内容 |
|---|---|
| [Diagnosis](prompts/diagnosis.md) / [Preconditioner](prompts/preconditioner.md) / [Editor](prompts/editor.md) / [Replay](prompts/replay.md) | 四份独立可读的完整英文 Prompt，无需拼接其他文件 |
| [CONTRACTS.md](CONTRACTS.md) | 接口、职责交接、证据、Gate/Memory 和运行分支 |
| [PROMPT_REVIEW.md](PROMPT_REVIEW.md) | 相对 v29.5 的逐项差异、来源选择与静态审阅 |
| [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) | 完整冻结参数、运行边界与分析方式 |
| [diffs](diffs/) / [changes.json](changes.json) | 标准 unified diff 与精确替换记录 |
| [baseline](baseline/README.md) / [source_map.json](source_map.json) | v29.5 快照、来源和哈希 |
| [validate_design.py](validate_design.py) / [design_validation.json](design_validation.json) | 可复现的静态核对与结果 |

静态检查用于确认范围、快照、差异、保留段落、JSON 示例和参数一致性；运行时接入与恢复分支另由离线验收检查。独立代码、CLI 和配置已建立，原设计与受保护基线快照保留。上述离线验收未调用真实模型。其后已获正式运行授权并启动独立 campaign，训练完成后顺序运行 Test；未设置定时任务。验收快照中的未启动标记描述验收结束时的历史状态，实时运行状态以上方链接为准。

本版没有预设能缩短 Skill 或提高 Test。v28.5 的 SearchQA 结果同时受 Prompt、批次、并发和 Editor 预算变化影响，不能据此断言单个方法机制的收益，也不将该实验的答案或具体补救规则迁入 DocVQA。
