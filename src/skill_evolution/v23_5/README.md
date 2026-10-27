# V23.5 实现基线

[24 个实验与结果导航](../../../experiments/methods/v23_5/README.md)。截至 2026-10-27，
`alfworld_verified_feedback_001` 的六轮优化及最终 Test 已完成，结果为 120/134；
其他实验的准备、停止和追加尝试分别记录。下文的验证描述保留各功能实现时的上下文，
不代表本次目录整理重新运行了实验、测试或项目校验入口。

本版本实现独立版本入口、共用无行号补丁，以及已定稿的 Diagnosis、
Preconditioner、Editor Prompt 微调，以及 Knowledge Only 输入投影与配套 Prompt。
Preconditioner、Replay 的新运行默认采用 Knowledge Only；Memory v3 保留为显式兼容选项。
新 Campaign 默认启用有限输出校验反馈，使用独立的精简 Prompt；旧协议及原 Prompt 保留。
新的 ALFWorld 准备/运行入口采用 `action_only_v1` 输出协议，thinking 保持开启。

## 已实现范围

| 模块 | 内容 |
|---|---|
| Diagnosis | 可执行的行为选择；针对具体异常恢复；协议内可观察性与阶段范围；先核对 Parent 已有要求 |
| Preconditioner | 整条 Keep 判断；探索取舍；所有存活 Updates 与 Parent 的一致性；无行号补丁 |
| Editor | 无行号补丁；字段/标签内部约束不扩大为整个响应禁令 |
| Grouping / Actor / Gate | 复用已有实现；Actor 输出措辞按冻结配置选择，Gate 不变 |
| Replay | 适配 V23.5 Editor 来源链；按配置选用 P4 / Memory v3 或 Knowledge Only Prompt / 视图；Memory schema 不变 |

Checks 仍可为空、无需逐项覆盖。任务要求不得因恢复而改变；信息可用性由 Actor
执行协议决定。历史证据支持提出并检验策略，不要求历史已经证明新策略有效。

Knowledge Only 的 `memory_knowledge_only_v1` 已实现。配置将 Preconditioner 的
视图/Prompt 和 Replay 的配对视图/Prompt 一起冻结；混搭或未知版本会明确失败，
不自动回退 Memory v3。V23.4 继续使用其原有协议。

## 配置与入口

当前 ALFWorld 入口使用
[Actor 反馈实验配置](../../../experiments/methods/v23_5/alfworld_action_feedback_001/README.md)。
旧 [initial skill 对齐实验](../../../experiments/methods/v23_5/alfworld_initial_skill_001/README.md)
保留原始协议和全部记录。

`actor_output_format=action_only_v1` 将 Actor 无历史、有历史模板中的输出要求替换为：

```text
Return exactly one XML-style element named `action`.
Its text content must be one command copied verbatim from the current admissible action list.
Do not include any text outside this element or any nested elements.
```

本版本的 [ALFWorld 初始 Skill](alfworld_initial_skill.md) 只将原 Output format 一句
替换为同一措辞。准备脚本核验它与 SkillOpt 初始快照之间只有这处修改，并冻结完整正文及哈希。
新模板由共享 Actor 适配器显式选择，不覆盖 SkillOpt 源文件或旧模板快照，不在发送时修改 Skill。
观察、最近两步历史、动作候选、Skill 注入位置、动作解析器、模型参数和请求额度均不变。
新协议仍使用 `thinking=enabled`；它只取消正文另行输出 think 标签的要求。

新准备的配置同时设置 `actor_retry_invalid_actions=true`、`actor_action_feedback=true`。Actor 每次正常返回后，
沿用原解析器检查是否找到完整 action 标签，以及提取的命令是否属于本步实际展示的
动作列表。缺少标签或命令不在列表时，在原始输入后追加最近一次实际正文（assistant）
和具体诊断（user，`# Previous Action Validation Error`）。诊断只指出格式问题或
非法命令，不推荐替代命令，不加入独立思考字段，不累积所有失败历史。技术重试及
截断原样复用整份既有请求，包括已有反馈。不修改输出预算，与超时、限流、截断等
共用每步最多六次总请求。有效动作只请求一次
即可执行；拒绝的响应不执行回退 `look`，不推进环境或历史。耗尽额度停止 episode
并保存现场。合法动作执行后的 `Nothing happens` 不触发请求重试。

这是本地校验，不调用额外模型。每份 HTTP 原始响应、请求哈希、实际 usage 及输出
拒绝原因均保存；失败请求已消耗的 tokens 仍计入成本。运行协议记录为
`previous_action_validation_error_v1`，训练、Candidate 和最终 Test 共用该冻结规则。
每次请求另存完整 messages、反馈来源尝试号、失败正文和诊断；重载逐次重建请求，
核对请求哈希与原始响应正文。只启用动作重试的旧配置继续使用
`retry_invalid_action_same_request_v1`；两项都未启用时保留原回退行为。普通恢复不会把中断 episode
伪装为续接同一步；显式恢复仍按既有规则重跑中断任务，已完成任务复用。

实际模板与 `output_format` 写入 Actor 运行记录，训练、同批 Gate、最终 Test 共用配置。
Grouping、Diagnosis、Preconditioner、Editor、Replay 继续从运行记录获取 execution context，
无需在各模块 Prompt 中维护模板副本。重载重建实际消息并核验协议，不能在恢复时切换。
未声明 `actor_output_format` 的配置仍采用旧模板；旧版本/通用适配器的默认值不变。
`baseline_config(base)` 仍保留调用方的 Actor 配置；创建新 action-only 配置时应显式设置该字段。

`scripts/runs/prepare_v23_5_alfworld.py` 与 `run_v23_5_alfworld.sh` 的默认目标已切换为
新的 `alfworld_action_feedback_001`；带 Memory 核验的入口使用
`alfworld_verified_feedback_001`。不会原地切换旧实验协议。准备只生成离线配置，
不初始化或执行 Campaign。旧 Campaign 的源码冻结要求仍然有效，不能用新源码绕过它恢复。
旧 SkillOpt 初始 Test 成绩仅作历史参考，不视为修改后 Actor/Skill 的同条件基线。

这项修改减少已知标签触发源，不修复服务端解析器，也不保证后续 Plan 重新引入标签时不会复发。
前置验证见 [16 次真实请求报告](../../../experiments/methods/v23_5/action_format_probe_001/RESULTS.md)。
旧 `u3`、历史失败输出、请求和额度均未修改。
新配置可指定 `initial_skill` 的完整 `text` 和 `sha256`，初始化时冻结为
`initial_skill.md`；省略时仍从 No Skill 开始。`epoch_schedule` 显式记录 epochs、
round_epochs 和 batch_size，允许任务跨 epoch 重复，但每个 epoch 必须恰好覆盖同一
任务池一次；省略时保留全 Campaign 不重复规则。Memory 连续跨 epoch 发布。
恢复及最终 Parent 审计均核对初始 Skill；不改变 Gate、模型预算或已有 Campaign。
本次 ALFWorld 配置显式设置 `actor_skill_injection=skillopt_user_v1`，将 Skill 按
SkillOpt 原包装放在 user 消息前部。训练、同批 Gate 和独立 `v23_5.evaluation`
最终 Test 共用 Actor 命令构造及协议；只有任务、用途和待执行 Skill 不同。
省略字段时继续使用原 system 注入；协议和实际消息都进入冻结及轨迹校验。
`module_max_tokens` 可为指定方法模块冻结独立的正整数输出预算，仅覆盖 `max_tokens`，
其他参数继续共用 `call_config`。未指定模块保留默认值；Actor 不读取这个映射。
当前 ALFWorld 实验将 Preconditioner、Replay 设为 32,768，其余模块及 Actor 为 16,384。
反馈重试与旧重试入口均采用相同的模块预算，重载核对已保存的调用配置。

`config.method_config()` 返回完整的方法版本配置；`config.baseline_config(base)`
深拷贝已有运行配置，仅替换方法配置，并执行 V23.5 配置验证。任务批次、模型配置、
执行预算等原值保留。必须使用新的 Campaign 目录，不更新已运行版本的冻结记录。

```python
import json
from pathlib import Path
from src.skill_evolution.v23_5.config import baseline_config, MEMORY_V3

base = json.loads(Path("/absolute/path/to/base/config.json").read_text())
config = baseline_config(base)
# 显式 Memory v3 对照使用 baseline_config(base, memory_view=MEMORY_V3)。
Path("/absolute/path/to/new-config.json").write_text(
    json.dumps(config, ensure_ascii=False, indent=2) + "\n"
)
```

运行入口（执行这些命令会开始真实模型和 Actor 工作）：

```bash
python -m src.skill_evolution.v23_5.evolution run --campaign /absolute/path/to/new-campaign --config /absolute/path/to/new-config.json
python -m src.skill_evolution.v23_5.evolution resume --campaign /absolute/path/to/new-campaign
python -m src.skill_evolution.v23_5.evolution status --campaign /absolute/path/to/new-campaign
```

保留现有冻结、配置化有界请求预算、技术失败恢复、配对、Gate 与原子发布行为。
`max_attempts` 与 `actor_request_attempts` 均计入首次请求，支持 1–6 次总尝试。
当前 ALFWorld 实验使用 6（首次加最多 5 次重试），历史配置中的 3 仍表示三次总尝试。
不会继承 V23.4 某次运行的 output-budget amendment；本阶段的 V23.5 基线固定预算，
没有新增预算恢复策略。整个方法配置和依赖源码/Prompt 在初始化时冻结。
严格模式 Actor 与 V23.5 方法调用将 HTTP 401 纳入同一总尝试额度，
仍不重试 HTTP 400/403。已启动 Campaign 只有在用户明确授权后才可通过
`retry_401.enable(campaign, reason=...)` 登记 HTTP 401 恢复变更：保留原始配置、
源码快照和全部轨迹，另存批准源码、差异和授权原因。恢复复用已完成任务，
仅重跑中断的 episode；旧/新 Actor 配对须经精确源码哈希审查。
Editor 耗尽六次调用后，只有用户明确要求继续时，才可通过
`editor_retry.enable(campaign, round_number=..., reason=...)` 为指定轮次追加六次调用。
保留旧请求与反馈，按 007–012 接续；原始配置、其他轮次/模块、token 上限不变。
批准源码与单轮额度另存于 `amendments/editor_retry_v1/`；普通 resume 不会再次增加额度。

新调用的配置构造、Preconditioner 输入/校验与 Replay 输入/校验默认一致采用
Knowledge Only。视图绑定下表版本；新的 `retry_policy` 同时绑定对应的精简 Prompt 变体，
不修改旧 Prompt 文件或输出契约。
加载器始终按记录中的视图和 Prompt 版本重建输入，不用当前默认值覆盖。
Campaign 重试和断点恢复沿用其冻结配置；Memory v3 配置仍通过版本校验。
已有源码冻结校验保持不变：源码不同的旧 Campaign 需在其冻结实现下继续，
不能用本次默认切换改写旧契约。冻结对照仍按原 arm、messages 和配置读取。

## Knowledge Only 输入与引用权限

| 配置项 | Knowledge Only 版本 |
|---|---|
| memory_view | `memory_knowledge_only_v1` |
| preconditioner_prompt | `v23_5_preconditioner_knowledge_only_v1` |
| replay_input_view | `v23_5_replay_pairs_knowledge_only_v1` |
| replay_prompt_version | `v23_5_replay_knowledge_only_v1` |

`memory_view.py` 先验证完整 Memory，再输出 `{format, entries}`。全部活跃条目及
Knowledge 的顺序、文本和 evidence 原样保留；旧格式可在只读视图中包成一个
Knowledge，不改磁盘记录。不会筛选、总结、截断、增加 Knowledge ID 或改变输出 schema。

Preconditioner 保留当前 Parent、Original Plan、Grouping、按原规则选出的完整
当前执行及动作候选。Replay 保留当前 Parent、实际 Diff、Effective Plan、全部
配对执行、动作候选，以及经过核验的 task_id / outcome / steps 配对信息。
历史原始 Parent、Diff、轨迹、详细观察、动作候选、pairing、窗口和 command pool
均不发送给模型，也不触发历史配对检索。完整档案仍保存，供校验与审计使用。

历史引用权限为输入全部 Knowledge 的 evidence 数组的**精确并集**，还必须在完整
档案中存在。提供一个 step 不会自动授权其 run、相邻 step、initial、outcome 或
关联 Diff。Preconditioner 的 reason 仍可引用当前证据、Memory ID 和已有 Plan
对象，保留单反引号规则；其他生成文字中的显式历史引用也受限制。Replay 的
`revises` 仅接受活跃 Memory ID；每项 `evidence` 接受当前证据与已提供的历史出处，
Memory ID 不能充当事实证据。Knowledge 文本中的显式历史引用同样受限。

Replay 的 Knowledge 正文及 Preconditioner 的 `change`、Update、Check 正文
按完整斜杠表达识别引用。`P6/Q6`、`Q10:35/Q10:39`
等表达仅在每个成员都是本轮实际存在的执行或步骤 ID 时，作为当前引用并列处理；
不会从步骤表达中截取 `35/Q10:39`。若同时与历史来源名称冲突，明确拒绝为歧义。
历史来源名称仅用于程序判别，不增加模型输入或引用权限。`evidence` 数组仍要求
每项是一个精确 ID；正文兼容不扩展到证据数组。Preconditioner 的 `reason` 仍需
逐个反引号引用，不能将多个 ID 放在同一对反引号中。v23.5 的 Effective Plan
编译和 Editor 重验采用相同正文扫描器，旧版本编译默认规则不变；不自动改写旧实验结果。

两个 Prompt 均允许直接复用历史认识，区分当前直接观察与历史转述，保留条件、
反例和不确定性。Replay 修订仍替换整个 MemoryEntry，必须自行输出应保留的完整
Knowledge 数组；程序不自动补回遗漏项。未提供历史原件不是反证，不得虚构历史
细节或声称重新核查。引用存在和结构有效不保证语义正确，也不保证知识不会遗漏。

两个模块均保存完整 `input.json`、实际发送的 `model_input.json`、`messages.json`、
`prompt.md` 和版本元数据；重载重新构造投影、核对 Prompt，并重验引用权限。
Replay 的 `history_pair_sources.json` 在此视图下固定为空对象。非法档案在请求前
失败；非法输出是失败尝试，不转换为 Keep / 无修改。重试沿用相同冻结输入与视图，
没有自动补证据或回退视图；输出反馈修正与技术重试共用原有请求额度。

## 有限输出校验反馈

`method.retry_policy = previous_output_validation_error_v1` 是新 Campaign 的默认协议。
Diagnosis、Preconditioner、Editor、Replay 使用各自 `*_feedback.md` Prompt 变体：
合并重复格式提醒，保留 JSON schema、单反引号引用、无行号 Diff 和必要示例。
Grouping、Actor、Gate 的 Prompt 与职责不变。Grouping 当前也接入同一输出校验反馈；
Actor 的两类动作错误使用上文的独立动作诊断，其他技术错误保留既有请求。

新请求不超过冻结配置中的 `max_attempts`；格式修正和技术重试共用额度，断点恢复不会重置已用尝试。
先检查结束原因，`finish_reason=length` 不进入 JSON/补丁错误反馈；V23.5 固定输出预算，
不加预算、不续写 JSON，长度失败仍可能重复。旧版本的冻结长度恢复策略不变。

只有输出解析、schema、引用和补丁校验边界内的已知检查失败能生成反馈。
Preconditioner 的输出结构检查会定位数组下标、可用的 Update ID、缺失/额外字段及
类型路径，并有界汇总同层错误；超出诊断预算时明确标注未展示的错误数量。
结构完整后仍执行原有全部校验，不自动补字段。专用 schema 异常仅在明确的输出
检查来源处转换为具体 `location/error`，旧版共用 `fields()` 与输入校验保持不变。
分类依据执行函数及来源，不按异常文本猜测。输入/档案校验、保存、重载、未知内部异常，
以及显式标记的已识别校验器缺陷，均不反馈成模型内容错误。技术失败沿用可重试性判断；
已保存且正常结束的完整响应在技术失败后可复用，不要求此前已完成输出校验；
复用时仍须完整重验。运行中不修改程序。

修正消息为原有 system/user 消息，加上上一份实际正文的 assistant 消息，以及以
`# Previous Output Validation Error` 开头的 user 诊断。独立推理字段不加入。
只保留最近一次输出失败的正文和诊断；诊断最多 600 字符，不引入任务证据或历史权限。
每次要求重新提交完整结果，所有校验重新执行；合法语义停止、Gate 拒绝不触发修正。

技术重试保留整份既有请求。例如“引用错误 → 带反馈请求超时 → 原样重发带反馈请求”，
既不追加超时说明，也不退回无反馈的原始输入。新输出错误则替换最近一次反馈。

各尝试保存 `request_context.json`、实际 `messages.json`、响应和含错误类别的 `error.json`。
请求上下文记录协议及反馈来源；重载据此核对实际消息、视图和引用权限。
恢复保存的完整响应不发新请求，也不占用新请求额度。未完成的恢复目录保留，
再次恢复在同一尝试下新建带序号的恢复目录；已完成的恢复结果直接重载。
本地恢复失败按配置的尝试次数有界停止，后续 resume 可继续处理缓存响应，
即使模型请求额度已耗尽。普通 resume 不自动追加模型请求额度。

旧方法配置没有 `retry_policy` 时继续使用原 Prompt 和重试路径。需要新建原样重试对照时，
可显式使用 `baseline_config(base, retry_policy=LEGACY)`（`LEGACY` 来自 `output_feedback`）。
冻结对照工具明确采用旧协议，既有输入、Prompt、配置和结果不迁移、不重写。

## 无行号补丁

实现位于 `shared/unnumbered_patch.py`，Editor 和 Preconditioner 共用：

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@
 ## Action Output
-- Never output reasoning text.
+- Inside <action>, output exactly one currently admissible action command and no reasoning, explanation, or placeholder text. Follow the runtime prompt for the rest of the response format.
```

- 只有 `@@` hunk 头；有行号、行数或尾注的头均拒绝。
- 每行只移除第一个编辑标记，Markdown 列表、缩进、空白和 LF/CRLF 原样保留。
- 每个旧片段必须在冻结源的完整行边界上精确且唯一匹配。
- 模型必须按源位置递增输出；程序不排序、不模糊匹配、不修补、不回退全文替换。
- 各 hunk 的匹配区间（含上下文）不能重叠；全部通过后才生成结果。
- 非空源中的插入必须有上下文；空源只允许一个纯新增 hunk。
- 末尾无 LF 使用 `\ No newline at end of file`，JSON 中反斜杠须转义。
- 单行 Original 可以删除旧行并添加修改后的新行；不要求迁移历史文本。

Editor 匹配 Parent Skill，保持 `patch: ""`（no_change）和 `patch: null`
（needs_revision）。Preconditioner 匹配 `target` 对应的冻结 Original Update，
保持 `to: null`（Keep）、`to: []`（撤回）和非空 `to.patch`（修改）。
Preconditioner 不接受 Editor 的空补丁或 null 补丁语义。

Editor 保存原始 `patch.diff`、`candidate.md` 与标准 `actual.diff`。
Preconditioner 保存原始 `parsed.json`、编译结果及按 target 索引的标准
`actual_diffs.json`；撤回仍由原始 Adjustment 明确记录，不伪造存活 Update。
两个加载器均重新验证上游和实际应用结果。

## 验证

```bash
python -m pytest -q tests/skill_evolution/v23_5
python -m src.skill_evolution.v23_5.evolution --help
```

测试使用合成响应与轨迹，不调用模型或 ALFWorld。覆盖精确编辑和拒绝行为、
Keep/撤回语义、两轮交接、Memory 提交、版本隔离、保存后重载与篡改拒绝。
Prompt 中的 JSON 补丁示例也经过实际应用检查。Knowledge Only 测试覆盖投影无损、
当前事实保留、不可见引用拒绝、保存后权限重验、版本混搭拒绝，以及 ACCEPT / RETAIN
两轮 Memory 交接和非法引用后的同输入重试。

`test_default_view.py` 检查默认版本与引用权限，并对两个模块、两种视图分别验证：
响应保存后中断的零请求恢复、有效结果保存后中断的重载、三次失败后恢复仍保持额度耗尽。
第二轮包含历史 Memory，恢复前后 messages、视图和 Prompt 版本一致。

`test_feedback_retry.py` 覆盖四个模块的输出反馈、最近一次反馈替换、同请求技术重试、
截断先于解析、固定预算、保存/重载与校验器缺陷分类，以及带反馈请求的中断恢复。

测试通过证明接口和确定性处理成立，不证明策略有效、泛化能力或成功率提高。
已实现并构造 R03–R06 的单轮冻结对照输入、运行/恢复入口和统计工具，见
[对照协议](../../../experiments/methods/v23_5/knowledge_only_single_round_001/PROTOCOL.md) 与
[准备验收报告](../../../experiments/methods/v23_5/knowledge_only_single_round_001/reports/PREPARATION.md)。
R03–R06 的实际对照与语义核查已完成，见
[R04–R06 效果比较](../../../experiments/methods/v23_5/knowledge_only_single_round_007/reports/R04_R06_COMPARISON.md)。
本次默认切换仅进行离线接入验证，没有新增真实模型或 Actor 调用。连续 Memory
回放另行实现，不能用合成测试或固定轨迹证明任务成功率提升。
