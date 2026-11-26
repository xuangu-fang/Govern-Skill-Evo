# SpreadsheetBench v25.4 正式设计

v25.4 从 v25.3 的初始 Skill、空 Memory 和原来的 120 道优化题出发，只替换四个优化模块的提示词。实验问题是：把修改集中在有证据支持的行为上，并明确出错后的处理，能否让进化出的 Skill 在完整 280 题 Test 上超过用作 v25.1、v25.2 对照的 SkillAdam？

| 参照 | 完全成功题数 | v25.4 的判断口径 |
|---|---:|---|
| [v25.3 历史运行](../../../experiments/methods/v25_3/v25_3_spreadsheetbench_proxy/results/v25_3_spreadsheetbench_proxy_test280/summary.json) | 214/280 | 同流程基线，比较逐题得失 |
| [v25.1、v25.2 结果](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/comparison.md) | 223、229/280 | 参照提案筛选和最终交付行为 |
| [Actor 与 v25.1 对齐的 SkillAdam](../../../experiments/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/results/skilladam_v25_1_actor_aligned_20261030_001_test280/summary.json) | 229/280 | 主目标至少 **230/280（82.14%）**，比 v25.3 净增至少 16 题 |
| [较早的四组对照 SkillAdam](../../../experiments/methods/skilladam/spreadsheetbench/shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam/results/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_skilladam_test280/summary.json) | 231/280 | 若也要超过这个历史最高分，则至少 **232/280（82.86%）** |

**设计已定稿。** 四份经认可的英文正文继续使用原文件路径，便于对照审阅记录。[设计清单](design_manifest.json) 固定正文、共享执行说明以及 v25.3 实际训练和测试配置的 SHA-256。

## 四个模块如何配合

| 模块及定稿 Prompt | 要改变的判断 | 保留的分工 |
|---|---|---|
| [Diagnosis](prompt_draft/diagnosis.md) | 从题目要求追到实际提交程序，找出有证据支持的第一个行为偏差。已有检查时，沿错误分支追到程序出口。优先提出一两条独立且可迁移的修改，有额外独立证据时允许更多，也允许零条。 | 读本批 Parent 执行记录，产生原始提案。数量偏好只写在 Prompt 里。 |
| [Preconditioner](prompt_draft/preconditioner.md) | 区分历史结果支持了哪种行为、哪些实现路径仍待确认。若修复提案缺少“仍失败时怎么办”，把具体动作写入有效文本。对已有规则优先局部改写，保留合法空值、类型和交付要求。 | 根据 Parent、当前证据和 Memory 决定 KEEP、REPLACE、WITHDRAW。 |
| [Editor](prompt_draft/editor.md) | 在对应旧条款处落实有效提案。对恢复类提案，保留触发条件、修复、复验、最终失败动作。其他表格操作只写与提案有关的行为。 | 每个有效 ID 生成一份基于同一 Parent 的独立补丁，策略由上游决定。 |
| [Replay](prompt_draft/replay.md) | 区分代码中存在的分支、执行记录能确认的动作、已有证据能确认的输出性质。若两条路径都能得分，在同一条 Knowledge 写清已知结果和未决路径。 | 只解释当前输入中的整题翻转；沿用既有 Update 关联与 null 语义。 |

## 改动依据

- **选择哪些提案。** v25.3 八轮提出 35 条、34 条进入 Gate，其中 24 条没有可关联的整题翻转。它们可能有价值，但联合执行很难区分各自效果。v25.2 每轮最多提两条，是可借鉴的设计；历史成绩不能独立证明这个上限有效。本版采用优先级，不设硬限。对普通表格任务同样适用：如果程序按错连接键，提案应说明如何由任务和表头确定键；如果程序找对了键却写错区域，则修正目标定位。[v25.3 逐轮记录](../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy/campaign/rounds) · [v25.2 设计](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/README.md)
- **经验可以支持多强的结论。** R03 的 H3:H6 由 0/4 到 4/4，但最终工作簿存的是四个静态数值。源码同时具备缓存注入与静态值兜底。正式 Replay 只根据其获配证据写经验；如果分支无法区分，可以记录“读值改善，保留公式未获确认”。R04 的合并区 J23:N23 只有锚点可写，提交结果中 J23 保留公式并读回 January。该程序读取的是输入文件，归档无法支持“保存后进行了验证和修复”。[R03 兜底分支](../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy/campaign/rounds/R03/candidate_runs/train_36097/code/001/program.py) · [R04 提交程序](../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy/campaign/rounds/R04/candidate_runs/train_55060/code/001/program.py)
- **什么经验要进入有效文本。** R07 的成功程序会在读回不符时修复、重读，仍不符则抛出具体错误。程序最终通过，记录并不能证明异常分支被触发。该轮有效 Update 只留下了“直到正确”；同类条件在 v25.2 的 R03 则进入了有效修改。保障应由 Preconditioner 明确交给 Editor，并由 Replay 如实记录观察范围。[R07 成功程序](../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy/campaign/rounds/R07/candidate_runs/val_59595/code/001/program.py) · [R07 有效提案](../../../artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy/campaign/rounds/R07/preconditioner/result.json) · [v25.2 R03 调整](../../../experiments/comparisons/v25_2_prompt_only_20261101_001/campaign/rounds/R03/preconditioner/attempts/001/parsed.json)

## 固定条件与结果解读

实施时以 [v25.3 实际训练配置](../../../experiments/methods/v25_3/v25_3_spreadsheetbench_proxy/config/config.json)、[执行合同](../../../experiments/methods/v25_3/v25_3_spreadsheetbench_proxy/config/campaign/contract.json) 和[测试配置](../../../experiments/methods/v25_3/v25_3_spreadsheetbench_proxy/config/evaluation/config.json)为基准。使用独立目录和本稿四份模板；初始 Skill、Actor、执行环境、模型调用参数、模块预算、数据顺序、评分、重试策略、输入证据范围、每条补丁的 Gate 和 Memory 发布语义均沿用 v25.3。训练八轮，各 15 题；最终 Selected Skill 冻结后进行完整 280 题评估。

主表报告整题成功数、成功率和平均单元格正确率，并对 v25.3 与主对照 SkillAdam 分别给出独赢、独输题数。230 是超过历史点估计的门槛；单次多做对一题不能证明稳定优势。部分 Test 案例已用于历史诊断，报告应披露这一点。训练中可用归档检查改善是否符合预期：修复失败是否触发了有用的执行反馈、要求公式的结果是否保留公式、成功分支是否被过度泛化，以及普通数据处理题有没有退步。训练复盘与最终评分分别报告，避免把一次 Candidate 的结果当作未单独执行的 Selected 子集成绩。

## 版本接入设计

训练和测试的版本标识使用 `v25_4_spreadsheetbench`，方法版本使用 `v25_4_selective_updates_prompt_v1`。配置从清单指定的 v25.3 实际归档派生，逐字段差异限定为 `candidate`、`method.version`。正式实验使用单独的 campaign、测试输出和恢复记录，从第一批与空 Memory 开始。

当前 [消息构造入口](../../../src/skill_evolution/v25_3/stages.py) 直接读取包内模板。实施时在此处按冻结版本选择四份正文，将选中模板的实际字节纳入 campaign 合同。引用规则、共享执行说明的渲染、各阶段证据视图及输入顺序均复用原入口。恢复已有 campaign 时须核对同一份合同，避免前后轮使用不同正文。最终测试仍将训练发布的 Selected Skill 交给原 Actor，四份优化器 Prompt 只在训练阶段使用。

## 接入后的离线验收

1. **版本与消息。** 用同一份历史输入构造各阶段消息，核对优化模块 system 正文与清单逐字一致、user 证据输入相同；Editor 继续只读 Parent、goal 和有效提案。核对同题同 Skill 的 Actor 消息一致。
2. **配置与产物。** 逐字段比较训练、测试配置，检查 8 × 15 个优化任务与 280 个测试任务的有序 ID、初始 Skill、评分器和模型预算。核对输出目录隔离及最终测评 Skill 与训练发布内容一致。
3. **行为审阅。** 用以下已有训练案例审阅模型今后的实际输出。静态检查只能证明版本加载和输出契约，行为达成以届时输出为准。

| 训练场景 | 判读标准 |
|---|---|
| R03：同一程序既尝试修复缓存，又允许退回静态值 | Replay 可记录数值评分改善。若两条路径均可解释得分且执行证据不能区分，Memory 要保留分支的不确定性。 |
| R04：输入文件被重新读取，输出只执行了保存 | Replay 区分读取对象；Preconditioner 判断改进适用的结果类型和可写目标，不把这个样例当作输出复验成功。 |
| R07：一段程序包含修复后报错的分支，另一段程序验证了错误的目标格 | 对前者，区分“有失败出口”和“此次确实触发”。对后者，Diagnosis 优先修正目标定位。恢复类提案中的最终失败动作要能在 Editor 产出的条款里找到。 |
| 普通跨表写入：已有键在不同日期重复；或键正确但目标列错位 | Diagnosis 区分记录匹配与目标定位，仅提出当前轨迹支持的修改；Editor 保留当前有效的写入行为。 |

## 运行入口与验收结果

独立入口为 [run_v25_4_train_test.py](../../../scripts/runs/v25_4/run_v25_4_train_test.py)。使用 SpreadsheetBench 归档解释器运行，`prepare` 核验冻结资产、工作簿、执行环境与评分器，`run` 从独立 campaign 恢复或开始训练，完整发布最终 Skill 后自动测试 280 题。已有运行持有排他锁。

[离线验收记录](../../../experiments/methods/v25_4/v25_4_spreadsheetbench_proxy/reports/offline_acceptance.json)覆盖四阶段消息差异、历史 Actor 消息一致性，以及合成任务训练中断后恢复、发布所选补丁子集并测试最终 Skill。v25.4 两项验收和 v25.3 的 32 项回归检查均通过。正式运行的进度以[独立实验目录](../../../experiments/methods/v25_4/v25_4_spreadsheetbench_proxy/README.md)为准。

[正式实验与四次评测](../../../experiments/methods/v25_4/v25_4_spreadsheetbench_proxy/README.md) 分别列出首测、全量复测和诊断成绩。从仓库根目录执行以下命令。

```sh
python scripts/runs/v25_4/verify_bundle.py
python scripts/runs/v25_4/verify_bundle.py --archive
```

第一条只读取精选材料。第二条还读取本机原始记录，核对训练发布顺序、受测 Skill 和 574 条评测轨迹。
