# P3-C1 R05 Candidate Replay 协议

本协议在任何真实 Editor/Actor 调用前冻结。比较两种方法各一次 Preconditioner 结果、各一次 Editor Candidate 的探索性端到端行为，不能分离 Prompt、输出表示及 Editor 随机性的独立作用。取消输出格式对照。本轮只执行 R05 和新 Train 预注册，不进入下一轮。

## 来源与阶段门

读取并重新解析 memory_v3_integration_001：A 用其原适配层 load_a 复核真实 raw/parsed/Effective；B 用正式 V23.3 load_preconditioner 恢复。原 compile_effective_plan 复核，Editor 使用原 editor_input/messages_for/validate_editor/apply_patch/actual_diff/load_editor。Adapter 只负责输入衔接、一次调用与归档，A 不伪装成 Update Patch。

Original、Parent、历史 Memory 和当前证据相同；A 修改 u1/u2，B ready/全部 Keep。两组 Editor 输入只有 Effective Plan 不同；B Keep 不等于 Editor 不改 Skill。Parent/Original/Memory/Effective 不人工修正，不运行 Diagnosis/Preconditioner、Replay 知识生成、Gate 或 Memory 更新。

阶段0：来源装配、新任务清单、两次无动作 reset、协议、配置和预算全部冻结。阶段1：A 然后 B 各一次 Editor，解析/应用/重载且完成实际 Diff 审计后才能 Replay。合法 Editor no_change/needs_revision 或格式失败不重采样；无有效 Candidate 的分支不运行，另一有效组可与 Parent 比较但不宣称完整三方对照。共性环境或调用契约阻碍停止受阻分支。

## Editor 固定配置

原 V23 Editor Prompt，渲染原 Actor background；内网 `http://llm-proxy.intra.xiaojukeji.com/chat/completions`，`deepseek-v4.1-flash`，temperature=1、thinking enabled、reasoning_effort=medium、max_tokens=16384、stream=false。采用原生产 Editor 生成预算；timeout=(60,300)。每组只一次 HTTP，无技术重试，无格式/内容修补。冻结 messages 完整保存。

## 四个固定开发实例与 Parent 重执行

| 原编号 | task_id | 原归档任务请求 | 任务族 |
|---|---|---|---|
| P3 | val:0003 | put some mug on sidetable. | pick_and_place_simple |
| P6 | val:0006 | put a clean butterknife in drawer. | pick_clean_then_place_in_recep |
| P7 | val:0007 | clean some butterknife and put it in drawer. | pick_clean_then_place_in_recep |
| P10 | val:0010 | cool some apple and put it in microwave. | pick_cool_then_place_in_recep |

规范 gamefile、实例、原 run_id 对应轨迹、文件摘要保存于 tasks.json。它们是原实验优化池里的 valid_seen/val 开发任务，**不是新的 Train 任务，也不是最终 Test**。来源由 Grouping sources→历史 trajectory→edition manifest 三者核对，不从报告猜测。

历史 Parent 轨迹有效，固定 seed=42 的新环境两次 reset 与历史初始观察和完整候选菜单相等。但旧 Actor 为外网 deepseek-flash，当前 route 使用内网 deepseek-v4.1-flash，且执行实现摘要不同，不能证明模型与实现完全等价。因此不把历史 Parent 当严格配对基线；在预算内重执行四条 Parent，A/B 使用同一新冻结 Actor 配置。旧结果仅作开发背景，不与新结果混算。新三组配对成立不代表与旧外网运行等价。

## Actor、环境与预算

复用原 run_task_skill.run_episode、build_skill_messages、chat、project_action 和 verify_record。模型请求参数与原 R05 一致（max_tokens=16384、temperature=1、thinking enabled、reasoning_effort=medium），模型路由统一改为上面的当前内网配置。原 system/initial/history 模板、最近两对动作前历史、每次请求固定 Skill、50 步、合法动作候选协议不变。只过滤精确等于 `help` 的候选，其他内容/顺序/重复保留；不强制修改模型选择的非法动作。

TextWorld PDDL + AlfredDemangler(shuffle=False)，每条 Episode 新环境 seed=42/reset 一次。实际版本、协议和源码摘要存 preflight.json；执行前检查版本与游戏/manifest 冻结。每条首次模型调用前核验初始 observation 和完整原始菜单与预检相等。之后不同动作产生不同状态属正常。每对结束后核对 task/split/model/backend/protocol/versions/game/manifest/initial/implementation；不一致保留并单列非严格配对。

上限：2 Editor + 12 Episode（Parent/A/B 各四条）×50 步 = 最多600 Actor 决策。并发最多4 Episode，按 Parent、A、B 及 P3/P6/P7/P10 的固定提交顺序；不因先前输赢改变后续任务。Actor 使用原 timeout=(10,300)，每个决策只1 HTTP、strict_response=True；**关闭原客户端对截断/格式错误的再生成**，技术失败也不重试、不重启 Episode。总 HTTP 上限602，无额外 Judge 或知识生成调用。预算上限输出为602×16384=9,863,168 tokens，实际 input 不设虚构计费；usage 缺失和货币成本记未知，reasoning 不重复累计。

成功以原生 won/done 及合法 verifier 为准。任务失败/step_limit 与技术异常分别报告；请求内容缺少 action 标签沿用原 look fallback，非空但不合法策略不触发重采样。空响应或 finish!=stop 停止该 Episode，保留原始 HTTP。若出现共性鉴权/路由/环境错误，停止未启动分支，不追加请求。

## 冻结评价

先逐组分析，再按 task 配对。每条记录 native_success、episode_complete、执行动作数、决策请求数、最后状态、50步上限、错误及初始状态验证。技术未完成的 native_success 记不可判定，不当作语义失败；同时完整列出预注册总数和可评价分母，不筛掉不利结果。

行为指标：唯一实际导航位置与类型；打开/查看位置和不同实例；重复导航及其前后观察是否重复（这仅是代理指标，有效回返另标）；候选外动作、Nothing happens、fallback、可用 direct action；精确目标 acquire、近似物品操作；按任务要求 clean/cool 和最终交付；找到目标后预算不足、过早结束。当前实验没有照明/多实例任务，不能据此证明这些能力保留。不凭关键词/次数单独判断策略好坏。

Editor 审计逐条检查 Effective Update→实际 Diff，区分原要求落实、遗漏、新增未要求策略与必要能力保留；即使有策略风险，只要 Candidate 通过原契约仍照预注册执行，不人工修改。Actor 比较区分与 Skill Diff 一致的观察和随机/环境等可能解释；不作小样本显著性或总体成功率估计。

特别关注 A 的覆盖顺序是否导致过多检查、延迟有效返回、跳过 direct action；B 原始探索是否减少循环、是否仍依赖不可获得的全局访问状态。两方向都允许，Keep 不自动得分。

## 新 Train 与保护

NEW_TRAIN_CASES.md 与 new_train_cases.json 必须先于 Editor/Replay 冻结。只读身份筛选，未来共同 Parent/Memory 保持 R05 时间边界。本轮不 reset/执行新任务，不访问最终 Test，不因 R05结果改样本。

只新增本目录的适配入口和归档；保留已有未提交修改，正式源码/Prompt、旧 Parent/Memory/输入输出/报告不改。开始保存 baseline/Git diff，结束核查既有文件。freeze.json 验证输入、接口源码、协议、清单与游戏。完成报告后停止。
