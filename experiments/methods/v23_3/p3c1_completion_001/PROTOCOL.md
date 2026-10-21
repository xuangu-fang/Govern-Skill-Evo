# P3-C1 结项分析协议与实际执行范围

本目录在全部 12 条任务正常结束后补齐分析，**不是执行前预注册**。原先的协议、评价标准和新 Train 清单仍以 [原始 PROTOCOL](../p3c1_r05_replay_001/PROTOCOL.md)、[freeze.json](../p3c1_r05_replay_001/freeze.json) 为准。本轮只读重载结果、复核证据并新增报告；模型调用 0、环境运行 0。旧报告保留中断时的事实，最终结论以本目录为准。

## 输入与方法边界

沿用 `memory_v3_integration_001` 的唯一 Original、Parent、Memory v3 与真实 A/B 输出。A 自由替换修改 u1/u2，u3 Keep；B 全部 Keep，Effective 等于 Original，未生成 Update Patch。没有重新生成 Diagnosis/Preconditioner，也没有人工修改 Update、Editor Patch 或 Candidate。

原 V23 Editor 的输入构造、解析、校验、Patch 应用和重载用于两组。重新执行 `load_editor` 证明两组 raw→parsed→Candidate→actual.diff 一致；输入唯一不同字段是 `plan`，同一系统 Prompt 与模型参数。B 的 Keep 仍把 Diagnosis 提出的更新交给 Editor。比较的是两个已生成方法结果的端到端表现；不把它解释为单独 Unified Diff 格式的因果效果。

## 固定任务及执行条件

| 编号 | task_id | 真实任务请求 | 环境实例 trial |
|---|---|---|---|
| P3 | val:0003 | put some mug on sidetable. | T20190909_032318_169393 |
| P6 | val:0006 | put a clean butterknife in drawer. | T20190908_052007_212776 |
| P7 | val:0007 | clean some butterknife and put it in drawer. | T20190909_124425_112757 |
| P10 | val:0010 | cool some apple and put it in microwave. | T20190906_210937_878489 |

完整规范路径与来源在 [tasks.json](../p3c1_r05_replay_001/tasks.json)。四条均为 R05 已参与设计的 valid_seen/val 开发实例，不是新 Train 或最终 Test。P3 的本次实际轨迹很短，不因为此前研究给它贴过“循环”标签就宣称本轮也循环。

历史外网 `deepseek-flash` Parent 与本次内网配置/实现不能证明等价，因此使用本轮重新执行的 Parent。所有最终轨迹统一内网 `deepseek-v4.1-flash`、temperature=1、thinking enabled、reasoning_effort=medium、max_tokens=16384、stream=false；环境 seed=42，50 步上限，最近两对动作前观察/动作历史，单 Episode 固定 Skill。候选只过滤精确 `help`，不强行纠正模型输出。Editor timeout=(60,300)，Actor=(10,300)，单决策一次传输尝试；参数详见原 [config.json](../p3c1_r05_replay_001/config.json)。实际版本及协议按存档核验。

重新通过 8 组 Parent–Candidate 和 4 组 A–B 的 `verify_pair`，并核对 request_policy 与执行源码摘要。可核验的任务、环境初始观察/菜单、模型参数、协议一致；后续轨迹自然不同。相同环境 seed 不代表模型采样或服务器状态完全确定。

## 重启授权与选择规则

最初冻结的是 12 Episode、不自动重启。随后用户明确授权对 429/网络中断重启、最多三轮的阶段性尝试、恢复与 V23 一致的最多四路并行，之后又明确要求补完最后的 Parent/P7，并在网络恢复后继续。**这些是执行中追加的技术恢复授权，不能倒写为最初协议。**

保留各条件最早正常结束的一条轨迹；`step_limit` 是正常的行为失败，不重跑择优。中断轨迹全部保存并计成本，但不拼接进最终行为统计。独立重算全部 25 次 Episode 尝试，只有 12 次正常结束，最终选择均为该条件首次正常结束；未发现因语义失败替换结果。重启时 reset 重开，不是从中断处接续动作。

| 归档阶段 | 完成/异常概况 |
|---|---|
| 原始 replay_001 | 5 条正常结束，4 条 429 中断，3 条未启动 |
| restart_001 | Parent/P7 再次 429 |
| restart_002 | 按追加授权恢复；最终补齐 6 条 A/B。一次并行切换遗留 worker 被终止，单列工程中断；Parent/P7 仍 429 |
| restart_003 | Parent/P7 分别遭遇 429、ReadTimeout、ConnectionError；网络检查失败，无正常结果 |
| restart_004 | 网络恢复后 Parent/P7 正常运行 50 步，以 step_limit 结束，补齐最终 12 条 |

重启改变了时间与实际并发安排，且温度为 1；可作为已核验条件下的小规模配对观察，不能宣称消除了模型随机性、服务负载或时间混杂。

## 评价与成本口径

遵循原冻结标准：原生成功、步数、位置/类别/实例覆盖、重复与无信息动作、合法性、精确目标、必要处理与交付、预算和退化。先逐组记录，再比较 Parent→A、Parent→B、A→B。动作数或少改几行均不单独等于质量。

“同位置且相同返回观察的重复导航”是描述性代理，可能漏计第一次打开后的重返，也可能把拿到目标后的必要回返计入；必须结合任务阶段解释。搜索覆盖以实际访问/打开及可见候选为准，不读取隐藏答案判定目标位置。

全部尝试共 480 Actor 决策/客户端传输尝试，仍在原 600 决策上限内；加 2 Editor 共 482 次客户端传输尝试。DNS/连接错误不等于服务端实际收到 HTTP。总 Episode 尝试已由追加授权扩至 25，不宣称仍只执行了 12 次。行为统计只使用最终 229 个已执行动作；成本含全部中断前缀的 467 个执行动作及失败请求。

本轮未运行新 Train、Test、Gate、Memory 更新、完整进化或 D/S/C 实现。所有结果来源和可复算检查见 [validation.json](validation.json)、[costs.json](costs.json)、[audit.py](audit.py)。
