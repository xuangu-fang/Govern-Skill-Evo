# v28 Actor Prompt 与评分适配方案

状态：原始设计稿保留。2026-11-01 已按本稿完成 Prompt、解析评分，随后接入持久化 Actor、六次共享尝试、批次恢复和完整 EM-only Gate 身份校验，详见 `src/skill_evolution/v28/README.md` 与 `artifacts/verification/v28_actor_runtime_20261101/validation.json`。本目录 `design_validation.json` 是此前的设计检查快照，完整 campaign/五模块接入仍待完成。参考本地 SkillAdam commit `b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1` 的 SearchQA rollout、evaluation 和 adapter；未启动训练、Test 或真实模型请求。

## 1. 单轮任务与消息构造

每道题只有一轮 Actor 作答，无工具、无在线搜索，不在 Actor 请求中暴露参考答案。执行输入包含当前 Skill、原始 question、原始 context。正常 stop 的回答进入答案抽取与评分。

system 模板见 `actor_system.md`，user 模板见 `actor_user.md`。模板文件末尾的一个 LF 是文件排版约定；构造消息时去掉该模板末尾 LF，再插入数据。保留注入内容自身的所有字符。替换采用单次模板插值，不能在填入 Skill/context 后再次做模板展开，以免修改内容中的花括号。

Skill 沿用 SkillAdam 的注入规则：若为非空字符串，`skill_section = skill.strip() + "\n\n"`；否则为空字符串。它位于 Task Format 后、Answer Format 前。不额外添加 Skill 标题，初始 Skill 的来源不由本方案决定。

question/context 必须是非空字符串；只用 strip 检查是否为空，实际输入保留原字符串，不裁剪、不去重、不改写。数据已固定为 context 字符串，不需要新增 documents 降级路径。当前最长 context 为 4820 字符；这一统计不能替代完整 Skill＋消息的容量验收。

## 2. 相对 SkillAdam 的 Prompt 差异

保留角色、Task Format、Skill 位置、Think step by step、短答案要求和不重复题目的要求。仅将 Answer Format 中的字面标签占位示例改为“名为 answer 的 XML-style element”的文字描述，并将 Abraham Lincoln 示例改为文字描述元素内容。差异见 `actor_system.diff`。

这延续 v27 使用文字描述元素的适配方式，但尚无 SearchQA 实测证明它优于原始标签写法；属于待审阅的候选改动。保留 `skilladam_actor_system.md` 作为未经修改的源模板，便于选择原版。

不继承 LMB 的单选标签 A–E 或“元素外不得有文字”等额外限制。SearchQA 原生解析允许解释后给出答案；本方案不额外收紧该行为。不在固定 Prompt 中加入实体消歧、证据投票、词形修正等新策略，这些属于演化 Skill 的内容。

## 3. 响应接入与解析

DeepSeek transport 按已确认的 v27 机制验证响应信封和终止状态。只把普通 `message.content` 作为 `{"response": content}` 传入 SkillAdam 的 extract_answer；不传其可优先覆盖解析结果的 answer 字段，也不从 reasoning_content、缓存摘要或参考答案取预测值。

沿用原始正则 `<answer>(.*?)</answer>`，IGNORECASE＋DOTALL：

1. 存在完整匹配时，取最后一个匹配内容并 strip。
2. 没有匹配时，取最后一个非空行并 strip。
3. 整体为空时，返回空字符串。

不使用 XML parser，不补齐损坏标签，不删除解析结果中的残余标签，不做二次模型解析。多个完整元素按最后一个评分；只有未闭合标签时按最后非空行评分。解析结果即使看起来不合格式，也不额外修复或归零。任何可选的格式诊断只用于审计，不改变评分和 Gate。

## 4. 正式 scorer 候选

采用 SkillAdam SearchQA `evaluation.py` 的 exact_match 和 best_token_f1，函数语义逐字保持。它与环境验收时保存的 SkillOpt scorer 不是同一实现；环境验收快照继续保留，不能静默替换。

归一化顺序严格为：

1. lower；
2. 按 `\b(a|an|the)\b` 删除英文冠词；
3. 按 `[^\w\s]` 删除非 word、非 whitespace 字符；
4. 合并空白并 strip。

保留 Python Unicode 正则语义。下划线是 word 字符，不能像 ASCII punctuation 方案一样删掉；标点删除顺序也不能换。不要添加数字等值、单位换算、别名补充、重音去除或模糊匹配。

EM：预测与任意一个参考答案归一化后完全一致即为 1，否则为 0。F1：按归一化后的空白分词，使用 Counter 计算重复词的交集，逐个参考答案计算 token F1，取最大值。任一侧 token 为空时按原生函数处理：双方都空为 1，否则为 0。

Gold 必须是非空的非空字符串列表；非法数据在请求前报错，不记为作答错误。原生函数的归一化空串行为不另外改写。

向本方法内部映射：`exact_match → em`、`best_token_f1 → f1`、`success = (em == 1)`；EM 只允许 0/1，F1 是有限的 [0,1] 浮点数。不能继承 LMB 的 f1==em 二值校验。

## 5. Gate 与汇总

Gate 比较同一批 15 个 ID，Parent 与 Candidate 必须各自完整、无重复，并处于相同数据、Prompt、模型和 scorer 协议下。成功数分别为 EM=1 的题数：Candidate 严格更多才 ACCEPT，否则 RETAIN。F1 提高不能抵消成功数持平或下降，不继承 SkillAdam 原生的 EM/F1 增益阈值 Gate。

训练时可按原演化框架复用同批、同协议下已完成的 Parent 轨迹；不为得到更好的分数重新请求 Parent。缓存和恢复必须绑定题目、Skill、Prompt、模型和数据身份。

最终 Test 汇总为 1400 题的平均 EM、平均逐题最佳 F1，以及成功数／总题数。未完成题不能当零分；可显示完成进度，但在完整完成前不发布正式全量指标。Test 不反馈给演化或 Memory。

## 6. 失败与证据边界

| 情况 | 行为 |
|---|---|
| 正常 stop，答案正确／错误／空串／无标签 | 按上述抽取和评分完成一次，不因得分重试 |
| length，即使 content 已含答案 | 原始响应先归档；不评分，原消息原参数重试 |
| 可重试网络或信封结构错误 | 与 length 共用六次总尝试，含首次 |
| 明确拒绝、非法工具调用等终止错误 | 按 v27 原有分类停止 |
| 六次耗尽 | 标记未完成，无 result，不补零分，恢复不重置额度 |
| 完整响应已落盘 | 本地恢复解析与评分，避免重复请求 |
| 完成归档损坏 | 校验失败后停止，不能伪装成待重跑题 |

隐藏推理与失败尝试只保存在审计归档。普通响应、真实输入和任务完成结果才可进入执行证据；参考答案只能用于训练评分／允许的诊断事实，不能回注 Actor 或改写既有预测。

## 7. 最小执行产物与身份

建议每题保存 task ID、数据 revision/哈希、Skill 哈希、Prompt profile/哈希、Actor 参数、普通 content、extracted_answer、em/f1、终止原因、已耗用尝试及 usage。预测字段只由 content 推导；参考答案可记录在隔离的评分结果中，不加入 initial_messages。

版本候选：`v28_searchqa_actor_answer_element_words_v1`、`v28_searchqa_skilladam_scoring_v1`。未来切换 Prompt 或 scorer 必须改变对应身份，不能复用旧身份继续写同一执行归档。

已有参数保持不变：600／1400，batch=15，1 epoch，40 批，训练／测试并发 15／15，Actor 输出上限 49,152，DeepSeek thinking enabled／medium／temperature=1，300s／10s 超时，SDK 重试 0。

## 8. 实施后的离线验收要求

- 逐题比对 2000 条输入中 question/context 的原始字符，确保 Gold、数据内部字段和隐藏推理不会进入 Actor。
- 非空／空 Skill 的注入位置与源实现一致；检查花括号、换行和非 ASCII 文本。
- 标准标签、多标签、大小写标签、标签内换行、无标签、空串、未闭合标签及最后匹配规则。
- 与 SkillAdam 原生评分函数逐例差分：冠词、标点、Unicode、下划线、重复词、多答案、部分匹配、空 token。
- Gate 的成功数增加／持平／下降、仅 F1 增加、不完整配对、任务集合或身份不一致。
- 用合成响应验证 length 共用额度、六次耗尽、已保存响应恢复、归档损坏及隐藏字段隔离。

本轮 `design_validation.json` 仅记录源模板提取、候选 Prompt 差异和原生解析／评分合成样例的核对，不代表上述完整适配验收已完成。
