# Phase-A Operational Semantic Taxonomy

本文件定义静态 classification target，不是 Agent context，不执行文本删除或改写。原则为 **Environment-first**：本地 canonical τ² + 统一 contract + semantic taxonomy → registry。版本：`phase-a-static-semantic-v1`。

## 1. Unified Phase-A Contract

| Contract | 含义 |
| --- | --- |
| C1 Complete-Upfront User Intent | 用户完整意图在开始时给出；不在本轮构造 conversation。 |
| C2 Stable Intent | 意图保持稳定。 |
| C3 Full Normative Governance | 完整保留允许、禁止、资格、认证、确认、授权、scope、用户控制与规范要求的顺序。 |
| C4 Full Domain/Object Semantics | 完整保留稳定对象含义、字段、标识符、单位与状态词汇。 |
| C5 Full Tool Interface / Payload Semantics | 完整保留 purpose、参数、payload、cardinality、alignment、直接调用条件和 primary effect。 |
| C6 Observable Current State Remains Available | 当前状态仍可通过真实 read tools 读取。 |
| C7 Latent Backend Transition Semantics Are Not Explicitly Documented | 不显式讲解 secondary mutation、未来可行性、资源生命周期、历史结算、跨交易耦合及 backend enforcement。 |
| C8 True Tool Outcomes / Errors Remain Observable | 实际结果和错误保持原样可观察；LATENT 不是屏蔽结果。 |
| C9 Derived Reasoning Is Not Scaffolded | 保留推理输入，不提供答案、重建步骤或 reasoning checklist。 |
| C10 Same Domain-Level Transformation Is Applied to Every Task | 一个 domain 的同一语义规则适用于所有任务，不允许逐任务选择 context。 |
| C11 Outcome-Blind Context Construction | 不使用任务结果、预期弱点、难度或测量结果决定可见性。 |

## 2. Primary Roles

| Role | 定义 | 默认最终可见性 |
| --- | --- | --- |
| N — Normative Governance | WHAT is allowed / forbidden / required，包括 eligibility、allowed reasons/payment methods、认证确认、scope、用户控制、policy-required ordering。API 不执行规则也不改变其规范性。 | VISIBLE |
| D — Domain / Object Semantics | 对象是什么；稳定字段含义、ID 区分、状态词汇、单位、membership、trip/cabin 类型。当前字段值属于保留的观察输入。 | VISIBLE |
| I — Tool Interface Semantics | 理解当前 tool 和正确构造调用必需的 purpose、参数表示、必填性、列表与数量、位置对应、当前直接前置条件。 | VISIBLE |
| E — Immediate Primary Effect | 显式承诺的直接目标效果，例如地址替换、reservation cancellation、item substitution、return/exchange request registration。 | VISIBLE |
| L — Latent Operational Dynamics | 当前 action 基本含义之外的 secondary state、future feasibility、resource lifecycle、历史结算、跨交易耦合或 enforcement 行为。 | LATENT |
| R — Derived Procedural Reasoning | 基于已经可见或已观察到的证据进行计算、绑定、聚合、重建和分支判断；不把未知 backend law 假定为推理输入。 | DERIVED |

每个 unit 只有一个 primary role。原文可能同时包含多个 role，必须先拆分。N/I 重叠时，明确的治理规则优先 N；独立 schema 调用 cardinality 可按 I 记录，同一意义在不同来源的出现不是一个联合句。

## 3. Latent Tags

每个 L unit 至少一个 tag，可多标签；tag 不替代 primary role。

| Tag | 定义 |
| --- | --- |
| L1 SECONDARY_STATE_MUTATION | 除 primary target 外，改变其他 backend state，例如追加 payment history。 |
| L2 FUTURE_OPTION_TRANSITION | 当前 action 改变未来 action set 或破坏之后的 prerequisite；包括状态关闭和顺序不可逆性。 |
| L3 RESOURCE_LIFECYCLE | 资源使用后 consume、disappear、persist、recover 的具体行为。 |
| L4 STATEFUL_HISTORICAL_VALUATION | 交易成本、价格、settlement 依赖历史 state 的规则，区别于对已知值进行算术。 |
| L5 CROSS_TRANSACTION_COUPLING | 一个交易改变另一个交易的资源、状态或可行性。 |
| L6 BACKEND_ENFORCEMENT_SEMANTICS | backend 如何或是否执行约束；不改变同一约束的规范 role。 |

例如 certificate 不可退款是 N，第一次使用删除整个 certificate 是 L3，其他 booking 因删除不能再使用它是 L3/L5。每条分别记录，不合并成“certificate rule”。

## 4. Classification Decision Tree

```text
Q1: Is this knowledge normative: allowed / prohibited / required?
    YES → N → VISIBLE
Q2: Is it stable domain/object meaning?
    YES → D → VISIBLE
Q3: Is it necessary to understand the tool, argument, payload,
    or current direct invocation?
    YES → I → VISIBLE
Q4: Is it the immediate primary effect of the tool?
    YES → E → VISIBLE
Q5: Does it mainly describe secondary state change, future feasibility,
    resource lifecycle, historical settlement, cross-transaction coupling,
    or backend enforcement?
    YES → L → LATENT
Q6: Can the conclusion be derived from already visible information?
    YES → R → DERIVED
Ambiguous → default VISIBLE
```

Q5 与 Q6 的判断对象是不同 atomic assertions：backend 采用哪一个 historical baseline 是 L4；在 baseline 已知时计算合计是 R。不能因为一个答案能从 Codex 读到的函数体算出，就把 Agent 尚未知的规则归为 R。

### Direct precondition 与 future invalidation

“当前 payment history 必须恰好一笔 payment”是 I，即使 canonical 只在函数体或未导出的 Raises 中表达。“items mutation 追加 history，从而让后续 payment modification 失效”是 L1/L2。可见性来源和最终 role 是独立维度：`NO + I + VISIBLE` 是公开接口知识缺口，不是把源码默认视为已公开。本轮只登记缺口，不生成补充文档。

### Primary effect 与 secondary mutation

取消的 primary target 是取消对象；附带财务 ledger 更新单独审计。修改 payment 的退款承诺可视为“替换 funding”基本含义，保守保留 E；具体 history append 和 gift-card 算法仍分别为 L。Return/exchange 注册请求是 E，不能把它误报为完成退货、换货或已经到账。

状态的**词汇含义**是 D，**状态转移规律**可能是 E（直接注册请求）或 L1（items 替换同时写 status）。后续可行性规律再分为 L2。单次调用限制属于 N/I，不能连同未来不可行性说明一并隐藏。

## 5. Conservative Ambiguity Rule

在 N/D/I/E 与 L 之间存在真实、未能消解的歧义时默认 VISIBLE，并记录 `ambiguity` 与理由。`LOW` 表示边界存在可说明的接近性或源间差异，并非仍有未解决的真实二义性；真正无法决定的分类必须保守可见并上报。

不会因 API 没有检查、文本不严谨或实现缺陷而删除 normative requirements。源间矛盾逐项记录，不自动修复 Policy 或 tool description。任何偏离默认 role→visibility 映射的 exception 必须列出；当前 registry 无此类映射 exception。

## 6. Outcome-Blind Rule

仅允许以 domain semantics、Policy、真实 tool interface、implementation 与 taxonomy 为分类依据。不读取任务内容或 trajectory 以选择 classification，不引用 outcome、不以已知 failure family 为理由。JSON 不含 task ID、related_failure_family、expected_failure 或 success_headroom。

报告结尾按审查要求回答关于特定“类型知识”的问题，但不把这些标签写入 registry 或用于构造 unit。

## 7. Semantic-unit Rule

原文先拆成独立断言，再分类；不是给整句、整段分配一个 role。

Retail modify items 至少分别记录：purpose I；same-product N；duplicate representation I；single-call N/I；item substitution E；status change L1；future modification L2；future cancellation L2；settlement L1；gift-card mutation L1/L3；history mutation L1。

字段含义、字段类型和必填性是不同 interface units。枚举 alternatives 和一个 list 的数据表示是单个约束，不按单词拆分。Policy 和 schema 的重复断言保留各自出处，统计为 **source-occurrence semantic units**，不声称是去重后“知识数量”，也不使用数量表示重要性。

实现审计只补充公开文档没有完整表达的调用缺口、动态、边界和实现差异，不 dump 源码、不枚举任意可构造程序路径。R 是由 canonical representation 支持的推理义务，不是虚构的额外 environment law。

## 8. Canonical Runtime Visibility Rule

以本地 text Agent 的实际数据流为准：

```text
Policy → Environment.policy → LLMAgent.system_prompt
Decorated methods → ToolKitBase.get_tools → as_tool(bound method)
→ Tool.openai_schema → llm_utils.generate tools_schema → completion tools
Conversation and ToolMessage.content → next-turn messages
```

| Surface | 实际情况 |
| --- | --- |
| Policy | 环境读取本地 policy.md 并交给 text Agent。 |
| Short + long function description | 默认 `use_short_desc=False`，两者进入 function.description。 |
| Args descriptions | 进入 parameters.properties 的 description。 |
| 类型、enum、required、nested model fields | Pydantic parameters.model_json_schema 进入参数 schema。 |
| Returns / return model | Tool 对象内部有解析结果，但 openai_schema 不导出。不能把 return 字段描述标成已作为 schema 可见。 |
| Raises | 内部解析，但 openai_schema 不导出。 |
| Examples section | 内部解析，但 openai_schema 不导出；description/Args 内的行内示例仍可见。 |
| Python body / private helpers / comments | 不进入 schema。 |
| `Tool.to_str` / `get_tool_signatures` | 能产生含完整 docstring 的其他表示，但本地 text Agent 发送 tools 使用 openai_schema，不走这些表示。 |
| Read/write result | 真实对象经 model_dump/JSON 序列化成为 ToolMessage，包含真实字段值。 |
| Error observation | get_response 捕获异常并返回 `Error: ...`；不是预先导出的 Raises 清单。 |

`agent_visible_in_canonical_runtime` 是**该 source occurrence 的说明是否实际导出**，YES/NO 不表示 Agent 永远能否学会这条知识。对 read-result model 的字段描述标 NO，同时明确真实字段值在读取后可见；Policy 另有同义断言时对应 Policy occurrence 标 YES。R 结论没有被直接写入 schema，标 NO，而其证据保持可观察。

`final_visibility` 是统一 Phase-A contract 下的语义判定，不是本轮已经生成或应用的 context。特别是 `IMPLEMENTATION / I / NO / VISIBLE` 和未导出的 D 字段描述都只形成审查项；本轮不执行文档补全。
