# SpreadsheetBench v25.3 自进化方法设计

状态：优化器与独立运行入口已实现。SpreadsheetBench 的基线取自 [v25.2 冻结配置](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/config.json)。沿用其初始 Skill、Actor 提示、工作簿输入与执行环境、反馈边界、评分器和原优化批次；新一轮进化从初始 Skill 与空 Memory 开始。版本变化集中在优化器如何提出、实施、选择和记住修改。

模型输入去重已补齐，格式为 `v25_3_shared_execution_text_v1`，当前 27 项离线测试通过。下述 19 项为此前领域指导和职责调整时的检查记录；本次没有启动正式实验。

第二项优化已接入 SkillAdam 来源的 SpreadsheetBench 领域指导，完成 19 项离线检查。模块分工、删减记录和来源哈希见[领域指导设计与实施记录](SPREADSHEET_DOMAIN_GUIDANCE_DESIGN.md)。正式实验待后续启动。

后续职责优化已完成：Diagnosis 聚焦当前执行暴露的问题，Preconditioner 对照完整 Parent 与相关 Memory 做 D/S/C 预条件，Replay 迁入原版 v29.6 的行为变化、Update 关联和得分解释区分。已按 SpreadsheetBench 的程序、工作簿及评分证据适配，未引入 `parent_memory_delta_v1`。19 项离线测试通过，详见[职责调整与迁移记录](ROLE_ALLOCATION.md)。

## 一轮的选择单位

v25.2 先 Grouping，再提出带 Checks 的 Plan；Editor 生成整体修改，Gate 根据整批成功题数决定是否接受整个 Candidate，随后 Replay 写入历史。[冻结运行链路](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/frozen_workspace/src/skill_evolution/v25/evolution.py)

v25.3 使用四个模型模块。Parent 是本轮开始时的 Skill。程序先用 Parent 执行全批；Diagnosis 直接读全批，Preconditioner 逐条调整提案，Editor 为每条有效 Update 生成 patch。程序将 patches 一起应用到 Parent，执行一次完整 Candidate 批次。Replay 解释整题结果翻转，程序化 Gate 据此逐条选择，再将选中的 Skill 和本轮 Memory 一起发布。一次联合执行可以产生多个改动的关联证据，不能据此声称测得单条改动的独立效果。

## 四个模型模块的交接

| 模块 | 可读输入 | 输出与职责 |
|---|---|---|
| Diagnosis | 完整 Parent 和本批全部 Parent runs，包括成功、失败和反例 | 输出 `decision/reason/plan`。有修正时，Plan 含 `goal` 和 `updates[{id,text,basis}]`；无修正时返回 `no_change` 和空 Plan（`null`）。依据当前执行直接引用证据，取消 Grouping、Group 引用和 Checks。 |
| Preconditioner | Parent、完整 Original Plan、Plan 引用的完整本轮 runs、按轮只读的 Memory | 每个 Original ID 恰好一个 `KEEP / REPLACE / WITHDRAW`，附 reason；只有 REPLACE 提供完整替换文本。程序保留 goal、原 ID、依据和顺序，编译 Effective Plan。 |
| Editor | Parent、有效 goal 和每条 Update 的 id/text | 每个 ID 交付一个以同一原 Parent 为基准的精确 patch 及实施理由。程序校验定位及冲突，按有效顺序合成 Candidate 和实际 diff。选取子集时仍对同一 Parent 应用。 |
| Replay | Parent、有效 goal/id/text、实际 diff、各 ID 的 patch、发生翻转任务的成对结果和双方正式 runs | 每道翻转题恰好一条事件，含 `task_id/update_id/text`。说明可见程序行为、结果翻转和与实际修改的联系；无法唯一关联时保留 `update_id=null`。 |

**Diagnosis 的拆分原则。** 一条 Update 应当能独立采纳或暂缓。一个行为需要同时成立的触发条件、动作和保护分支放在同一条；即使来自同一道失败题，有独立依据且能分别实施的两个修正也可分开。v25.3 采用参考方法的数量规则，去掉 v25.2 提示中的“每批最多两条”；提案数量由独立、可实施且有证据支持的行为决定。一次失败本身不足以说明 Skill 缺了一条规则。

**Preconditioner 的 D/S/C。** 方向（Direction）判断提议动作是否针对观测到的问题；范围（Scope）判断在什么条件下采用、哪些已有行为应保留；协调（Coordination）判断该修正如何与 Parent 及其他存活提案共同生效。Memory 提供历史行为与结果的记录，当前 Parent 提供现行规则。必要的条件、例外、优先级或对旧条款的处理全部进入有效文本，不能只留在 Editor 看不到的 reason 中。已有提案充分时 KEEP，需要调整时全文 REPLACE，缺乏合理行为增量时可 WITHDRAW。避免拆并 ID 或假设另一条必然被选中。

## SpreadsheetBench 的事件与证据

程序先核验全批配对，包括题目、输入工作簿、Actor 设置、两侧实际 Skill 和独立执行身份，再筛选 `parent.hard != candidate.hard`。整题 hard 取自原评分器：所有目标单元格均正确才通过。单元格通过率、已提供的错格坐标、缺失工作表、程序执行和错误反馈有助于解释变化；仅有局部改善不产生 Gate 事件。Actor 仍只获得原执行器允许的反馈，评分证据供优化模块按阶段读取。[原评分器](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/frozen_workspace/src/skill_evolution/v25/benchmarks/spreadsheetbench/scoring.py)

Replay 追溯到实际提交的程序和对应结果，区分代码中出现的动作、实际运行反馈及最终评分。例如，目标单元格未通过且程序写入过公式，仅凭这两点不能断言公式缓存是失败原因。若两侧同时改了目标区域和写值方式，材料不足以区分是哪条 patch 起作用，就记录观察到的变化并保留 null。沿用 v25.2 的执行时间线、预览和评分字段可见范围；不从参考工作簿补读答案、从截断坐标推断完整错格列表，或把测试任务写入 Memory。

## 模型输入去重

Diagnosis、Preconditioner 和 Replay 在选定各自有权读取的完整 runs 后，统一经过 [execution_input_view.py](../../../src/skill_evolution/v25_3/execution_input_view.py)：

- 保留原有时间线表示：逐次 `request_messages` 由 initial messages、此前正式回答及返回的反馈重建，不反复发送完整历史。这里无损还原的是已选定的正式执行证据，不包含原本已排除的临时格式纠错请求。
- 多条 run 完全相同的 system message 只保存一次，其他位置使用 `shared_message` 引用 `shared_initial.messages` 中的完整消息。不同 Parent/Candidate system 分别保存，只有一处出现的 system 保留原位。
- Replay 中仅对已核验同题 P/Q 的完整 user-message 序列做精确共享；不同题之间不共享 user。题目、工作簿预览和消息元数据保持原样，不使用字符范围引用。
- 保留每次完整 `response`。仅当 `executed_code` 与该回答的 Python 代码块完全一致、且未经执行前改写时，使用 `{"from_response":"python_fence_body_exact_v1"}` 标记；改写过的实际代码继续完整保留。

共享键不是证据 ID。提示明确要求仍引用原 run/step ID，Actor 消息仍属于执行证据。共享表的排列与 v27.2、v28.5、v29.6 一致：Diagnosis、Preconditioner 的 `shared_initial` 在 `runs` 后，Replay 的在 `runs` 前。顶层 Parent、Plan、Memory、执行结果与评分边界不变；Editor 输入不变。

发送前校验共享视图能精确还原原始 payload，重试沿用同一份去重后的基础输入。阶段 `input.json` 保存完整证据，`attempts/*/messages.json` 保存实际发送视图。去重代码位于 v25.3，未修改 v25.2 冻结源码或实验归档；旧准备目录若运行合同不匹配，仍按原机制拒绝混用。

## Gate、Memory 与下一轮

对每条非空 patch，G 为明确关联到该 ID 的 0→1 题数，L 为明确关联的 1→0 题数。一题至多一票。Gate 只读本轮经核验的事件与编辑结果。

| 本轮证据 | 决定 | 本轮 Skill 的处理 |
|---|---|---|
| G > 0 且 L = 0 | Retain | 采用这条 patch |
| G = 0 且 L > 0 | Reject | 省略这条 patch |
| G 和 L 都大于 0，或都等于 0 | Defer | 省略这条 patch |
| 该 ID 的 patch 是空字符串 | null | 保留原文 |

程序把所有 Retain patches 应用到原 Parent 得到 Selected。只有 Selected 文本与本轮实际执行的 Parent 或 Candidate 完全一致，才记录对应执行来源；选出新组合时来源为空，下一轮以该组合为 Parent，不附上完整 Candidate 的成绩。

Memory 按轮追加所有 Effective Updates 的 id、文本和 Gate 决定，以及每个翻转事件的 Knowledge；保留 Reject、Defer、空 patch 和无法归因的事件。被 WITHDRAW 的 Original 留在当轮决策档案。下一轮 Preconditioner 可以使用这些历史记录；原始轨迹和补丁在运行档案中留存。Memory 与 Selected 共用一次原子发布，恢复时以同一提交为准，避免新 Skill 配到旧 Memory。

| 特殊分支 | 行为 |
|---|---|
| Diagnosis 无提案或 Preconditioner 全部撤回 | 沿用 Parent 和已有 Memory，进入下一批。 |
| Editor 全部返回空字符串 | 记录有效 Updates、空决定与空事件，发布原 Parent。 |
| Editor 任一 patch 为 null | 表示无法忠实实施，停止本轮，保存现场，不发布部分结果。 |
| 有 Candidate 但无 hard 翻转 | 跳过 Replay 模型调用；非空 patch 全部 Defer，记录本轮。 |
| 有翻转但都无法归因 | 保存全部 null 事件，非空 patch 全部 Defer。 |
| Gate 所选子集无法合法组合 | 停止发布并保留现场，不以整包代替子集。 |

## 方法来源

- [v26.1 接口合同](../v26_1/CONTRACTS.md)提供四模块输入边界、逐 Update 补丁、翻转计票、停止分支与原子发布的参照。
- [v27.2 Diagnosis](../v27_2/prompts/diagnosis.md)提供可独立采纳的提案划分原则。
- [v28.5 方法合同](../v28_5/CONTRACTS.md)与 [v29.6 方法合同](../v29_6/CONTRACTS.md)提供 Parent、Memory、当前执行证据的职责分配，以及 Replay 区分行为关联与分数解释的参照。迁移范围是共同自进化方法；各 benchmark 的领域指导和 DocVQA 后续专项调优不进入本版。

## 已有实验

- [代理线路正式训练与首测](../../../experiments/methods/v25_3/v25_3_spreadsheetbench_proxy/README.md)，8 轮训练，首测整题成功 214/280。
- [定时任务取消记录](../../../experiments/methods/v25_3/v25_3_spreadsheetbench_20261106_1200/README.md)，训练启动前取消，完成 0 轮。

## 实现与使用

从仓库根目录使用 SpreadsheetBench 的 Python 环境。下列命令在新的独立目录准备初始状态，然后读取当前进度。准备阶段校验冻结源码和工作簿哈希，既不调用模型，也不启动 Docker。

```sh
python scripts/runs/v25_3/run_v25_3_campaign.py prepare --campaign experiments/campaigns/v25_3_spreadsheetbench
python scripts/runs/v25_3/run_v25_3_campaign.py status --campaign experiments/campaigns/v25_3_spreadsheetbench
```

需要真实训练时，同一入口的 `run` 使用已准备目录、原 Actor Docker 镜像和冻结的官方 endpoint；`--rounds 1` 只推进一轮。再次运行从已发布 HEAD 继续，未完成轮次复用落盘的执行与模型响应，已消耗的请求额度跨进程保留。八轮结束后导出 `final_skill.md`。

- [模块合同与 Gate](../../../src/skill_evolution/v25_3/method.py)、[四模块提示词](../../../src/skill_evolution/v25_3/prompts/)及[运行与发布入口](../../../src/skill_evolution/v25_3/campaign.py)。
- [离线闭环用例](../../../tests/skill_evolution/v25_3/test_campaign.py)使用临时合成工作簿、预设响应和本地执行替身；运行命令为 `python -m unittest tests.skill_evolution.v25_3.test_campaign`。

[完整训练与首测入口](../../../scripts/runs/v25_3/run_v25_3_train_test.py) 可用 `prepare --output <新目录>` 准备包含 Docker 运行环境记录的配置。

从仓库根目录运行 `python scripts/runs/v25_3/verify_bundle.py` 核对发布材料。加 `--archive` 可核对本机的 8 次轮次发布、280 条首测轨迹和取消现场。
