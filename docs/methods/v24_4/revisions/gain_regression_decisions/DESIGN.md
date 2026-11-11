# v24.4 Preconditioner 对历史收益与退步的判断

同一种动作偏好曾在不同任务中带来收益和退步时，Preconditioner 用准备交给 Editor 的同一段文字，分别检查一条相关收益记录和一条相关退步记录。以各自记录能支持的最早决策为准，列明 Actor 在动作前可见的条件，以及这段文字会提高或降低哪个动作的优先级。事后找到目标的位置只能解释结局。较晚的兜底规则需要有证据支持 Actor 能够进入并执行它，才能算作对较早风险的修正。

## 决定与交接

- **KEEP** 适用于 Original 已能利用可观察条件保住有用选择的情况。历史退步关联较弱时，当前轨迹也可以独立支持保留。
- **REPLACE** 适用于能用证据收窄触发条件、改变优先级或降低规则强度，而且修改相对 Parent 仍会改变具体选择的情况。决定依据放进 reason，Actor 真正要用的条件写进 text。
- **WITHDRAW** 适用于相同可见条件下两种选择各有根据，且在 Original 范围内找不到一条有实质行为差异的修正。每条 Original 独立判断。

沿用已有的 adjustments 接口，完整英文提示词在 [preconditioner.md](../../../../../src/skill_evolution/v24_4/revisions/gain_regression_decisions/prompts/preconditioner.md)。训练和观察的对照版本是 [historical_attempt](../../../../../src/skill_evolution/v24_4/revisions/historical_attempt/prompts/preconditioner.md)。

## R05 开发验证

使用 20261107_135247 正式训练事先归档的 R05 Parent、Original、引用轨迹、可选命令和 Memory。只改首次请求的系统提示词中关于历史失败的一段。先逐条比较有效 Update 的实际动作优先级，实质不同且能生成 Candidate 时，再复用该轮 Parent 结果，按原批次运行十题及 Replay、Gate。退回 Parent 可以体现预条件的取舍；单批结果不能估计独立 Test 收益。
