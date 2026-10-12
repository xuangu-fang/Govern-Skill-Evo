# 记忆契约、更新与示例

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v20 第 1 步：最小 Memory 契约与独立边界](#v20-memory-contract)
- [v20 第 2 步：问题 Memory 保存与增量更新](#v20-memory-update)
- [v20 最小 Memory：构造示例与验收映射](#v20-memory-examples)

<a id="v20-memory-contract"></a>

## v20 第 1 步：最小 Memory 契约与独立边界

日期：2026-10-01。本文记录第 1 步设计契约；第 2 步的独立存储与增量合并已实现，见[第 2 步说明](MEMORY.md#v20-memory-update)。v20 尚未接入 Issue Fusion、真实模型或实验入口。配套见[构造示例与验收映射](MEMORY.md#v20-memory-examples)。

### 1. 三个目标与复杂度边界

v20 保留持续 Memory 的三个核心目标：

1. 保存被整包 RETAIN 的 Candidate 中仍有依据的局部修改方向，使其能在后续重新利用。
2. 已随 Candidate ACCEPT 的修改仍可依据新证据修订，不把接受视为永久正确。
3. 保存失败尝试及其具体限制，避免同一问题反复触发相同且已知有问题的方案。

设计原则是机制简单、长期可运行，同时不牺牲以上目标。核心变化只有两项：按问题维护可更新的尝试记录；取消逐历史 edit 的全量 Memory Review，将历史与当前发现的关联交给已有 Issue Fusion。

首版不增加效果评分、四类主张矩阵、问题生命周期状态机、自动淘汰、向量数据库、独立关联 Agent、压缩 Agent 或信息损失检查 Agent。不设置每轮“判断预算 → 压缩 → 检查损失”的方法流程。正常请求失败仍须如实停止，不能通过截断反证或伪造 NO_EDIT 继续。

### 2. 与 v19 的独立边界

| 部分 | v20 边界 |
|---|---|
| v19 源码、Prompt、测试、冻结配置、既有产物 | 保持原样；不改变 v19 默认入口或恢复行为 |
| Current Diagnosis、Evolution 配对执行、Attribution、Monitor/Gate、Compiler/Editor 的稳定能力 | 可通过显式适配只读复用；记录依赖版本，不通过修改旧模块或全局 monkeypatch 改变行为 |
| 问题/尝试身份、Memory 保存与更新、消费视图 | v20 独立实现和协议 |
| Issue Fusion 输入、来源引用与校验；局部 Evidence Review 的历史输入组装 | v20 独立适配；不能伪造 v19 HistoricalReviews 满足旧接口 |
| 多轮调度、检查点、配置与命令入口 | v20 独立；不直接 resume v19 运行 |
| v19 四轮实验 | 可只读用于分析或离线转换；派生产物另存并注明来源，不视为 v20 真实闭环成绩 |

后续文件使用 `src/skill_evolution/*_v20.py`、`tests/skill_evolution/test_*_v20.py`、`scripts/run_v20_*.py` 和 `docs/V20_*.md`。配置和 manifest 使用独立 v20 名称，运行目录使用 `experiments/v20/pilot/`、`experiments/v20/formal/`。这些是命名约定，本步不创建运行器、空实现或实验数据。

v20 自己拥有的协议使用 `*_v20.1`；复用的旧版叶子产物保留真实原版本，由 v20 外层记录依赖，不改字段冒充新版。后续新实验默认使用空 v20 Memory 和明确的初始 Skill；从 v19 导入历史属于另行记录的转换，不能静默复用其 memory head。

### 3. 两种保存内容

**完整档案**保存逐轮 edits、配对轨迹、Attribution、生成来源、Gate 完成回执和历次记忆更新。追加保存，可追溯和恢复；不会整体放入模型上下文。

**问题记忆**保存每个问题及不同修改方案的当前认识。它是下一轮使用的简明状态，可以依据新证据更新；不是新的 policy，也不是修改授权。历次状态留在档案中，不递归嵌入下一版记忆。

每次使用来源引用时从档案解析。模型看到摘要时只能依据摘要判断，不能声称已经检查未加载的轨迹原文。

### 4. 最小记录结构

以下字段是第 2 步运行时实现的规范；具体 Python 接口和持久化细节见 [第 2 步说明](MEMORY.md#v20-memory-update)。

#### 问题记忆

| 字段 | 内容与约束 |
|---|---|
| `schema_version` | `issue_memory_v20.1` |
| `run_id` | 所属独立运行 |
| `issues` | 问题记录数组；空历史为 `[]` |

每个问题仅包含：

| 字段 | 内容与约束 |
|---|---|
| `issue_id` | 运行内稳定、由程序分配的身份 |
| `problem` | 问题及适用情形的简短描述；可保留尚未找到修改方案的问题 |
| `source_refs` | 问题来源引用，指向可解析的 Findings / 局部审阅等学习侧记录 |
| `attempts` | 实质不同的修改方案；尚未尝试时为 `[]` |

每个尝试仅包含：

| 字段 | 内容与约束 |
|---|---|
| `attempt_id` | 运行内稳定、属于该问题的方案身份 |
| `approach` | 方案改变什么行为、适用于什么条件；原始精确文本由 edit 引用恢复 |
| `assessment` | 一段简短自然语言，写已有观察、具体限制及必要的不确定性；不引入效果枚举或置信分 |
| `edit_refs` | 实际形成 Candidate 的原始 edit 引用，非空；相同方案历轮产生的不同 edits 可归于同一尝试 |
| `source_refs` | 支持 assessment 的学习侧记录引用；证据不足也须能追溯到本轮审阅/归因范围 |

`source_refs` 是带来源类型的归档引用，能解析到来源轮次、记录及原始事件/标签；不能以任意字符串或自由文本摘要替代。v20 不新增一套证据 ID 体系，具体来源解析由后续闭环适配既有 artifact 引用。

本轮 Gate 决策、Parent/Candidate/retained Skill 引用属于提交档案，不复制成每个尝试的质量标签。当前规则绑定在读取时按所引用 edits 与当前 Parent 推导；沿用 EXACT / PARTIAL / ABSENT / UNRESOLVED 的含义，不持久化容易过期的“已部署=true”。DELETE 按被删除目标的当前存在性解释。

#### 身份规则

- 相同问题沿用 `issue_id`，不因新轮次、新证据、描述修改或输入摘要变化而换 ID。现有 v19 Fusion 的轮次输入绑定 issue ID 不能直接充当跨轮问题身份。
- 同一行为方案及适用范围沿用 `attempt_id`；改写措辞或补充证据不创建新尝试。改变行为路径或实质适用范围时创建不同尝试，旧尝试仍保留。
- 精确 `edit_id` 继续绑定一次实际修改，不能因方案合并而合并原始 edit 身份。
- 新对象由模型使用请求内临时标识，验证后由程序分配正式 ID；恢复同一更新时复用分配结果。已有对象必须引用已有 ID。
- 语义匹配由正常的问题分析和更新完成；无把握时保留不同记录，不凭关键词或相似文本自动强制合并。
- 一个 edit 可涉及多个问题；多个 edits 也可共同支持一个尝试。共同引用保持原身份，不能复制为多份独立证据；无法拆分的联合关联在 assessment 中说明。

### 5. 增量更新规则

输入为本轮相关问题的旧状态、本轮 Findings 与局部审阅、实际 edits、Evolution 配对归因及整包 Gate 完成回执。使用当前的 [v19 Pair Attribution 事实语义](../v19/ATTRIBUTION.md#v19-pair-attribution)，不恢复早期 v19 的 BENEFICIAL/HARMFUL 等效果枚举。

默认一次 Memory 更新调用处理本轮涉及的问题，输出新建或更新的问题记录；其余问题由程序原样保留。该步骤是记忆写入，不额外调用总结器或压缩器。涉及范围由 Fusion、实际 edit 来源和新增归因共同确定，包含 NO_EDIT 的相关议题；新观察不能仅因 Fusion 未选中旧问题就被忽略。

| 新情况 | 更新动作 |
|---|---|
| 同一问题、同一方案，没有新增结论 | 保留正文；新原始证据归档，引用按集合关联，不追加逐轮叙述 |
| 同一方案出现新支持、反证或限制 | 更新原 assessment，保留仍成立的观察和限制 |
| 行为或适用范围发生实质变化 | 在原问题下新增尝试，原尝试保留 |
| 新问题 | 创建问题记录；没有实际 edit 时不伪造尝试 |
| 没有新证据涉及某问题 | 原记录不变；不能解释为问题已解决 |
| RETAIN | 与 ACCEPT 一样保存完整本轮训练证据和尝试，保留 Skill 仍为 Parent |

更新以“受影响的问题记录替换”表达，未提交的对象不变；已有问题和尝试不能因为更新响应漏列而删除。首版不提供删除历史尝试的操作。新增来源引用只在归档侧累计，消费侧使用问题/尝试短引用，不展开所有引用 ID。

旧限制只有在新证据明确改变该判断时才修正，并在 assessment 中说明依据；一次新支持或一次 ACCEPT 不足以擦掉旧反证。联合效果、不同范围的相反观察和证据不足可以直接用自然语言表达，不要求额外字段。程序校验身份、结构和引用，不宣称能自动证明语义合并正确，也不另设逐轮信息损失检查。

### 6. 下一轮如何消费

1. **Current Diagnosis**继续独立分析当前 Parent 的训练经验，产出 Findings，不因历史方案预先限定当前发现。
2. **v20 Issue Fusion**一次读取当前 Findings、简明问题记忆及当前 Parent 规则。日常视图只展开 `problem`、`approach`、`assessment` 和请求内短引用；规则绑定为派生信息，完整来源列表和旧 edit 全文留在档案。
3. **局部 Evidence Review**对拟修改的问题读取关联尝试与原始证据，包括相关反证和联合关系；结合当前 Parent 决定是否形成可执行 gap。历史摘要不能直接成为 VERIFIED 或精确编辑坐标。
4. **Compiler / Editor**仍只执行本轮获得授权的修改，形成完整 Candidate。

Fusion 必须允许纯历史议题：即使当前没有相关失败，未部署但仍有依据的方向也可进入局部核验。历史问题不必每轮逐项生成新的审阅结论；没有被选中只表示本轮未处理，不改变其记忆。

首次版本让 Fusion 一次读取全部简明问题记忆，不增加检索 Agent、top-k 淘汰或休眠队列。局部核验只展开相关问题的详细证据；原有整轮/跨轮闭包不能默认整包进入每个局部请求，必要依赖和反证仍必须可解析。

重试必须回应原方案的具体限制，说明行为、范围或所依据证据有什么实质变化；新证据能解除原顾虑时允许方案不变。仅再次遇到同类失败不足以证明旧方案有效或无效。已接受方案同样允许重新修改，不能以整包 ACCEPT 阻止审阅。

### 7. 流程、信息权限与提交

```text
Parent Evolution → 当前 Diagnosis
→ v20 Issue Fusion（Findings + 问题记忆）
→ 局部 Evidence Review → Compiler / Editor
→ Candidate Evolution → Attribution → Monitor / Gate
→ 增量更新 Memory → 原子提交 retained Skill 与 Memory → 下一轮
```

归因阶段不读取 Monitor。Memory 学习侧只读取 Evolution 可见政策、工具、对话、原有 Level-0 success/compliant 标签及其来源；不能读取隐藏任务机制、私有数据库、evaluator 原因或 Monitor 轨迹/分数。Gate 只提供完成状态和整包 ACCEPT / RETAIN，供记录部署历史。

完整档案保留全部本轮 edits 和配对归因。每个实际 edit 必须能关联到问题尝试；没有可信局部关联时写明证据不足，不能跳过该 edit 或制造效果判断。未归因观察继续归档，不能强行分配到某个 edit。

一个逻辑提交同时发布问题记忆与 retained Skill，绑定运行、轮次、前一 memory head、精确两侧 Skill、Gate 回执和源产物。Memory 更新失败时保留阶段产物，不发布新 head、不开始下一轮；重试同一已完成提交不得重复添加问题或尝试。

NO_UPDATE / UNABLE 保存当轮分析产物并停止，不伪造 Candidate、归因、Gate 或完成轮次。已提交 Memory 保持不变；NO_EDIT 只是某议题本轮不修改。存在有效 Candidate 的完成轮次仍可更新相关 NO_EDIT 议题的已有认识。

### 8. 长期运行的含义

节省 token 来自正常更新与消费方式：重复经验更新同一条记录，取消 N 个历史 edit 各读一遍当前 Findings，历史全文只在相关局部核验时展开。引用列表和逐轮审计仍可在存储中增长，不随之全部进入 prompt。

不声称固定大小、无损压缩或无限轮次必定能装入上下文。真正不同的问题和方案增加时，简明状态也可能增加。首版先消除按轮次复制和全量重复审阅；若后续实验显示不同问题规模仍成为瓶颈，再独立评估消费方式，不以“长期可运行”为由提前加入预算治理链路。

### 9. 本步交付与后续顺序

第 1 步只交付本契约、构造示例、文档索引和 Decision Log；第 2 步已增加独立 Memory 存储与增量合并代码及专项测试。示例不是实际实验，也不是已通过测试的运行 fixture。仍没有 v20 模型调用、实验迁移或闭环入口。

| 后续步骤 | 交付范围 |
|---|---|
| 第 2 步 | **已完成**：问题记忆类型、增量更新与独立存储；稳定身份与重复经验验证 |
| 第 3 步 | v20 Fusion 直接消费记忆；支持当前问题、已部署方案纠偏、纯历史方向 |
| 第 4 步 | 局部证据组装、Evidence Review 与修改生成适配 |
| 第 5 步 | 独立多轮闭环、原子提交/恢复、v19 四轮只读离线验证 |
| 第 6 步 | 独立 Pilot、长轮次运行与对照实验 |

三个目标、增长行为及边界的具体预期见[验收映射](MEMORY.md#v20-memory-examples)。成本与效果是后续实验指标，不增加为每轮运行的模型检查步骤。

### 10. 设计依据

- 本次用户明确的三个 Memory 目标，以及独立 v20、机制简单、避免每轮预算/压缩/信息损失检查的约束。
- v19 当前语义：[Pair Attribution](../v19/ATTRIBUTION.md#v19-pair-attribution)、[Issue Fusion](../v19/FUSION_AND_RECONCILIATION.md#v19-issue-fusion)、[共享 Memory 消费边界](../v19/MEMORY.md#v19-memory-consumption)。早期设计文档与当前协议有差异，以此处明确采用的事实语义为准。
- SkillAdam 的[问题/尝试组织方式](https://github.com/ruc-datalab/SkillAdam/blob/b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1/skilladam/core/momentum.py)可借鉴；其 attempts 仍追加，不能作为已解决长期增长的证据。v20 不引入其 `problem_addressed` 布尔判断、resolved 生命周期或动态 edit budget。

<a id="v20-memory-update"></a>

## v20 第 2 步：问题 Memory 保存与增量更新

日期：2026-10-02。状态：已实现独立存储和确定性增量合并；尚未接入 v20 Issue Fusion、真实模型或多轮 campaign。

实现文件：

- `src/skill_evolution/v20/issue_memory_v20.py`
- `tests/skill_evolution/v20/test_issue_memory_v20.py`

### 接口

```python
from src.skill_evolution.v20.issue_memory_v20 import (
    initialize_issue_memory,
    load_issue_memory,
    merge_update,
    commit_issue_memory_update,
)

snapshot = initialize_issue_memory(store_dir=memory_dir, run_id="run-1")

update = {
    "schema_version": "issue_memory_update_v20.1",
    "run_id": "run-1",
    "round_id": "round-01",
    "issues": [{
        "new_issue_key": "settlement-price",
        "problem": "搜索报价不能确定最终结算金额。",
        "source_refs": ["FINDING/1"],
        "attempts": [{
            "new_attempt_key": "disclose-and-confirm",
            "approach": "披露搜索报价，不把它当作最终结算金额。",
            "assessment": "已有配对观察支持披露行为，但最终金额仍不可见。",
            "edit_refs": ["EDIT/1"],
            "source_refs": ["ATTRIBUTION/1"]
        }]
    }]
}

ref = commit_issue_memory_update(
    store_dir=memory_dir,
    update=update,
    expected_head_ref=snapshot.memory_ref,
)
snapshot = load_issue_memory(memory_dir)
```

模型或上游语义分析负责判断两个问题/方案是否相同；本模块不做关键词或 embedding 匹配。新对象使用 `new_issue_key` / `new_attempt_key`，程序根据运行 ID 和 key 生成稳定的 `ISSUE/<sha256>`、`ATTEMPT/<sha256>` 身份。已有对象用正式 ID 更新。

更新是部分提交：只处理本轮涉及的问题，省略的问题和尝试原样保留。来源引用和 edit 引用按首次出现顺序去重合并；同一方案没有新结论时不会追加新的自然语言段落。相同临时 key 重试时，如果问题和方案一致，会复用已有对象并合并新增引用；方案冲突则拒绝。已有尝试可更新 `assessment`，但不会因为更新请求遗漏字段而删除旧字段。

### 存储与恢复

目录为独立的 v20 memory root：

```text
memory/
  genesis.json
  head.json
  revisions/<memory-sha256>/memory.json
```

每次有实际变化写入新的不可变 revision，再原子替换 `head.json`。`load_issue_memory` 会校验版本、运行 ID、完整问题/尝试结构和当前 memory 摘要；`expected_head_ref` 提供比较并提交，过期更新会停止。完全相同的已提交更新可安全重试并返回原引用，不重复增加 revision。

Gate、Parent/Candidate、Monitor 分数和完整轨迹不进入问题 Memory；它们由后续 v20 闭环保存的外围档案引用。ACCEPT/RETAIN 的区别不在本模块内生成，也不会把 Gate 结果复制成尝试效果标签。

本步没有实现语义判断、Evidence Review、Memory 消费视图或压缩流程。完整原始证据仍由后续闭环归档；当前实现只保存学习侧问题状态及其来源引用。

### 验证

专项测试覆盖：

- 空 Memory 初始化、幂等恢复和运行 ID 隔离；
- 新问题/尝试的稳定 ID；
- 同一方案更新 assessment 与来源集合；
- RETAIN/ACCEPT 不改变问题状态模型；
- 新方案在同一问题下保留；
- 省略字段不删除旧问题/尝试；
- 重复临时 key 追加新证据而不复制正文；
- 非法重复、未知 ID、运行冲突和篡改 revision 拒绝；
- 原子提交、CAS 冲突和完全相同提交幂等。

`pytest -q tests/skill_evolution/v20/test_issue_memory_v20.py`：**10 项通过**。

相关 v19 回归：`pytest -q tests/skill_evolution/v19/test_memory_v19.py tests/skill_evolution/v19/test_memory_consumption_v19.py`：**45 项通过**。本步没有模型调用或实验运行。

<a id="v20-memory-examples"></a>

## v20 最小 Memory：构造示例与验收映射

日期：2026-10-01。配套规范：[最小契约与独立边界](MEMORY.md#v20-memory-contract)。

以下全部为人工构造，不是 v19/v20 实验结果，也不是可直接加载的运行 fixture。简写引用须在后续测试中替换为可解析的完整来源。Gate 决策均为独立给定，不能从示例中的 Evolution 标签推导。

### A. RETAIN 后合理的局部方向仍可利用

R1 的 Candidate 有两个修改：`R1/e1` 在条件操作前查询可见状态，`R1/e2` 不看条件固定选择方案甲。Evolution 配对观察：

- `R1/p1`：Parent 未查询状态、遗漏后续动作；Candidate 查询后完成动作，CF → CS。归因把查询行为与 e1 关联，但未隔离其他修改。
- `R1/p2`：Parent 按条件选择乙并完成；Candidate 固定选甲失败，CS → CF。归因保留与 e2 的关联及限制。
- Gate 返回 RETAIN，下一轮 Parent 仍是原 Skill。两个 edits 与全部证据均归档。

其中查询问题的简明记忆示意：

```json
{
  "schema_version": "issue_memory_v20.1",
  "run_id": "constructed-A",
  "issues": [{
    "issue_id": "I1",
    "problem": "工具可提供条件状态时，操作前未查询，可能遗漏应完成的动作。",
    "source_refs": ["R1/F1"],
    "attempts": [{
      "attempt_id": "A1",
      "approach": "在条件操作前查询当前状态，再按结果选择动作。",
      "assessment": "配对观察到查询后完成动作，关联结果由 CF 变为 CS；尚未隔离其他 edit 的作用，只支持已观察的可查询场景。",
      "edit_refs": ["R1/e1"],
      "source_refs": ["R1/attribution1"]
    }]
  }]
}
```

这只是完整记忆中 I1 的片段，固定选甲的问题及 e2 也必须有记录。`R1/attribution1` 解析到 p1 双侧事件、标签及关联限制。Gate 存在轮次档案中，e1 对当前 Parent 的绑定为 ABSENT。

R2 即使没有对应的当前失败，Fusion 也允许以 I1/A1 的历史依据提出议题。Evidence Review 检查原始配对、适用条件与当前 Parent 后，可授权新的 MISSING；新的 ADD 产生 `R2/e1`，不能直接晋升 `R1/e1`。若方案与范围未变，R2 完成后把新 edit 关联到 A1，而非创建相同尝试 A2。

**验收预期：**RETAIN 不抹掉局部依据；纯历史议题可进入核验；重试绑定当前 Parent，并重新经过完整闭环。

### B. ACCEPT 后仍能根据新证据修订

R1 的 Candidate 含一条“某事项信息不全时暂停全部事项”的修改 `R1/e1`，另有其他修改。Gate ACCEPT；问题 I1 下的尝试 A1 保存原观察与适用限制。

R2 当前 Findings 表明：另一事项缺信息时，Agent 连已经授权且可独立完成的事项也暂停。当前绑定确认旧规则仍在 Parent。

Fusion 将新发现关联到 I1，局部审阅检查新证据与原尝试后，可以授权把暂停范围限制在确有依赖的事项。新 REPLACE 为 `R2/e1`；由于适用范围实质变化，在 I1 下保留新尝试 A2。

| 尝试 | approach | assessment 中应保留的内容 |
|---|---|---|
| A1 | 任一事项缺信息就暂停全部事项 | 已观察到阻断独立事项的限制；历史 ACCEPT 不推翻该观察 |
| A2 | 仅暂停确实依赖缺失信息的事项 | 待 R2 配对结果补充观察；不能在生成方案时宣称已解决 |

R2 无论 ACCEPT 或 RETAIN，完整尝试均保存；当前部署情况按提交后的实际 Parent 推导。

**验收预期：**已接受的方案仍可审阅；收窄方案与旧方案不混成同一尝试；产生新 edit 不自动清除旧限制。

### C. 记住失败方案的具体限制，避免机械重复

I1 是“搜索报价与最终结算不一致”。A1 曾尝试“根据搜索报价直接选择用户设定的金额阈值分支”。既有配对证据记录：查询报价后仍出现实际结算超阈值；可见工具没有提供更新前最终结算值。assessment 保留这一限制及观察范围。

再次遇到同类问题时：

| 新提案 | 预期处理 |
|---|---|
| 仅把“根据搜索报价选择”改成“务必根据搜索报价选择” | 同一方案，无新依据解除限制；局部审阅不授权机械重试，不创建措辞不同的重复尝试 |
| 在特定适用范围内改为先取得明确行程确认 | 行为改变，可作为不同尝试审阅；需有证据和可执行依据，不能自动通过 |
| 后续环境新增了能提供最终结算值的可见工具 | 若新证据解除旧限制，允许重新考虑原方向；不能把历史失败变成永久禁令 |

仅有 RETAIN、失败标签或问题复发，均不能代替上面的具体限制证据。没有可支持的替代方案时，保留记忆并返回 NO_EDIT。

**验收预期：**限制可被下一轮看见；无实质变化的重复方案不被重新授权；新证据允许修正旧判断。

### D. 重复经验不会变成逐轮重复正文

以 A 中的 I1/A1 为起点，连续多轮观察到相同范围下的相同查询行为，没有新增结论：

- I1/A1 身份保持不变，`approach` 和 `assessment` 不追加“第 N 轮再次支持”段落。
- 新回放仍完整归档；确有新实际 edit 时加入 A1 的 `edit_refs`，来源引用去重关联。
- Fusion 一次看到 I1/A1 的简明内容，不展开逐轮来源 ID、原始 edit 全文或全部轨迹。
- 后续出现范围外反例时，更新 A1 的限制，而不是只保留最近一次正向观察。

重复证据输入造成的结构增长可在第 2 步用构造测试检查；这是开发验收，不新增每轮压缩检查调用。不同方案和新问题仍可增加记录，本例不证明无限轮次固定 token。

### E. 来源、联合修改与停止边界

- 同一配对只能关联 `[e1, e2]` 的联合影响时，assessment 明确不能拆分；若两个问题都引用它，仍是同一份来源，不得到两份独立支持。
- 某 edit 没有可信关联时，仍关联到来源问题的尝试，写明观察不足；不能生成有益/有害标签，也不能从记忆中漏掉它。
- 来源轮曾 ACCEPT，但规则后来被替换：读取当前绑定，不能沿用旧部署事实授予修改坐标。
- 没有任何当前相关观察：已有 assessment 保持原样，不能写成解决、失败或新增支持。
- 正常更新响应遗漏旧尝试：视为无效更新，不能将遗漏解释为删除；不增加语义损失检查 Agent。
- 已完成轮次恢复：复用问题/尝试 ID 与提交结果，不重复添加记录。更新阶段失败：旧 head 与 retained Skill 保持可用，新轮不开始。
- NO_UPDATE / UNABLE：本轮分析留档，已提交 Memory 不变，不伪造 Candidate/Gate。没有真实 edit 的提案不计作已尝试方案。

### 第 1 步验收映射

| 契约要求 | 构造示例 / 规范位置 | 后续主要验证步骤 |
|---|---|---|
| RETAIN 中局部方向不丢失 | A；契约 §5–6 | 第 2–4 步 |
| ACCEPT 后继续纠偏 | B；契约 §6 | 第 3–4 步 |
| 失败尝试及限制可复用 | C；契约 §5–6 | 第 2–4 步 |
| 同一方案更新，实质不同方案保留 | A/B/D；契约 §4–5 | 第 2 步 |
| 无当前失败也能利用历史 | A；契约 §6 | 第 3 步 |
| 不重复读取全批 Findings | D；契约 §6 | 第 3、5 步 |
| 原始证据、反证、联合来源保留 | A/C/E；契约 §3–7 | 第 2、4 步 |
| 不将摘要或 Gate 当编辑授权 | A/B/E；契约 §6–7 | 第 4 步 |
| Monitor 私有资料不进学习侧 | 契约 §7 | 第 2–5 步 |
| 提交/恢复一致，无伪造完成轮次 | E；契约 §7 | 第 5 步 |
| v20 独立，不修改 v19 | 契约 §2 | 所有后续步骤 |
| 不增加预算/压缩/损失检查链路 | D；契约 §1、5、8 | 第 2–5 步 |

本步完成的是契约与预期行为定义；尚未通过运行时测试证明这些行为，更未证明 token 节省或演化收益。
