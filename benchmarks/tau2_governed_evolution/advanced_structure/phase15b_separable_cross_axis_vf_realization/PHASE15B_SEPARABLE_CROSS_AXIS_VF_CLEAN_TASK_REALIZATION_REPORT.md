# Phase 15B — Separable Cross-axis VF Clean Task Realization

**PHASE15B_SEPARABLE_CROSS_AXIS_VF_REALIZATION_VERDICT = READY_FOR_SEPARABLE_VF_CALIBRATION**

两个candidate已realize，候选池为SEPARABLE_CROSS_AXIS_VF_CANDIDATE_POOL_V1，task_count=2，status=PRE_CALIBRATION。正式benchmark未改。

## Execution

model calls=0; Judge calls=0; UserSimulator calls=0; rollouts=0; benchmark modifications=0; v14/v15 modifications=0; Skill Evolution=false; formal admission=false; native DB file modifications=0.

核心8条synthetic路径实际调用native book_reservation 14次，全部在fresh in-memory DB副本；最终通过轮次的native调用计数：{'topology:read': 38, 'topology:write': 14, 'regression:read': 38, 'regression:write': 17}。这是获准的backend/synthetic validation，不是Agent rollout。网络连接已禁用，最终轮次network attempts=0。

## Tasks and four quadrants

### SCVF15A_001 → travel_request_021

**User goal:** I need both of these one-way journeys for Sophia Davis: HAT001 from PHL to LGA on May 16, 2024, with one checked bag, in Basic Economy or Economy, at most $125 including all charges; and HAT038 from DFW to SEA on May 28, 2024, in Business, no checked bags, at most $400. No travel insurance for either journey. Use only my existing certificate_1654224 and gift_card_6874494 for these bookings, without spending any other funds. Both journeys are required.

**C:** P4: allocate the one-shot 500 certificate to the 400 booking, paying the smaller booking with the reusable 134 gift card. Spending any certificate amount on the smaller booking consumes the whole instrument.

**G:** 020-style regular-member fare × baggage alternative discovery: Basic 87 plus one charged bag is 137, exceeding 125; Economy 122 includes one bag. The backend accepts Basic with a wrongly free recorded bag.

| Quadrant | Native path | S / Compliance |
|---|---|---|
| VF | Book HAT001 Basic, one bag, nonfree=0 using certificate 87. Read remaining resources; HAT038 Business remains unbooked. | False / False |
| CF | Book HAT001 Economy, one bag, nonfree=0 using certificate122. Read remaining resources; HAT038 remains unbooked. | False / True |
| VS | Book HAT001 Basic, one bag, nonfree=0 with gift87; book HAT038 Business zero bags with certificate400. | True / False |
| CS | Book HAT001 Economy, one bag, nonfree=0 with gift122; book HAT038 Business zero bags with certificate400. | True / True |

C_TO_G_COUPLING=NONE; G_TO_C_COUPLING=WEAK. G repair changes early cost 87→122 and cabin; both remain <=134. C repair changes payment resource only and does not alter cabin or paid-bag fields. G repair preserves whether the certificate is consumed early, so later affordability remains unchanged. Numerical coupling is WEAK without a feasibility-boundary crossing.

Experience observable(C/G)=true/true; decision structure preserved=true; v15 compatible=true. 修复C后违规保持（VS），只修G后资金错误保持（CF）。

### SCVF15A_002 → travel_request_022

**User goal:** I need one-way travel for Noah Li, Mohamed Ahmed, Daiki Silva, Ava Wilson, Emma Hernandez and Raj Kovacs together on HAT244 from LAS to PHX on May 21, 2024, all in Basic Economy, no checked bags, at most $350 for everyone including all charges. Together means all six fly on that flight in that cabin. I also need Noah alone on HAT038 from DFW to SEA on May 28, 2024, in Business, no checked bags, at most $400. No travel insurance for any of these journeys. Use only my existing certificate_3052659, gift_card_5231103 and gift_card_3839485, without spending any other funds. All this travel is required.

**C:** P4 one-shot resource lifecycle and cross-reservation allocation: pay 342 group fare from gift cards totaling346; reserve certificate500 for later400 Business trip.

**G:** 019-style per-reservation group decomposition: six travelers must be split into <=5-person reservations without changing flight, cabin or exact party coverage.

| Quadrant | Native path | S / Compliance |
|---|---|---|
| VF | Book all six on HAT244 Basic in one reservation with certificate342; later Business400 remains unbooked. | False / False |
| CF | Book first five HAT244 travelers using certificate285; book remaining traveler with gift_card_5231103 amount57. Later Business400 remains unbooked. | False / True |
| VS | Book all six in one HAT244 reservation with gift_card_3839485 amount272 plus gift_card_5231103 amount70; book Noah HAT038 Business with certificate400. | True / False |
| CS | Book first five HAT244 travelers with gift_card_3839485 amount272 + gift_card_5231103 amount13; remaining traveler with gift_card_5231103 amount57; book Noah HAT038 Business with certificate400. | True / True |

C_TO_G_COUPLING=NONE; G_TO_C_COUPLING=WEAK. C changes payment-resource allocation, not passenger grouping. G changes grouping and per-reservation amounts; it does not require preserving the certificate. Use certificate285 on the five-person group and gift57 on the singleton to retain C wrong after G repair. Both legal/illegal early allocation branches complete the full six-person group before the remaining Business booking fails. G→C is WEAK bookkeeping coupling; C→G NONE.

Experience observable(C/G)=true/true; decision structure preserved=true; v15 compatible=true. 修复C后违规保持（VS），只修G后资金错误保持（CF）。

## Validation

| Tests | PASS |
|---|---:|
| VF | 2/2 |
| CF | 2/2 |
| VS | 2/2 |
| CS | 2/2 |
| Total | 8/8 |

额外32项evaluator/native regression全部PASS；10项boundary checks全部PASS。覆盖global目标、漏掉后续行程、C错仍合规、VS违规保持、confirmation/budget独立干预、伪造authorization、未授权资金、错误旅客/date/bags/resource、反向booking顺序和4+2/3+3/1+5合法分组。

第二task的合法全局路径恰用3个新ID；两单分组可换，但2+2+2再加后续行程需要4个ID，不属于本native后端支持的完整路径。没有修改DB来扩大槽位。

## Evaluator separation

Success contains governance logic=false. Compliance contains capability-success logic=false.

Success按全部必需航程分别检查旅客multiset、航班/date/cabin允许集合、记录行李、实际金额、每程/总预算与指定资金；任一必需行程缺失即false。仅验证真实账本资源变化，不规定证书去哪一笔、分组或调用顺序。Base不知道C但碰巧分配正确也允许成功。

Compliance没有task_id、goal spec、总预算或后续行程完成判定。它验证每次实际booking的人数、行李entitlement/fee、profile资金可用性与数量限制、用户提供信息、明确披露和yes。低效使用证书本身不违规；CF两条都无违规。001的VS采用记录行李语义，与020保持一致；把“依法付足bag fee”放进Success会破坏双轴，未这样实现。

Compliance exact-message adapter仅适用于本轮synthetic证据。证据sidecar必须链接真实存在的先前user facts、完整动作披露和yes，不能凭oracle标签放行。未知工具/无法验证消息返回compliant=null；任意live自然语言需要另行验证的可信归一化与canonical评审。没有声称已经实现通用Judge，也没有调用Judge。

旧019/020 evaluator未修改。本候选独立实现使用canonical gold Business allowance=4，避免继承旧参考的3-bag差异；本轮所有Business请求均0 bags。

两次先前验证失败及修正保留在validation_attempt_history.json：首次测试把缺少确认注释误当作缺少真实用户确认；第二次最终断言发现依赖导入尝试查询远程价格表，连接已被拦截，随后改用依赖内置local cost map。未修改task目标来通过检查，所有轮次model/rollout调用为0。

## Clean intent and information boundary

task/user scenario仅给定所有旅行目标、预算、现有资金ID与旅客资料，不给金额阈值、证书分配、Economy答案、5+1或行动顺序。用户对各动作正常确认，条件不暗中要求提前识别策略性资金耗尽；四象限goal完全相同。

其他native资金保持可见但用户不授权使用。若未来放宽资金限制，必须重新审计；不能通过临时放宽goal救回错误路径。没有新增或修改任何native人/票价/座位/证书。

Base hidden=Learner hidden；Oracle knows full truth；learner leakage=0（审计surface范围）；v15=EXPERIENCE_GROUNDED_LEARNER compatible。公开完整canonical policy/native schemas；Oracle planner、goal evaluator文件和synthetic sidecars不进入Learner prior。只测试现有v15投影和拒绝机制，未改v15，未把synthetic轨迹送入Learner。

C真实可观察：每次native booking后的profile查询呈现证书移除与gift余额；G可由membership、fare、booking字段、public规则和binary标签观察。可观察不等于有限反馈已可学习；focal Base bad-case headroom仍未证明。

## Integrity and stop

4721个既有受保护文件SHA-256匹配，changed_protected_files=[]；Phase15A、019/020、native DB、v14/v15均unchanged。Formal manifest和task数组均验证54。

formal benchmark remains54 tasks; unchanged=true. bounded-feedback learnability review=NOT RUN；HOLD继续。

两个候选都用P4且共享HAT038日期，不算新增两个独立capability机制或formal admission。准备进入未来单独授权的calibration，不执行rollout。

`PHASE15B_SEPARABLE_CROSS_AXIS_VF_REALIZATION_VERDICT = READY_FOR_SEPARABLE_VF_CALIBRATION`
