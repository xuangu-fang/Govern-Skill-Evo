# v27 五项审查修复与离线验收补充

后续按用户要求，容量配置已改为沿用旧版本4M字符／6M字节、context_window_tokens可选。本文的必填描述保留为当时修复记录；当前规则见 [运行配置对齐记录](RUNTIME_CONFIG_20261030.md)。

后续复审发现的 Actor 完成标记丢失恢复缺口已另行修复；最新49测试结果及恢复契约见 [后续修订记录](ACTOR_RECOVERY_FIX_20261030.md)。本页保留此前43测试阶段的记录和 C01 规模说明。

本次只修复实现、补充合成回归和容量验收，不启动实验，不发送真实模型请求。
修订稿 `draft_20261030_001` 保留为原始设计基线；本文件补充其数据与证据契约和验收清单。
五个模块的职责、输出 schema、Prompt 文本、Preconditioner 的 KEEP／D/S/C 与 checks 规则、Replay 的逐 Knowledge 引用及整 entry 替换均保持不变。

## 五项修复

| 问题 | 实现及契约补充 | 回归依据 |
|---|---|---|
| 方法响应结构错误不可重试 | `response_value` 先校验顶层、choices、choice、message 类型；`message=null`、数组、数字等结构错误统一为可重试 `RequestFailure`，不依靠兜底捕获任意异常 | 非法类型矩阵、真实 HTTPGenerator 注入响应、第二次成功、六次耗尽、恢复不重置、HTTP 正文已落盘后中断恢复 |
| C01 覆盖不足且窗口可遗漏 | 用实际五模块 builder、完整十题配对、增长 Skill／Memory、真实输出校验诊断及完整上次错误输出构造消息；Campaign 强制显式冻结各模块 context_window_tokens | 完整输入成功、反馈容量仅超一单位时拒绝第二次请求、恢复仍拒绝、更大 Replay 输入拒绝首次请求 |
| Campaign 缓存绕过 Actor 原始归档 | 新增只读 `read_completed`，并在 Campaign 复用及 Test 报告中校验批次身份、轨迹、签名、请求槽、已接受原始响应及其 content／终止／评分／usage 与 result 一致 | Parent／Candidate、发布前／后、响应删除／content 改动／usage 改动组合；最终读取不写文件，恢复不补发请求；完整 HTTP 后备归档可只读验证 |
| CRLF Skill 被文本读取规范化 | adapter 改为 `read_bytes().decode('utf-8')`，Skill 身份保留原始换行；Actor 消息仍使用原生 SkillAdam 构造函数 | CRLF 和混合 CRLF／LF／CR 经 Actor、Editor、Candidate、Gate、发布及恢复保持一致 |
| 残缺答案标签被判格式合规 | 同时核对标签起始标记和完整标签数量；额外残缺 `<answer`／`</answer` 会判不合规 | 大小写、空格、属性残片及 stop／length 组合；与原生提取对照，EM 不变且不补答 |

## 数据与证据契约补充

- 数据内容及 53／124 ID、十题批次、确定性选项顺序均不变。raw 与 prepared_v1 继续只读核对。
- 归档验证可以读取原始响应做一致性检查，但模块输入仍只允许正式 content 白名单；不将独立 reasoning_content、provider metadata 或完整 raw response 加入证据。
- `records.json`／`trajectory.json` 本身不再足以证明 Actor 结果可复用。已完成结果须关联同一任务、同一 Skill、同一 Actor 参数的签名和连续请求槽，并有已接受原始响应。若同时保存 JSON 与 HTTP 归档，两者也须一致。
- 只有 HTTP 状态和完整正文、尚无 response.json 时，完成结果允许只读验证，不写回 response.json。未完成请求的既有恢复路径保持不变。
- 只读完整性失败不得通过重新作答“修复”。技术响应结构异常与本地归档损坏分别处理，后者保持停止。
- Skill 的身份和补丁基线以 UTF-8 字节为准；原生 Actor Prompt 构造中的既有处理保持不变。
- 方法输出结构异常不产生语义证据，也不增加合法引用范围；技术重试沿用六次总额度，不将此类错误当成 output-validation 反馈。
- Campaign 配置验证要求五个 module_calls 均提供有效 `context_window_tokens`。`campaign_config` 新增必填关键字参数；字符和 UTF-8 上限仍分别检查。无容量默认值，也未生成正式实验配置。

## C01 完整容量场景

固定配置为 [capacity_profile.json](../../../tests/skill_evolution/v27/capacity_profile.json)，场景由 [capacity_fixture.py](../../../tests/skill_evolution/v27/capacity_fixture.py) 构造。

| 项目 | 明确规模 |
|---|---|
| 当前执行 | 10 Parent＋10 Candidate；Grouping／Diagnosis 各10条，Preconditioner 的 Plan 直接引用全部10条，Replay 含20条和10组配对 |
| Skill | 从短初始 fixture 增长到4,096字符；Candidate 再追加真实可应用的精确 patch |
| 题目 | 每题2,048字符，含非 ASCII 文本；相同任务的两侧题目和选项一致 |
| 普通 content | 每个 run 完整8,192字符，保留答案标签；不是截取长内容生成的摘要 |
| Memory | 32个完整 entry，每条 Knowledge 512字符；经真实 commit/load 构造，引用可解析；模型按原有 Knowledge Only 投影读取 |
| 上一轮输出 | 65,536字符的完整非法 JSON schema 输出；通过每个真实模块 validator 取得诊断，再由正式反馈构造器追加 |
| 输出预留 | Grouping／Editor 16,384；其余32,768 |
| 输入上限 | 1,000,000字符、1,000,000 UTF-8 bytes |
| context 预算 | 1,048,576；仅用于离线验收，不是对真实 provider 能力的确认 |

所有模块继续遵守各自投影边界：Editor 仅 parent／plan，不为容量测试额外塞入 runs 或 Memory。普通 content、父技能的原生消息、outcome 等按真实 builder 输出保留；没有去重或裁剪。

带完整错误反馈的核算结果：

| 模块 | UTF-8 bytes | 输出预留 | 含框架及预留的估算 | 相对冻结 context 预算的余量 |
|---|---:|---:|---:|---:|
| Grouping | 409,566 | 16,384 | 426,270 | 622,306 |
| Diagnosis | 413,699 | 32,768 | 446,787 | 601,789 |
| Preconditioner | 440,415 | 32,768 | 473,503 | 575,073 |
| Editor | 77,997 | 16,384 | 94,701 | 953,875 |
| Replay | 776,411 | 32,768 | 809,499 | 239,077 |

更大场景保持同一预算，仅把每个 run 的完整 content 增为16,384字符。Replay 带反馈为1,104,091 UTF-8 bytes，估算1,137,179，超过 context 预算88,603，且超过字节硬上限。实际阶段入口在首次请求前拒绝这个 Replay 输入，未裁剪、未扩大预算、未调用模型。报告中的超限测量仅用于说明大小，不代表输入被接受。

另对五个模块分别构造“基础输入可容纳、加完整错误反馈后只超一单位”的冻结预算：首次合成输出留下完整错误正文；第二次请求之前停止，恢复也不发送。输出预留计入所有检查。

这些规模是字符数和离线估算，不能与 Actor 的16,384输出 token 上限混同。测试证明指定规模的构造、保存及拒绝行为，不证明任意最大输出或无限增长 Memory 都能容纳，也不证明真实服务支持该窗口。正式实验前须按实际服务已确认的窗口冻结配置并做无损预检。

## 验收清单与证据解释

原107项清单继续保留；C01 改为关联完整场景及超限测试。另在 [acceptance_map.json](../../../tests/skill_evolution/v27/acceptance_map.json) 的 `review_regressions` 中逐项映射以上五项问题。

新增10个测试方法，总计43个。原生协议／评分对照、Preconditioner／Replay 边界、来源文件与 Prompt 不变性检查继续执行。独立 LMB 环境运行，网络与模型子进程均被拦截；真实177题只读检查数据，不执行作答。

报告现在按每个已映射测试的真实结果生成状态，不再根据整套测试成功给107行统一贴“场景全部通过”。10项历史人工样例保留原判断，但标记为本轮未重新执行，不能代替真实模型语义评测。

正式复验产物保存在 `artifacts/verification/v27_offline_reviewfix_20261030/`：

- `validation.json`：总结果、环境、网络计数、数据不变性、源码及验证程序哈希。
- `test_results.json`／`unittest.log`：逐测试状态和日志。
- `acceptance.json`：107项对应测试状态，以及五项修复的回归状态。
- `capacity.json`：完整场景和较大拒绝场景的逐模块大小、预算、余量和边界。
- `c01_messages/`：两个场景的五组实际输入消息，包含完整错误反馈，方便离线复核。

此前33个测试的报告保留，不覆盖。本次未改动 v24.1／v25／v26 实现，没有启动优化、真实 Test 或任何真实模型调用。
