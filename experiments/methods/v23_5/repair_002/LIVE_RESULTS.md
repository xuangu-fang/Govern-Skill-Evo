# Repair v2：R01–R03 单次运行与独立审阅

三轮各调用一次，全部正常结束并通过局部输出、确定性合并及正式 Schema/引用权限校验。三处原始问题均得到修正；R01 新增一处不够准确的空间描述，记录为轻微表述问题。其他 15 条候选 Knowledge 原样保留，没有删除条目，没有写入正式 Memory。

本报告由当前助手在模型返回后独立对照原始记录撰写，不是人工金标准或盲审，也没有增加第二次语义 Verifier 调用。审阅重点是本次修正及其连带影响，不是重新证明所有历史经验。

## 修正效果

| 轮次与位置（零起点） | 实际修正 | 审阅结论 |
|---|---|---|
| R01 `[0,4]` | 将 Q5:49 从返回 drawer 1 的列表中移除，改写为前往 shelf 1；保留 Q5:12/22/35 真实重复访问及长周期循环经验 | 原问题已修复；新增 `within the shelf block` 不够准确，建议收窄 |
| R02 `[0,2]` | 将“水壶可见”改为两次 countertop 1 观察列表均没有水壶，因此不能由这些观察断定错过拾取机会 | 修正有效，未发现新增明显事实错误；新增末步未持物有原始 inventory 反馈支持 |
| R03 `[0,1]` | 将 Parent 普遍先放入设备、循环开关门的概括缩小到 train:0027/0028，并补入 train:0022 的实际开门→冷却→交付记录 | 修正有效；保留真实加热案例、步数改善和因果尚未隔离的限制 |

### R01：核心错误修好，但扩写产生轻微歧义

原文把 Q5:49 列为返回 drawer 1。修正后保留真正的返回步骤 Q5:12、Q5:22、Q5:35，同时补写：

> at Q5:49 it was again moving within the shelf block, going to shelf 1

原始 `Q5:49.before.observation` 是打开 drawer 10 后的观察；`Q5:49.action` 为 `go to shelf 1`。因此目的地现在正确，但 `within the shelf block` 容易让人理解成 shelf 区块内部移动，实际该步是从 drawer 10 转向 shelf 1。

建议只写 `at Q5:49 it went to shelf 1`。这是审阅建议，未替换模型原始输出。按已经约定的“明显、重要事实错误”目标，本项不升级为新的重要错误；同时不将该结果描述为毫无问题的完美修正。

### R02：纠正事实，也移除了错误前提下的推论

P6:1 和 Q6:9 的 after 观察列出 butterknife、knives、ladle、lettuce、pan、peppershakers、spatulas、windows，没有 kettle。Repair 把限制明确放在这些观察上，没有推断整个环境不存在 kettle，也不再保留原来的可见却未拾取前提。

新增“Parent 最后仍未持有物品”来自 P6:50：action 为 `inventory`，after 为 `You are not carrying anything.`。此前关于失败结果与搜索覆盖的段落原样保留；引用列表没有变化。

### R03：收窄概括并保留有效经验

P8:19–25 与 P9:7–13 支持两个加热实例中的放入、开关门、取出、再加热过程。修正开头明确只指这两个任务，并加入 P3:5 开冰箱、P3:6 冷却手持 bread、P3:8 交付的不同模式。

新增引用 P3:5、P3:6 均已存在于冻结 Repair 输入，是 Verifier 反馈提供的原始证据，没有检索新材料后交给模型。步数对比和“变换条款贡献尚未隔离”的限制继续保留。

审阅时额外查看冻结档案中的完整 P3 八步，以澄清 `opened the fridge once`：全轨迹确实只有 P3:5 是开冰箱动作。这份完整轨迹仅用于事后审阅，没有注入 Repair 请求。所提供的相邻两步本身支持开门后冷却的局部顺序，不应据此建立一般性的全程否定规则。

## 调用和成本

模型及参数沿用最近一次 Verifier：`deepseek-v4.1-flash`、medium reasoning、thinking enabled、temperature 1、输出上限 32,768、超时 300 秒。请求直接使用 repair_002 冻结 messages，三轮并发，无重试。运行协议在调用前冻结。

| 轮次 | 输入 Token | 输出 Token | 总 Token | 调用耗时 |
|---|---:|---:|---:|---:|
| R01 | 9,597 | 4,021 | 13,618 | 46.880 秒 |
| R02 | 17,746 | 3,130 | 20,876 | 21.485 秒 |
| R03 | 20,178 | 3,033 | 23,211 | 55.633 秒 |
| 合计 | **47,521** | **10,184** | **57,705** | 并发整体 **56.565 秒** |

输出中包含 8,845 个 reasoning Token，不能再次加到总量中。三次均为 `finish_reason=stop`；费用金额因缺少内部计价信息而未计算。这是本次 Repair 的成本，不包含此前 Replay/Verifier 调用。

## 验证与局限

- 运行器 3 项离线测试通过，覆盖冻结输入接线、原样返回、长度失败、传输失败及未知结果不重发。
- 保存的 HTTP 请求与冻结 messages 一致；归一化 response 与原始 HTTP 响应一致；重新校验实际输出和合并结果通过。
- 3 条授权 Knowledge 都发生修改，删除 0 条，原样返回 0 条；15 条未授权 Knowledge 及 Entry 的 revises 保持不变。历史归档、冻结输入未变化。
- 本次只含三个真实问题，尚未实证验证 Repair 能否识别 Verifier 误判并原样保留正确 Knowledge。允许原样返回的程序分支只通过了结构测试。
- R03 `[0,3]` 的 Verifier 漏检不在授权范围内，仍未修正。不能把本次 3/3 原问题修复理解为整个 Memory 已无错误。
- R01 提醒我们：纠正具体错误时，额外扩写仍可能引入不必要的解释。后续优化应优先控制修改范围；这次不修改冻结 Prompt 或覆盖结果。

## 文件

- 输入包：`artifacts/methods/v23_5/repair_002/`
- 原始请求/响应与逐轮结果：`artifacts/methods/v23_5/repair_run_001/runs/R01|R02|R03/attempts/001/`
- 每轮 `repair_output.json` 是模型真实局部输出，`merged_candidate.json` 是确定性合并候选。
- `structural_usage_summary.json`：可复算的结构与成本统计。
- `adjudication.json`：逐项审阅、修正前后全文及原始证据锚点。
- `protocol.json`、`LIVE_PROTOCOL.md`：运行前冻结的调用与审阅范围。

以上均为独立离线产物，没有启动 Actor、重跑 Replay、发布 Skill 或提交正式 Memory。
