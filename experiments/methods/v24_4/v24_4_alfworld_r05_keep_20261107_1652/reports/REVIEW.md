# R05 Preconditioner 单次快检

复用正式 R05 的 Parent、Original、当前轨迹、命令和 Memory。三次调用（正式版、上次快检、本次快检）的输入文件、调用参数和首轮用户消息一致。相对上次快检，系统提示词只有 KEEP 段发生变化。模型第一次回复即通过原有输出校验。

| Update | 正式 R05 | 上次快检 | 本次快检 |
|---|---|---|---|
| u1 防止回访 | WITHDRAW | WITHDRAW | REPLACE，打开并检查后，以最近检查为基准判断内容是否再变。保留了耗尽未访位置时的 inventory 兜底，本批失败没有为该兜底提供直接验证。 |
| u2 搜索顺序 | REPLACE | KEEP | REPLACE，查一个封闭容器，查一个抵达即可看到内容的新位置，然后接回下一个未查封闭容器。 |

u1 收窄了 Parent 关于开门后状态变化的例外，针对已有轨迹中的重复回访。u2 相对上次形成了实质选择差异：从一个封闭容器切出去后，下一个封闭容器获得明确的回程优先级。但 M6 的成功动作是从台面直接去餐桌（两个开放位置），M7 的成功分支是沿台面查到 3 号。模型自己的理由在 P10:2 会从第一个台面转去封闭容器。早期先到开放位置时，有效文本对该选择的起点也不如理由明确。因此 Memory 支持更早恢复有效搜索的动机，却没有验证固定的一比一交替能够兼容这些分支。M7 的翻转归因为空，仅用作行为证据。

本次仅执行 Preconditioner，Candidate 执行数为 0，无 Gate 或成功率。保留原正式入口。

[本次模型输出](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/preconditioner/result.json) · [冻结输入](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/preconditioner/input.json) · [上次模型输出](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_gain_regression_20261107_1637/preconditioner/result.json)
