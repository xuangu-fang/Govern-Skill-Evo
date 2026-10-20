# 方法 V22 文档

当前入口：[实验与源码引用导航](../../../experiments/methods/v22/README.md) · [去重收尾与产物归属](../../repository/V22_CLEANUP.md) · [五轮最终报告](ALFWORLD_57_FIVE_ROUND_EXPERIMENT.md)。2026-10-20 已完成目录去重及生成记录忽略；以下保留早期阶段说明，实验最终状态以五轮报告和各恢复报告为准。

[文档总索引](../../README.md) · [V20 方法](../v20/README.md) · [V21 方法](../v21/README.md)

2026-10-15 阶段记录：08 两轮均为7/10→8/10、Gate ACCEPT，第二轮已通过独立Memory恢复完成Skill／Memory共同发布。恢复前声明输出上限65536，保留原输入，仅新增一次Pro调用、零环境执行；Memory由3条更新为5条。第二轮Replay实测并行峰值8。两轮链路已完成，但包含明确恢复，历史预条件化的独立收益仍未证明；一项复合限制的退役范围边界见恢复报告。详见[最新Memory恢复报告](../../../experiments/methods/v22/08_grouped_continual/reports/MEMORY_RECOVERY_REPORT.md)、[分类恢复报告](../../../experiments/methods/v22/08_grouped_continual/reports/RECOVERY_REPORT.md)与[原运行报告](../../../experiments/methods/v22/08_grouped_continual/reports/REPORT.md)。统一主线仍为一次全局分类→独立Diagnosis→Fusion／Editor→Replay→整体成功率Gate→Memory→实际继承；两轮Train不重复，无Direct／Selection／Test。V22离线测试327项通过；恢复另有合成路径和正式发布核验。

此前已完成[07 原 Train 响应与后续更新验证](../../../experiments/methods/v22/07_train_response/reports/REPORT.md)：11 个新 Train episode、7 次语义调用，新增 Selection／Test 为零。旧 Conditioned 修复原 CD 失败；两臂真实反馈生成五条带来源和限制的 Effect。新批次一成功、两失败，后续同信息更新中 Direct 引用历史增加目的地检查，Conditioned 保持要求；Replay 为 Direct 1/2、Conditioned 0/2，但新增检查未实际触发，故尚未验证历史预条件化收益。旧结果、失败及候选原文保留，全部候选仍为 staging。

V22 研究基于诊断预条件化的持续 Skill 自进化，围绕**更新方向、更新尺度、更新方向之间的关联**组织各模块。核心假设是学习 Skill 更新自身的作用规律，据此把初步修订变换为行为影响更合理的实际更新。

响应结构 Memory 是更新器的历史状态，继续承担有价值方向保留、已接受修改纠偏和失败限制复用。空历史时当前诊断与局部构造仍可运行；Issue—Attempt、证据学习和历史保留能力继承 V20/V21，不重新包装为新贡献。

| 文档 | 内容 |
|---|---|
| [GROUPED_TWO_ROUND_PROTOCOL.md](GROUPED_TWO_ROUND_PROTOCOL.md) | 当前统一算法、固定分类、两轮任务与预算、整体成功率 Gate、真实继承、严格流式的单一主线及失败出口；原运行和独立恢复停点分别记录 |
| [CONTINUAL_RUNNER.md](CONTINUAL_RUNNER.md) | 单主线两轮编排、启动预检、调用存档、预算／冻结、异常停点和离线档案核验；默认8并行；真实运行和中止档案可核验 |
| [PARALLEL_SCHEDULING.md](PARALLEL_SCHEDULING.md) | 最多8并行、失败后停止补发并收齐在途任务、旧档案与显式调度修订核验 |
| [08最新Memory恢复与发布](../../../experiments/methods/v22/08_grouped_continual/reports/MEMORY_RECOVERY_REPORT.md) | 独立提高输出预算、复用冻结轨迹，完成第二轮Memory及共同发布；保留失败费用和语义边界 |
| [08真实持续运行报告](../../../experiments/methods/v22/08_grouped_continual/reports/REPORT.md) | 第一轮ACCEPT、真实继承、第二轮分类截断、未完成机制与全部费用 |
| [08 Fusion续行报告](../../../experiments/methods/v22/08_grouped_continual/reports/FUSION_RESUME_REPORT.md) | 实际要求变换、统一Candidate、第二轮7/10→8/10与Gate ACCEPT；Memory截断未发布、完整费用与剩余工作 |
| [08分类恢复报告](../../../experiments/methods/v22/08_grouped_continual/reports/RECOVERY_REPORT.md) | 复用已完成轨迹，分类和Diagnosis有效，Fusion不合约停止；原失败与新增成本分别保留 |
| [CONTINUAL_INTERFACES.md](CONTINUAL_INTERFACES.md) | 当前共享表示、分组来源、实际 Parent 与发布接口的实现边界及离线验证 |
| [DESIGN.md](DESIGN.md) | 更新表示、模块机制、D／S／C 最小规则、跨轮协议、真实材料与构造案例走查、候选技术及阶段安排 |
| [MINIMAL_INTERFACES.md](MINIMAL_INTERFACES.md) | Plan、带限制的作用认识、要求变更、组级落实、稀疏发现及认识增量；设计与独立本地协议的边界 |
| [COMPACT_CYCLE.md](COMPACT_CYCLE.md) | 紧凑 Replay／Memory、独立 Diagnosis、Fusion 增量、Editor、执行及后续学习的实现、预算和核验入口 |
| [FIXED_CONSUMPTION.md](FIXED_CONSUMPTION.md) | 有效认识修订、具体更新规则、完整初稿的空历史／有效 Memory 消费、独立失败与恢复边界 |
| [CONDITIONAL_TRIAL.md](CONDITIONAL_TRIAL.md) | 通用条件化变换、目标与策略区分、同信息普通历史辅助／预条件化 proposal＋共享 Editor、05／06 历史协议及 07 Train Replay 范围调整 |
| [ENVIRONMENT_INTERFACE.md](ENVIRONMENT_INTERFACE.md) | No Skill／固定 Skill 注入、任务与用途、完整可见轨迹、来源及原生结果核对 |
| [NO_HISTORY_ROUND.md](NO_HISTORY_ROUND.md) | 原 v0／v1 无历史更新路径；初稿原样传递、实际 diff 与固定任务执行，旧产物保持原样 |
| [BEHAVIOR_FEEDBACK.md](BEHAVIOR_FEEDBACK.md) | 旧 Editor v1 六方面检查与 Replay 首版；保留其实现和四次真实验证失败的历史 |
| [无历史执行报告](../../../experiments/methods/v22/01_no_history/reports/REPORT.md) | No Skill → Diagnosis → Editor → Candidate；照明 28→7 步、清洁 7→8 步，均成功，Candidate 未采用 |
| [旧行为反馈验证报告](../../../experiments/methods/v22/02_behavior_feedback/reports/REPORT.md) | 四次调用均被输出校验拒绝；原始失败、事实核对和全部成本 |
| [紧凑学习构造报告](../../../experiments/methods/v22/03_compact_cycle/reports/REPORT.md) | 新协议的真实学习、历史消费、要求是否变化、执行、后续认识及独立语义复核 |
| [固定初稿消费报告](../../../experiments/methods/v22/04_fixed_consumption/reports/REPORT.md) | 错误限制退役、u5→u6 的实际变换、语义缺口、重复观察问题、零新环境与全部费用 |
| [新 Train 与条件化验证报告](../../../experiments/methods/v22/05_conditional_trial/reports/REPORT.md) | 三条新 Train、合法 no_change 停点、未触发的构造／独立评价、真实费用和诊断边界 |
| [原 Train 响应与后续更新报告](../../../experiments/methods/v22/07_train_response/reports/REPORT.md) | 不变的旧候选 Replay、分臂真实反馈学习、相关新失败 Train 的同信息构造及对应 Replay |
| [失败 Train 同信息对照报告](../../../experiments/methods/v22/06_failure_trial/reports/REPORT.md) | 两条失败反馈、共同初稿、双分支构造、原文冻结与六任务三臂评价；4/6 对 3/6、两次基线中断、原始定位错误及全部成本 |

紧凑路径保存初稿、有效要求、实际 Skill 和执行反馈，模块交付必要增量。Fusion 按来源改变具体要求，程序装配有效 Plan；Editor 给出文本、组级定位和重要例外；Replay／Memory 共用一次后处理。去掉逐维自证和目标 × 任务输出矩阵，但不把空例外当成保持，也不把可解析引用当成结论正确。

紧凑跨轮路径常规是五次语义调用：旧真实反馈学习、当前 Diagnosis、Fusion、Editor、新执行反馈学习；仅 Editor 明确返回构造问题时允许一次 Fusion／Editor 返工。05／06 的独立对照采用一次共享 Diagnosis＋两侧各一次 proposal／Editor、最多五次的预算。07 另加原 Train 的两次分臂学习，总上限七次；新候选在对应失败 Train Replay，暂停新增 Selection，旧评价不回流。轨迹使用 `deepseek-v4-flash`，自进化调用使用 `deepseek-v4-pro`。不同运行配置及实际成本分别记录。

01—07 阶段沿用 No Skill Parent，因为旧 Candidate 仍未采用。操作内 Memory 可参与后续构造，但不发布全局状态。报告分别记录“历史已提供”“要求变更引用历史”“实际要求／Skill 改变”“执行效果”：恒等是合法决策，不能因此宣称已展示历史驱动的非恒等变换；同任务 Train 执行不证明泛化或收益。

既有真实规则走查只支持带边界的联合认识和部分保持／暂缓判断，搜索分支仍为明确标注的构造案例。新运行保留原始输出中的错误和遗漏，不人工补成成功。初始学习漏读一项非法动作、完整 Memory 证据展开仍偏重等问题单独记录，不能用链路核验通过掩盖。

07 先修正验证顺序与历史适用性：旧候选先回答原 Bread 搜索和双 CD 交付失败是否改善，再从真实联合修改及执行中学习。旧照明／清洁 Memory 保留归档，不因存在就假定适用；本轮两臂各从空状态学习，带来源合并为后续共享认识。这是局部更新器状态构造，不是完整历史继承或活动 Skill 连续发布验证。07 当时的后续构造保留独立当前 Diagnosis、同信息双分支和对应 Train Replay；不强迫变换，不按结果换题或重试，不扩展成功经验、效率优化及模块复杂度。历史读取成本、正式 Gate 与持续发布仍未解决；数值模型继续作为候选。

08 已完成第一轮真实发布及第二轮的要求变换、统一Candidate、十项Replay和Gate。Fusion理由提到历史m3限制，但变更basis只引用当前证据和能力，历史响应的独立作用尚未确认；Gate后Memory截断使第二轮尚未发布。取消Direct和旧任务回归批次，旧实验保持原解释、不充当本轮Memory初值。后续只需明确Memory恢复，不应重跑已完成工作。
