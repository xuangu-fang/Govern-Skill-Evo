# Phase-A Static Semantic Registry Audit

`STATIC_SEMANTIC_REGISTRY_VERDICT: READY_FOR_HUMAN_REVIEW`

本轮仅完成 taxonomy、两个 domain 的 semantic registry 与静态审计报告。未进行 rollout、Agent/UserSimulator 调用、evaluator、measurement、Diagnosis/Editor、Skill 工作、task construction/selection、context generation 或 Policy/tool-description rewriting。未使用任务内容、trajectory 或 outcome 作为分类证据。此 verdict 不是 context freeze，也不是后续执行授权。

## 1. Source authority and actual runtime surface

当前 Govern-Skill-Evo Python 环境实际解析 `tau2` 到 `external/tau2-bench/src/tau2/__init__.py`。`compiler/resolvers.py:ensure_tau2_importable` 同样显式绑定本地 checkout；Phase-A runner 的 shared import 链使用该 resolver。为确认导入路径，只静态查看 runner import 段，没有导入或执行 runner。

- 本地 τ² 包版本：`1.0.1`；Python `3.13.13`，Pydantic `2.13.5`。
- τ² commit：`1d244f5dca42944b67a379b44bfeb9f5748f189d`。
- Govern-Skill-Evo commit：`8cae2679634351621223b8e6c7be78bfc5021e96`。
- Shell 的 `TAU2_DATA_DIR` 未设置；实际 utils 解析的数据目录是本地 `external/tau2-bench/data`。
- Canonical policy：`data/tau2/domains/airline/policy.md`、`data/tau2/domains/retail/policy.md`（均相对 τ² root）。
- 本地 τ² 工作区有预先存在的改动，包括 `utils/llm_utils.py` 与新增 `agent/manual_skill_agent.py`；因此 commit 不是唯一 source identity。本报告和 JSON 记录所审计源码的 SHA-256。本轮没有修改这些文件。
- 未获取或依赖 GitHub upstream；没有假设 upstream 与 runtime 一致。

### Serialization trace

`domains/{domain}/environment.py:get_environment` 读取本地 Policy；`Environment.get_tools` 返回 `ToolKitBase.get_tools` 包装的 bound methods。`as_tool` 默认使用完整 short + long description。`LLMAgent.system_prompt` 放入 domain policy；`llm_utils.generate` 的 `tools_schema = [tool.openai_schema ...]` 将真正的 function schema 传给 completion。ManualSkillAgent 继承相同 schema 路径，它额外添加的 Skill 不是 canonical source，本轮未加载 Skill。

仅实例化 `AirlineTools(None)` / `RetailTools(None)` 并访问 `.get_tools()`、`.openai_schema` 进行只读 schema introspection；未加载数据库、未执行任何 domain tool method、未创建 Agent/UserSimulator 或执行 evaluator。首次正常导入触发 package 组件注册日志，但注册不等于实例化或调用；后续使用 namespace import 只载入所需源码。没有网络模型请求。

| Docstring / source component | Before-action tool schema | 审计解释 |
| --- | --- | --- |
| Short description | YES | function.description |
| Long description | YES | 默认与 short 拼接；其中规范、effect 与 dynamics 必须拆分 |
| Args descriptions | YES | parameters.properties.*.description |
| Python argument types / enum / required | YES | parameters.model_json_schema |
| Argument model nested fields | YES | 例如 Airline FlightInfo、Passenger、Payment 的 $defs |
| Return model / Returns section | NO | Tool 内部解析，但 openai_schema 未输出 returns |
| Raises section | NO | Tool 内部解析，但 openai_schema 未输出 raises |
| Standalone Examples section | NO | 未输出 examples；Args/description 内行内示例仍 YES |
| Python body / helper / comments | NO | Codex 读取不意味着 Agent 读取 |
| Read/write results | 调用后可见 | BaseModel.model_dump / JSON → ToolMessage.content |
| Actual error | 调用后可见 | get_response 捕获 Exception → `Error: ...`，error=True |

`Tool.to_str` 和 `get_tool_signatures` 是不同表示，不能据此把全部 Python docstring 宣称为 text Agent 输入。所审计的 LLMAgent/ManualSkillAgent 调用路径使用 openai_schema。

### Visibility 字段约定

Registry 保留 source occurrences：同一规则在 Policy 和 schema 中出现时分别可追溯。YES/NO 判断**该出处的说明是否被导出**，不把同义 Policy 规则嫁接到未导出的 Raises 或 return model。Read-result model 字段描述标 NO，但实际读取后的字段和值保持 C6/C8 可见；这不是要隐藏当前状态。R 结论标 NO，其可见证据在 audit_notes 明示。

`NO + I/D + VISIBLE` 是 contract 下应保留的 interface/object 语义，不表示本轮已经补全文档。Implementation 的 I entries 用来记录直接调用缺口；没有将函数体整体提升为 Agent knowledge。此处没有 role→visibility 例外。

## 2. Coverage and summary statistics

统计单位是 source-occurrence atomic assertion，包含参数的 meaning/type/requiredness 和 read-result 字段含义。不是去重知识数量，也不代表难度、重要性或预期表现。完整条目见两个 JSON 的 `entries`；`coverage` 给出每个真实 serialized tool 的参数清单、schema hash 和条目关联。

| Domain | Total | N | D | I | E | L | R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Airline | 418 | 94 | 91 | 174 | 7 | 46 | 6 |
| Retail | 413 | 92 | 87 | 175 | 16 | 39 | 4 |

L tag counts 是多标签计数，不能相加解释为 L unit 数量。

| Domain | L1 | L2 | L3 | L4 | L5 | L6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Airline | 9 | 1 | 13 | 8 | 10 | 20 |
| Retail | 20 | 7 | 9 | 5 | 2 | 5 |

| Domain | VISIBLE | LATENT | DERIVED | Canonical exported YES | Canonical occurrence NO |
| --- | ---: | ---: | ---: | ---: | ---: |
| Airline | 366 | 46 | 6 | 298 | 120 |
| Retail | 370 | 39 | 4 | 305 | 108 |

### Source coverage

- 两份 Policy：preamble、domain basics、每个对象字段和全部业务 action sections 均拆分登记；compound eligibility 和 secondary effect 分开。
- 所有 14 Airline 与 16 Retail decorated public tools：purpose、每个顶层参数 meaning/type/requiredness，以及实际导出的 Airline nested payload fields 均登记。
- 每个 public tool 的 long-description 附加语义和 argument 内的 duplicate/alignment/ID-prefix 等约束另行拆分；未导出的 return schema、Raises、examples 不冒充 visible schema。
- 两个 tools.py 全文及 private helpers 静态审计，补充未完整文档化的 dynamics、direct-call gaps 和源间差异。相同公开规则的每一次代码检查不机械重复收录；只有其 enforcement 机制或差异有独立意义时记录。
- Data models 仅用于确认导出的 nested input schema 和实际 read-result representation。返回字段说明不是 Agent upfront 文本；未读取具体 db 实例，也未用任务对象作为分类证据。
- 无需穷举任意参数组合或任意长 action sequence。Registry 覆盖有源码依据的接口、规则、直接实现规律及明确的共享资源关系，不宣称已证明所有可达程序路径。

### Public tool inventory

| Domain | Tool | Top-level parameters | Registry schema occurrence count |
| --- | --- | ---: | ---: |
| airline | `book_reservation` | 11 | 58 |
| airline | `calculate` | 1 | 5 |
| airline | `cancel_reservation` | 1 | 5 |
| airline | `get_reservation_details` | 1 | 28 |
| airline | `get_user_details` | 1 | 33 |
| airline | `list_all_airports` | 0 | 3 |
| airline | `search_direct_flight` | 3 | 21 |
| airline | `search_onestop_flight` | 3 | 19 |
| airline | `send_certificate` | 2 | 8 |
| airline | `transfer_to_human_agents` | 1 | 6 |
| airline | `update_reservation_baggages` | 4 | 14 |
| airline | `update_reservation_flights` | 4 | 22 |
| airline | `update_reservation_passengers` | 2 | 17 |
| airline | `get_flight_status` | 2 | 8 |
| retail | `calculate` | 1 | 5 |
| retail | `cancel_pending_order` | 2 | 17 |
| retail | `exchange_delivered_order_items` | 4 | 25 |
| retail | `find_user_id_by_name_zip` | 3 | 12 |
| retail | `find_user_id_by_email` | 1 | 5 |
| retail | `get_order_details` | 1 | 41 |
| retail | `get_product_details` | 1 | 13 |
| retail | `get_item_details` | 1 | 9 |
| retail | `get_user_details` | 1 | 29 |
| retail | `list_all_product_types` | 0 | 3 |
| retail | `modify_pending_order_address` | 7 | 26 |
| retail | `modify_pending_order_items` | 4 | 25 |
| retail | `modify_pending_order_payment` | 2 | 12 |
| retail | `modify_user_address` | 7 | 25 |
| retail | `return_delivered_order_items` | 3 | 18 |
| retail | `transfer_to_human_agents` | 1 | 6 |

## 3. Core boundary tables

以下两表聚焦边界：列出所有 L/R、实现独有的 I 缺口，以及关键保护项。逐参数类型、必填性和普通对象字段的完整行在 JSON；不通过缩短此表排除任何 tool。

### Airline

| Knowledge | Source | Role | Latent tags | Canonical visible? | Phase-A visibility | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| AIR_POLICY_GOVERNANCE_001 — Disclose action details before a database update. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_002 — Obtain explicit affirmative user confirmation before a database update. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_003 — Use only information supplied by the user or available tools. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_004 — Do not give subjective recommendations or comments. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_005 — Make at most one tool call at a time. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_006 — Do not combine a tool call with a simultaneous user-facing response. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_007 — Deny requests contrary to policy. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_008 — Transfer to a human if and only if the request cannot be handled within agent action scope. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_009 — Call transfer_to_human_agents before the prescribed transfer message. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_GOVERNANCE_010 — After transfer call, send: YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON. | POLICY · Preamble | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BOOK_PAYMENT_001 — At most one travel certificate may fund a reservation. | POLICY · Book flight / Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BOOK_PAYMENT_002 — At most one credit card may fund a reservation. | POLICY · Book flight / Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BOOK_PAYMENT_003 — At most three gift cards may fund a reservation. | POLICY · Book flight / Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BOOK_PAYMENT_004 — Remaining certificate amount is not refundable. | POLICY · Book flight / Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BOOK_PAYMENT_005 — Every payment method must already exist in the user profile. | POLICY · Book flight / Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_001 — regular booking member: 0 free checked bags per basic economy passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_002 — regular booking member: 1 free checked bags per economy passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_003 — regular booking member: 2 free checked bags per business passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_004 — silver booking member: 1 free checked bags per basic economy passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_005 — silver booking member: 2 free checked bags per economy passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_006 — silver booking member: 3 free checked bags per business passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_007 — gold booking member: 2 free checked bags per basic economy passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_008 — gold booking member: 3 free checked bags per economy passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_009 — gold booking member: 4 free checked bags per business passenger. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_010 — Each extra checked bag costs 50 dollars. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_BAG_ALLOWANCE_011 — Do not add checked bags the user does not need. | POLICY · Book flight / Checked bag allowance | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_FLIGHT_IDENTITY_001 — Obtain the user id from the user. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_FLIGHT_IDENTITY_002 — Obtain the reservation id. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_FLIGHT_IDENTITY_003 — Help locate the reservation id using tools when the user does not know it. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_FLIGHT_CHANGE_001 — Basic economy flights cannot be modified. | POLICY · Modify flight / Change flights | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_FLIGHT_CHANGE_002 — Other reservations may change flights while preserving origin. | POLICY · Modify flight / Change flights | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_FLIGHT_CHANGE_003 — Other reservations may change flights while preserving destination. | POLICY · Modify flight / Change flights | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_FLIGHT_CHANGE_004 — Other reservations may change flights while preserving trip type. | POLICY · Modify flight / Change flights | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_FLIGHT_CHANGE_005 — Some flight segments may be kept. | POLICY · Modify flight / Change flights | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_FLIGHT_HISTORY_001 — Kept flight segment prices are not updated to current prices. | POLICY · Modify flight / Change flights | L | L4 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_POLICY_FLIGHT_ENFORCEMENT_001 — API does not check the stated flight-change eligibility rules. | POLICY · Modify flight / Change flights | L | L6 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_POLICY_MODIFY_RESTRICTIONS_001 — Checked bags may be added. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_MODIFY_RESTRICTIONS_002 — Checked bags may not be removed. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_MODIFY_RESTRICTIONS_003 — Insurance cannot be added after initial booking. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_MODIFY_RESTRICTIONS_004 — Passenger information may be modified. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_MODIFY_RESTRICTIONS_005 — Passenger count may not change. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_MODIFY_RESTRICTIONS_006 — Human agents also cannot change passenger count. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_MODIFY_RESTRICTIONS_007 — Flight changes use a single gift card or credit card for payment or refund. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_MODIFY_RESTRICTIONS_008 — The flight-change payment method must already exist in the user profile. | POLICY · Modify flight / Change baggage and insurance; Change passengers; Payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_001 — Obtain the cancellation reason (change of plan, airline cancellation or other). | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_002 — If any portion has been flown, agent cannot cancel and must transfer. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_003 — If no portion has been flown, booking within the last 24 hours permits cancellation. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_004 — If no portion has been flown, airline cancellation permits cancellation. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_005 — If no portion has been flown, business cabin permits cancellation. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_006 — If no portion has been flown, insurance covering the cancellation reason permits cancellation. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_007 — Refund goes to the original payment methods. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_008 — Refund is promised within 5 to 7 business days. | POLICY · Cancel flight | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| AIR_POLICY_CANCEL_ENFORCEMENT_001 — Cancellation API does not enforce cancellation eligibility. | POLICY · Cancel flight | L | L6 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_TOOL_CANCEL_RESERVATION_PURPOSE_001 — Cancel the whole reservation. | TOOL_SCHEMA · cancel_reservation / function.description | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_TOOL_CANCEL_RESERVATION_EFFECT_001 — Marks the whole reservation cancelled. | TOOL_SCHEMA · cancel_reservation / function.description | E | — | YES | VISIBLE | Immediate primary target effect is part of the action meaning, protected by C5. |
| AIR_TOOL_CANCEL_RESERVATION_ARG_RESERVATION_ID_001 — The reservation ID, such as 'ZFA04Y'. | TOOL_SCHEMA · cancel_reservation/parameters/properties/reservation_id | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_TOOL_CANCEL_RESERVATION_TYPE_RESERVATION_ID_001 — Argument reservation_id representation: {"type": "string"}. | TOOL_SCHEMA · cancel_reservation/parameters/properties/reservation_id | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_TOOL_CANCEL_RESERVATION_REQUIRED_RESERVATION_ID_001 — Argument reservation_id is required. | TOOL_SCHEMA · cancel_reservation/parameters/required | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_TOOL_UPDATE_RESERVATION_FLIGHTS_ARG_FLIGHTS_001 — flights contains each segment in the ENTIRE new reservation. | TOOL_SCHEMA · update_reservation_flights/parameters/properties/flights | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_TOOL_FLIGHT_UPDATE_KEPT_PAYLOAD_001 — Include unchanged flight segments in the full replacement flight list. | TOOL_SCHEMA · update_reservation_flights / parameters.flights | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_DIRECT__GET_USER_001 — Current lookup requires that user id exists. | IMPLEMENTATION · _get_user | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_DIRECT__GET_RESERVATION_001 — Current lookup requires that reservation id exists. | IMPLEMENTATION · _get_reservation | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_DIRECT__GET_FLIGHT_001 — Current lookup requires that flight number exists. | IMPLEMENTATION · _get_flight | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_DIRECT__GET_FLIGHT_INSTANCE_001 — Current lookup requires that date exists for the flight. | IMPLEMENTATION · _get_flight_instance | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_BOOK_DIRECT_001 — Requested flight instance must be available. | IMPLEMENTATION · book_reservation | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_BOOK_DIRECT_002 — Each requested flight must have at least passenger-count seats in the selected cabin. | IMPLEMENTATION · book_reservation | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_BOOK_DIRECT_003 — Each gift card or certificate must cover its supplied allocation. | IMPLEMENTATION · book_reservation | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_BOOK_DIRECT_004 — The sum of payment allocations must equal the computed reservation total. | IMPLEMENTATION · book_reservation | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_UPDATE_DIRECT_001 — Payment method must be in the reservation owner profile. | IMPLEMENTATION · _payment_for_update | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_UPDATE_DIRECT_002 — Certificates are rejected for reservation updates. | IMPLEMENTATION · _payment_for_update | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_UPDATE_DIRECT_003 — Gift-card balance must cover a positive computed update amount. | IMPLEMENTATION · _payment_for_update | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_PASSENGER_ENFORCEMENT_001 — Backend compares submitted passenger count to stored count and rejects inequality. | IMPLEMENTATION · update_reservation_passengers | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CERTIFICATE_DELETE_001 — First successful use removes the entire certificate from user.payment_methods, regardless of allocated amount. | IMPLEMENTATION · book_reservation | L | L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CERTIFICATE_REMAINDER_001 — Unused certificate value does not persist as a reusable profile balance after successful use. | IMPLEMENTATION · book_reservation | L | L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CERTIFICATE_REUSE_001 — A certificate consumed by one booking is absent for subsequent bookings for the same user. | IMPLEMENTATION · book_reservation | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_GIFT_BALANCE_001 — Successful booking subtracts allocated amount from each gift-card balance. | IMPLEMENTATION · book_reservation | L | L1, L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_SHARED_BALANCE_001 — Gift-card deductions by one booking reduce shared funds available to other transactions. | IMPLEMENTATION · book_reservation | L | L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_SEATS_001 — Successful booking subtracts passenger count from each booked flight-date cabin seat inventory. | IMPLEMENTATION · book_reservation | L | L1, L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_HISTORY_001 — Reservation payment_history stores a copy of supplied payment allocations. | IMPLEMENTATION · book_reservation | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_USER_LINK_001 — Booking appends the new reservation id to the user reservations list. | IMPLEMENTATION · book_reservation | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_ID_POOL_001 — Only HATHAT, HATHAU and HATHAV are considered; exhaustion raises Too many reservations. | IMPLEMENTATION · _get_new_reservation_id | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CERTIFICATE_ID_POOL_001 — Certificate issuance uses three fixed candidate IDs per user and fails if all are occupied. | IMPLEMENTATION · send_certificate,_get_new_payment_id | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CERTIFICATE_ID_RECYCLE_001 — A removed issued-certificate ID can be allocated again by later issuance. | IMPLEMENTATION · send_certificate,book_reservation | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_NONENFORCEMENT_001 — Booking has no explicit maximum-passenger-count check. | IMPLEMENTATION · book_reservation | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_NONENFORCEMENT_001 — Booking does not enforce payment-method-count limits. | IMPLEMENTATION · book_reservation,update_reservation_flights,update_reservation_baggages | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_NONENFORCEMENT_002 — Booking does not verify free baggage allowance against membership and cabin. | IMPLEMENTATION · book_reservation,update_reservation_flights,update_reservation_baggages | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_NONENFORCEMENT_003 — Booking does not verify that flights match supplied trip origin, destination or trip type. | IMPLEMENTATION · book_reservation,update_reservation_flights,update_reservation_baggages | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_NONENFORCEMENT_004 — Mutation methods receive no confirmation token and do not enforce conversational confirmation. | IMPLEMENTATION · book_reservation,update_reservation_flights,update_reservation_baggages | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_HISTORY_MATCH_001 — Historical segment price reuse requires matching flight number, date and unchanged cabin. | IMPLEMENTATION · update_reservation_flights | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_CURRENT_PRICE_001 — A nonmatching segment uses the current selected-cabin price from flight-date inventory. | IMPLEMENTATION · update_reservation_flights | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_OLD_BASELINE_001 — Settlement subtracts the sum of stored old reservation segment prices multiplied by stored passenger count. | IMPLEMENTATION · update_reservation_flights | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_NEW_AGGREGATION_001 — Settlement multiplies each selected historical/current segment price by stored passenger count before subtracting the old flight baseline. | IMPLEMENTATION · update_reservation_flights | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_DIRECT_004 — Nonmatching segments must have available status. | IMPLEMENTATION · update_reservation_flights | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_UPDATE_DIRECT_005 — Nonmatching segments need seats at least equal to existing passenger count. | IMPLEMENTATION · update_reservation_flights | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| AIR_IMPL_UPDATE_KEPT_CHECKS_001 — Matching kept segments bypass current flight availability and seat checks. | IMPLEMENTATION · update_reservation_flights | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_SEATS_001 — Flight update does not decrement new-flight seats or release replaced-flight seats. | IMPLEMENTATION · update_reservation_flights | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_HISTORY_001 — Nonzero update settlement appends a signed Payment to reservation.payment_history. | IMPLEMENTATION · update_reservation_flights,update_reservation_baggages | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_ZERO_HISTORY_001 — Zero settlement returns no Payment and causes no history append. | IMPLEMENTATION · _payment_for_update | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_GIFT_001 — Gift-card amount is reduced by signed settlement, so a negative delta replenishes the balance. | IMPLEMENTATION · _payment_for_update | L | L1, L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_UPDATE_SHARED_FUNDS_001 — A reservation update changes gift-card funds available to other reservations. | IMPLEMENTATION · _payment_for_update | L | L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BAG_SETTLEMENT_001 — Charge is 50 × max(0, submitted nonfree_baggages − stored nonfree_baggages). | IMPLEMENTATION · update_reservation_baggages | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BAG_INCREMENTAL_001 — Baggage update charges only an increase in paid bags, not the gross new paid-bag total. | IMPLEMENTATION · update_reservation_baggages | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BAG_NONENFORCEMENT_001 — Backend overwrites baggage counts without enforcing add-only policy or free-allowance consistency. | IMPLEMENTATION · update_reservation_baggages | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CANCEL_HISTORY_001 — Cancellation appends one negated Payment per existing history entry, including earlier adjustments. | IMPLEMENTATION · cancel_reservation | L | L1, L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CANCEL_SEATS_001 — Cancellation does not release seat inventory. | IMPLEMENTATION · cancel_reservation | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CANCEL_PROFILE_FUNDS_001 — Cancellation records refund entries without restoring gift-card or certificate profile balances. | IMPLEMENTATION · cancel_reservation | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CANCEL_REPEAT_001 — Backend does not reject already-cancelled reservations; repeated cancellation negates the then-current history again. | IMPLEMENTATION · cancel_reservation | L | L6, L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CANCEL_FUTURE_001 — Update methods do not check reservation.cancelled status before mutating it. | IMPLEMENTATION · update_reservation_flights,update_reservation_baggages,update_reservation_passengers | L | L6, L2 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_COMPENSATION_ENFORCEMENT_001 — Issuance does not enforce membership, reason, passenger-based amount or prior change/cancellation requirements. | IMPLEMENTATION · send_certificate | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_SEARCH_FILTER_001 — Direct search returns only available-status flight instances, without requiring a positive seat count. | IMPLEMENTATION · _search_direct_flight | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_SEARCH_CONNECTION_001 — One-stop search compares second departure to first arrival using stored strings and an arrival +1 date branch hardcoded to May 2024. | IMPLEMENTATION · search_onestop_flight | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CALCULATOR_ROUNDING_001 — Calculator rounds the computed float to two decimal places. | IMPLEMENTATION · calculate | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. Immediate output representation, protected conservatively although precision is absent from visible schema. |
| AIR_TOOL_TRANSACTION_BINDING_001 — Bind the user request to the correct reservation using returned user and reservation identifiers. | TOOL_SCHEMA · get_reservation_details,get_user_details / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| AIR_TOOL_RESERVATION_AGGREGATION_001 — Aggregate selected per-segment values at reservation scope. | TOOL_SCHEMA · get_reservation_details,search_direct_flight / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| AIR_TOOL_PASSENGER_PROPAGATION_001 — Propagate observed passenger cardinality into explicitly per-passenger costs and allowances. | TOOL_SCHEMA · get_reservation_details,book_reservation / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| AIR_TOOL_HISTORY_RECONCILIATION_001 — Reconcile observed stored reservation values with current flight values for the transaction being discussed. | TOOL_SCHEMA · get_reservation_details,search_direct_flight / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| AIR_TOOL_PAYMENT_ALLOCATION_001 — Aggregate supplied payment allocations and compare them to the applicable observed transaction amount. | TOOL_SCHEMA · book_reservation,get_user_details / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| AIR_TOOL_ELIGIBILITY_BINDING_001 — Combine current flight state, booking time, cabin, insurance and reason to apply visible cancellation eligibility. | TOOL_SCHEMA · get_reservation_details,get_flight_status / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| AIR_TOOL_FLIGHT_UPDATE_CABIN_EFFECT_001 — Flight update sets the requested reservation cabin. | TOOL_SCHEMA · update_reservation_flights / parameters.cabin | E | — | YES | VISIBLE | Immediate primary target effect is part of the action meaning, protected by C5. |
| AIR_IMPL_BOOK_ALLOCATION_VALIDATION_001 — Repeated allocations for the same gift card are balance-checked individually before all deductions, rather than checked as an aggregated per-method amount. | IMPLEMENTATION · book_reservation | L | L6, L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BOOK_SIGN_ENFORCEMENT_001 — No explicit nonnegative check is applied to supplied payment amounts or baggage counts. | IMPLEMENTATION · book_reservation | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_FLIGHT_NONENFORCEMENT_001 — No explicit check enforces unchanged origin, destination or trip type. | IMPLEMENTATION · update_reservation_flights | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_CABIN_FLOWN_ENFORCEMENT_001 — No explicit reservation-wide flown-segment check enforces cabin-change eligibility. | IMPLEMENTATION · update_reservation_flights | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| AIR_IMPL_BAG_ZERO_VALIDATION_001 — Even a zero-charge baggage update validates payment-method existence and rejects certificates. | IMPLEMENTATION · update_reservation_baggages,_payment_for_update | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |

### Retail

| Knowledge | Source | Role | Latent tags | Canonical visible? | Phase-A visibility | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| RET_POLICY_GENERIC_001 — Generally order actions are limited to pending or delivered orders. | POLICY · Generic action rules | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_GENERIC_002 — Exchange tools can be called only once per order. | POLICY · Generic action rules | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_GENERIC_003 — Modify order tools can be called only once per order. | POLICY · Generic action rules | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_GENERIC_004 — Collect all items to change before the exchange or modification call. | POLICY · Generic action rules | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_CANCEL_REFUND_001 — Cancellation refunds the order total. | POLICY · Cancel pending order | L | L1 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. Refund routing/timing entitlements remain N. This unit concerns the automatic financial secondary effect of cancellation. |
| RET_POLICY_PAYMENT_001 — Choose a single replacement payment method. | POLICY · Modify pending order / Modify payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_PAYMENT_002 — Replacement payment method must differ from the original. | POLICY · Modify pending order / Modify payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_PAYMENT_003 — A replacement gift card must cover the total order amount. | POLICY · Modify pending order / Modify payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_PAYMENT_004 — Original gift card is refunded immediately. | POLICY · Modify pending order / Modify payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_PAYMENT_005 — Other original payment methods are refunded in 5 to 7 business days. | POLICY · Modify pending order / Modify payment | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_PAYMENT_STATUS_001 — Payment modification leaves order status pending. | POLICY · Modify pending order / Modify payment | E | — | YES | VISIBLE | Conservative primary-object guarantee: payment replacement preserves pending status; no secondary mutation occurs. Preserve the explicit guarantee. Does not imply that history-based prerequisites for another payment change remain satisfied. |
| RET_POLICY_PAYMENT_REFUND_001 — Replacing payment refunds the original payment. | POLICY · Modify pending order / Modify payment | E | — | YES | VISIBLE | Immediate primary target effect is part of the action meaning, protected by C5. Conservative boundary: reversing original funding is part of payment replacement itself; retain the promise. History layout is separate L1. |
| RET_POLICY_MODIFY_ITEMS_001 — Items modification can be called only once per order. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_002 — Confirm all modification details are correct before the call. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_003 — Remind the customer to confirm all items to modify have been provided. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_004 — Replacement item must be available. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_005 — Replacement item must be of the same product. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_006 — Replacement item must have a different product option. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_007 — Changing product type is forbidden. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_008 — User supplies a method for paying or receiving the price difference. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_009 — A gift card must cover a positive price difference. | POLICY · Modify pending order / Modify items | N | — | YES | VISIBLE | Permission, prohibition or required governance remains explicit under C3, independently of API enforcement. |
| RET_POLICY_MODIFY_ITEMS_STATUS_001 — Item modification changes status to pending (items modifed). | POLICY · Modify pending order / Modify items | L | L1 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_POLICY_MODIFY_ITEMS_FUTURE_MODIFY_001 — After items modification the agent cannot modify the order anymore. | POLICY · Modify pending order / Modify items | L | L2 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. Describes future-option consequence, not a standalone permission rule. Retain independent normative single-call and pending eligibility rules. Implementation address behavior differs; see implementation entries. |
| RET_POLICY_MODIFY_ITEMS_FUTURE_CANCEL_001 — After items modification the agent cannot cancel the order anymore. | POLICY · Modify pending order / Modify items | L | L2 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. Describes future-option consequence, not a standalone permission rule. Retain independent normative single-call and pending eligibility rules. Implementation address behavior differs; see implementation entries. |
| RET_POLICY_RETURN_EFFECT_001 — Confirmed return request sets return requested status. | POLICY · Return delivered order | E | — | YES | VISIBLE | Immediate primary target effect is part of the action meaning, protected by C5. |
| RET_POLICY_EXCHANGE_EFFECT_001 — Confirmed exchange request sets exchange requested status. | POLICY · Exchange delivered order | E | — | YES | VISIBLE | Immediate primary target effect is part of the action meaning, protected by C5. |
| RET_TOOL_EXCHANGE_DELIVERED_ORDER_ITEMS_DUPLICATES_001 — item_ids may contain duplicate IDs representing multiple item occurrences. | TOOL_SCHEMA · exchange_delivered_order_items / parameters.item_ids | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_EXCHANGE_DELIVERED_ORDER_ITEMS_DUPLICATES_002 — new_item_ids may contain duplicates. | TOOL_SCHEMA · exchange_delivered_order_items / parameters.new_item_ids | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_EXCHANGE_DELIVERED_ORDER_ITEMS_ALIGNMENT_001 — Each new_item_ids entry corresponds to item_ids at the same position. | TOOL_SCHEMA · exchange_delivered_order_items / parameters.new_item_ids | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_EXCHANGE_DELIVERED_ORDER_ITEMS_ONCE_001 — This operation may be invoked only once per order. | TOOL_SCHEMA · exchange_delivered_order_items / description | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. Explicit invocation cardinality is protected by C5, even though backend state transitions help enforce it. Policy counterpart is N. |
| RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_DUPLICATES_001 — item_ids may contain duplicate IDs representing multiple item occurrences. | TOOL_SCHEMA · modify_pending_order_items / parameters.item_ids | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_DUPLICATES_002 — new_item_ids may contain duplicates. | TOOL_SCHEMA · modify_pending_order_items / parameters.new_item_ids | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_ALIGNMENT_001 — Each new_item_ids entry corresponds to item_ids at the same position. | TOOL_SCHEMA · modify_pending_order_items / parameters.new_item_ids | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_ONCE_001 — This operation may be invoked only once per order. | TOOL_SCHEMA · modify_pending_order_items / description | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. Explicit invocation cardinality is protected by C5, even though backend state transitions help enforce it. Policy counterpart is N. |
| RET_TOOL_RETURN_DELIVERED_ORDER_ITEMS_DUPLICATES_001 — item_ids may contain duplicate IDs representing multiple item occurrences. | TOOL_SCHEMA · return_delivered_order_items / parameters.item_ids | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_EXCHANGE_RETURN_ONCE_001 — For a delivered order, return or exchange may be done only once by the agent. | TOOL_SCHEMA · exchange_delivered_order_items / description | I | — | YES | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_TOOL_CANCEL_DETAILS_003 — Cancellation refunds the payment. | TOOL_SCHEMA · cancel_pending_order / description | L | L1 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_TOOL_CANCEL_DETAILS_004 — Gift-card cancellation refund increases user gift-card balance immediately. | TOOL_SCHEMA · cancel_pending_order / description | L | L1, L3 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_DIRECT__GET_USER_001 — Current lookup requires that user id exists. | IMPLEMENTATION · _get_user | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_DIRECT__GET_ORDER_001 — Current lookup requires that order id exists. | IMPLEMENTATION · _get_order | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_DIRECT__GET_PRODUCT_001 — Current lookup requires that product id exists. | IMPLEMENTATION · _get_product | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_DIRECT__GET_ITEM_001 — Current lookup requires that item id exists in some product. | IMPLEMENTATION · _get_item | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_DIRECT__GET_VARIANT_001 — Current lookup requires that variant exists within the referenced product. | IMPLEMENTATION · _get_variant | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_DIRECT__GET_PAYMENT_METHOD_001 — Current lookup requires that payment method exists in the order owner profile. | IMPLEMENTATION · _get_payment_method | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_CALCULATOR_ROUNDING_001 — Calculator rounds the computed float to two decimal places. | IMPLEMENTATION · calculate | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. Immediate output representation, protected conservatively although precision is absent from visible schema. |
| RET_IMPL_MODIFY_PENDING_ORDER_ITEMS_DIRECT_001 — Requested multiplicities cannot exceed matching item occurrences in the order. | IMPLEMENTATION · modify_pending_order_items | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_MODIFY_PENDING_ORDER_ITEMS_DIRECT_002 — Old and replacement item lists must have equal length. | IMPLEMENTATION · modify_pending_order_items | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_EXCHANGE_DELIVERED_ORDER_ITEMS_DIRECT_001 — Requested multiplicities cannot exceed matching item occurrences in the order. | IMPLEMENTATION · exchange_delivered_order_items | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_EXCHANGE_DELIVERED_ORDER_ITEMS_DIRECT_002 — Old and replacement item lists must have equal length. | IMPLEMENTATION · exchange_delivered_order_items | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_PAYMENT_HISTORY_DIRECT_001 — Current payment history must have exactly one entry and that entry must be a payment. | IMPLEMENTATION · modify_pending_order_payment | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_PENDING_ADDRESS_DIRECT_001 — Address API accepts any status containing the substring pending. | IMPLEMENTATION · modify_pending_order_address,_is_pending_order | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. Exact current direct precondition. Does not override stricter normative rules; future behavior is separately L6. |
| RET_IMPL_PENDING_PAYMENT_DIRECT_001 — Payment API accepts any status containing the substring pending. | IMPLEMENTATION · modify_pending_order_payment,_is_pending_order | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. Exact backend status predicate, independent of its payment-history prerequisite. |
| RET_IMPL_ITEM_HISTORY_001 — Item substitution appends a payment for positive delta or a refund otherwise, including a zero-value refund. | IMPLEMENTATION · modify_pending_order_items | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_GIFT_BALANCE_001 — Gift-card balance is reduced by signed price difference and rounded to two decimals. | IMPLEMENTATION · modify_pending_order_items | L | L1, L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_PAYMENT_FUTURE_001 — Item history append invalidates payment modification exactly-one-entry prerequisite, even when price difference is zero. | IMPLEMENTATION · modify_pending_order_items,modify_pending_order_payment | L | L2 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_ADDRESS_ENFORCEMENT_001 — After item modification, address API still accepts the resulting pending (item modified) status. | IMPLEMENTATION · modify_pending_order_items,modify_pending_order_address | L | L2, L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_STATUS_SPELLING_001 — Implementation status is pending (item modified), not policy spelling pending (items modifed). | IMPLEMENTATION · modify_pending_order_items | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_PRICE_BASELINE_001 — Price difference uses stored order-item price as old basis and current catalog variant price as new basis. | IMPLEMENTATION · modify_pending_order_items,exchange_delivered_order_items | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_LAST_VARIANT_001 — Mutation loop assigns the last validation-loop variant price and options to every modified occurrence. | IMPLEMENTATION · modify_pending_order_items | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_SEQUENTIAL_LOOKUP_001 — Mutation resolves each next old ID against the already-mutated order list, so overlapping old/new IDs may target a newly changed occurrence. | IMPLEMENTATION · modify_pending_order_items | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_PAYMENT_HISTORY_APPEND_001 — Payment replacement preserves original history and appends a new payment followed by an original-method refund. | IMPLEMENTATION · modify_pending_order_payment | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_PAYMENT_AMOUNT_BASELINE_001 — Replacement charge/refund amount comes from payment_history[0].amount, not a recomputed item total. | IMPLEMENTATION · modify_pending_order_payment | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_PAYMENT_NEW_GIFT_001 — Replacement gift-card balance is debited by the historical payment amount and rounded to two decimals. | IMPLEMENTATION · modify_pending_order_payment | L | L1, L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_PAYMENT_OLD_GIFT_001 — Original gift-card balance is credited by the historical payment amount and rounded to two decimals. | IMPLEMENTATION · modify_pending_order_payment | L | L1, L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_PAYMENT_REPEAT_001 — The first payment change grows history to three entries and therefore prevents a subsequent payment change. | IMPLEMENTATION · modify_pending_order_payment | L | L2 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_PAYMENT_ITEMS_001 — Payment change leaves status pending, so item substitution still meets its status predicate and has no history-length check. | IMPLEMENTATION · modify_pending_order_payment,modify_pending_order_items | L | L2 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_SHARED_GIFTS_001 — Gift-card balance mutations on one order change funds available to other orders of the same user. | IMPLEMENTATION · modify_pending_order_items,modify_pending_order_payment,cancel_pending_order | L | L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_CANCEL_HISTORY_001 — Cancellation creates positive refund entries for every history entry without filtering transaction_type or netting prior refunds. | IMPLEMENTATION · cancel_pending_order | L | L1, L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_CANCEL_GIFT_HISTORY_001 — Gift-card refund accumulation iterates every history amount, including amounts on earlier refund entries. | IMPLEMENTATION · cancel_pending_order | L | L3, L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_EXCHANGE_DEFERRED_001 — Exchange only stores request fields and price difference; it does not replace order.items immediately. | IMPLEMENTATION · exchange_delivered_order_items | L | L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_EXCHANGE_FUNDS_001 — Exchange checks gift-card sufficiency but does not debit/credit balance or append payment history. | IMPLEMENTATION · exchange_delivered_order_items | L | L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_EXCHANGE_SORT_001 — Old and new exchange ID lists are sorted independently when stored, losing original positional pairing. | IMPLEMENTATION · exchange_delivered_order_items | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_EXCHANGE_ROUNDING_001 — Exchange price difference is rounded to two decimals before the balance check and request storage. | IMPLEMENTATION · exchange_delivered_order_items | L | L4 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_RETURN_DEFERRED_001 — Return records sorted item IDs and refund method without applying refund or changing item inventory. | IMPLEMENTATION · return_delivered_order_items | L | L3 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_RETURN_ORIGINAL_DIRECT_001 — For non-gift-card refund, the current accepted original method is payment_history[0].payment_method_id. | IMPLEMENTATION · return_delivered_order_items | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. |
| RET_IMPL_RETURN_EXCHANGE_FUTURE_001 — Either request changes delivered status, preventing subsequent return/exchange calls requiring exact delivered status. | IMPLEMENTATION · return_delivered_order_items,exchange_delivered_order_items | L | L2 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_EMAIL_NOT_IMPLEMENTED_001 — Backend registers requests but performs no email sending despite canonical email promises. | IMPLEMENTATION · return_delivered_order_items,exchange_delivered_order_items | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_CONFIRM_NOT_ENFORCED_001 — Backend does not enforce prior conversational authentication or confirmation. | IMPLEMENTATION · cancel_pending_order,modify_pending_order_items,modify_pending_order_payment,modify_user_address | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_EXCHANGE_SAME_ITEM_001 — Exchange has no explicit old-id equals new-id rejection, unlike item modification. | IMPLEMENTATION · exchange_delivered_order_items | L | L6 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_LOOKUP_CASE_001 — Email and name matching are case-insensitive, while zip equality is exact. | IMPLEMENTATION · find_user_id_by_email,find_user_id_by_name_zip | I | — | NO | VISIBLE | Tool purpose, payload or current direct invocation semantics are protected by C5. Lookup matching is immediate interface behavior, conservatively retained although absent from schema. |
| RET_TOOL_TRANSACTION_BINDING_001 — Bind the request and payment evidence to the correct order and authenticated user. | TOOL_SCHEMA · get_order_details,get_user_details / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| RET_TOOL_ITEM_MULTIPLICITY_001 — Count requested item occurrences and bind each replacement to its corresponding old occurrence. | TOOL_SCHEMA · get_order_details,modify_pending_order_items / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| RET_TOOL_ORDER_AGGREGATION_001 — Aggregate applicable per-item values over requested occurrences for one order. | TOOL_SCHEMA · get_order_details,get_product_details / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| RET_TOOL_HISTORY_RECONCILIATION_001 — Reconcile observed payment/refund entries and profile balances for the intended transaction. | TOOL_SCHEMA · get_order_details,get_user_details / read-result transaction representation | R | — | NO | DERIVED | Conclusion requires binding, aggregation or inference over available evidence; C9 protects inputs without supplying the answer. |
| RET_TOOL_EXCHANGE_DELIVERED_ORDER_ITEMS_PRICE_DIFFERENCE_001 — Selected payment method settles the item price difference as payment or refund. | TOOL_SCHEMA · exchange_delivered_order_items / parameters.payment_method_id | L | L1 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_PRICE_DIFFERENCE_001 — Selected payment method settles the item price difference as payment or refund. | TOOL_SCHEMA · modify_pending_order_items / parameters.payment_method_id | L | L1 | YES | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_ITEM_HISTORY_BEFORE_MUTATION_001 — Payment history and gift-card balance mutate before the sequential item replacement loop completes, without a rollback wrapper in the function. | IMPLEMENTATION · modify_pending_order_items | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_PAYMENT_REFUND_BEFORE_LOOKUP_001 — History append and new gift-card debit occur before the old payment method is looked up for refund, without a function-local rollback. | IMPLEMENTATION · modify_pending_order_payment | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_CANCEL_GIFT_BEFORE_COMMIT_001 — Gift-card balances update during history iteration before order status and refund history are finalized. | IMPLEMENTATION · cancel_pending_order | L | L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_INVENTORY_NOT_UPDATED_001 — Item operations do not change product variant availability in the catalog. | IMPLEMENTATION · modify_pending_order_items,exchange_delivered_order_items,return_delivered_order_items | L | L3, L5 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |
| RET_IMPL_DEFAULT_ADDRESS_SCOPE_001 — Changing the user default address does not propagate to already-stored order shipping addresses. | IMPLEMENTATION · modify_user_address | I | — | NO | VISIBLE | Conservative target-scope semantics: default user address and stored order address are distinct targets. No propagation is not tagged as a secondary mutation. This clarifies the direct target scope without generating any context. |
| RET_IMPL_EMPTY_ITEM_LIST_001 — No minimum item-list length check prevents a zero-item call from appending history and changing status. | IMPLEMENTATION · modify_pending_order_items | L | L6, L1 | NO | LATENT | Backend operational dynamics are not explicitly documented under C7; actual results and errors remain observable under C8. |

## 4. Required focused audits

### Retail Modify Items

| Atomic question | Classification | Source-backed finding |
| --- | --- | --- |
| Purpose | I / VISIBLE | 变更 pending order 的 item variants。 |
| Same product / different options / available | N / VISIBLE | Policy 规定；schema 同 product 约束单列。 |
| Duplicate item representation | I / VISIBLE | item_ids 与 new_item_ids 可重复；按出现次数表示多个 item。 |
| Positional alignment / equal cardinality | I / VISIBLE | 同位置配对；实现检查等长与已有 multiplicity。 |
| Single call | N/I / VISIBLE | 保留 Policy 要求、schema invocation cardinality 及收集完整清单的规范要求。 |
| Requested variant substitution | E / VISIBLE | primary target mutation。 |
| Status transition | L1 / LATENT | Policy 文本 `pending (items modifed)`；代码 `pending (item modified)`。 |
| Future modification invalidation | L2 / LATENT | Canonical broad consequence；API 地址仍可改，payment 因 history 失效，items 因 exact status 失效，三者不能混为一个 predicate。 |
| Future cancellation invalidation | L2 / LATENT | cancel 检查 exact pending；具体当前 eligibility 仍 N/I 可见。 |
| Payment/refund effect | L1 / LATENT | secondary settlement；支付方式参数含义、差额支付责任仍 I/N。 |
| Gift-card balance mutation | L1/L3 / LATENT | 减 signed delta 并 round；负值补回余额。 |
| Payment-history mutation | L1 / LATENT | 始终追加，包括 zero delta 的 refund entry。 |
| Assignment behavior | L1 / LATENT | mutation loop 的 variant 来自前一循环最后一次迭代；不是 Agent 已知 interface。 |

“single call”不能随着未来状态说明一起删除。用户必须确认完整修改清单属于 N，不能以 C9 为由删除 policy-required ordering。

### Retail Payment Modification

Purpose 和 replacement funding effect 分属 I/E。Policy 的 single method、new differs、gift-card sufficiency、pending eligibility 均为 N/VISIBLE。`payment_history` **恰好一条且 transaction_type == payment** 是源码独有 I/VISIBLE：它是当前调用条件，Raises 没有进入 schema，不能标 canonical YES。

Append `[new payment, old refund]` 而保留原 entry 为 L1；新旧 gift-card balance 更新为 L1/L3；从 history[0].amount 而非当前 item total 取金额是 L4；追加后的 history 使后续 payment change 失效是 L2。Items mutation 追加 history 也破坏该 prerequisite，是另一条 L2。Payment change 不改变 pending 状态，这个明确的 primary-object 保证保守保留 E/VISIBLE；它不保证其他 prerequisite 永远成立。

### Airline Flight Update

| Atomic question | Classification | Finding |
| --- | --- | --- |
| ENTIRE reservation payload | I / VISIBLE | 所有新 itinerary segments 均提交，包括未改变段。 |
| Kept segment allowed | N / VISIBLE | 不可把“允许保留”和“价格保留”一起删除。 |
| Historical price persistence | L4 / LATENT | Policy 已公开；实现精确条件是 number + date + unchanged cabin。 |
| New flight current price branch | L4 / LATENT | nonmatching segment 使用 current cabin price；价格数据本身仍 D/observable。 |
| Passenger cardinality in settlement | L4 / LATENT for backend law; R / DERIVED for aggregation | 实现对 segment price 乘 stored passenger count；对已知 per-passenger 费用传播人数是独立 R。 |
| Old flight-cost subtraction | L4 / LATENT | 扣除 old reservation flights 的 stored price 合计 × passengers，不扣整个 payment history。 |
| Payment append | L1 / LATENT | 非零 signed delta 追加，零 delta 不追加。 |
| Current new-flight seat prerequisite | I / VISIBLE | available status + enough seats；不因 Raises 未导出变为 L。 |
| Seat dynamics | L3/L5 / LATENT | booking 扣座位；update 不扣新座位、不释放旧座位；cancel 不释放。 |
| Cabin update | E / VISIBLE | cabin 参数选定 primary target，实际代码更新 reservation.cabin。 |

正确 transaction delta 涉及两个不同层次：取得/学到适用的 valuation rule，以及把观察到的 transaction inputs 绑定和聚合。后者是 R；在前者未知时不能凭“会算术”假定 Agent 知道历史分支。

### Airline Certificate

Allowed payment type 是 D/N 可见；at-most-one certificate 与 unused amount nonrefundable 是 N/VISIBLE。Sufficient balance for allocated amount 是 I/VISIBLE，但精确检查在 implementation、canonical schema 未公开。成功使用即 pop 整个 certificate 是 L3；remainder 不再作为可重用 balance 存在是 L3；另一个 booking 因共享 profile 删除无法重用是 L3/L5。Nonrefundable 不逻辑蕴含 first-use deletion，两者不能合并。

Update 的 payment_id Args 包含 certificate 示例，但 `_payment_for_update` 拒绝 certificate。示例可见不等于允许支付：flight-change Policy 的 single gift-card/credit-card 规范必须保留；baggage 的实际 helper 条件作为 I gap 登记。没有修改 normative surface。

### Airline Baggage

所有 9 个 membership × cabin 免费 allowance cells、extra bag = 50 dollars、no unneeded bags、add-only rule 均 N/VISIBLE。`total_baggages` 和 `nonfree_baggages` 是更新后的 reservation totals，I/VISIBLE，不是这次新增数量。

实现收费 `50 * max(0, new_nonfree - stored_nonfree)` 是 L4；incremental 而非 gross charging 是同一机制的独立表述。后台不检查 add-only/free allowance 是 L6；规则仍 N。Passenger list、当前 baggage counts 与 policy rate 均保留，基于已知 rate/allowance 进行数量聚合是 R。

## 5. CANONICAL_VISIBLE_TO_PHASE_A_LATENT

以下是按本 taxonomy 判定的公开说明候选，不执行 removal，不估计其效果。重复来源单独列出，以防只处理 Policy 却遗漏 schema。

### Airline

- `AIR_POLICY_FLIGHT_HISTORY_001` — Kept flight segment prices are not updated to current prices. (L/L4)
- `AIR_POLICY_FLIGHT_ENFORCEMENT_001` — API does not check the stated flight-change eligibility rules. (L/L6)
- `AIR_POLICY_CANCEL_ENFORCEMENT_001` — Cancellation API does not enforce cancellation eligibility. (L/L6)

### Retail

- `RET_POLICY_CANCEL_REFUND_001` — Cancellation refunds the order total. (L/L1)
- `RET_POLICY_MODIFY_ITEMS_STATUS_001` — Item modification changes status to pending (items modifed). (L/L1)
- `RET_POLICY_MODIFY_ITEMS_FUTURE_MODIFY_001` — After items modification the agent cannot modify the order anymore. (L/L2)
- `RET_POLICY_MODIFY_ITEMS_FUTURE_CANCEL_001` — After items modification the agent cannot cancel the order anymore. (L/L2)
- `RET_TOOL_CANCEL_DETAILS_003` — Cancellation refunds the payment. (L/L1)
- `RET_TOOL_CANCEL_DETAILS_004` — Gift-card cancellation refund increases user gift-card balance immediately. (L/L1,L3)
- `RET_TOOL_EXCHANGE_DELIVERED_ORDER_ITEMS_PRICE_DIFFERENCE_001` — Selected payment method settles the item price difference as payment or refund. (L/L1)
- `RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_PRICE_DIFFERENCE_001` — Selected payment method settles the item price difference as payment or refund. (L/L1)

这不授权删除包含这些断言的整句。特别是 payment_method_id 的参数 meaning、允许 payment/refund 的规范和 single-call constraint 都必须分别保留。任何实际 transformation 仍需人工审查。

## 6. ALREADY_LATENT_IN_CANONICAL

这些 implementation dynamics 没有从该来源进入 canonical schema，不需要文本 removal。真实 result/error 仍可暴露后果。列表不含 I/D 的 upfront documentation gaps。

### Airline

- `AIR_IMPL_PASSENGER_ENFORCEMENT_001` — Backend compares submitted passenger count to stored count and rejects inequality. (L/L6)
- `AIR_IMPL_CERTIFICATE_DELETE_001` — First successful use removes the entire certificate from user.payment_methods, regardless of allocated amount. (L/L3)
- `AIR_IMPL_CERTIFICATE_REMAINDER_001` — Unused certificate value does not persist as a reusable profile balance after successful use. (L/L3)
- `AIR_IMPL_CERTIFICATE_REUSE_001` — A certificate consumed by one booking is absent for subsequent bookings for the same user. (L/L3,L5)
- `AIR_IMPL_BOOK_GIFT_BALANCE_001` — Successful booking subtracts allocated amount from each gift-card balance. (L/L1,L3)
- `AIR_IMPL_BOOK_SHARED_BALANCE_001` — Gift-card deductions by one booking reduce shared funds available to other transactions. (L/L5)
- `AIR_IMPL_BOOK_SEATS_001` — Successful booking subtracts passenger count from each booked flight-date cabin seat inventory. (L/L1,L3,L5)
- `AIR_IMPL_BOOK_HISTORY_001` — Reservation payment_history stores a copy of supplied payment allocations. (L/L1)
- `AIR_IMPL_BOOK_USER_LINK_001` — Booking appends the new reservation id to the user reservations list. (L/L1)
- `AIR_IMPL_BOOK_ID_POOL_001` — Only HATHAT, HATHAU and HATHAV are considered; exhaustion raises Too many reservations. (L/L3,L5)
- `AIR_IMPL_CERTIFICATE_ID_POOL_001` — Certificate issuance uses three fixed candidate IDs per user and fails if all are occupied. (L/L3,L5)
- `AIR_IMPL_CERTIFICATE_ID_RECYCLE_001` — A removed issued-certificate ID can be allocated again by later issuance. (L/L3,L5)
- `AIR_IMPL_BOOK_NONENFORCEMENT_001` — Booking has no explicit maximum-passenger-count check. (L/L6)
- `AIR_IMPL_NONENFORCEMENT_001` — Booking does not enforce payment-method-count limits. (L/L6)
- `AIR_IMPL_NONENFORCEMENT_002` — Booking does not verify free baggage allowance against membership and cabin. (L/L6)
- `AIR_IMPL_NONENFORCEMENT_003` — Booking does not verify that flights match supplied trip origin, destination or trip type. (L/L6)
- `AIR_IMPL_NONENFORCEMENT_004` — Mutation methods receive no confirmation token and do not enforce conversational confirmation. (L/L6)
- `AIR_IMPL_UPDATE_HISTORY_MATCH_001` — Historical segment price reuse requires matching flight number, date and unchanged cabin. (L/L4)
- `AIR_IMPL_UPDATE_CURRENT_PRICE_001` — A nonmatching segment uses the current selected-cabin price from flight-date inventory. (L/L4)
- `AIR_IMPL_UPDATE_OLD_BASELINE_001` — Settlement subtracts the sum of stored old reservation segment prices multiplied by stored passenger count. (L/L4)
- `AIR_IMPL_UPDATE_NEW_AGGREGATION_001` — Settlement multiplies each selected historical/current segment price by stored passenger count before subtracting the old flight baseline. (L/L4)
- `AIR_IMPL_UPDATE_KEPT_CHECKS_001` — Matching kept segments bypass current flight availability and seat checks. (L/L6)
- `AIR_IMPL_UPDATE_SEATS_001` — Flight update does not decrement new-flight seats or release replaced-flight seats. (L/L3,L5)
- `AIR_IMPL_UPDATE_HISTORY_001` — Nonzero update settlement appends a signed Payment to reservation.payment_history. (L/L1)
- `AIR_IMPL_UPDATE_ZERO_HISTORY_001` — Zero settlement returns no Payment and causes no history append. (L/L1)
- `AIR_IMPL_UPDATE_GIFT_001` — Gift-card amount is reduced by signed settlement, so a negative delta replenishes the balance. (L/L1,L3)
- `AIR_IMPL_UPDATE_SHARED_FUNDS_001` — A reservation update changes gift-card funds available to other reservations. (L/L5)
- `AIR_IMPL_BAG_SETTLEMENT_001` — Charge is 50 × max(0, submitted nonfree_baggages − stored nonfree_baggages). (L/L4)
- `AIR_IMPL_BAG_INCREMENTAL_001` — Baggage update charges only an increase in paid bags, not the gross new paid-bag total. (L/L4)
- `AIR_IMPL_BAG_NONENFORCEMENT_001` — Backend overwrites baggage counts without enforcing add-only policy or free-allowance consistency. (L/L6)
- `AIR_IMPL_CANCEL_HISTORY_001` — Cancellation appends one negated Payment per existing history entry, including earlier adjustments. (L/L1,L4)
- `AIR_IMPL_CANCEL_SEATS_001` — Cancellation does not release seat inventory. (L/L3,L5)
- `AIR_IMPL_CANCEL_PROFILE_FUNDS_001` — Cancellation records refund entries without restoring gift-card or certificate profile balances. (L/L3,L5)
- `AIR_IMPL_CANCEL_REPEAT_001` — Backend does not reject already-cancelled reservations; repeated cancellation negates the then-current history again. (L/L6,L1)
- `AIR_IMPL_CANCEL_FUTURE_001` — Update methods do not check reservation.cancelled status before mutating it. (L/L6,L2)
- `AIR_IMPL_COMPENSATION_ENFORCEMENT_001` — Issuance does not enforce membership, reason, passenger-based amount or prior change/cancellation requirements. (L/L6)
- `AIR_IMPL_SEARCH_FILTER_001` — Direct search returns only available-status flight instances, without requiring a positive seat count. (L/L6)
- `AIR_IMPL_SEARCH_CONNECTION_001` — One-stop search compares second departure to first arrival using stored strings and an arrival +1 date branch hardcoded to May 2024. (L/L6)
- `AIR_IMPL_BOOK_ALLOCATION_VALIDATION_001` — Repeated allocations for the same gift card are balance-checked individually before all deductions, rather than checked as an aggregated per-method amount. (L/L6,L3)
- `AIR_IMPL_BOOK_SIGN_ENFORCEMENT_001` — No explicit nonnegative check is applied to supplied payment amounts or baggage counts. (L/L6)
- `AIR_IMPL_FLIGHT_NONENFORCEMENT_001` — No explicit check enforces unchanged origin, destination or trip type. (L/L6)
- `AIR_IMPL_CABIN_FLOWN_ENFORCEMENT_001` — No explicit reservation-wide flown-segment check enforces cabin-change eligibility. (L/L6)
- `AIR_IMPL_BAG_ZERO_VALIDATION_001` — Even a zero-charge baggage update validates payment-method existence and rejects certificates. (L/L6)

### Retail

- `RET_IMPL_ITEM_HISTORY_001` — Item substitution appends a payment for positive delta or a refund otherwise, including a zero-value refund. (L/L1)
- `RET_IMPL_ITEM_GIFT_BALANCE_001` — Gift-card balance is reduced by signed price difference and rounded to two decimals. (L/L1,L3)
- `RET_IMPL_ITEM_PAYMENT_FUTURE_001` — Item history append invalidates payment modification exactly-one-entry prerequisite, even when price difference is zero. (L/L2)
- `RET_IMPL_ITEM_ADDRESS_ENFORCEMENT_001` — After item modification, address API still accepts the resulting pending (item modified) status. (L/L2,L6)
- `RET_IMPL_ITEM_STATUS_SPELLING_001` — Implementation status is pending (item modified), not policy spelling pending (items modifed). (L/L1)
- `RET_IMPL_ITEM_PRICE_BASELINE_001` — Price difference uses stored order-item price as old basis and current catalog variant price as new basis. (L/L4)
- `RET_IMPL_ITEM_LAST_VARIANT_001` — Mutation loop assigns the last validation-loop variant price and options to every modified occurrence. (L/L1)
- `RET_IMPL_ITEM_SEQUENTIAL_LOOKUP_001` — Mutation resolves each next old ID against the already-mutated order list, so overlapping old/new IDs may target a newly changed occurrence. (L/L1)
- `RET_IMPL_PAYMENT_HISTORY_APPEND_001` — Payment replacement preserves original history and appends a new payment followed by an original-method refund. (L/L1)
- `RET_IMPL_PAYMENT_AMOUNT_BASELINE_001` — Replacement charge/refund amount comes from payment_history[0].amount, not a recomputed item total. (L/L4)
- `RET_IMPL_PAYMENT_NEW_GIFT_001` — Replacement gift-card balance is debited by the historical payment amount and rounded to two decimals. (L/L1,L3)
- `RET_IMPL_PAYMENT_OLD_GIFT_001` — Original gift-card balance is credited by the historical payment amount and rounded to two decimals. (L/L1,L3)
- `RET_IMPL_PAYMENT_REPEAT_001` — The first payment change grows history to three entries and therefore prevents a subsequent payment change. (L/L2)
- `RET_IMPL_PAYMENT_ITEMS_001` — Payment change leaves status pending, so item substitution still meets its status predicate and has no history-length check. (L/L2)
- `RET_IMPL_SHARED_GIFTS_001` — Gift-card balance mutations on one order change funds available to other orders of the same user. (L/L5)
- `RET_IMPL_CANCEL_HISTORY_001` — Cancellation creates positive refund entries for every history entry without filtering transaction_type or netting prior refunds. (L/L1,L4)
- `RET_IMPL_CANCEL_GIFT_HISTORY_001` — Gift-card refund accumulation iterates every history amount, including amounts on earlier refund entries. (L/L3,L4)
- `RET_IMPL_EXCHANGE_DEFERRED_001` — Exchange only stores request fields and price difference; it does not replace order.items immediately. (L/L3)
- `RET_IMPL_EXCHANGE_FUNDS_001` — Exchange checks gift-card sufficiency but does not debit/credit balance or append payment history. (L/L3)
- `RET_IMPL_EXCHANGE_SORT_001` — Old and new exchange ID lists are sorted independently when stored, losing original positional pairing. (L/L1)
- `RET_IMPL_EXCHANGE_ROUNDING_001` — Exchange price difference is rounded to two decimals before the balance check and request storage. (L/L4)
- `RET_IMPL_RETURN_DEFERRED_001` — Return records sorted item IDs and refund method without applying refund or changing item inventory. (L/L3)
- `RET_IMPL_RETURN_EXCHANGE_FUTURE_001` — Either request changes delivered status, preventing subsequent return/exchange calls requiring exact delivered status. (L/L2)
- `RET_IMPL_EMAIL_NOT_IMPLEMENTED_001` — Backend registers requests but performs no email sending despite canonical email promises. (L/L6)
- `RET_IMPL_CONFIRM_NOT_ENFORCED_001` — Backend does not enforce prior conversational authentication or confirmation. (L/L6)
- `RET_IMPL_EXCHANGE_SAME_ITEM_001` — Exchange has no explicit old-id equals new-id rejection, unlike item modification. (L/L6)
- `RET_IMPL_ITEM_HISTORY_BEFORE_MUTATION_001` — Payment history and gift-card balance mutate before the sequential item replacement loop completes, without a rollback wrapper in the function. (L/L1)
- `RET_IMPL_PAYMENT_REFUND_BEFORE_LOOKUP_001` — History append and new gift-card debit occur before the old payment method is looked up for refund, without a function-local rollback. (L/L1)
- `RET_IMPL_CANCEL_GIFT_BEFORE_COMMIT_001` — Gift-card balances update during history iteration before order status and refund history are finalized. (L/L1)
- `RET_IMPL_INVENTORY_NOT_UPDATED_001` — Item operations do not change product variant availability in the catalog. (L/L3,L5)
- `RET_IMPL_EMPTY_ITEM_LIST_001` — No minimum item-list length check prevents a zero-item call from appending history and changing status. (L/L6,L1)

## 7. PROTECTED_VISIBLE_SEMANTICS

- 全部 N：认证、用户 ownership、确认、scope、拒绝与 escalation、资格、取消 reasons、支付方式及数量限制、free baggage、add-only、保险和 compensation 规范，包括 API 未 enforce 的规则。
- 全部 D：对象与 ID 区分、status vocabulary、trip/cabin/membership、金额单位、每个 read-result 字段的稳定含义。保持真实当前值可读；字段描述未导出不等于可以删 read-tool 的字段。
- 全部 I：每个 tool purpose、参数含义/type/enum/requiredness、nested payload、direct prerequisite。保留 full reservation payload、kept segments、重复 item occurrence、positional alignment、single-call cardinality。
- 全部 E：primary target mutation、return/exchange request registration、明确的 user-facing promises。资金替换退款承诺与 pending 状态保证按保守边界保留。
- `RET_IMPL_PAYMENT_HISTORY_DIRECT_001`：恰好一个 payment history entry 的直接条件判为 I，即使 canonical 未公开；future invalidation 仍可另列 L2。
- `AIR_IMPL_BOOK_DIRECT_003`：certificate/gift-card allocation balance sufficiency 属于 I；first-use deletion 另列 L3。
- `AIR_TOOL_FLIGHT_UPDATE_KEPT_PAYLOAD_001`：unchanged segments 仍要加入 full list。
- `RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_ALIGNMENT_001` 和各 DUPLICATES units：不能删除 payload 对齐或多重性以改变环境信息条件。

这些是 guardrail，不涉及期望表现。完整保护集合是 JSON 中 `final_visibility == VISIBLE` 的所有 entries。

## 8. DERIVED_REASONING_SEMANTICS

只登记由 canonical policy/interface/transaction representation 支持的推理义务。R 的结论未直接导出，不向 Agent 提供清单、计算答案或恢复算法。

### Airline

- `AIR_TOOL_TRANSACTION_BINDING_001` — Bind the user request to the correct reservation using returned user and reservation identifiers. (R)
- `AIR_TOOL_RESERVATION_AGGREGATION_001` — Aggregate selected per-segment values at reservation scope. (R)
- `AIR_TOOL_PASSENGER_PROPAGATION_001` — Propagate observed passenger cardinality into explicitly per-passenger costs and allowances. (R)
- `AIR_TOOL_HISTORY_RECONCILIATION_001` — Reconcile observed stored reservation values with current flight values for the transaction being discussed. (R)
- `AIR_TOOL_PAYMENT_ALLOCATION_001` — Aggregate supplied payment allocations and compare them to the applicable observed transaction amount. (R)
- `AIR_TOOL_ELIGIBILITY_BINDING_001` — Combine current flight state, booking time, cabin, insurance and reason to apply visible cancellation eligibility. (R)

### Retail

- `RET_TOOL_TRANSACTION_BINDING_001` — Bind the request and payment evidence to the correct order and authenticated user. (R)
- `RET_TOOL_ITEM_MULTIPLICITY_001` — Count requested item occurrences and bind each replacement to its corresponding old occurrence. (R)
- `RET_TOOL_ORDER_AGGREGATION_001` — Aggregate applicable per-item values over requested occurrences for one order. (R)
- `RET_TOOL_HISTORY_RECONCILIATION_001` — Reconcile observed payment/refund entries and profile balances for the intended transaction. (R)

四个要求检查的维度都有 representation 依据：transaction baseline binding（reservation/order/user/payment 的归属）、reservation-level aggregation、passenger cardinality propagation、historical/current state reconciliation。Retail multiplicity 同样来自公开 duplicate/position semantics。

边界限制：源码显示某个历史规则，不意味着 Agent 已拥有这个规则。L4 backend baseline-selection law 不能重新命名成 R；R history reconciliation 仅在相关证据已观察/获知后成立。各 R entry 的 audit_notes 明示输入来源和限制。

## 9. Ambiguities, discrepancies and conservative resolutions

| Finding | Resolution |
| --- | --- |
| Retail future no-modification statement 与 address API substring pending | 保留 normative restrictions；canonical future consequence 记录 L2；实际地址可接受该状态记录 L2/L6，不能虚报所有 API 均关闭。 |
| Policy `pending (items modifed)` vs implementation `pending (item modified)` | 分别保留证据，准确状态值可观察；不改源。 |
| Retail payment description 使用 item-price-difference 文案 | 标记描述与 purpose/body 不一致；payment ID interface 仍 I；实际金额从历史支付取得单列 L4。 |
| Retail exchange price-difference method wording vs no immediate settlement | 文案表达的 secondary settlement 单独列 L1；实现只记录请求、检查余额但不扣款，单列 L3。保留其真实行为，不替换工具结果。 |
| Retail final validation variant reused during item mutation | 静态记录 L1，未运行、测量或修复。不能假装 requested variant 的所有字段都按承诺正确更新。 |
| Retail cancellation iterates all payment history including refunds | L1/L4；没有净额化和 transaction_type 过滤。不是简单“退款等于当前订单总价”的实现。 |
| Airline retained-price matching includes unchanged cabin | Broad Policy assertion 与 exact implementation predicate 分开；cabin change 不能无条件假设保留历史价格。 |
| Airline cancellation ledger vs profile balances / seats | cancellation primary effect E；refund entitlement N；具体未恢复余额/座位 L3/L5。 |
| Airline Policy says flight time local, returned field names/descriptions use EST | 两种 source assertions 均保留并标差异；不静默修正时区。 |
| Human-transfer tool allows explicit request; Policy says iff outside action scope | 两条都是 N/VISIBLE，源间 priority 不在本轮补写。 |
| Return/exchange email promised but no backend email operation | 明确输出承诺保守 E/VISIBLE，backend omission L6；不声称已发送邮件。 |
| Payment replacement refund / pending persistence | 与 primary payment-replacement meaning 紧密，按保守规则保留 E，不扩大 L1 到“没有 mutation”。 |
| Default user address vs order shipping address | 目标 scope 是 I/VISIBLE，不把独立对象含义误当 latent。 |
| Calculator precision / identity lookup matching | immediate representation/matching 行为按 I/VISIBLE 保守登记，canonical upfront 未写明。 |

这些差异需要人工审查具体措辞，但不使实际 source serialization 不明确，也没有强迫改变六类 taxonomy。没有未解决的 HIGH ambiguity；LOW 均附明确定义或保守可见处理。不能把 READY 理解为这些原始实现差异已修好。

## 10. Static integrity verification and provenance

已核验 JSON required fields、knowledge_id 唯一性、合法枚举、默认 role→visibility 映射、L tag 一致性、public-tool 与每个顶层参数覆盖、所有 R 的输入说明、source paths 存在性及 source hashes。摘要表从最终 JSON 生成。没有运行任何 behavioral test 或 benchmark。

四份文件是唯一仓库新增内容；canonical policies、tools、runtime schema 和既有 benchmark 未修改。JSON schema hashes 针对静态序列化对象，source SHA-256 记录下表，不是 context freeze。

| Audited source file | SHA-256 |
| --- | --- |
| `external/tau2-bench/pyproject.toml` | `23d59670b4ad7bbc0f57420fd9643a8d9188c24abe4f29c9c965544d8cc4cb8d` |
| `external/tau2-bench/src/tau2/environment/tool.py` | `6dd74021ba95a6f8dfa0971546b768b90e15b212f8f9051156ae6bcdd24b77d3` |
| `external/tau2-bench/src/tau2/environment/toolkit.py` | `3e897891e8878c3399aec72e42eb0eb5546642420c0c902b225421fc936b924a` |
| `external/tau2-bench/src/tau2/environment/environment.py` | `b5357f11e2914c11ce0372af919cc1d726191b91cd97f776b8fb388ae0615350` |
| `external/tau2-bench/src/tau2/utils/llm_utils.py` | `948e4491bf828d5352f8cd1bb95a0c7799c3c6a6ddfaf9a3a207078c65a5c5d3` |
| `external/tau2-bench/src/tau2/agent/llm_agent.py` | `d13412ff502859f0ef0492af0128f1b2666be32640057ba8e076d2602af084d8` |
| `external/tau2-bench/src/tau2/agent/manual_skill_agent.py` | `9bd86ee44963d189f64a5274fda94bf4ca08ef4ecd752cdd73df7f2c27d7b208` |
| `external/tau2-bench/src/tau2/utils/utils.py` | `e0c39544b01700e60a3a26c7cf2c2d17e37e3852d5f0fa466b8517f82b83622b` |
| `benchmarks/tau2_governed_evolution/compiler/resolvers.py` | `4d1c644d27d8e67ef7143ca012e12ea1235bc7fc74f35d564c8435c886c2ad4a` |
| `external/tau2-bench/data/tau2/domains/airline/policy.md` | `10dc0525421521208be39cee235bba84a16e2bcba9899eb93d92cd81d2f62fc4` |
| `external/tau2-bench/src/tau2/domains/airline/tools.py` | `3987f21c286314cb48764f97052934ff4fd60e27a0b2e4a43423911adf8eaa26` |
| `external/tau2-bench/src/tau2/domains/airline/data_model.py` | `a8083e2f590e4b9b66a65d7cd50b7a0247e4fa33d6961aaeb02e4d92488b3cff` |
| `external/tau2-bench/src/tau2/domains/airline/utils.py` | `9da26327af3d7fa94e05d48869d8b06cd8110313fc24d308993a750106b11f06` |
| `external/tau2-bench/src/tau2/domains/airline/environment.py` | `64589faffbcb75c8ac7c95d2c94ad27f4bd70e23b9856a6928fa678a0f7fcc8d` |
| `external/tau2-bench/data/tau2/domains/retail/policy.md` | `2c9652afbce57d6e087768d37cda64d31c53d50b3e3225cfdb791bac66466467` |
| `external/tau2-bench/src/tau2/domains/retail/tools.py` | `34f4fe9702d36f0dd4697700fbcd63d0cf5386e6eb8e7499aaa336243bad8750` |
| `external/tau2-bench/src/tau2/domains/retail/data_model.py` | `f5ad09590953855cc49d2ab2ad5c0594be408cae74d1500fb278e5a6bf2c50d6` |
| `external/tau2-bench/src/tau2/domains/retail/utils.py` | `a385b085b63d0e5921c15f7e2201b00df1d984990f4dbb7b24a867e3bf7cb648` |
| `external/tau2-bench/src/tau2/domains/retail/environment.py` | `5b819fb895a4ef49df71404c3d9678ab09e8578eec841b8ec9229c8f51e32405` |

## 11. Final review questions

**Q1. Can Airline and Retail be described using the same semantic taxonomy?**

可以。两个域都能以 N/D/I/E 保留规范、对象、interface 与 primary effect，以 L1–L6 描述后台 dynamics，以 R 描述已有证据上的计算与绑定。没有 domain-specific role 或 task-specific visibility 例外。

**Q2. Is there a principled boundary between Tool Interface Semantics and Latent Operational Dynamics?**

有。I 回答“这个 tool/payload 是什么、当前调用直接要求什么”；L 回答“调用还改变哪些状态、资源以后怎样、历史如何影响 settlement、另一个操作因此怎样”。当前 history==one-payment 是 I；其他操作追加 history 导致其失效是 L1/L2。当前 certificate allocation 足额是 I；首次使用删除整个资源是 L3。source-visible 与 role 是独立判定。

**Q3. Does the taxonomy classify S1-like knowledge as latent without using S1 rollout evidence?**

是。如果这里指 action 引发的 secondary mutation 和 future-option invalidation，本地 Retail status/history 写入与后续 guard 已足以支持 L1/L2。这个回答只是把审查问题的名称对应到已完成的静态分类；未读取或使用相关 rollout、任务标签或结果。明确的单次调用与直接 prerequisite 仍保留 N/I。

**Q4. Does it protect S2/S5-style reasoning inputs from being removed?**

是。保留所有对象、标识符、人数、item occurrence、当前/历史 transaction values、完整 itinerary payload、position alignment、normative fees，以及真实 read results。Binding/aggregation/reconciliation 是 R，不用隐藏输入制造 latent knowledge；未知 backend valuation law 另列 L4，不伪称纯算术可推出。

**Q5. Are there additional canonical-visible operational semantics that would become LATENT under the same taxonomy, even though no current benchmark task was designed around them?**

静态发现的额外 canonical-visible 候选包括 Retail cancellation 自动退款及 schema 明示的 gift-card balance replenishment、Retail item/exchange 参数描述中的 secondary price-difference settlement，以及 Airline Policy 中 flight-change/cancellation 的 API non-enforcement 说明。完整清单见 CANONICAL_VISIBLE_TO_PHASE_A_LATENT。

本轮刻意没有查看 task construction 或 selection 内容，所以不能独立断言“现有任务没有覆盖这些现象”；该子句的事实状态未核实。这里列出的仅是从所有 canonical sources 一致分类得到的 static findings，没有设计、建议或选择任务。Refund/payment 的规范承诺与 interface meaning 仍保留，不能整句删除。

`STATIC_SEMANTIC_REGISTRY_VERDICT: READY_FOR_HUMAN_REVIEW`

到此停止。未生成 unified context，未启动后续实验或审计；registry 等待人工审查。
