# V23.4 多 Knowledge Memory：统一契约 v1

日期：2026-10-22。状态：**P1–P3 已完成；P4 候选已冻结接入，并完成本轮要求的离线技术验收；P6 真实语义效果尚未验证。** 边界与历史冻结检查例外见 [P2 说明](MULTI_KNOWLEDGE_P2.md)、[P3 说明](MULTI_KNOWLEDGE_P3.md) 和 [P4 候选说明](MULTI_KNOWLEDGE_P4.md)。

本契约覆盖 Replay 提案、Memory 提交与读取、v3 模型投影、Preconditioner 消费和跨版本重载。不改变 D/S/C 输出协议、Actor、Editor、Gate 或单次 Replay 学习方式。不新增 Knowledge ID、Knowledge 操作、模型角色或审核调用。

依赖与现状见 [依赖审计](MULTI_KNOWLEDGE_AUDIT.md)。JSON 形状定义见 [schema](../../../experiments/methods/v23_4/multi_knowledge_contract_001/contract.schema.json)；动态引用与修订规则以本文为准，JSON Schema 不负责语义判断。

## 1. 认识粒度与职责

- 一个 MemoryEntry 维护相对连贯的实际编辑—行为响应主题；不要求一 Update 一 Memory。
- 每条 Knowledge 表达一项条件、范围和证据明确的完整认识；不要求一任务一条，也不机械按句拆分。
- 多项实际编辑无法分离时，允许以联合响应为对象。
- 同主题中的改善、退化、无变化、能力保持和未触发均可保留；数量与类别不固定。
- 同一 Memory 内证据相反的 Knowledge 必须在适用条件/解释边界上相互协调，不能把反例移到另一条后让正面结论保持无条件。
- Knowledge 是可修订认识。资料保存在 sources，不要求每次重述全部案例，但不得遗漏会改变认识的重要对照。

## 2. 新 Replay 输出：唯一模型契约

```json
{
  "entries": [
    {
      "revises": ["M7"],
      "knowledge": [
        {
          "text": "实际温变编辑后，在持有目标且动作可用的条件下，Candidate 直接温变，Parent 出现了额外家电操作；该局部比较不单独解释整项任务差额。",
          "evidence": ["diff", "P4:36", "Q4:6"]
        },
        {
          "text": "另一对执行中，两侧取得目标后都直接冷却，没有观察到局部温变步骤减少；整项效率差异需要结合各侧搜索轨迹解释。",
          "evidence": ["P2:15", "Q2:7"]
        }
      ]
    }
  ]
}
```

上例仅展示形状；引用示意不宣称足以支持所有自然语言细节。具体生成仍需引用建立条件、响应和差异的充分事实。

| 层级 | 精确字段 | 规则 |
|---|---|---|
| Replay | `entries` | 数组，可为空；`[]` 表示没有值得新增或修订的 Memory |
| Proposal Entry | `revises / knowledge` | 不允许顶层 evidence、模型生成 ID 或额外字段 |
| revises | — | 数组，允许空；非空项必须为当前 Active 中的 Memory ID，内部不重复；一个旧 ID 在整份输出中最多被一个 Entry 修订 |
| knowledge | — | **非空数组**；保留模型顺序，不按文本排序或自动合并 |
| Knowledge | `text / evidence` | 精确两字段，无 ID、分类、操作或隐式 Keep |
| text | — | 非空且非纯空白字符串；验证不修剪、改写其内容 |
| evidence | — | 非空字符串数组；每条内部引用不重复；不同 Knowledge 可重复引用同一事实 |

每条 evidence 均必须在当前完整事实或可用历史来源中解析。合法引用沿用 `diff`、当前 run/step/initial/outcome 以及 context-qualified 历史引用；不添加 `M7/K1` 等新引用语法。Memory ID 是 revises 目标，不是行为证据。

**证据类型约束在 MemoryEntry 层聚合检查：**其所有 Knowledge 的引用并集必须包含至少一个实际 Diff 和至少一个执行引用。单条 Knowledge 不强制重复 Diff，也不强制每次同时引用两侧；但陈述双侧比较或状态条件时，必须具有相应证据支持，这是语义要求。合法 ID 不等于支持文字，其他 Knowledge 的引用不能自动为本条背书。

任一结构、未知引用、重复修订目标或版本错误使整个提案失败，不能部分提交、忽略错误 Knowledge 或改成 `entries: []`。

## 3. 完整数组替换与身份

`revises: ["M7"]` 表示以新 Entry 的**整个 Knowledge 数组**替代旧 M7。程序分配新 Memory ID，例如 M12；旧 M7 保留在不可变归档中并退出 Active，而不是原地修改或继续沿用 M7 身份。

若旧 M7 有三项认识，新结果需要改第一项、保留第二/三项、新增第四项，模型必须输出全部四项。程序不会自动补回旧文本、自动认定某条已保留，或依靠数组位置匹配跨轮身份。

- 新证据可以纠正、撤销旧错误解释；省略某项旧认识的语义合理性由 Replay 决定并由实验审查。
- 保留的历史认识必须保留必要历史 Evidence；不得把历史引用改为本轮同名 P/Q。
- 多个旧 Memory 可被一个 Entry 合并修订，但必须保留重要条件区别。
- 同一旧 Memory 不可被两个输出 Entry 同时修订；本阶段不增加一拆多的身份操作。需要细化时，在一个替代 Entry 中组织多个 Knowledge。
- 没有新增/修订的 Memory 原样保持 Active。
- `knowledge: []` 非法，不定义为“删除整个 Memory”；纯删除整项 Memory 不在本阶段契约中。可以在有证据的新认识中纠正或撤销过去解释，不能为凑非空数组生成无信息占位文本。
- `entries: []` 不改变 Active IDs。若调用方仍显式提交这一合法结果，可沿用现有空结果归档行为，记录该轮上下文但不分配新 Memory ID；并非删除历史。

技术“完整替换”不能验证语义“完整保留”。P5 应验证遗漏不会被程序偷偷补齐；P6 才审查重要历史认识是否被合理保留、修正或遗漏。

## 4. 各层数据形状

| 层级 | 新格式字段 | Evidence 形式 |
|---|---|---|
| 原始模型提案 | `revises, knowledge[{text,evidence}]` | 本轮引用保持局部名称；历史引用全限定 |
| 归档 Entry | `id, context_id, revises, knowledge[{text,evidence}]` | 每条 Knowledge 独立限定引用：本轮加提交 context 前缀，历史引用保持不变 |
| 新格式 Active/完整输入 Entry | `id, knowledge[{text,evidence}]` | 全部历史引用全限定；不把 context_id/revises 加进模型 Entry |
| 完整 Memory | `entries, sources` | sources 保持现有完整实际编辑/执行格式 |
| v3 模型 Memory | 既有 format/policy/entries/sources/command_pool，Replay 另有 pairs/unpaired_runs | entries 保留多 Knowledge 及各自证据；sources 按既有算法投影 |

原始 `response / parsed / replay result` 不改写。归档中限定引用后的 Entry 是确定性派生对象，必须能由原始提案、上下文和版本精确重建。不得把限定后的结果写回原始响应。

提交容器继续保存 `context_id/context/result/before_active_ids/after_active_ids/entries`；Active 索引继续是 `active_ids/commits`。新提交仅增加下面定义的程序版本字段，Knowledge 不增加元数据。

## 5. 显式版本边界

统一逻辑版本标识：

- 旧：`memory_contract = "entries_sources"`。
- 新：`memory_contract = "entries_sources_multi_knowledge_v1"`。

这是程序元数据，不是 LLM 输出字段，也不增加 User 顶层字段。

| 位置 | 版本规则 |
|---|---|
| 新 Replay `run.json` | 明确记录新 memory_contract；新主 Prompt 使用独立 `prompt_version = "v23_4_replay_multi_knowledge_v1"`，选择已登记的模板 |
| 新 Preconditioner `run.json` | 使用现有 memory_contract 字段记录新值；D/S/C `contract_version = v23_4_transformations_v2` 不变 |
| 新 Memory commit 顶层 | 明确记录新 memory_contract，决定该提交的 result/context Memory/归档 Entry 读取规则 |
| 已有归档 | 缺少新字段只按已知旧版本读取；不能因 knowledge 是 list 就猜测新格式。已有旧 PC 的 entries_sources 记录照旧 |
| 未知版本或版本/形状不符 | 明确失败，不尝试不同校验器直到通过 |

`memory_evidence_view_v3` 继续标识压缩机制；现有 Replay `input_view` 继续标识 Pair 排列与历史 Pair 机制。它们均不能代替 memory_contract 判断 Entry 形状。归档复用键同时核验 Memory 契约、Prompt、视图、输入、调用配置和来源；空 Memory 也必须区分新旧运行版本。

本阶段不全局覆盖默认版本或旧 Prompt。新格式通过显式 opt-in 进入生产 API 路径，默认旧调用行为保持不变。后续实现可组织兼容函数，但不得将版本选择变成新的模型阶段。

## 6. 旧格式兼容读取

定义只读转换 N：先按原格式校验，再将每个旧 Entry 的 `knowledge: string` 与顶层 evidence 原样包装成唯一的 `{text, evidence}`；移除派生视图 Entry 的顶层 evidence。ID、条目顺序、文字字节、引用顺序、sources 内容保持不变。不做语义拆分，不增删证据。

N 的来源契约必须由调用参数或可信归档元数据明确给出，不根据字符串/数组形状试探版本。

- N 对已合法的新格式 Memory 为恒等转换；不得接受单个快照内无版本约束的混合 Entry 形状。
- 旧原始归档、旧模型消息和旧 result 按旧版本核验，不先归一化后伪称与原记录精确相等。
- 新读取路径支持一个目录的提交历史跨旧/新版本：每个 commit 按自身版本核验后，再将需要呈现的 Active Entry 统一投影为新格式。
- 在已有旧目录副本上首次新提交，新 context.payload.memory 必须与 **N(该目录核验后的 Active 快照)** 精确相等。不能拿新数组快照直接与旧字符串快照比较，也不能为通过比较而改写旧 active/archive 文件。
- 多轮新提交后，新路径按统一新形状精确比较快照；保留并发快照变化检测、pending commit 恢复及同 context 精确幂等语义。
- 旧读取路径遇到新 commit 应明确报不支持，不把多个 Knowledge 拼回一条字符串。这是“新读旧”的兼容，不承诺旧算法无损读新。
- 原始上下文里保存的旧 Memory 仍按原版本核验；其新模型视图是派生副本，不原地覆盖。

旧 Replay 的输出不在旧加载器中自动改成新格式；新实验读取旧 Memory 用 N，旧 Replay 重载仍返回其历史原始输出。

## 7. Sources 与 Memory v3

确定性证据汇总 U：按 Active Entry 顺序、Knowledge 顺序、各 evidence 顺序遍历，首次出现保留，去重仅作用于派生解析/窗口锚点，不修改每条 Knowledge 的 evidence。

- Sources 解析使用 U，继续加载被引用的完整执行，并保留其对应实际 Diff 与执行背景。
- 来源 context 与 run 的身份严格验证；当前引用只在新提交时加前缀一次，历史限定引用不重写。
- v3 以 U 产生现有固定 ±2 窗口，numeric/initial/outcome/unlocalized 的行为、完整 action/feedback、菜单池去重规则均保持原语义。
- 同一执行被多个 Knowledge 引用时取所需窗口的并集；不每条重复展开轨迹，不引入动态窗口。
- Input View 的 entries 仍保留逐 Knowledge 绑定，不能因 U 的存在新增顶层 evidence 或把 Knowledge 拼成大段文本。
- 历史 Pair 来源仍从真实归档取，并验证 hashes、任务身份和 source 内容。`history_pair_sources` 的快照比较必须采用与调用方一致的 Memory 契约；历史 archive 内 payload 仍按其提交版本核验。
- 不自动扩充未引用的另一侧轨迹；unpaired_runs 等现有行为不变。双侧比较是否引用充分属于语义审查。

旧单条字符串经 N 后，使用同一算法应得到与旧版**相同 sources/trace/窗口/menu_pool**；允许不同的只有 Entry 表示和明确的新格式说明，不得顺带改变证据压缩策略。

## 8. 下游与 Prompt

Preconditioner 接收新 Memory 的多条 Knowledge，继续引用 Memory ID 及具体事实 ID；不新增 Knowledge ID 引用，Adjustment 四字段决策含义及 to.patch、编译行为不变。

需要贯通的技术位置包括输入校验、模型投影、引用可见性、共享 compile_effective_plan 对 Memory 的验证和归档重载。不能只改 JSON 序列化后忽略旧编译器的 validate_memory。

新 Replay 主 Prompt 后续以候选版的事实/比较/范围约束为基础设计完整数组替换过程，不只换 JSON 示例。Actor execution context、v3 说明和 Pair 说明继续程序拼接。旧基础 Prompt、共享说明不能直接改成新文案导致旧消息无法重建；新格式说明按显式版本选择，并保留可核验旧模板。不能仅信任归档自行声称的任意 Prompt 文本。

Editor 模型仍只接收 Effective Plan；其上游加载须能通过新 Memory 链，Editor 职责和生成 Prompt 不变。Diagnosis、Actor、Gate 的模型接口不变。V23 evolution 默认流程不切换到新实验格式。

## 9. 后续验收边界

| 阶段 | 必须验证 |
|---|---|
| P2 | 严格新旧形状、完整替换、唯一修订目标、引用逐项限定、ID 分配、不可变提交、空结果、幂等与中断恢复、并发快照不符拒绝、旧新混合提交历史 |
| P3 | Replay 完整输入与模型视图分离、每条证据进入 sources/window、Preconditioner 输入与编译、Editor 上游链、历史 Pair 来源重建 |
| P4 | 单次调用；新认识、保留、纠正/撤销均输出完整数组；无额外角色/字段；不同 Knowledge 仍相互约束结论范围 |
| P5 | 新契约 opt-in 正反例、N 不变性/幂等性、旧消息精确重建、未知版本/篡改拒绝、旧路径不读新、预算与错误不自动降级、原档案字节不变 |
| P6 | 历史 heat plate 13 成功/50 失败、cool tomato 零局部收益、apple 改善、范围外对照、未知/不存在、对象身份、证据充分、有效旧认识遗漏及条目/文本/token/窗口膨胀 |

P6 复用冻结的原始 Memory，经只读 N 得到新表示；知识文本与原始证据不变，但 **User JSON 不会与旧实验逐字相同**。这是研究表示变更必须报告的差异，不能延用“User 消息完全一致”的旧实验结论。输入事实、模型参数、调用/重试策略仍须冻结；新 Prompt 和新表示一起变化，少量案例不能分离各自贡献。

目前完成 P1–P4 候选及离线技术检查；P3 结构模板与 P4 学习模板独立版本化，旧默认不变。语义改善不能由技术测试提前宣称通过，须由 P6 独立验证。
