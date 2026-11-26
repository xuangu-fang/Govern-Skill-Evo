# V25 对照与 V25.1：拟议实验定义

状态：等待审阅。这里是接入设计，不是可直接运行的配置或启动命令。

## 两组定义

| 项目 | V25 对照组 | V25.1 修改组 |
|---|---|---|
| 实验标识 | `v25_common_actor_no_review_control` | `v25_1_current_update_preconditioning` |
| 共同配置基准 | `experiments/configs/v25_sheetbench_upstream_actor_no_review_20261030.json` | 同左 |
| Actor system/user/feedback | 本稿 `common/` 三份 Actor 模板 | 同左，逐字一致 |
| 优化器环境说明 | 本稿 `common/execution_context.md` | 同左 |
| 初始 Skill | 本稿 `common/initial_skill.md`，与旧实验相同 | 同左 |
| 初始 Memory | 原配置下的新实验初始状态 | 同左；不继承旧实验或另一组的 Memory |
| Preconditioner 正文 | `baseline/preconditioner.md` | `v25_1/preconditioner.md` |
| Preconditioner Prompt 标识 | 保留原 `v25_preconditioner_evidence_decision_boundaries_v7` | 拟用 `v25_1_current_update_evidence_to_behavior_v1`，尚未注册 |
| Verify/Repair | `disabled_v1` | 同左 |
| Gate | Candidate 成功任务数严格大于 Parent 才接受，否则保留 Parent | 同左 |
| Diagnosis/Editor/Replay 等其他模块 | 原冻结逻辑和 Prompt，仅加载共同环境说明 | 同左 |
| Actor/优化器模型与凭据 | 官方 `deepseek-flash`，原凭据来源；不保存密钥 | 同左 |
| 训练数据 | 原 Train 后 Val 顺序，120 题，8 批，每批 15 题，1 个 epoch | 同左 |
| Test | 各自训练完成并校验后的最终 Skill，完整 280 题 | 同左 |
| 采样、并发、超时、请求重试、评分兼容 | 基准配置原样继承 | 同左 |

Actor 输出上限 49152；优化器基础输出上限 16384；Diagnosis 32768、Preconditioner 与 Replay 49152，其他模块保持基础上限。移除 Verify/Repair 的模块预算只表示这些模块不执行，不把节省的预算分配给其他模块。

原采样参数保持原样，不额外注入 seed、降低温度或调整推理设置。两组模型调用彼此独立；同配置不意味着随机输出逐次相同。历史 SkillAdam 的个别 Momentum 恢复授权不属于这两组 V25 实验的参数。

## 完整接入清单（待批准后实施）

1. 以原实验的冻结代码作为运行行为基准，并纳入已完成的关闭审核分支。当前工作区与原冻结代码存在其他差异，不能整目录替换后假定等价。
2. 两组同样加载本稿共同 Actor 与 execution_context，保留原渲染接口：system 使用 `skill_section`，user 使用 `instruction / task_metadata / workbook_preview`。保持原 task metadata 的类型与 answer region 结构；不增加 worksheet 提示或额外策略。
3. 初始和后续各轮使用相同 Actor 模板；Skill 插入的方式保持一致。原错误反馈模板和消息历史/格式纠正逻辑保持原样；不把运行日志或评分当成新反馈。
4. 注册 V25.1 的独立 Prompt 标识与版本元数据，不覆盖 V25 标识或旧实验。底层运行实现可复用，但对外实验身份和冻结 Prompt 哈希必须区分；命名变化本身不引入算法差异。
5. 建立新的独立输出目录、状态与缓存；保留旧实验。使用相同配置基准生成两组配置，审计差异只含身份、路径、Preconditioner 标识及对应正文。
6. 冻结实际源码、Prompt、配置、数据清单和评分兼容逻辑，记录哈希。验证所有优化器的实际注入环境说明与 Actor 消息一致。确认旧的含预算 Actor 模板没有被意外加载。
7. 离线验证成功后，按用户审阅后的明确启动范围运行。本文不提供或执行启动命令，不创建定时任务。

当前关闭审核的 JSON 仅冻结参数，未安装本稿模板。不能直接以它启动并声称运行了本对照。

## 审阅后的行为检查建议

这部分涉及真实优化器请求时需要在批准的执行范围内进行；目前仅列检查标准，没有调用模型。

使用历史训练轮次当时冻结的 `model_input.json`、Parent、Original Plan、runs 和当时已有 Memory；不追加该轮之后的 Replay、参考答案、测试结果或新的历史记录。旧输入须明确保留其真实 Actor 环境，不可把共同新 Actor 说明伪装成旧轨迹的执行条件。

| 历史案例 | 检查重点 | 不应强求 |
|---|---|---|
| R04 u2：计数语义 | 不把分数或不匹配坐标直接升级成确定的分组关系；根据当时信息决定是否有必要改变触发条件 | 固定选择我们预写的某一种分组方案 |
| R05 u2：未匹配与空值 | 将 Memory 中的具体反例及条件迁移到当前 lookup Update，避免自动生成相反通用默认值 | 所有 lookup 一律留空或一律报错 |
| R04 u1：列位置与示例 | 修改冲突的布局时保留非冲突的配对信息 | 为了更保守而取消必要列调整 |
| R06 u1：指定起点 | 保留有效的修改方向；明确未覆盖区域的保留边界 | 所有已有内容一律保留，无视完整替换任务 |
| 无明显缺陷的原 Update | KEEP 有具体理由；缺乏历史证据不自动导致修改或撤回 | 要求每次都产生 patch 或更多 Memory 引用 |

历史输入检查用于观察模型是否理解新指令；它不能证明新共同 Actor 下的训练表现或测试收益。若用这些训练案例迭代 Prompt，应如实记录为开发过程。

## 离线接入与正式结果的验收

离线阶段检查：
- 两组实际 Actor 消息逐字一致（任务和当前 Skill 相同时），只在生成的 Skill 不同后自然产生差异。
- 两组 Preconditioner 输入、输出契约、patch 解析器一致；第 5—7 节契约不变。
- Verify/Repair 不被调用，Replay 结构和引用校验继续生效；恢复不重复调用已完成步骤。
- Gate、Actor 环境、模型、采样、预算、数据顺序、评分规则没有额外差异。

正式报告至少包含：
- 280 题成功数及 hard 成功率、任务级 per-cell 平均分，两组共同任务上的得失配对。
- 每轮 Gate 的 Parent/Candidate 成功数与决定、最终发布的 Skill。
- 当前 Update 的重要边界是否从 reason 落实到有效 Update、Editor 是否实现；结合轨迹区分有执行机会、实际执行、结果变化。
- KEEP、修改、撤回的分布，Skill 长度、模型调用与费用；这些是解释性指标，不以更多引用、更短 Skill 或更高接受率作为目标。
- 失败、恢复及运行期间任何参数变更；不能静默修改其中一组。

同一对照中的唯一算法差异为 Preconditioner Prompt。单次对照可给出该次结果，不能消除模型随机性；如需更强结论，再单独授权重复实验。当前计划不包含自动增加种子、No Skill、SkillAdam 或额外 Gate 消融。

已经分析过部分 280 题测试失败案例，应披露其不再是完全未参与开发的测试集。新 Prompt 不写入这些案例或解法，不根据新测试失败继续逐题调参；若需独立泛化证据，另行安排未用于开发的数据。

## 方法边界

Replay 的证据经 Memory 影响下一次相关 Update；不改变本轮 Gate，不在 Candidate 评估后插入修复再发布，也不新增发布否决。若后续 Update 未涉及某条已发布问题规则，本方法不主动回退它。V25.1 的预期改进是历史证据对当前更新方向、范围、强度和协调的实际作用，尚未由实验验证。
