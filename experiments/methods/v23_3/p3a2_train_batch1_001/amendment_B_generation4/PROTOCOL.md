# P3-A2 Batch-1 执行前冻结协议

仅执行 P3-C1 预注册 Batch-1 六例的完整方法对照。A 为正式 V23 自由替换 Prompt/契约；B 为当前 V23.3 选择性 Update Patch。Prompt 差异是方法的一部分，不做格式单因素对照。禁止根据结果重采样、改 Prompt、换任务/模型/Memory、补第二批或设计案例。

## 样本与共同输入

权威来源：`../p3c1_r05_replay_001/new_train_cases.json` 的 batch=1，抽样种子 230302，原排除表不变。本目录 manifest.json 是六例的独立合法清单，保留原实验局部 task_id；不覆盖默认 edition。tasks.json 包含完整规范实例、任务请求和两次相同 seed reset 的初始观察/原菜单。任务请求由环境实际反馈读取，没有猜写或读取解法。

| ref | task_id | 任务请求 | 族 |
|---|---|---|---|
| P1 | train:p3a2_1_01 | put some box on armchair. | pick_and_place_simple |
| P2 | train:p3a2_1_02 | clean some kettle and put it in cabinet. | pick_clean_then_place_in_recep |
| P3 | train:p3a2_1_03 | heat some mug and put it in coffeemachine. | pick_heat_then_place_in_recep |
| P4 | train:p3a2_1_04 | cool some apple and put it in diningtable. | pick_cool_then_place_in_recep |
| P5 | train:p3a2_1_05 | examine the alarmclock with the desklamp. | look_at_obj_in_light |
| P6 | train:p3a2_1_06 | put two watch in dresser. | pick_two_obj_and_place |

六例原始 split=train，实例互异且不在冻结历史排除表中；R04/R05/R06 是另一 split 的实例。先前身份筛查有前缀截断/别名/仓库外记录局限，只称已核查范围内未发现先前实验暴露，不作绝对独立声明。预检只 reset、不执行 Actor 动作；不访问 Test 或 Batch-2 游戏。

共同 Parent 精确复制预注册指定 `p3c1_r05_replay_001/parent.md`，核对为正式 R05 Parent。Memory 精确复制 `memory_v3_integration_001/config/full_payload.json.memory`，仅 M1/M2/M3/M6/M7/M8/M9，历史截止 R05 当前执行之前；不加入 P3-C1 Replay、本轮 Parent/Candidate 或后续 Memory。完整 Memory 用于校验，模型用现有 Memory v3 投影。Diagnosis 不读取 Memory。

## 固定模型、协议和资源

全部使用当前内网 `deepseek-v4.1-flash`，temperature=1、thinking enabled、reasoning_effort=medium、stream=false。Grouping max_tokens=8192（正式默认）、Diagnosis/Editor=16384、Preconditioner A/B=32768（已成功配置）、Actor=16384（原协议）；timeout=(60,300)，显式增加连接/上传容忍，生成协议不变。完整参数在 config.json 与每个真实 request.json。

全部模型调用**串行**，共用持久化节流状态，上一请求结束后至少 3 秒再发；已采用单并发，连续 429 不再额外启动队列。A/B 及 Parent 使用相同并发/间隔规则。上游顺序为 Grouping→Diagnosis→A→B→Editor A→Editor B；Parent 六条按 P1–P6；Candidate 按 task 顺序每题 A 后 B。一次调用内技术重试不启动新样本。

Actor 复用 run_episode/build_skill_messages/chat/project_action/RecordingSession，原 system/initial/history Prompt、最近两对动作前观察与动作、固定 Skill、每条 50 步；只过滤精确 help，其他菜单顺序/重复不变；不提供全历史或笔记。独立新环境 seed=42，reset 一次，版本和实现摘要冻结。每条首次请求前核对预检初始观察/完整原菜单。传输层可重试，环境提交不重试。

最多 6 次上游逻辑生成、18 Episode、900 Actor 决策。每个逻辑调用最多 5 次传输尝试，总理论上限 4,530 次尝试；明确发出前连接探测失败也消耗该预算，但不称服务端已收到 HTTP。正常 Parent 轨迹直接复用，不额外跑 Parent。上游输出上限合计 122,880 tokens；Actor 最多 14,745,600 output tokens，实际 usage 单独统计；reasoning 若包含于 completion 不重复加总。金额未知，不编造单价。

各请求记录真实正文 bytes、字符数及 chars/3 的粗略 token 估算（非服务 tokenizer）；硬装配上限 4,000,000 message characters。阶段0记录历史 Memory v3 输入体积作为规模参考，动态 Grouping/Diagnosis/PC 在发送前另存实际输入预算。服务上下文容量不额外探测或臆测；若拒绝，保留失败，不裁剪证据或改单组预算。

## 有界技术重试与恢复

429 优先 Retry-After 秒数或 HTTP 日期，否则 15/30/60/120 秒退避；502/503 无有效模型内容时同样有界重试。额度耗尽、quota_exceeded、insufficient_quota、权限错误停止；错误状态携带有效模型输出也不追加采样。单逻辑请求至多 5 次尝试，累计等待至多 600 秒；超长 Retry-After 不抢先重试，停止该调用。共享队列遵守冷却。

发送前 DNS/TCP 探测失败可在同一预算内重试，未向模型/环境提交。实际 POST 抛出的 ReadTimeout/ConnectionError 等若不能确认未生成，统一按结果不确定停止，不重发。没有请求去重支持，不假装可安全恢复不确定生成。

每次尝试持久化 logical_call_id、index、请求正文/配置/bytes、时间、实际等待、HTTP 状态/响应头/Retry-After/request_id（若有）、完整正文/usage 或异常堆栈。Actor 通过原 RecordingSession 另保留逐步传输和 raw body，重试仅重复同一步固定 messages，成功后只提交一次动作。JSON/Diff/契约错误、Keep/no_change/need_evidence、length、非法动作/策略失败都不追加模型生成。

调用 journal 发送前写 in_flight；重启遇到该状态按不确定停止，不能重置五次预算。已收到完整响应重载该响应，成功 Episode 重载、不再运行；上游有效归档重新校验。活动进程内的限流在原环境和同一步恢复；若进程已失去环境且无法证明动作提交状态，则保留不完整 Episode，不重放动作/重开整局冒充续跑。本轮无无限 Episode 重启授权。

## 阶段门

0. 来源、清单、配置、预检、评价和重试测试全部冻结后才能 Parent。
1. 必须六条 Parent 全部正常结束（success/step_limit/environment_ended）且轨迹有效才进入 Grouping；任一技术不完整不删样本，停止依赖阶段，其余已固定 Parent 可完成并报告。
2. Grouping 一次合法结果、Diagnosis 一次合法 revise；至少一个 Update 含两项可独立判断的行为要求行，且两组能共同消费，才进入 PC。人工仅审阶段门，不改 Original；no_change/need_evidence/非法或无可比多行均停。
3. 同一 Diagnosis 构建共同证据，`project_messages(V23)` 与 `V23.3.messages_for` 的 user message 必须完全相同，并在调用前保存。A/B 独立调用、解析、编译；一个无合法 Effective 不伪造，另一有效组可继续，标记不完整对照。
4. 每组一次 Editor，原校验/Patch 引擎/编译不变。输入只 Effective 不同。每份有效 Candidate 经 load_editor 重载、actual.diff 审计后进入 Replay；合法停点不硬造 Candidate。Keep 仍正常执行 Editor。
5. Candidate 用相同六例、初始状态、模型、协议，与阶段1 Parent 配对；成功结果不重跑，行为失败不重采样，技术不完整单列。
6. 完成独立评价、组间比较、成本/保护报告后停止。不启动 Batch-2/Gate/Memory 更新/完整进化。

## 执行前评价标准

Preconditioner：Keep/Adjustment、实际目标行为变化、当前证据支持、历史真实 Diff/响应支持、混合响应是否被过推、独立探索的具体性/可执行性、无依据附带承诺、必要能力保留。引用 Memory ID 不证明因果增量；无 Memory 消融不在本轮。

Editor：Original→Effective→Skill Patch→actual.diff，核对落实/遗漏/额外策略、边界与能力保留。B Keep 不等于 Skill 不变。Patch 少/短和结构成功都不等于语义或行为收益。

Replay：逐组再配对报告 native_success、episode_complete、步数、首次看见/取得精确目标、唯一位置/类别与同类实例覆盖、重复访问及是否带来新信息、非法导航/Nothing happens/fallback、必要 clean/heat/cool/lamp/数量/交付、预算和原成功退化。不适用记 N/A。使用实际观察，不读隐藏目标布局；同位置同观察重复是代理，带物处理/交付等有效回返另判。技术未完成不当语义失败，不静默排除分母。

归因分开 Preconditioner、Editor、Actor。结果不佳照实记录，不能用字数/行数代替任务收益。单批六例、单次生成、随机模型、服务重试时点差异均限制因果与泛化结论。

## 保护与交付

仅新增本目录文件。baseline 记录 Git HEAD/status/diff 与既有文件元数据，freeze 固定相关正式源码/Prompt/输入/游戏；结束验证。不得改正式模块、Memory、默认配置或历史材料，不提交/清理原有未提交修改。交付七份要求的报告及所有真实请求/响应/轨迹、失败 journal、预算和 Git Diff。离线技术测试的合成响应明确单列，不作为模型研究结果。
