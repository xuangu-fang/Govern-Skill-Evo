# v28 五模块 Prompt 与执行证据设计

状态：待审阅方案。只新增本目录文档、完整英文 Prompt 草稿及合成证据样例；不修改已验证的 Actor/Gate，不安装五模块，不调用模型，不启动训练或 Test。

## 1. 继承范围

按用户最新决定，以 v27 当前实现为方法基线，仅迁移 SearchQA 必需的任务和评分语义。v25.2 的两项新增 Prompt 要求不纳入 v28，也不安排对应消融实验。来源文件与哈希见 `source_manifest.json`；这是方法基线选择，不代表已证明那些改动有效或无效。

| 部分 | v28 方案 | 不随迁移改变的边界 |
|---|---|---|
| Grouping | v27 分组职责，换成 SearchQA 的可见决策问题 | 覆盖当前全部 Parent，每题恰好一组；不提出修复、不读历史 |
| Diagnosis | v27 的 Plan 合同与证据驱动提议 | 不设固定 Update 数量；每条有独立依据，保留必要耦合要求 |
| Preconditioner | v27 的 D/S/C、精确 Update patch、显式引用 | 不重新 Diagnosis、不加 Update ID；KEEP／修改／撤回均可 |
| Editor | v27 精确 patch 和最小必要修改 | 仅实现 Effective Plan，不读执行、Memory 或调整理由 |
| Replay | v27 的 Knowledge Only、多 Knowledge MemoryEntry、整条修订 | 引入 SearchQA 连续 F1 的解释；F1 不成为接受条件 |
| 审查、恢复 | 沿用 v27 当前 `knowledge_review=disabled_v1` 和方法输出校验重试 | 不新增 Verifier/Repair 调用或语义重采样；结构通过不证明语义正确 |

Diagnosis 不新增数量上限、截断、自动合并或数量驱动的重试。保留 v27 已有的独立依据、去重、冲突和必要依赖判断；不为覆盖所有失败而凑数。Preconditioner 保留原 D/S/C 判断，不叠加新的精简修订段落，也不能跨 Original ID 做结构性合并。

## 2. 调用链与模型可见范围

```text
Parent 批次执行与归档校验
  → Grouping → Diagnosis → Preconditioner → 编译 Effective Plan
  → Editor → 程序应用 patch 得到 Candidate 与 actual diff
  → Candidate 同批执行与归档校验
  → 程序 Gate（只看 EM 成功数）
  → Replay（不接收 Gate 决策）→ 校验并提交 Memory
  → 一并发布选中的 Skill 与 Memory，进入下一批
```

沿用 v27 的分支：Diagnosis 合法 no_change、Preconditioner 撤回全部 Updates、Editor 返回空 patch 时，保留 Parent 和已有 Memory 并继续下一批，不生成 Candidate 或调用 Replay。Editor 返回 null 表示必要要求无法实现，停止本轮等待处理，不当成 no_change。存在完整 Candidate 配对时，Gate 无论 ACCEPT/RETAIN 都进入 Replay；若 Replay 或 Memory 提交失败，不提前发布已算出的 Gate 结果。

模型参数继续使用既定 v28 配置：Actor 与五模块均为现有 DeepSeek 配置；Grouping/Editor 输出上限 16,384，Diagnosis/Preconditioner/Replay 为 32,768；方法调用最多六次、失败间隔 2 秒。此稿不增加调用阶段或改变预算。

| 模块 | user JSON 顶层字段 | 可见执行与历史 |
|---|---|---|
| Grouping | `parent, runs` | 当前整批 Parent 的允许证据；无历史 Memory |
| Diagnosis | `parent, runs, grouping` | 同一整批 Parent＋Grouping；无历史 Memory |
| Preconditioner | `parent, plan, runs, memory` | Original Plan 直接引用所选中的完整 Parent runs；全部活跃 Knowledge Only Memory |
| Editor | `parent, plan` | 仅 Parent 与程序编译的 Effective Plan；basis 只是来源 ID，不授权读取证据 |
| Replay | `parent, diff, plan, runs, pairs, memory` | 当前全批已验证 P/Q、实际 diff、有效 Plan；活跃 Knowledge Only Memory |

每个 system Prompt 内嵌同一份无 Skill 的 Actor 基础协议及真实运行约束；它们是被分析的数据，不是给模块的作答指令。五模块输出保持英文 JSON。

Preconditioner 的选 run 规则沿用 v27：扫描完整 Original Plan 中的直接执行引用，取对应完整 run；不只扫描 basis。Group ID 不自动展开其所有成员。内部可保留 Grouping 用于合同校验，但发送给模型的 JSON 不包含 Grouping。

Editor 不看到 Diagnosis reason、Preconditioner reason 或 adjustment 对象；它收到的是已落实条件的 Update。因此行为条件必须在 Update 文本里，不能只藏在 reason 或 Checks。Replay 的 Plan 仅保留 goal、Update 的 id/text、checks，不把原 basis 当成当前执行事实。

## 3. 执行证据结构

区分两层：

1. **原始审计层**：保留已实现的 request、HTTP 原文、解码响应、六次尝试收据、签名、result、trajectory、batch records 和完整来源身份。它们供程序校验，不直接序列化到五模块。
2. **模型证据层**：由已通过原始归档验证的 train 执行投影而来；保持 v27 的 `P1/P1:0/P1:1/P1:outcome` 引用结构。Candidate 使用对应的 Q 引用。

拟使用独立版本 `v28_searchqa_facts_v1`，不能把新 schema 冒充 v27 LMB facts。

```text
run = {
  ref, task_id, run_id,
  initial: {
    ref: "P1:0",
    task: {question, context},
    messages: [完整 system, 完整 user]
  },
  attempts: [{
    ref: "P1:1",
    request_context: "searchqa_single_turn_v1",
    request_messages: 与 initial.messages 完全一致,
    assistant: {role: "assistant", content: 最终正常 stop 的普通文本}
  }],
  outcome: {
    ref: "P1:outcome", status: "completed", termination: "stop",
    answer: {raw_content, extracted_answer},
    reference_answers: 当前训练题的完整参考答案列表,
    model_rounds: 1, tool_calls: 0, api_requests: 1..6,
    score: {em: 0或1, f1: [0,1]内有限数}
  }
}
```

`reference_answers` 是新增的 SearchQA facts 字段，取自已冻结 dataset.case.reference。现有 Actor result/trajectory 不新增这一字段、不改变预测或重算基准。程序构造 facts 时关联参考答案并再次验证评分；参考答案只出现在训练执行 outcome，不出现在 Actor 请求中。

Grouping、Diagnosis、Replay 因可见相关训练 outcome 而可分析参考答案；Preconditioner 只看获授权 run 的 outcome；Editor 无此字段。Test 执行不得转为五模块或 Memory 输入。Skill/Knowledge 不得积累题号—答案、实体—答案或题目措辞—答案查表。

`attempts` 始终只有一个最终可见模型回合，不是 HTTP 重试列表。六次失败中的文本、length 答案、HTTP 错误和 reasoning_content 都不进入此层。api_requests 只说明请求次数，不能证明检索、思考、检查或犹豫过程。

上下文、问题和消息保留原字符；不裁剪、不改写、不按 `[DOC]` 自动生成新检索事件。引用 `P1:0` 表示 Actor 看到了该上下文，不表示它阅读、采用或核验了某个片段。仅输出短答案时，实体消歧、证据比对、答案筛选过程均不可见。普通 content 中的解释也只是模型陈述，不是独立验证。

保持 v27 的精确重复消息结构，不在本稿中新增去重、压缩或自动摘要。SearchQA context 会在 task、initial messages 和 request messages 中重复；后续容量验收需覆盖完整 15 个 Parent、15 个 Candidate 和活跃 Memory，不能用单题最长 context=4820 字符代替容量证明。

## 4. SearchQA 的判断边界

- EM 表示冻结归一化规则下与某个参考字符串完全一致，不等于对整个回答语义的独立裁判。不能凭低 EM 就宣称事实错误或 Skill 缺陷。
- F1 是与各参考答案的归一化词元重叠 F1 的最大值，允许连续值。`EM=1` 时 F1=1，但 `F1=1` 未必 EM=1，例如相同词元顺序不同。
- EM 和 F1 分别在完整参考答案列表上计算；现有 scorer 不输出“匹配了哪一个参考答案”的身份，模型不能据此虚构唯一匹配项或隐藏别名映射。
- F1 仅作结果诊断和报告；EM 持平而 F1 上升仍 RETAIN，EM 成功数增加即接受，即使平均 F1 下降。Replay 可以记录两者的变化，但不能将它们改写成双指标 Gate。
- 部分词元匹配不必然表示部分语义正确；补齐名字或限定词只在问题和 context 支持时有意义，不能为了 F1 堆词、列多个候选或复述参考答案。
- 标签偏离、答案边界与事实选择分别分析。当前 scorer 取最后完整 answer 元素，否则取最后非空行；无标签不一定得零分。格式偏差是否解释分数变化必须看真实抽取结果。
- 可考虑的决策问题包括实体区分、问题限定、证据冲突、时间关系、答案边界等；这些不是预设分组、固定错误标签或必加策略。不得默认多数片段正确、固定来源最可靠或每题必须逐篇核对。

## 5. 五模块的具体设计

### Grouping

围绕可见的“情境—选择”组织比较，例如两个相似实体在问题限定下如何区分；不能写成“Actor 没有认真读上下文”这类不可观察原因。正确与错误题可以同组，单例合法，不按得分或主题名称机械分组。每个成员必须在 shared_basis 中有最终回合引用，必要时辅以 input/outcome。输出仍为 `groups`，每组字段与 v27 一致。

### Diagnosis：沿用 v27 的证据驱动提议

不设固定 Update 数量。根据当前证据形成独立成立、可通过 Skill 实现的行为改动；区分不同修复并保留必要耦合要求，不机械按句子拆分，也不为了完整而加入无关最佳实践。没有合理依据支持的 Update 时返回 `no_change`；仍有其他合理、完整修复时可提出，不能省略必要依赖。

区分“Parent 缺少指导”“已有指导但未观察到执行”“可见执行仍未奏效”“仅凭短答案无法判断”。单例可支持合理的可迁移假设，无需先证明因果；但不能把观察不到的搜索/推理过程写成事实。每条保留 material trigger、行为、强度、例外、必要依赖和能力保留边界；理由写 reason，引用写 basis。

### Preconditioner：沿用 v27 的 D/S/C 调整

Direction 决定促进、限制或替代的行为；Scope 决定适用条件与强度；Coordination 处理 Parent 与各 Update 的冲突、依赖和重复。保持原 ID 与 Goal，逐个 Original 做 KEEP、精确 patch 或撤回；不新增独立修复。

沿用 v27 对方向、适用范围、强度、依赖和冲突的判断。历史 Knowledge 可以支持修正缺陷或发展合理提议；没有历史不自动 KEEP，有历史也不强制修改。保留已有的去重与能力保护要求，不额外引入 v25.2 的“逐项新增行为差异／优先替换合并”指导段落，也不设置缩短比例或撤回配额。Checks 仍是观察性问题，不是额外 Actor 指令。

明确处理完整 Update 的所有条件，包括附加排序、fallback、例外；不能认可主要方向后忽略有问题的附带要求。Checks 用 null 继承、[] 清空或完整列表替换；撤回使 Check 失效时必须显式修正。

### Editor：忠实实现有效 Plan

只修改 Skill，按 v27 无行号精确 patch 合同工作；不重新诊断、不插入新策略。优先修改相关规则并保留作用范围，避免并行矛盾条款。SearchQA 允许普通解释后提交短答案，不能照搬 LMB 的 A–E 标签或禁止所有元素外文本要求。

`patch=""` 表示 Parent 与基础协议已满足全部有效要求；`patch=null` 表示必要要求无法忠实实现，按 v27 停止本轮，不能伪装为无变化并继续。非空 patch 由程序原子应用，生成 Candidate 和 actual diff。初始 Skill 尚未选定，本稿不假定它非空，也不借用 v27 初始 Skill。

这里保留 v27 的两种不同格式：模型输出的 Editor/Update patch 使用裸 `@@` 的无行号合同；程序生成给 Replay/Memory 的 actual diff 是带行号的标准 unified diff。后者通过对应的带行号解析器核对 Parent→Candidate，不能误用无行号 patch 解析器。

### Replay：观察实际编辑与配对响应

先读 actual diff 和 Parent 上下文，再遍历全部显式 pairs；不能凭 P/Q 编号或列表顺序猜配对。对比输出文本、抽取答案、EM/F1 与相关输入条件；区分 EM 改善、退化、持平但答案改变、F1 改善等现象。

明确“本次实际修改与观察到的变化”及其适用边界，保留反例和联合编辑的不确定性。一次采样差异不证明稳定 Skill 因果效应；RETAIN 仍可产出有价值的历史 Knowledge。历史只见 Knowledge Only，不假装重读历史原文。

MemoryEntry 仍为整条替换、多 Knowledge 结构；每条 Knowledge 自带证据，每个输出 entry 的 evidence 联集须包含实际 Diff 来源和执行来源。修订时保留原有仍有效的知识及其原历史引用，不把新结果倒写成旧事实。输出仅 `entries`，不新增 Gate、分数报告、置信度或任务答案表字段。

## 6. 输出合同与引用

| 模块 | 顶层输出 | 核心约束 |
|---|---|---|
| Grouping | `{groups}` | 每组 group_id/members/decision_problem/shared_basis/important_differences；全覆盖且无重复 |
| Diagnosis | `{decision, reason, plan}` | revise 时 plan=goal/updates/checks；no_change 时 plan=null；Update=id/text/basis |
| Preconditioner | `{adjustments, checks}` | 每项 target/focus/change/reason/to；KEEP＋[]＋null 配套，修改为精确 patch，撤回为 [] |
| Editor | `{patch, reason}` | patch 为有效精确 diff、空字符串或 null；不另传 Candidate |
| Replay | `{entries}` | entry=revises/knowledge，Knowledge=text/evidence；不由模型分配 Memory ID |

普通执行引用仍为 P1、P1:0、P1:1、P1:outcome；无工具子引用。Preconditioner 继续使用显式单反引号命名空间，例如 `Evidence:P1:outcome`、`Memory:M1`、`Update:u1`。历史只能引用当前 Knowledge evidence 中逐字授权的 context-qualified ID；不扩张到整 run、相邻 step 或旧 diff。

输出校验错误只反馈位置、错误和上次输出，沿用最多六次方法调用与已有间隔；错误提示不能变成补充任务证据，也不能读取隐藏推理。合法 no_change/null 不是格式错误，不语义重采样。Memory 无新增语义审查模型，代码校验只承诺结构、身份、引用和精确 patch 的正确性。

## 7. 后续实现与验收

本稿不改动 `src/skill_evolution/v28`，因此当前 Actor 实现身份不会因设计稿而改变。审阅后再新增 facts/evidence/prompting、模块合同和 campaign 接线，并使用新版本 ID。已有 Actor/Gate 档案不得在实现哈希变化后静默继续使用。

实施验收需覆盖：

1. 各模块实际发送 JSON 的字段白名单；Gold/隐藏推理/Test/失败尝试不能通过引用、错误反馈或 Memory 绕过可见范围。
2. facts 与原始归档、dataset reference、原始 content、EM/F1 的逐字段一致；多答案及 EM=0/F1=1 案例；不继承 LMB 的 f1==em 校验。
3. Grouping 全覆盖；Diagnosis basis 的直接证据及组成员约束；Preconditioner 只接收 Plan 授权 runs 与 Knowledge Only。
4. 无行号 patch、末尾换行、KEEP/修改/撤回、失效 Checks、Editor 空串与 null 的区别、引用越权及重复 ID。
5. Replay 完整 P/Q、真实 diff、跨历史引用、整条 Memory 修订、反例保留；Gate 拒绝时仍可提交有效 Memory。
6. 阶段中断后恢复不重跑已完成 Parent/Candidate、不重置模块额度；发布前重新检查 Gate 与 Memory，防止发布半完成轮次。
7. 15 题完整 context、双边 runs 与活跃 Memory 的输入容量。超限明确停止，不自动删题、摘要或截断证据。

`static_checks.json` 只报告本设计包的来源、模板一致性与合成样例检查，不代表五模块 runtime 或自然语言判断已验收。
