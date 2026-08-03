# Task 7

- Task score: 0.0
- Process compliance: fail

## Local diagnosis

这条轨迹的主要问题不是取消判断本身，而是 **在明确属于可处理范围的请求上，过早转人工，且未先继续按政策收集并推进必要信息**。

前半段中，Agent 对两个取消请求做了较完整的资格核验：已获取 user id、reservation id、取消原因，并检查了航班状态；据此判断 XEHM4B 不满足取消条件、59XX6W 因有保险而可取消，这部分总体有政策依据。对 59XX6W，Agent 也在执行写操作前先列出动作细节并要求用户明确确认，这一点是合规的。

但随后用户提出“先把 XEHM4B 升舱到 business，再取消它”，这里最关键的高风险点是：**Agent 没有先按“修改舱位”规则继续处理一个本可由自己处理的修改请求，而是直接转人工**。根据政策，basic economy 不能改航班，但**可以改 cabin**；且 cabin change 的前置条件是“任一航段尚未 flown”以及“整张预订统一舱位变更”。轨迹中 XEHM4B 两段航班状态都查到是 `available`，只能证明尚未起飞，因而从已见证据看，**舱位变更请求本身并未超出 Agent 处理范围**。如果要执行该修改，还需要进一步满足并确认：全部航段一起改为 business、确认差价、确认支付方式已在用户档案中、列出动作细节并取得用户明确 yes。Agent 既没有继续收集这些必要条件，也没有说明只能先处理升舱、升舱后取消资格仍不能被预先承诺，而是直接以“不能完全在 policy/tool scope 内解决”为由转人工，这违反了“仅当请求无法在自身范围内处理时才转人工”的要求。

这一行为直接影响任务结果：用户后续还问了“是否还有其他 upcoming flights 以及总成本”，而 Agent 在没有证据表明该问题超出能力边界的情况下中断了会话，导致任务未完成，task score 为 0。相比之下，前面一次并行发起多个工具调用也不合规，但风险和影响低于“错误转人工导致整体任务失败”。

## Evidence

- Event 18：Agent 告知 XEHM4B 不符合自助取消条件；59XX6W 因有 travel insurance 且航班未 flown，可取消，并在取消 59XX6W 前列出动作细节并要求用户回复 yes。
- Policy：取消前必须先获取 user id、reservation id、取消原因；若任一航段已 flown，则需转人工。否则仅在以下任一条件满足时可取消：24 小时内预订、航司取消、business、或有保险且原因受保。任何数据库更新前，必须先列出动作细节并获得用户明确 yes。

- Event 8：XEHM4B 为 `basic_economy`，创建时间 `2024-05-01`，`insurance: no`。
- Event 14-15：XEHM4B 两段航班状态均为 `available`。
- Policy：basic economy 不能改航班；但“在没有任何航段已 flown 的情况下，所有预订，包括 basic economy，都可以 change cabin 而不改航班”。取消规则另行独立判断，API 不会替 Agent 检查。

- Event 19：用户请求“for XEHM4B, upgrade it to business using the card ending in 2135, then cancel it”，并另问“Do I have any other upcoming flights, and what’s the total cost of those?”
- Policy：修改舱位属于 Agent 职责范围；若改舱后价格更高，用户需支付差价；若更低，应退款差额。若是数据库更新，必须先列出动作细节并获得明确 yes。只有“请求无法在 Agent 可执行范围内处理”时才可转人工。

- Event 7：用户档案中存在 `credit_card_2408938`，尾号 `2135`。
- Policy：修改涉及支付时，支付方式必须已在用户 profile 中。

- Event 20-22：Agent 直接调用 `transfer_to_human_agents`，摘要称该组合请求“cannot be fully resolved within policy/tool scope”，随后发送转人工话术。
- Policy：只有在请求无法在自身动作范围内处理时，才应转人工；转人工流程本身需先调用工具再发送固定消息。

- Event 4-6 与 Event 10-13：Agent 在同一轮同时发起 3 个工具调用，之后又同时发起 4 个工具调用。
- Policy：一次只能进行一个 tool call；如果进行了 tool call，就不应同时向用户回复。

## Local lesson

遇到“先修改再取消”这类组合请求时，要把每一步按政策拆开判断：对仍在权限内的修改请求先继续核验全部前置条件并收集确认，不能因为后续取消资格不确定就提前转人工。

## Patch recommendation

- Decision: add
- Location: baseline Skill 中的 `## Learned Rules`
- Content: 遇到组合请求（如“先改舱/改签，再取消”）时，必须按步骤分别判断权限与前置条件；只要当前这一步仍在政策允许范围内，就应继续收集所需信息、说明未决条件并推进确认，不能仅因后续步骤可能不被允许或结果不确定就直接转人工。
