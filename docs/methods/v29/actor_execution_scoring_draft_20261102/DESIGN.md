# v29 Actor Prompt 与执行、评分协议

2026-11-02 试跑后确认：后续运行采用 Actor 32768、Grouping/Editor 16384、Diagnosis/Preconditioner/Replay 32768；超时沿用 300 秒。正式配置为 `experiments/configs/v29_docvqa_optimization160.json`。首批试跑已完成；按用户要求，其临时配置、执行归档及专用验收输出已删除。

2026-11-02 试跑调整：按用户要求参照 v27，Actor 输出上限改为 49152；五模块临时采用 Grouping/Editor 16384、Diagnosis/Preconditioner/Replay 32768，超时均为 300 秒。仅试跑第一批 15 题，正式预算仍待试跑结果确定；下文未启动说明描述此前离线阶段。

状态：设计稿，2026-11-02。本文集中说明 Actor 的完整输入、单轮执行、答案抽取、hard/ANLS 评分及五模块文本证据投影。沿用已确认的 v29 设计，没有实现运行代码或调用模型。所有响应示例均为人工合成，图片数据只用明确的占位符展示。

后续实现进展：第一阶段 Actor/评分/文本证据、第二阶段五模块/Plan/Replay/Memory，以及第三阶段训练主循环、调度恢复和 Parent/Memory 联合发布均已完成离线验收，见[实现说明](../../../../src/skill_evolution/v29/README.md)与[第三阶段说明](../CAMPAIGN_IMPLEMENTATION.md)。本文及示例保留为设计依据，没有调用真实模型、训练或 Test；五模块预算继续待定，独立 Test 调度尚未接入。

## 1. 文件与设计来源

| 文件 | 内容 |
|---|---|
| [actor_system.md](actor_system.md) | 完整英文 System 模板，只有 skill_section 占位 |
| [actor_user.md](actor_user.md) | 完整英文 User 文字模板，只有 question 占位 |
| [initial_skill.md](initial_skill.md) | SkillOpt 原始初始 Skill 的设计副本，未改写 |
| [示例说明](examples/README.md) | 请求、合成响应、评分和优化证据的对应关系 |
| [scoring_examples.json](examples/scoring_examples.json) | 15 组合成抽取与评分示例 |
| [gate_examples.json](examples/gate_examples.json) | hard 与 ANLS 不同方向变化时的三组 Gate 示例 |
| [design_review.json](design_review.json) | 仅针对设计材料的离线一致性检查 |

System 模板及 Skill 插入位置来自 [SkillOpt DocVQA rollout](../../../../external/SkillOpt/skillopt/envs/docvqa/rollout.py)和 [SkillAdam DocVQA rollout](../../../../external/SkillAdam/skilladam/benchmarks/docvqa/rollout.py)，两份上游 System 模板内容相同。评分使用 [SkillAdam evaluation.py](../../../../external/SkillAdam/skilladam/benchmarks/docvqa/evaluation.py) 的抽取和 ANLS 定义。执行终止分类参考当前 v28 复用的 [Actor 响应解析](../../../../src/skill_evolution/v27/benchmarks/lmb/actor.py)。五模块输入边界以[已确认设计](../five_module_draft_20261102/DESIGN.md)为准。

## 2. Actor 实际收到什么

每题只发送一条 system 和一条 user 消息。system 包含固定协议及该次执行的实际 Skill；user 包含问题、固定答案提示和一张原始文档图片。参考答案、评分、Memory、其他题目及五模块分析均不进入 Actor 请求。

### 2.1 完整 System 模板

```text
You are an expert visual document question answering agent.

{skill_section}You will receive a document image and a question about the document.
Read the visual evidence carefully and answer concisely.

Rules:
- Ground the answer in the visible document content.
- Prefer exact spans, numbers, dates, and names from the document.
- Do not invent content that is not visible.
- If multiple near-matches exist, choose the one best supported by the document.

Return the final answer inside <answer>...</answer>.
```

非空 Skill 的 skill_section 为 `## Skill`、换行、`skill.strip()`、两个换行。只去掉 Skill 首尾空白，不改变内部内容；保存的 Parent/Candidate 原文不因此改写。模板保留上游文件末尾换行，不对最终 system 再做 strip。替换只作用于模板占位，不递归解释 Skill 内的花括号。

首次 Parent 使用本目录 [initial_skill.md](initial_skill.md)，与 [SkillOpt 原文](../../../../external/SkillOpt/skillopt/envs/docvqa/skills/initial.md)相同，不先执行 Stage0。Candidate 用 Editor 精确补丁生成的 Skill；只有 Gate 接受后才成为后续 Parent。没有 Skill 时 skill_section 可以为空，这是模板行为，不新增本轮无 Skill 实验。

### 2.2 完整 User 文字模板

```text
{question}

Return the final answer inside <answer>...</answer>.
```

question 使用数据中的原始非空字符串，保留其内部及首尾文字和空白；验证非空时可检查 strip 后的值，但不以该值替换原文。固定提示后不额外添加换行。此处与 SkillOpt 的直接拼接一致；SkillAdam 的辅助函数会去掉问题首尾空白，v29 明确选择完整保留问题。Skill 的首尾处理与问题的保留规则不同。

不加入 Training Readout、错误反馈、参考答案、强制解释或逐步推理提示。基础协议要求最终 answer 元素，但没有明确禁止元素外普通文本，也不要求额外解释。字母、编号、金额、日期等都可以是问题要求的合法文本答案。

### 2.3 图片内容块

user.content 按以下顺序包含两个块：

1. `type=text`，内容为上述 User 文字。
2. `type=image_url`，`image_url.url` 为本地原图字节编码的 data URI。

采用 `data:<MIME>;base64,<原图字节编码>`，不重新采样、裁剪、旋转或另做 OCR。按文件类型提供 MIME；沿用上游无法识别扩展名时的 image/png 默认值。本地相对路径以固定数据 release 根目录解析。图片必须能读取；不能把缺图静默降级成只给文字或图片路径的作答。

image_detail 的设计值是 auto。两份上游实现均在 auto 时省略 `image_url.detail`，v29 沿用该消息表示，不额外发送名为 image_detail 的顶层请求字段。普通文本路径不是图片附件。

[完整请求模板](examples/actor_request.template.json)已展开初始 Skill 和合成问题，仅图片编码保留占位符。该文件用于审阅，不能直接发送；没有创建合成图片，也没有包含真实图片字节。

## 3. 模型参数与单轮执行

| 项目 | 已确认值 |
|---|---|
| API | `https://api.deepseek.com/chat/completions` |
| model | `deepseek-flash` |
| thinking / reasoning_effort | enabled / medium |
| temperature / max_tokens | 1.0 / 32768 |
| stream | false，沿用现有执行方式 |
| Actor 模型轮次 / 工具 | 1 / 无 |
| 请求超时 / 连接超时 | 300 秒 / 10 秒 |
| 总请求尝试 | 最多 6 次，包含首次；SDK 隐式重试为 0 |
| 可重试失败后的等待 | 沿用 Actor 的 1 秒 × 已失败尝试序号 |

max_tokens 包括服务端计入输出额度的推理 token。这一 Actor 额度已确定，与尚待试跑确定的五模块输出预算分开。请求模板不包含凭据；执行记录不保存认证请求头。

一次任务是一次有效 stop 作答，而不是多轮对话。技术重试仍发送相同的 system、user、图片和参数，不拼接先前输出，不提高输出额度，不从多个响应中按分数挑答案。Parent 与 Candidate 使用相同题目、原图、模型参数和 scorer，只改变 Skill；Candidate 不接收 Parent 回答或评分。采样变化仍可能导致两侧输出不同。

### 3.1 响应与失败处理

| 情况 | 处理 |
|---|---|
| 有效 assistant 字符串 content，finish_reason=stop | 只从普通 content 抽取并评分一次 |
| stop，但答案错误、无标签、标签格式不理想或 content 是空字符串 | 按既定抽取规则评分，不按得分补答 |
| finish_reason=length，即使含完整 answer | 不评分；记录后使用相同请求重试，占用六次总额度 |
| 可重试技术错误或不完整/非法响应结构 | 沿用现有错误分类，共用六次总额度 |
| 明确拒绝、工具调用或不支持的终止原因 | 沿用现有终止分类，停止；不当成正常答错或补零分 |
| 图片/数据无法读取等本地输入错误 | 在发送请求前停止，不把它变成模型回答 |
| 六次额度耗尽 | 任务未完成，无评分；不形成完整 Gate 配对 |

“没有 content 字段”和“content 是空字符串”不同：前者是结构问题，后者在有效 stop 响应中可以正常得到零分。这里只规定与已有执行器一致的行为，不新增 HTTP 错误分类体系。

### 3.2 恢复与记录

保存任务 ID、使用的 Skill、实际请求参数与消息、图片路径、每次请求的开始/结束情况和响应、最终普通 content、抽取答案及评分。正常响应已保存时优先恢复抽取与评分，不重发请求；已经完成的题目直接复用。已开始但结果未知的请求占用原尝试次数；尚未开始的准备记录不凭空增加一次调用。恢复不重置六次额度。

原始请求中的图片编码属于执行侧记录，不能作为五模块输入。原始 API 响应若包含隐藏推理或 usage，保持在执行侧；优化证据不提供这些字段，也不从中补充解释。缺失 usage 保持未知，不写成零。失败尝试可以用于运行排查，但不作为 Diagnosis 或 Replay 的任务推理证据。

## 4. 答案抽取与评分

### 4.1 答案抽取

只读取通过执行校验的普通 assistant.content，不读取 reasoning_content、额外 answer 覆盖字段或工具结果。

按 SkillAdam 的 `<answer>(.*?)</answer>` 规则匹配，大小写不敏感并允许跨行：有匹配时，取最后一个完整匹配并去掉其首尾空白；没有匹配时，取最后一个非空行并去掉首尾空白；全文为空白时得到空字符串。已有完整匹配时，后面的未闭合标签不会覆盖它。

这是既有正则抽取，不增加 XML 修复、格式纠错、答案重写或再次模型调用。抽取后的预测与原始普通 content 都保留。

### 4.2 ANLS 与 hard

参考答案必须是非空字符串列表，每个答案去首尾空白后也必须非空。列表无效属于数据错误，不给任务补零分。

评分归一化仅做：转小写、去首尾空白、将连续空白合并为一个空格。不去冠词、标点、单位，不统一日期格式、数字分隔符或别名。

对于预测 p 和一个参考答案 a，先对两者归一化，再计算：

```text
d = Levenshtein(p, a) / max(len(p), len(a))
score(p, a) = 0       when d >= 0.5
score(p, a) = 1 - d   when d < 0.5
ANLS = max(score(p, a) for every supplied reference a)
hard = 1 if ANLS >= 0.999 else 0
```

空预测对有效非空参考答案的 ANLS 为 0。所有参考答案参与取最大值，不新增或改写参考答案，不输出命中哪条参考的身份。

hard 是上述阈值结果，并非严格的字符串相等判断：足够长的字符串即使差一个字符，也可能达到 0.999。评分时使用未四舍五入的 ANLS；展示时的小数格式不能改变 hard。

ANLS 表示字符相似程度，不证明语义部分正确或图片读取正确。单位、标点或日期格式差异可以解释字符串得分变化，但不据此产生“所有答案删单位”等通用策略。

### 4.3 Gate 与汇总

Gate 只对同一当前批次、完整的 Parent/Candidate 配对计算 hard 成功数：Candidate 严格更多才 ACCEPT，否则 RETAIN。ANLS 不作为附加接受条件。尾批同样按实际 10 题比较，不补题、不改变阈值。

完整评估集的汇总为题数、hard 成功数、hard 比例和逐题 ANLS 的算术平均。缺题时报告未完成，不把未完成题补成零分或冒充完整 Test 成绩。已确认 Test 为项目固定的 374 题保留集，不是官方 DocVQA test split。

## 5. 从图文执行到优化模块文本证据

Actor 的实际图文请求和优化模块的文本证据是两个不同视图。投影不改变原执行请求，只在供优化模块阅读的副本中替换图片内容块。

| 执行记录 | 优化模块可见内容 |
|---|---|
| system | 完整文本，保留本次实际 Parent 或 Candidate Skill |
| user 的问题及固定提示 | 完整保留文本、顺序和角色 |
| user 的 image_url 内容块 | 在原位置换成明确声明未提供图像内容的 text 块 |
| 最终有效 stop 响应 | 完整普通 content，不摘要、不截断 |
| 评分结果 | 预测、全部训练参考答案、hard/ANLS 和完成计数 |
| 失败响应、隐藏推理、usage、图片编码 | 不进入优化模块输入 |

图片占位示例为 `[Image attached to Actor: images/amount.png; image pixels are not supplied to this module.]`。路径只是文件标识，模块不打开图片，也不能据此声称看到了图片。Actor 自己在普通响应中描述或转录的文字完整保留并标明归属，不升级为独立核实的文档内容。

沿用既有 `ref/task_id/run_id/initial/attempts/outcome` 结构：`:0` 对应初始文本投影，`:1` 对应唯一有效模型回合，`:outcome` 对应答案及评分。attempts 不是 HTTP 重试历史；api_requests 记录实际请求次数。非 Replay 的 request_messages 等于该 run 的初始文本投影。

Replay 保留已确认的 shared_initial 共享方式并省略重复 request_messages；模型视图还省略与同 run 普通响应完全相同的 outcome.answer.raw_content，完整响应在 attempts[0].assistant.content 保留一次。两处省略均可无损还原，原始执行和 Memory 归档保留完整字段。Preconditioner 仍只读取 Plan 直接引用选中的 Parent 执行，并独立接收完整 Parent Skill。Editor 仍只接收 Parent 与 Effective Plan。Test 执行不进入这些优化输入。

## 6. 完整合成示例

本例沿用五模块主链的合成金额题：问题为 “What is the total amount due?”，参考答案为 “1,320”。Actor 的人工响应为：

```text
I will use the subtotal as the total.
<answer>1,200</answer>
```

抽取 “1,200”，与 “1,320” 的字符编辑距离为 2，长度为 5，因此 ANLS=0.6、hard=0。可以观察到 Actor 声称将 subtotal 当作 total；由于本例没有图片，不能确认图片中存在何种字段或实际读取过程。

请求、响应、评分、证据依次见 [actor_request.template.json](examples/actor_request.template.json)、[actor_response.synthetic.json](examples/actor_response.synthetic.json)、[scored_outcome.json](examples/scored_outcome.json)、[optimization_run.json](examples/optimization_run.json)。最后一份是五模块主链 P1 的完整副本，便于对照，未引入新 run 字段。

此次整理统一保留上游 System 模板的末尾换行，并同步补齐旧五模块合成示例的对应 system 字符串及共享表内容。其余 Actor 文字、合成响应、评分、Skill 策略和模块合同没有因此改变。

## 7. 已确定与仍待确定

Actor Prompt、初始 Skill、图文输入、单轮执行、Actor 参数、抽取评分及文本证据边界在本文集中确定。优化调度沿用既定 160 题、15 题批次、单遍 11 批；训练/Test workers 上限均参考 SkillAdam 设为 60，单侧训练实际并发受当前批次题数限制。

五模块 max_tokens 及其运行超时仍待后续试跑配置确定，不从 v28 的 batch=30 配置自动继承。本文不启动试跑、训练或 Test，也不把合成示例当作模型效果验证。
