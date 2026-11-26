# LMB 数据与证据契约草案

本契约将已确定方案细化为未来实现接口。输出 schema 保持现有方法语义；LMB 执行 schema 为新设计，不声称现有 v26 validator 可以直接接受。

## 数据身份与批次

内容 revision 为 `6f53c5ff7227633ea954b2847cd590314d582047`。成员依据 `external/SkillAdam/skilladam/data/profiles/lmb_main_results.json`：Train 35、Selection 18、Test 124，全集 177；`202512:46` 从现有 Test 转到来源 Selection。新视图不覆盖 `prepared_v1`。

每条本地数据记录保存 id、source_split、effective_split、source_file、内容 revision/hash、原始 mcq 及来源元数据。原始 theorem/sketch/paper_link 可以留在本地数据层，但不得经整体序列化进入 Actor 或优化模块。

优化顺序：`sorted(train_ids) + sorted(selection_ids)`，使用字符串排序；53 个唯一 ID，与 Test 不相交。按 10/10/10/10/10/3 顺序冻结六批；不循环补足 SkillAdam 的 max_iterations=15。`continue_no_change=true`，不早停，不以合并 Selection 再选检查点。

选项先按 SkillAdam loader 的原标签排序和文本规范化，再用 `int(sha256(f"42:{id}")[:16], 16)` 驱动局部 RNG 打乱、重新标记 A～E。记录 old_label→new_label 和正确标签映射，核对五个选项文本未丢失或互换归属。same task 的 Parent/Candidate/Test 采用同一映射。不得用全局 RNG 的消耗顺序生成选项。

## Actor 与请求归档

Actor 固定 SkillAdam LMB base prompt，Skill 插入方式和消息顺序冻结；初始 Skill 为 SkillOpt 原生 initial.md，Memory 初始为空。Actor 不读取 Memory、来源参考材料、其他任务或评分。

仅一轮生成，无工具。模型 deepseek-flash，thinking enabled、effort medium、temperature 1.0；max_tokens 16384；请求 300 秒、连接 10 秒。优化 workers 上限 20、Test 16。固定选项排列不保证模型采样确定。

每次 HTTP 尝试分别记录 attempt_id、序号、开始/结束状态、模型/配置身份和是否收到完整响应。凭据与认证头不归档。最多六次总尝试，恢复不重置；SDK 内层重试为 0。最终预算与等待规则需在实现配置中冻结为可验证字段，不能临时使用默认值。正常答错、无法解析和 length 不触发补答。

原始响应档案可保留 provider 返回的 reasoning_content；模型事实层必须通过白名单重新构造。任何调试信息、引用展开、摘要、反馈、Memory 和 Editor 输入都不允许绕过此边界。

## 许可执行事实

每个 run 的顶层字段沿用结构：`ref/task_id/run_id/initial/attempts/outcome`。task_id 使用原始题目 ID，run_id 为唯一执行身份；P/Q 编号由冻结批次顺序确定，不按完成时间编号。

| 对象 | 精确字段及约束 |
|---|---|
| `initial` | `ref/task/messages`；ref=P1:0；task=`{question,choices}`；messages 是实际 system/user 数组，仅 role/content |
| `attempts` | 恰好一个已返回、可计分的模型轮次。不是 HTTP 尝试数组 |
| 单个轮次 | `ref/request_context/request_messages/assistant`；ref=P1:1；request_context=`lmb_single_turn_v1`；request_messages 与 initial.messages 精确相等；assistant 只有 role=assistant、content |
| `outcome` | `ref/status/termination/answer/model_rounds/tool_calls/api_requests/score` |
| `outcome.answer` | `raw_content/extracted_answer/predicted_label/predicted_text/parse_valid/format_compliant/correct_label/correct_text` |
| `score` | `em/f1`，均为 0 或 1 且相等。f1 是原生兼容字段，不是独立指标 |
| 完成状态 | status=`completed`，termination=`stop` 或 `length`；model_rounds=1、tool_calls=0；api_requests 是已经消耗的 HTTP 尝试数 |

tool_calls 固定为 0，仅保留配对结果兼容形状；无 `tools` 数组、无工具引用和多轮轨迹。只有有效已完成 run 才进入 Grouping/Gate/Replay；技术失败保存在独立审计层。

正常 content 是原始字符串，不截断、不归一化全文。合法 length 的 content=null 在许可事实中投影成空字符串，termination 保留 length，原始 null 留在审计档案；该投影不是模型生成了空字符串的断言。其他字段类型错误按结构失败处理。

correct_label/correct_text 只存在于 outcome，表示事后反馈。格式、解析和 EM 是不同事实。ordinary content 只有标签时，不能建立某种中间推理已发生的事实。

## 引用与历史权限

当前引用：`P1`（完整许可 run）、`P1:0`（输入）、`P1:1`（正式请求与普通回答）、`P1:outcome`（事后结果）；Candidate 对应 Q。`diff` 表示程序计算的实际 Parent→Candidate diff。G 为分组，u/c 为计划对象，M 为 MemoryEntry。不存在 `P1:1_t1` 等工具引用。

完整 run 引用包含的也只是许可视图，不能访问原始 API 文件。历史证据为 `<context_id>/diff` 或 `<context_id>/P1:1` 等完整引用，context_id 不含斜杠。历史引用必须精确存在于已提供 Knowledge 的 evidence 中；不能去掉前缀、扩展邻近轮次、引用范围或用 M ID 代替执行证据。

引用存在性不证明语义支持。审查必须分别处理结构检查与自然语言证据充分性，后者不能以字符串匹配冒充证明。

Preconditioner 独有显式正文引用语法：单反引号包围 `Memory:M1`、`Group:G1`、`Evidence:P1:1`、`Evidence:R01/diff`、`Update:u1`、`Check:c1`。结构化 target/id/update_ids 仍为短 ID。其他模块保留自己的既有短 ID/历史引用规则，不全局替换成这一语法。

## 模块投影

| 模块 | user JSON 顶层 | 权限与关键处理 |
|---|---|---|
| Grouping | `parent/runs` | 当前完整 Parent 批次，无 Memory，无参考材料 |
| Diagnosis | `parent/runs/grouping` | 当前完整批次；分组不替代直接证据；无 Memory |
| Preconditioner | `parent/plan/runs/memory` | 仅 Plan 中直接执行引用选出的完整 run；Group 引用不展开全组；model input 无 grouping 正文。内部 validator 可保留 grouping 元数据 |
| Editor | `parent/plan` | plan 为 Effective Plan，Update 保留 id/text/basis；basis 仅来源标识，不授权查阅证据；无 runs/Memory/adjustment reasons |
| Replay | `parent/diff/plan/runs/pairs/memory` | 全部有效配对；plan 的 Update 仅 id/text，去除 basis；Goal/Checks 保留；不传 Gate 决策作解释依据 |

Knowledge Only `memory={format:"memory_knowledge_only_v1",entries:[{id,knowledge:[{text,evidence}]}]}`。空 entries=[]。历史原始 Parent/diff/run/配对不进入输入；sources 在内部档案维护，不进入此投影。未来可选审查模块只读取被授权的许可来源视图，不能展开原始响应。

pair 字段为 `parent/candidate/task_id/parent_result/candidate_result`；result 字段为 `status/model_rounds/tool_calls/api_requests/em/f1`。先由程序验证 task_id、输入题干、选项映射、运行参数、scorer、Parent/Candidate Skill 身份及唯一 run_id，再构造 pair。Q 按 task_id 与 P 配对，不能用数组位置猜。Parent 的 system Skill 与 Candidate 可不同，user 输入必须相同。

## 五个输出契约

| 模块 | schema |
|---|---|
| Grouping | `{groups:[{group_id,members,decision_problem,shared_basis,important_differences}]}` |
| Diagnosis | `{decision,reason,plan}`；decision=revise/no_change；plan=null 或 `{goal,updates:[{id,text,basis}],checks:[{id,update_ids,question}]}` |
| Preconditioner | `{adjustments:[{target,focus,change,reason,to}],checks}` |
| Editor | `{patch,reason}` |
| Replay | `{entries:[{revises,knowledge:[{text,evidence}]}]}` |

Grouping 必须非空并将每个 run 恰好分配一次；shared_basis 引用每个成员的返回轮次 Pn:1，即便只观察到标签；不由标签猜内部推理。

Diagnosis revise 至少一个 Update；basis 非空、无重复、至少一个直接执行引用。每个所引 Group 至少有一个成员的直接引用同时出现在该 Update basis。Checks 可为空；非空 update_ids 只引用当前 Updates，ID 不冲突。no_change 必须 plan=null。

Preconditioner 每个 Original Update 恰好一个 adjustment；KEEP 当且仅当 change=KEEP、focus=[]、to=null；非 KEEP 的 focus 为非空无重复 D/S/C。修改 to={patch:非空字符串}；撤回 to=[]。不创建新 Update ID，不做结构性拆分/合并；协调通过各自 patch 完成。修改保留 ID，basis 由原有来源继承并经既有 normalizer 验证，不允许模型重写 basis。每个 patch 独立针对冻结 Original，不针对其他调整结果。

checks=null 继承原列表；[]=清空；数组=完整替换。Checks 不能引用撤回项；全部撤回要求解析后的 Checks=[]。全 KEEP 继续 Editor；合法全撤回编译成 no_change。ready/no_change 是程序内部状态，模型不能输出 decision/reason 顶层字段或 need_evidence。

Preconditioner/Editor patch 均沿用 `unnumbered_diff_v1`：精确 `--- a/SKILL.md`、`+++ b/SKILL.md`，每个 hunk 的头严格为 `@@`，正文空间/减号/加号标记；唯一连续匹配、按冻结源位置递增、不重叠、精确换行，无 fuzzy/重排/修复/全文回退。缺失末尾 LF 使用标准 `\ No newline at end of file`，JSON 中转义反斜杠。Preconditioner 的 SKILL.md 是目标 Update 字符串的虚拟文件名。Editor null Parent 使用 `--- /dev/null`；首版实际 Parent 非空。

Editor patch="" 表示全部已满足；null 表示无法忠实实施，停止；空白字符串不是空 patch。合法候选必须实际改变 Parent 且不变成空白。程序生成 actual_diff，不用模型自述代替。

Replay entries=[] 为合法无 Knowledge 更新；每个输出 entry 有 revises 数组及非空 knowledge；每个 Knowledge 的 text 非空、evidence 非空无重复。revises=[] 新建；否则完整替换所列活动 entry，目标不能重复使用。未列入 revises 的活动 entry 保留。没有 Knowledge ID、entry-level evidence、删除/增量操作或隐式旧 Knowledge 继承。发布空 entries 也沿用既有 commit 记账，不新增特殊学习分支。

## 评分与状态

评分入口仅从 ordinary content 重新执行冻结的 SkillAdam extract/parse 流程：最后一个完整 answer 标签，否则最后非空行；标签规范化、选项全文匹配和首 token 回退均遵循原实现。禁止预填 answer/predicted_answer 覆盖 content；派生标签只用于复算一致性比较。casefold 等细节按 SkillAdam 实现，不能假设 SkillOpt 完全逐字相同。

format_compliant 是独立审计布尔值：恰好一个完整 answer 标签且标签内去首尾空白后为大写 A～E 单字符；标签外允许解释；额外未闭合/重复 answer 标记视为不合规。该布尔值不参与 Gate。parse_valid 表示解析结果命中某个呈现标签；不等于 format_compliant。

正常 stop 字符串（含空串）和合法 length 可计分；length/null 投影空串得 0，不重试。其他 choice/message 缺失、非法 content 类型或无支持的返回结构属于技术失败；拒绝/未知 termination 显式停止，不偷偷计 0。普通错误/无效答案不重采样。技术失败不进入 Gate，预算耗尽则可按同一解析器进入 Gate。

方法模块：最多六次总请求，结构/引用/patch 校验错误允许上一输出＋定位错误反馈；合法 no_change/null 不通过重试索要更好方案。技术失败与语义决定分离。反馈不得包括原始隐藏字段及其派生摘要。

| 分支 | 下一步 |
|---|---|
| Diagnosis no_change / Preconditioner 合法全撤回 / Editor 空 patch | Parent 与 Memory 均保留，完成当前批次，继续下一批；不调用 Candidate/Gate/Replay |
| Editor null | 语义阻塞，停止、不自动回跳、不发布 |
| 完整有效配对 | Gate 严格比较 EM 正确数；随后 Replay |
| ACCEPT＋Replay/校验成功 | 发布 Candidate 与新 Memory |
| RETAIN＋Replay/校验成功 | 发布原 Parent 与新 Memory |
| Replay/必要校验失败 | 不发布任何下一轮状态 |
| 传输/配对/身份失败 | 保留现场，恢复遵循冻结额度 |

## 容量与最终评估

容量按实际 system/user/feedback、Skill、Memory、配对的 ordinary content 以及预留输出计算；completion tokens 中的隐藏 reasoning tokens 不等于下一模块输入。只允许可逆去重，超限显式失败。五份 Prompt 是完整 system 草稿；未来加入可逆编码需另冻结输入视图身份，不能悄悄改变当前 JSON 语义。

Actor 技术请求六次、length 处理和相同初始 Skill 是双方显式覆盖配置，不称为 SkillAdam 原生默认。保留 v27 Parent 复用、全六批和 SkillAdam 新执行 Gate Parent/原生早停的差异。正常十题配对分别为 20 与 30 次任务执行。

最终冻结初始 Skill、v27 最终 Parent、SkillAdam 最终 Skill，独立评估 124 Test；报告 EM/正确数、逐题改善退步、批次/接受/停止、调用/token/耗时/解析/截断/技术失败。不按 Test 回选版本。正式结束前未完成六批的 v27 不是完成的最终版本。
