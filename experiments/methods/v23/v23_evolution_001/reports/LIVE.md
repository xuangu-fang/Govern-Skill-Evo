# 报告 B：V23 两轮真实自进化验证

本次已完整执行并发布两轮状态：两轮 Gate 均 RETAIN，最终 Parent=null，Active Memory 为 M1、M2、M3。所有任务、Prompt、代码和参数在启动前冻结，运行中未根据模型表现修改。

## 冻结实验

- 初始 Parent=null，Memory 为空；没有导入此前探索实验的 M1/M2/M3。
- R01：train:0001、0006、0016、0022，分别为灯下查看、简单放置、清洁后放置、冷却后放置。
- R02：train:0002、0007、0017、0028，分别为灯下查看、简单放置、清洁后放置、加热后放置。
- 所有 ID 从现有 Train manifest 读取，实际任务身份与环境文件内容冻结；无 Validation 或 Test。
- Actor/模块均使用现有 deepseek-flash 路由；temperature=1、thinking enabled、reasoning_effort=medium、stream=false。Actor 每任务 50 步，输出上限 16,384，超时 300 秒；模块同输出上限和超时，输入上限 300,000 字符、400,000 UTF-8 字节。
- 上限 2 轮、16 个 episode、800 Actor 步。单步/模块最多三次请求，对应最坏 2,400 次 Actor HTTP、30 次模块 HTTP、39,813,120 生成 Token。正常成功请求不追加采样；本次不自动重跑 episode、不自动 resume。
- 这是请求和 Token 预算，不是货币报价。实际提供方账单未返回时，货币费用记为不可得，不猜测价格或将未知用量当作零。

完整配置见 `config/campaign.json`，成本边界见 `config/budget.json`，程序输出见 `results/summary.json` 和 Campaign 目录。

## 第一轮：完整执行，RETAIN，Memory 正式发布

| 任务 | Parent 状态 / 步数 | Candidate 状态 / 步数 |
|---|---|---|
| train:0001 | success / 4 | success / 4 |
| train:0006 | success / 31 | success / 30 |
| train:0016 | success / 8 | success / 7 |
| train:0022 | success / 7 | success / 30 |

Parent 4/4、Candidate 4/4，Gate=RETAIN。任务成功层面的修复 0、退化 0。Parent 50 步、Candidate 71 步，步数差异不影响 Gate。下一轮 Parent 仍为 null。

Grouping 产生两组：P1/P3/P4 的获取目标后设备操作顺序，以及 P2 的搜索/运输。Diagnosis 给出两项 Update、三项 Check：u1 为获取—交互—放置流程，u2 为搜索纪律。虽然全部成功，P2 的多次重访有实际轨迹支持，Diagnosis 没有仅按任务失败生成更新。

空 Memory 的 Preconditioner 调整 u2，指出原文“work list / not yet examined”依赖完整访问历史，改为仅依据当前观察、最近两对历史和编号递进；同步修改 c2。这属于当前事实和能力约束调整，不能称为历史响应预条件化。

Editor 首次请求生成可严格应用的 22 行新 Skill，落实两项有效 Update。保留了获取目标、设备交互、目的地条件及最近两步历史限制，没有把 Checks 作为独立规则写入。u1 对 slice/heat 等未在本轮实际覆盖的操作进行了扩展，并包含环境本就强制执行的停止条件；程序应用成功不证明这些泛化都合理。未据此修改 Prompt 或 Candidate。

Candidate 的报纸搜索仍有长周期重复：Q2:1–5 检查 shelf 1–5，此后数次返回同组书架和桌面，Q2:27 才发现报纸；Parent 在 P2:28 发现，整体仅 31→30 步。冷却任务的 Candidate 先检查大量柜子并打开多个容器，之后才在 countertop 发现面包；Parent 直接到 countertop，整体 7→30 步。这些是真实联合编辑后的配对差异，单次随机轨迹不能确证独立因果关系。

Replay 首次请求形成两条真实 Memory，程序保存为本 Campaign 的 M1、M2：

- **M1：** 获取—设备操作—放置指导与若干成功行为兼容；清洁任务中目的地开门时机不同仍成功。原 Parent 也成功，因此不能归因为新增流程导致成功。
- **M2：** 最近历史/编号搜索未消除长周期重访，且冷却任务中观察到大量柜子探索后的延迟；记录 30 对 31、30 对 7 的具体配对响应，保留样本少、联合编辑和非因果限制，不建立普遍的容器优先级。

M1 的“简单发现目标”适用范围应主要理解为灯具和清洁片段，不能将它引用的冷却任务也概括为 Candidate 快速找到目标。M2 提到目标实际所在表面属于 Replay 后见事实，不能在下一轮据此假设 Actor 在观察前已知物体位置。两条认识的完整文本、证据及 Archive 均保留原样。

发布状态为 `next_round=2, parent=null, active_memory=rounds/R01/memory`。第二轮 round_input 已读取这两条真实 Memory及其原始来源。Gate RETAIN 没有阻止有效 Replay 认识跨轮保存。

## 第二轮：真实历史 Memory 的消费与语义核查

Parent 仍为 null，开始时的 Memory 精确等于 R01 已发布的 M1/M2 和来源。Parent 四条均成功：train:0002 为 21 步、0007 为 10 步、0017 为 11 步、0028 为 15 步，共 57 步。

Grouping 最终形成三组：灯具条件、铅笔搜索和清洁/加热后放置。Diagnosis 产生两项 Update、两项 Check：u1 避免对不变对象重复无信息检查并建立所需条件；u2 为搜索—转换—放置。

Preconditioner 实际引用 **M1、M2** 修改 u2，提出先检查可直接观察内容的开放表面，再打开关闭容器，并限定设备只有在交互确实需要时才先打开；保留 u1。Checks 同步替换，Effective Plan 由程序继承原 Goal/basis 并编译。Editor 首次请求成功生成第二份 22 行 Skill；因为 Gate 第一轮 RETAIN，实际 Patch 仍是从 null 创建，并非在第一轮 Candidate 上追加。

这是一次真实的跨批次历史认识消费和非恒等更新构造，但存在以下语义限制：

- **当前与历史事实混淆。** 有效 Adjustment 的 reason 写道“Current P3 opens drawer 1 ... knife”，该事件来自第一轮 P3；当前 P3 实际为生菜/餐桌任务。结构校验通过不代表引用的自然语言解释正确，模型错误保留原样。
- **作用尺度扩张。** M2 明确保留不能推出普遍表面/容器排序的限制，新的 u2 将其扩展为较强的“first ... only then ...”优先级。历史柜子搜索延迟和当前搜索片段为尝试这一路径提供动机，但不足以证明该顺序对所有任务更优。
- **有限历史边界仍不完全清楚。** u2 对“刚检查过”的避免有最近历史依据；对长周期重复的禁止仍可能超出 Actor 可辨认范围。
- **灯具必要条件未证实。** 当前 P1 最后执行放下 CD、开灯、再取回后成功，只说明该顺序发生；第一轮持有 CD 直接使用灯也成功。u1 保留“if necessary”，但不能把放下物体解释为已证实的必要条件。
- Editor 基本落实有效 Update 的条件与顺序，未自行消除上述策略问题；这符合实施职责，但补丁通过不等于策略有效。

## 实际技术重试

R01 五个模块均首次通过。R02 共记录三次失败，均在相同请求的第二次尝试通过：

| 阶段 | 第一次失败 | 后续处理 |
|---|---|---|
| Grouping | `shared_basis lacks a decision-step reference for P1`：原文写“P1 steps 17-21”，未使用规定引用形式 | 原样保存；相同请求第二次通过 |
| Preconditioner | `reason: unavailable historical reference`：自然语言中的“P3/P4”触发历史引用解析 | 原样保存；相同请求第二次通过 |
| Replay | `evidence: invalid references`：引用当前 Q4:21/22/25/26/28/30，但当前 Q4 只有 15 步；这些编号与上一轮 Q4 的范围混淆 | 原样保存；相同请求第二次通过 |

Preconditioner 首次错误包含引用解析歧义，不能直接描述为模型虚构历史。没有修改校验器、自动修复文字或向第二次请求追加反馈。两侧 request.json 经逐值比较完全相同。被拒绝输出消耗纳入总成本，第二次通过仅代表结构与引用契约通过，不证明自然语言判断更好。真实运行尚未触发三次耗尽或人工 resume；这些路径由离线故障注入验证。


## 第二轮执行、Replay 与最终发布

| 任务 | Parent 状态 / 步数 | Candidate 状态 / 步数 |
|---|---|---|
| train:0002 | success / 21 | success / 30 |
| train:0007 | success / 10 | success / 11 |
| train:0017 | success / 11 | success / 19 |
| train:0028 | success / 15 | success / 15 |

两侧都是 4/4，Gate=RETAIN。修复 0、退化 0（按最终成功状态），步数 57→75。灯具任务的 Candidate 仍重复检查和放下/取回物体；清洁任务仍多次搜索和重访；加热任务在微波炉中放入鸡蛋后反复开关，取回后才执行 heat。原 Parent 在持有鸡蛋、微波炉关闭时直接 heat 成功。不能把原始 Plan 或已应用 Patch 当成实际行为落实证明。

Replay 第二次输出一条新增认识（revises=[]），程序分配 **M3**。它描述联合新 Skill 保留最终完成，但未可靠消除重复检查和循环，并可能伴随额外容器操作；明确保留联合编辑、随机性和非因果限制。M1/M2 未被撤下或覆盖。真实实验观察到跨轮新增，没有观察到旧条目修订；修订与合并能力由离线测试覆盖，不能冒称真实已经验证。

M3 仍存在事实概括错误：末尾称“targets already at the destination were not tested”，但本轮生菜原本就在目标餐桌、鸡蛋原本就在目标台面。这两个条件实际出现过。该条目也同时概括多个行为问题，粒度偏宽；不应将它视为已经充分可靠的长期规律。原模型输出和已提交认识保留原样，未增加自动审核或人工改写。

最终一次性发布：

```json
{
  "next_round": 3,
  "parent": null,
  "active_memory": "rounds/R02/memory"
}
```

next_round=3 表示两轮计划完成，没有启动第三轮。两份 22 行 Candidate 都保留为实验产物，没有晋级为正式 Parent。Archive 中保存两次不可变提交，最终 Active 为 M1、M2、M3。上一轮 Active 索引仍为 M1/M2，不被第二轮准备操作改写。

## 消耗、复用与档案核验

| 范围 | Actor HTTP | 模块 HTTP | 已知总 Token | 其中推理 Token |
|---|---:|---:|---:|---:|
| R01 | 121 | 5 | 237,652 | 55,737 |
| R02 | 132 | 8 | 598,251 | 195,132 |
| 总计 | 253 | 13 | 835,903 | 250,869 |

输入 Token 557,204，输出 Token 278,699。推理 Token 是输出的子集，未重复相加。16 个 episode 共 253 个已执行步骤；Actor 无 HTTP 重试，13 次模块请求包含 10 次合法结果和 3 次契约失败。三次失败消耗分别为 Grouping 20,789、Preconditioner 59,224、Replay 75,611，总计 155,624 Token，已包含在总量内。所有请求 usage 可得，未知请求用量数为 0；响应没有货币账单，实际金额未知。

从首次 Campaign session 到最终发布约 **1,593.78 秒（26 分 34 秒）**。没有技术重试耗尽，没有用户 resume，没有中途修改请求、Prompt、代码或预算。

完成后用必定拒绝任何模型/Actor 调用的函数再次进入同一 Campaign，直接返回 complete，正式 state.json 字节不变。另对十个合法模块结果执行原有读取校验、253 份 Actor HTTP 归档执行原文/usage 核验，均通过。引用现有 Gate 保护清单核验 423 个旧档案未变。复用和核验材料见 results/completion.json、verification.json；未通过增加真实请求验证恢复。

## 交付结论与证据边界

- **统一调度串联：** 已在真实运行中完成全部模块两轮串联，并保持冻结输入与原子状态发布。
- **Gate 推进：** 两轮真实正确 RETAIN；ACCEPT 后采用 Candidate 的路径已离线验证，本次真实没有触发。两轮 Parent 都已 4/4，严格成功数规则下没有可增加空间。
- **跨轮 Memory：** 真实从空到 M1/M2，再到 M1/M2/M3；旧认识未覆盖，Archive/Active 一致。真实修订尚未发生。
- **历史消费：** 第二轮 Preconditioner 确实读取第一轮原始来源并引用 M1/M2 调整 u2；但存在当前/历史事实混淆和策略范围扩张，不能认定调整质量已经得到证明。
- **恢复与复用：** 离线验证故障、三次停止、显式 resume、部分 Actor 重开与统一发布；真实验证了三次独立技术失败后的有限重试及完成后零调用复用，没有实际人工 resume。
- **效果证据：** 两轮成功数量均不变，Candidate 总步数 146 对 Parent 107。没有独立空 Memory 对照或重复随机试验，不能将差异完全归因于 Memory，也不能宣称泛化或持续进化收益。非空 Parent 上的跨轮局部编辑、本轮未触发的 ACCEPT、真实旧认识修订，以及更长期冻结实验、消融与最终独立 Test 仍需后续验证。

本次止于两轮完成。未运行第三轮、Validation 或 Test，未修改已生成的模型结果，不因语义问题重采样。
