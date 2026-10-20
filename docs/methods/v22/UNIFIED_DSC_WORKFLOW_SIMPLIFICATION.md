# V22 统一 D/S/C Skill 自进化：全流程简化讨论与设计方案

讨论时间：2026-10-16—2026-10-17。整理日期：2026-10-17。

本文覆盖共同证据表示、问题分类、Diagnosis、Fusion／Compiler、Editor、Replay／Memory，以及全流程工程简化。它是后续逐项修改的统一设计记录，不是仅针对 Diagnosis 的接口说明，也不是新实验结果报告。

**状态说明：** 已认可方向、候选设计和待核查事项分别标明。当前尚未按本文迁移代码、Prompt、Schema 或运行配置，未开展新的模型调用或 ALFWorld 实验，未验证简化收益。后续实施另行开展。

## 1. 目标、范围与决定总览

### 1.1 不变的研究目标

```text
共同决策问题分类
    ↓
Diagnosis 原始 Update
    ↓
Fusion 根据历史响应调整 D/S/C → Compiler 有效 Plan
    ↓
Editor 实际 Skill 修改
    ↓
Parent／Candidate 执行比较 → Replay／Memory 条件化响应学习
    ↓
下一轮更新
```

简化模型读写和程序维护负担，不改变 D/S/C 统一更新思想。方向、条件、尺度、义务强度、依赖、反例和未知仍需表达，但不要求五个模块各输出一套 D/S/C 字段。不增加独立 Agent、正常调用次数或任务专用规则，不以更保守代替更合理，不改变 Gate 的研究规则。

### 1.2 总览

| 范围 | 讨论结论 | 状态 |
|---|---|---|
| 分类／Diagnosis 输入 | 共用行为证据表示，减少无关元数据和重复装配 | 方向已认可；别名迁移细节待定 |
| 分类输出 | 保留五字段，明确问题、事实依据和重要差异的分工 | 已认可 |
| Diagnosis 输出 | 保留更新核心，减少 reason／intent／watch 重复，核查 open 独立用途 | 方向已认可；未决定删除字段 |
| Fusion 输入 | 读取 Diagnosis 直接依据及必要上下文，不重读全批轨迹、不另选反例集 | 已认可 |
| Fusion 输出 | 保留增量 changes，hold 并入 withdraw；减少机械 Watch 迁移和重复说明 | 合并已认可；迁移细节待核查 |
| Editor 输入 | Parent Skill、有效 Plan、与 Diagnosis 共用的能力和基础协议 | 已认可 |
| Editor 输出 | 保留完整文本与映射，缩短理由，限定 issues；核查新增 Watch 价值 | 方向已认可；取消 watch 未定 |
| Replay／Memory 输入 | 保留完整配对轨迹，复用 P1，只消除确定性重复 | 已认可；不做关键步骤或复杂历史筛选 |
| 共享内容与执行事实 | 解决 Memory 将共享内容误判为非独立执行的问题，见 §6.1.1 | 用户确认需要解决；具体实现待定 |
| Memory 输出 | 候选 effects＋unresolved，直接形成有依据的响应认识并完整修订 | 已记录候选方案；尚未冻结接口 |
| 全流程工程 | 全部移除 SHA256、重复哈希、嵌套绑定和冗余指纹 | 用户明确决定；尚未实施 |
| 术语命名 | 确定 goal／updates，记录 checks、issues、adjustments、MemoryEntry／entries 等候选 | 详见 §2.4；尚未迁移接口 |

### 1.3 讨论边界

下文描述“当前”时，是讨论期间核对过的实现；描述“拟议”时，是后续方向，不能混为已实现能力。教学示例不是实验事实。历史档案不在本次编辑范围内，本文不把过去失败重写为成功。术语决策集中在 §2.4；其余章节保留讨论时的字段名以说明对应关系，不表示继续采用已被否定的候选命名。

## 2. 共同输入表示与全流程工程简化

### 2.1 当前事实及共同表示方向

分类与 Diagnosis 读取同一批 Parent 行为事实。当前分类使用 experiences／T 别名，Diagnosis 使用 runs／P 别名；分类还重新编号合法动作列表。两者保留完整有序动作、观察、动作机会和结果，但元数据与外层组织不同。

拟共用的内容是：Parent Skill、Actor 能力、基础协议、任务目标、初始观察、完整有序步骤、合法动作菜单和结果。模型角色不同，不代表必须重复实现同一份事实的装配；共用基础表示也不意味着所有阶段读取同样范围。

- task_id、run_id、Actor 模型名称、环境种子、协议名称等通常不帮助模型理解具体行为，可从模型消费中省略。
- history 若已由 capabilities 说明，不重复展开；能力与基础协议必须表达实际执行能力。
- phase 若在装配前已确定全部为 executed，可不逐步重复发送，不能把未执行步骤当作已执行。
- 步数预算、结束原因和影响执行的配置差异不能因为精简而误述。共同约束可提供一次。
- 技术中断、步数耗尽、正常失败与成功应保持含义区别。
- T/P 别名及菜单编号是否统一另行核对，不为命名整齐扩大修改范围。

SHA256、冗余指纹和嵌套绑定不再采用“从模型输入挪到程序侧”的早期建议，按下一节的最新决定处理。

### 2.2 全流程移除 SHA256、重复哈希、嵌套绑定和冗余指纹

用户明确要求：**全部移除 SHA256，不采用逐个判断是否有作用再决定保留的方案。** 清理覆盖模型输入、内部数据结构、接口、持久化记录、版本命名、运行器及冻结／恢复流程中的相关字段、计算、传递、绑定与校验逻辑。

移除重复哈希、嵌套绑定和冗余执行指纹，不仅隐藏展示；不通过改字段名或换用另一种哈希继续保留同一套机制。此决定取代此前“这些内容只需留在程序侧”的建议。实施范围是后续流程，当前记录没有执行源码清理或改写旧实验档案。

### 2.3 command_sets 与 P1 不是同一次优化

合法动作由 ALFWorld 提供，项目程序负责存放、编号和去重。compact 输入以完整有序列表为键，生成 a1、a2 等编号；完全相同的菜单只保存一次，顺序和重复项仍保留。不同任务引用同一菜单不意味着目标、观察或动作相同。

至少在 2026-10-14 的 03 紧凑接口阶段，完整动作列表去重已存在，早于 17 P1。当前没有首次 Git 提交可用于确认精确编写时间。P1 在此基础上进一步共享不同菜单中的重复动作字符串、观察文本等，不是 command_sets 的首次引入。

先检查实际 P1 messages，已消除的重复不重新设计。模型省略元数据与 P1 精确还原是不同概念，不把前者宣称为消息完全无损。

### 2.4 统一术语：直观表达职责，不堆叠 D/S/C 标签

记录日期：2026-10-17。用户认为 Watch、Effect 等名称抽象、不易从代码理解用途，提出调整命名。命名应让读者直接理解对象与职责，不强行给所有字段加 D/S/C 前缀，也不改变算法语义。

**已明确认可的调整：**

| 当前名称 | 新名称 | 含义 |
|---|---|---|
| intent | goal | 本次更新希望改善的行为目标 |
| requirements | updates | 准备实施的行为更新及必要保留约束 |

updates 不意味着每项都必须产生新 diff；某项要求可能已被 Parent 满足。引用前缀是否从 requirement 改为 update、具体迁移方式及程序内部名称尚未确定，不能只改字段名而破坏现有引用。

**已讨论并同意记录的候选名称：**

| 当前名称／候选结构 | 候选名称 | 职责与边界 |
|---|---|---|
| watch | checks | 执行后需要检查的问题，不是新增执行 Agent 或 Actor 指令 |
| Diagnosis／Fusion 的 open | issues | 尚未解决的具体构造问题；不与执行后未回答的问题混为一谈 |
| Fusion 的 changes | adjustments | 对原始更新作出的调整，仍使用增量编译 |
| Effect | MemoryEntry | 一条持久记忆，避免暗示已证明的独立因果效果 |
| 新 Memory 方案的 effects | entries | 与 MemoryEntry 集合对应 |

MemoryEntry 的名称说明它是记忆条目；D/S/C 的研究含义由条目所记录的更新、作用条件、行为响应和边界体现，不必全部塞进对象名。它属于 §6 候选 Memory 机制的命名整理，不是直接给旧复杂结构换名。

**仍需斟酌：**

- `mappings → edits`：较直观，但现有映射也能指向 Parent 已满足、没有改动的文字。若采用 edits，必须明确它是否表示落实记录，避免误解成每项都产生了编辑。尚未最终确定。
- 新 Memory 的 `response → knowledge`：可强调这是包含条件和未知范围的学习认识，而非原始环境反馈；但仍是候选。不能因为叫 knowledge 就把可修订认识当作确定事实。
- `basis / evidence / refs` 暂不统一改名：先区分对象关联和证据用途，不为命名整齐合并语义。
- `candidate_text` 已足够明确，保留。拟取消的 retire_limits 等机制不再单独做命名优化。

候选 Memory 命名示意（不是已冻结 Schema，也不是实际实验输出）：

```json
{
  "entries": [
    {
      "revises": [],
      "updates": ["更新引用"],
      "knowledge": "什么更新在什么条件下产生了什么行为，以及仍然存在的限制和未知。",
      "evidence": ["实际证据引用"]
    }
  ],
  "unresolved": []
}
```

**不采用的提议：** 用户否定 response_questions、blocking_issues、update_mappings、UpdateResponse、transformations，并取消以 proposed_updates／effective_updates／skill_diff／update_responses／accumulated update_responses 为各模块建立一套新命名的方案。这不表示旧名称必须不变，而是继续寻找更易懂的名称。后续提出的 Response 也不推荐：它更像一次反馈、容易与 API response 混淆，不能明确表达持久记忆。

命名迁移应与接口简化协调，核对 Prompt、Schema、函数／变量、引用和下游消费，避免同时维护多套互相冲突的术语。当前只记录命名决定和候选，没有修改实现或历史档案。

## 3. 问题分类与 Diagnosis

### 3.1 当前输入与拟议统一

分类实际模型输入为：

```text
parent（mode、text）
capabilities
base_protocol
command_sets
experiences[]
  task_ref、task_request、initial_observation、initial_commands
  steps[]：step、action、action_in_admissible_commands、observation、
           reward、done、won、commands
  outcome：status、native_success
```

分类不接收 Memory、Candidate 或 Plan。task_request 从初始观察提取，原观察保留。当前装配验证完整执行、连续步骤与 executed，再省略 phase；程序在模型外记录 T 与实际执行的对应关系。

Diagnosis 当前输入包括 parent、capabilities、base_protocol、runs、command_sets、sources，以及分类结果和版本信息。它读取同批全部 Parent 证据，包括成功和失败执行；拟与分类统一行为字段和装配逻辑，减少第 2 节列出的无关元数据。Diagnosis 仍需分类结果来组织问题，仍需将要求关联到实际依据。

### 3.2 分类输出：保留五字段，减少文字重复

| 字段 | 后续内容分工 |
|---|---|
| group_id | 组编号 |
| members | 明确任务成员 |
| decision_problem | 简洁说明共同决策条件和需要作出的选择 |
| shared_basis | 只写支持分组的执行事实，不复述问题，也不逐任务重讲轨迹 |
| important_differences | 只保留影响策略选择、适用条件或行为解释的差异，允许为空 |

例如“物体名称不同”本身不一定值得列出，而首次放置后原位置是否仍有第二个目标，会影响后续策略条件，应保留。分组文字是模型分析，不是环境原始事实。不为减少文字而截断关键条件，也不要求单任务组编造共性或差异。

本次未决定修改当前每任务恰好一组的规则，也没有授权多组归属设计。

### 3.3 Diagnosis 输出：聚焦原始 Update

当前输出为 decision／reason／plan；Plan 为 intent／requirements／watch／open。

| 部分 | 方向 |
|---|---|
| decision | 保留 revise、no_change、need_evidence 的流程区别 |
| reason | revise 时简短，避免重复 intent 和要求；没有 Plan 时说明决定依据 |
| intent | 共同目标与重要能力保留边界，不重复每项策略 |
| requirements | 核心：明确方向、触发条件、范围、强度、依赖和保留要求 |
| basis | 保留真实依据，减少重复列举和程序可推导的关系 |
| watch | 强调新增观察重点，不机械将要求改写为疑问句 |
| open | 核查独立用途，与 need_evidence、Fusion 阻碍及 Editor issues 的边界 |

教学例子中 reason“改善重复搜索”、intent“减少重复搜索”、Watch“是否减少重复搜索”可能重复；但检查“停止时是否仍有合理新候选”增加了过早停止的反例观察，不应一概删除。

尚未决定删掉任何 Diagnosis 字段。需统计实际重复和追踪下游消费；不能因 open 常为空就认定无用，也不能因收益未证实就制造构造阻碍。Watch 和 open 的调整须与 Fusion 迁移及学习覆盖规则一起设计。

## 4. Fusion／Compiler

### 4.1 输入：只取直接依据及必要上下文

```text
Parent Skill
Diagnosis Plan
Memory
Diagnosis 引用的真实 Parent 证据及必要上下文
共同能力说明、基础协议及必要分类背景
```

Fusion 比较当前更新与历史响应，不重新诊断整批任务。根据 basis 提取引用事件的实际动作、动作前观察、完整合法菜单和动作后反馈，保持多事件顺序；非事件引用按自身含义解析，不把组引用自动解释为全组轨迹展开。

不只给事件 ID，也不强制固定前后一步窗口。理解重复行为或状态变化所需的连续上下文范围尚待确定。**不另建有效行为、反例和跨要求关联的第二套证据筛选，不新增 Agent 或模型调用。**

接受 Diagnosis 未引用的重要证据可能遗漏。确定性提取不保证语义充分，Fusion 应知道展示范围，不把未展示当作不存在。历史适用性不明时允许 Keep 或有界探索，不自动阻断，也不强制历史驱动变换。只有实际反复出现明确遗漏并影响判断时，再评估补充。

### 4.2 输出：保留增量，精简外围维护

当前顶层 decision／reason／changes／watch_changes／open 的核心合理，不改为重新生成完整 Plan。Compiler 继续将增量应用到原 Plan，未改要求原样继承。

| 意图 | 拟议表示 |
|---|---|
| Keep | 不为该要求输出 change |
| 修改、合并或拆分 | replace |
| 本次撤下要求 | withdraw；hold 合并到这里 |

用户已认可合并 hold／withdraw。withdraw 不表示永久否定策略，不自动删除 Parent Skill 的相关规则，也不应因局部撤下阻断其余合法要求。实施时核对旧 hold 的下游行为并完成迁移，不继续维护两个仅理由不同的操作。

每项 change 保留 from／to／basis／reason／disposition：证据引用不等于适用性解释，reason 应说清历史条件与当前 Update 的关系，或如实说明调整来自当前证据。顶层 reason 只解释整体决定，不逐条重述。Keep 不代表不修改 Skill，而是保留 Diagnosis 的原始更新。

### 4.3 Watch 与阻断边界

- 确定的一对一对象引用迁移可交给程序；观察问题含义变化由模型显式修改。
- 不能仅因一对一替换就认定观察问题仍然适用。合并、拆分、撤回等无法机械确定的情况继续显式处理。
- 与 Diagnosis 的 Watch 精简共同核对，不能丢失仍重要的观察问题。
- 暂保留 ready／needs_revision 与 open；只对真实构造障碍阻断。效果未知不自动成为 open。
- 不增加固定 D/S/C 标签、自证表或历史贡献评分。

Watch 自动迁移的具体契约尚未冻结；本节补入此前对话已讨论但旧追加文档遗漏的 Fusion 输出方向。

## 5. Editor

### 5.1 输入：以有效 Plan 为唯一编辑决定依据

```text
Parent Skill 全文
有效 Plan：intent、requirements、watch、open
capabilities
base_protocol：system_prompt、initial_template、history_template
```

capabilities 与 base_protocol 直接与同轮 Diagnosis 共用，不另造 Editor 摘要。Editor 不默认读取整批 Parent 轨迹、command_sets、完整 sources、grouping 或历史 Memory，也不新增相关材料提取机制。

影响落实的方向、条件、强度、依赖及例外应直接写在有效要求里。不能只写“按 G1 改进”或“保留 P2 的有效行为”，让 Editor 从背景重新决策。basis 可供程序追溯，但不能要求模型凭未提供的来源 ID 恢复事实。Watch 不是新的行动义务，未确定分支也不能当作已授权策略。

这是输入范围改变，不是已验证的自足性结论；完整轨迹及历史档案不因此删除，后续学习继续读取所需事实。

### 5.2 输出：文本与落实定位是核心

| 部分 | 方向 |
|---|---|
| candidate_text | 保留完整 Skill，实际 diff 由程序计算；不改成模糊补丁 |
| mappings | 保留要求到精确原文的定位，允许多对多；不增加语义自证 |
| decision | 保留 candidate、no_change、needs_revision |
| reason | 简短，不重复映射和 issues |
| issues | 只报告具体落实障碍，不泛化为风险清单 |
| watch | 核查新增价值后决定减少或取消；不能先认定必须删除 |

映射与 diff 不重复：前者定位要求，后者记录文本变化；Parent 已满足的要求可能没有新 diff。映射合法不能证明语义等价，全文组织自由也不能变成独立策略规划。

既有 Watch 由程序继承。Editor 若主要重复上游问题，可考虑取消新增 Watch；若确有重要独立信息，可保持少量可空输出。选择任何方向均需同步学习覆盖规则。

no_change 可用于要求已被 Parent 满足，不是因效果未知就放弃更新；needs_revision 针对具体无法忠实落实的问题。精简输入后不能因没有完整背景本身就阻断，也不能允许模型补造策略。

## 6. Replay／Memory

### 6.1 输入：完整配对事实与确定性去重

Replay 与 Memory 学习共用一次模型调用，需对照预期更新、实际编辑、真实行为和旧认识。当前主要材料为有效 Plan／Watch、Parent／Candidate Skill、diff、Editor 映射、全批配对轨迹与菜单、能力／协议／分组、旧 Memory 和来源上下文。

已认可方向：

- 保留当前批次完整配对轨迹、步骤顺序、合法动作、反馈和结果。不按成败或 Watch 选择片段。
- 不自动找关键步骤，不新增复杂历史相关性检索，不只挑几条历史认识或反例。
- 复用 P1，仅处理实际 messages 中仍未消除的确定性重复。
- 同一份正文出现多次时共享一份，不选择性删除事实，不把不同执行身份混为一谈。
- 运行元数据的消费整理与全流程 SHA256 等清理按第 2 节处理。

去重示意包括根部与上下文重复的 diff／grouping，以及多条 Effect 共同关联的同轮更新正文。这些是待核对的重复模式，不是已重新测得的冗余统计。共享本轮更新不等于合并各条 Effect 的不同依据。

不能把 Editor 的小输入或 Fusion 的直接引用范围搬到学习端。Parent 的机会不能当作 Candidate 的机会，未触发、未执行、未验证与实际无效不能合并。Gate 结果不代替局部响应证据；是否改变 Gate 的模型可见性尚未决定。

去重不能消除真正新增的历史事实，也不保证未来所有轮次都不超限。新 Memory 输出方案不等于允许提前删除旧依据或仅保留认识卡片。

#### 6.1.1 五轮实验发现：Memory 把共享数据误认为没有独立执行

**状态：用户已确认需要解决，纳入下一版优化；本次只记录问题和方向，不修改代码或历史 Memory。**

2026-10-16—17 的 23 五轮实验中，R2—R5 的 Replay／Memory 输出反复将 Parent 与 Candidate 引用相同的 P1 共享步骤内容，解释成两侧没有分别执行。R5 的 `val:0009` 是明确例子：Parent 和 Candidate 分别运行，均完成相同的清洁、放置动作；模型却在 Finding、未回答问题和新 Effect 的 `limits[1]` 中认定，清洁分支没有独立的 Candidate 响应。

原始执行档案表明，两侧各有自己的执行记录、模型请求和返回结果。P1 共享的是完全相同的内容，并没有把两次执行合并为一次。**内容相同、共享存储、分别执行，是不同的概念。** 这里的“分别执行”也不意味着已经获得多次重复试验或证明单条编辑的因果收益。

这个错误会把真实的 Candidate 行为排除出学习依据，使“本次观察中原有行为得到保持”被误写成“没有证据”。错误限制进入有效 Memory 后，还可能被后续轮次继承，影响 Fusion 对历史响应适用性的判断。因此，它不只是解释文字不准确，而是会影响统一 D/S/C 更新作用链。

后续修改应让模型从输入结构上容易区分“某次执行中的事件”和“该事件引用的共享内容”。保留无损去重，但不能让共享内容的地址承担执行事件的含义；Parent 与 Candidate 各自的步骤、顺序、动作机会和结果仍应明确。优先整理现有输入表示，不以不断追加 Prompt 警告解决，也不增加审核 Agent、复杂绑定或恢复 SHA256 机制。具体是否调整 P1 的共享层级，需要检查实际消息后决定，当前不冻结新 Schema。

验证应覆盖“两侧分别执行但全程内容相同”“仅部分步骤相同”“两侧路径不同”三类材料：程序还原仍须保持完整事实；模型不能因共享内容而否认一次真实执行，也不能把一侧的机会或行动归给另一侧。相同行为可以支持本批次中的行为保持观察，不能直接证明更新带来改善。离线还原测试不足以证明模型理解正确，后续还需实际语义验证。

本次证据确认了反复出现的理解错误，但尚不能证明 P1 编码是唯一原因：后续输出也可能受已经写入 Memory 的错误认识影响。历史错误输出保持原样，不改写为成功结果。

依据：[五轮实验报告 §6](ALFWORLD_57_FIVE_ROUND_EXPERIMENT.md)、[R3 执行身份与过宽限制核验](../../../artifacts/methods/v22/23_alfworld57_five_round/analysis/recovery_02_semantic_identity_audit.json)、[R5 配对执行核验](../../../artifacts/methods/v22/23_alfworld57_five_round/analysis/recovery_06_semantic_identity_audit.json)、[R5 原始学习输出](../../../artifacts/methods/v22/23_alfworld57_five_round/recovery_06/rounds/r5/outputs/post_gate_learning.json)。

### 6.2 当前输出的复杂度问题

当前模型输出 findings／open／memory_delta，delta 包含 replace／claim／limits／findings／retire_limits。程序继承旧 basis 和未退役限制，加入本轮发现，生成新 Effect；retire_limits 按旧 Effect ACTIVE limits 下标退出整条限制，supersedes 记录本次替换，attribution 当前是程序固定的联合归因说明。

主要问题：

1. 模型同时承担行为分析、认识修订和多层存储操作。
2. Finding 与 claim、Open 与 limits 可能只是重复改写。
3. 一条自然语言限制含多个条件时，部分修订需要退役整句再补残余，精确下标不等于语义精确。
4. 自动继承可能累积陈旧、重复或矛盾的边界。
5. 上游重复 Watch 会继续放大学习端的重复回应。

需保留的是条件化响应、实际编辑、行为机会、反例、未知和联合归因边界，不是当前维护结构。具体重复比例和新方案收益尚未统计。

### 6.3 模型输出

候选顶层只有两项：

```json
{
  "effects": [],
  "unresolved": []
}
```

- `effects`：值得新增或修订的条件化作用认识。
- `unresolved`：本轮仍无法回答、且没有在相关认识中已经表达的重要观察问题。
- 不强制先生成独立 Findings，再通过 Finding ID 中转为 delta。
- `effects: []` 合法，不要求每轮强行积累认识。

每条模型生成的 Effect 提案保留四个字段：

```json
{
  "revises": [],
  "updates": ["requirement:u1"],
  "response": "实际编辑在什么条件下产生什么响应，以及仍然重要的反例、未知和归因边界。",
  "evidence": ["diff", "C1:4", "C1:5"]
}
```

此处以及以下案例均为教学示例，引用不是新增的真实实验事实。

| 字段 | 职责 |
|---|---|
| revises | 指定修订哪些已有 Effect；空数组表示新增，不让程序猜测语义合并 |
| updates | 关联本轮有效更新要求，允许多项联合；不能仅凭该关联认定实际落实或有效 |
| response | 一段完整条件化响应认识，包含必要适用条件、反例、未知和联合归因边界 |
| evidence | 直接引用合法输入证据，不通过本轮 Finding ID 中转；认识必须有相应实际编辑或执行依据 |

完整 response 示例：

> 本轮将继续搜索与避免重复操作共同写入 Skill。在存在未尝试候选的已观察情境中，Candidate 转向了新位置，减少了原有重复路径。尚未观察到候选全部耗尽的情况，因此不能据此要求无限继续搜索；也不能区分两项编辑各自的独立贡献。

它可同时表达 D 的实际策略响应、S 的证据覆盖条件和 C 的联合影响，不需要分成 D/S/C 三个字段，也不要求每条认识强行覆盖三个方面。

### 6.4 修订方式

模型填写 `revises: [旧EffectID]`，并直接给出修订后的完整 response。不再输出 replace 加逐下标 retire_limits，不再要求按限制数组操作。

修订应保留仍有依据的旧认识，结合新证据改变得到支持的范围。例如：

> 增强搜索持续性在仍有合理新候选时，曾伴随探索范围扩大；本轮在重复动作且观察没有变化的条件下，又观察到无效循环延长。当前证据支持区分这两类条件，不能将持续搜索无条件加强。候选耗尽后的处理仍未验证。

旧条件从“未测试”转为“已观察到某种响应”，直接在新认识中表达，不要求退役原句再写残余句。修订不是新证据可以任意覆盖旧反例；输入仍须提供被修订认识及必要历史依据。

### 6.5 程序保存方式

程序负责生成 ID、记录上下文、解析和保存证据、保存旧版本及修订关系。候选持久化结构的核心为：

```text
Effect
├── id
├── revises
├── updates
├── response
├── evidence
└── context_id
```

实际 Skill、diff、真实运行身份和历史证据可由共享上下文档案关联，避免每条 Effect 重复展开。具体存储布局尚未设计和验证，必须保证独立恢复与来源完整性。

当前有效 Memory 使用修订后的版本；旧版本留在档案，通过 revises 可追溯。旧有效限制不再由程序机械追加到新文字中。模型不再填写或操作 `limit_contexts / retired_limits / supersedes / attribution`；联合归因边界需要时写入 response，程序继续保存实际 Candidate 更新上下文。

### 6.6 未解决问题和 Watch

```json
{
  "about": ["watch:w2"],
  "reason": "Candidate 未遇到相应条件，本轮无法判断该条件下的更新响应。"
}
```

- unresolved 不生成 Effect，也不自动修改旧认识。
- 已在 response 中表达的重要未知不重复生成。
- 不要求为每个 Watch 单独生成一个报告对象；一个认识可以回答多个观察问题。
- 讨论中的轻量方案允许 evidence 引用 Watch 以表达关联，但 **Watch 是观察问题，不是行为事实证据**。是否采用这种关联方式，以及覆盖检查如何区分问题与事实，实施前需要明确；不能只凭 Watch 引用接受一条响应认识。
- 现有 Watch 覆盖验证必须同步核对，不能换了顶层输出却保留强制 Findings/Open 逐项回应的旧要求。

### 6.7 对 Fusion 与 D/S/C 的影响

Fusion 继续比较历史实际编辑、条件化响应和当前 Update 的可比性，允许 Keep、D 替代、S 扩大／收窄、C 协调及有界探索。不要求历史必然引起非恒等变换。

Fusion 读取有效 response、updates 及可追溯上下文，判断旧认识为何适用或不适用。取消的是繁琐的维护操作，不是“实际更新 → 条件化响应 → 可修订认识 → 后续预条件化”的关系。

| 当前机制 | 候选机制 |
|---|---|
| Findings 再通过 delta 写认识 | 直接输出带依据的响应认识 |
| claim 与 limits 分开维护 | 完整 response 包含作用和边界 |
| replace 加限制下标退役 | revises 加完整认识修订 |
| Open 与 limits 可能重复 | 相关未知写入认识，其余重要未解问题进入 unresolved |
| 模型维护多层引用 | 模型关联更新、直接证据和旧认识 |
| 程序自动追加未退役限制 | 程序保留旧版本，当前使用新完整认识 |

### 6.8 风险与实施前验证

主要风险是重写完整认识时遗漏旧边界。不能声称简化结构就解决语义错误；旧退役机制同样未能证明语义正确。应提供必要历史依据、保存旧版本，并检验新认识是否错误扩大范围、遗漏反例或机械保守，而不是再引入原子限制状态机。

后续设计和验证至少应明确：

1. updates 的合法范围，以及仅修订历史认识但无适用当前 Requirement 时如何表示，不能强行关联无关更新。
2. evidence 的当前／历史来源范围、跨轮身份解析和事实与 Watch 关联的区别。
3. revises 的合法目标、同轮重复修订／合并规则及有效 Memory 切换；程序不猜测语义对应。
4. 没有形成 Effect 的重要局部响应能否充分记录，避免取消 Findings 后只保留成功或可泛化结论。
5. 旧 Effect 到新消费视图的兼容方案；不得改写旧输出使其看似符合新契约。
6. 部分证据修订、重要反例、未触发条件、联合修改及尺度双向调整的通用验证。
7. 实测输出长度、输入消费、成本和模型可理解性；目前未证明收益，也未授权新调用。

本方案是候选设计，不是已冻结或已验证的契约。它涉及 Memory 输出和下游消费变更，不只是格式压缩；不得把旧输出改写成新版本成功结果。


## 7. 后续工作组织与验证

### 7.1 依赖关系

本文不是立即实施的任务清单。后续逐项修改时，建议按依赖组织：先明确共同输入和全流程工程清理范围；协调 Diagnosis Watch、Fusion 迁移和学习覆盖；落实已认可的模块输入方向；单独细化 Memory 候选输出及下游消费；最后核对整条 Update → 编辑 → 响应链。

不要求一次改完全部模块。字段删除、Memory 新 Schema 和上下文范围等未定事项，不因文档重排而自动变成已认可的实现要求。

### 7.2 验证重点

| 范围 | 需要验证 |
|---|---|
| 共同轨迹 | 动作、观察、菜单顺序与重复项、结果保真，执行侧不混淆 |
| 分类／Diagnosis | 输出分工清楚，更新条件自足，不为简短丢失有效行为和依据 |
| Fusion | 直接依据可理解；保持 D 替代、S 双向调整、C 协调、合理 Keep 与有界探索 |
| Editor | 精简输入后仍忠实落实，不强化义务、删除例外或自行重规划 |
| Memory | 完整修订不丢旧反例和未验证条件；联合响应可学习，不强求独立因果 |
| 程序衔接 | 移除全部 SHA256 等机制后，新流程不再暗中依赖旧字段或换一种哈希实现同类机制 |
| 历史材料 | 旧档案不覆盖，不把失败改写为通过；新旧契约区别清楚 |
| 成本 | 比较实际消息字符、Token、输出长度；估计与实测区分 |

输入省略不等于完全无损，引用有效不等于语义正确，离线通过不等于成功率提高。当前没有新增测试结果或模型表现可报告。

## 8. 源码与历史证据索引

本次讨论依据已核对的 v6 修订目录及 compact 实现；未来实施前应确认届时实际入口和继承路径。

- [分类装配与输出契约](../../../experiments/methods/v22/22_reference_consistency/revision/src/skill_evolution/v22/grouped_representation.py)：build_grouping_input、模型私有／程序映射分工、分区规则。
- [Diagnosis 基础输入](../../../src/skill_evolution/v22/compact_cycle.py)：diagnosis_input。
- [轨迹和动作菜单装配](../../../src/skill_evolution/v22/compact_learning.py)：build_learning_payload。
- [当前 Memory 修订与继承](../../../experiments/methods/v22/22_reference_consistency/revision/src/skill_evolution/v22/effective_memory.py)：validate_effective_learning、apply_effective_memory。
- [v4 真实 Diagnosis 输入](../../../artifacts/methods/v22/17_p1_input/official_flash_validation/cases/diagnosis_p1/payload.json)：10 个 Parent 任务的历史验证材料，不代表最新运行配置。
- [早期紧凑接口说明](COMPACT_CYCLE.md)：2026-10-14 已记录完整菜单按内容去重。
- [P1 编码实现](../../../experiments/methods/v22/17_p1_input/revision/src/skill_evolution/v22/p1_input.py)：跨菜单命令字符串共享等确定性编码。

本文由原 `CLASSIFICATION_DIAGNOSIS_INPUT_ALIGNMENT.md` 重新组织并改名。原路径仅保留跳转说明，避免早先对话链接失效；它不再维护第二份设计正文。
