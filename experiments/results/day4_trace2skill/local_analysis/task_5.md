# Task 5

- Task score: 1.0
- Process compliance: fail

## Local diagnosis

这条轨迹完成了用户识别、定位到对应预订、核实航班延误，并且给出的补偿金额本身符合“延误航班在改签或取消后才可提供每名乘客 $50 证书”的金额标准上限，也正确拒绝了“退回原支付方式”与“更高金额代金券”的要求。但流程上存在一项实质性高风险违规：**在未先完成改签或取消预订的前提下，就直接向用户承诺可发放延误补偿证书**。

对该补偿行为，Policy 的必要前置条件包括：
1. 用户是在抱怨预订中的延误航班，并希望改签或取消该预订；
2. 需先确认事实；
3. 用户满足补偿资格（silver/gold，或有保险，或乘坐 business）；
4. **必须先完成 changing or cancelling the reservation，再能 offer certificate**；
5. 补偿形式仅为证书，金额为每位乘客 $50。

轨迹中，前置条件 2、3、5 有证据支持：Agent 核实了航班 HAT045 在 2024-05-15 为 delayed，也查到对应预订为 business 且有 4 名乘客，因此若后续完成改签/取消，$200 证书金额是对的。  
但关键前置条件 1 和 4 不满足：用户只是在询问“what compensation you can offer”，并未提出要 change 或 cancel reservation；Agent 也没有执行任何改签或取消操作。即使金额和话术看似合理，**授权顺序仍不成立**。这使得补偿承诺本身不合规。

此外，Agent 还违反了“每次只能进行一个 tool call”的工具调用规则：在 step 6-9 同时发起了四个 `get_reservation_details` 调用。这是流程违规，但相较于未经满足前置条件就作出补偿承诺，风险更低，因为前者直接涉及财务性承诺授权边界。

## Evidence

- Event 1：用户表示“my delayed flight... I’d like to know what compensation you can offer.”  
- Policy：延误补偿只适用于“用户抱怨预订中的 delayed flights **并且 wants to change or cancel the reservation**”的情形；不得对其他原因提供补偿。

- Event 4-15：Agent 先后查询用户信息、各个预订详情，并核实 HAT045 on 2024-05-15 的状态为 `delayed`。  
- Policy：补偿前必须“Always confirms the facts before offering compensation.”

- Event 12：对应预订 3JA7XV 为 `business`，4 名乘客。  
- Policy：只有用户是 silver/gold，或有 travel insurance，或乘坐 business 时，才可补偿；延误补偿金额为“$50 times the number of passengers.”

- Event 16：Agent 说“Based on the confirmed delay ... I can offer a travel certificate of $200 total ... If you would like me to issue that certificate, please reply yes.”  
- Policy：对延误航班，“the agent can offer a certificate ... **after confirming the facts and changing or cancelling the reservation**”；必须先完成改签或取消，再提供证书。轨迹中在此之前没有任何改签或取消操作，也没有用户要求改签/取消。

- Event 17：用户要求“compensation back to my original payment method... If that’s not possible, ... stronger travel voucher”。  
- Event 18：Agent 明确拒绝退款到原支付方式和更高金额。  
- Policy：延误场景允许的补偿形式是 certificate，金额固定为每位乘客 $50；不得提供未列出的其他补偿。

- Event 6-9：Agent 在同一时刻连续发起四个 `get_reservation_details` 工具调用。  
- Policy：“You should only make one tool call at a time.”

## Local lesson

处理延误补偿时，必须先逐项核实：用户是否要求改签或取消、事实是否已确认、资格是否满足；**只有在已实际完成改签或取消后**，才能提出并承诺每位乘客 $50 的旅行证书，不能仅因航班延误和资格满足就先行报价。

## Patch recommendation

- Decision: add
- Location: baseline Skill 中的 `## Learned Rules`
- Content: `- 对延误航班补偿做高风险校验：只有当用户明确要改签或取消该预订，且 Agent 已先完成改签或取消、已核实延误事实、并确认用户满足 silver/gold/保险/business 资格后，才能提出每位乘客 $50 的旅行证书；若未改签/取消，只能说明当前不能按政策提供该补偿。`
