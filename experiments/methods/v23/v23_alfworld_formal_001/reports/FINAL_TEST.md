# V23 ALFWorld 正式 Test：S0 与 S1

状态：**正式对照已完成**。S0/S1 各 134 条；首次技术停点与本次明确恢复的原始证据均保留。最新完整统计见“正式完整结果”，前面的停点数据是历史记录。

## 冻结设置与范围

两组使用 `data/test.json` 的同一 134 条任务，保持原始顺序；与本轮 57 条优化任务按 gamefile 核对无交集。公开清单来源、真实本地路径和早期开发接触记录见本实验 `PREPARATION.md`、`data/prior_test_execution_inventory.json`。

S0 不注入 Skill。S1 通过 `evolution.final_parent()` 验证六轮提交链后读取 `S1/rounds/R05/editor/attempts/001/candidate.md`，不会选用 R06 Candidate。只注入该 Skill 正文，不注入 Memory、Plan 或更新模块信息。

两组使用冻结的 `protocol.json`、`no_skill_eval.json`、`v23_eval.json`：deepseek-flash、相同 API 路由、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、300 秒读取超时；当前观察、候选动作及最近两组历史；环境 seed=42、单任务最多 50 步。环境版本 alfworld 0.4.2、textworld 1.7.0、numpy 1.26.4、requests 2.32.5 已静态核对。

正式执行先 S0、再 S1，最大 8 个并行 Episode，复用既有 `_actors()` 和 `run_task_skill.py`。每任务独立子进程、环境、历史和输出目录。任务内动作顺序执行，结果按冻结 Test 顺序汇总。输出位置改为用户授权的 `evaluation/S0` 和 `evaluation/S1`，原准备配置文件不改写。

首次请求加最多两次技术重试完全由既有 Actor 负责，评估器不增加外层重试。技术失败停止整项评估，已启动任务保存真实结果；显式 resume 只重启未完成任务，保留旧部分轨迹，完整任务零调用复用。

## 实现与离线核验

最小运行入口：`experiments/methods/v23/v23_alfworld_formal_001/evaluate.py`。直接复用 `test_commands.py` 的参数和任务映射、既有任务并发／恢复函数及配对核验函数；不修改训练源码、Prompt 或算法。

运行命令：

```bash
PYTHONPATH=. /tmp/gse-v23-py313/bin/python experiments/methods/v23/v23_alfworld_formal_001/evaluate.py run
```

恢复时把 `run` 改为 `resume`；`status` 只读进度。已有结果目录拒绝再次 run，避免覆盖或意外重新采样。

离线验证：**577 tests、19 subtests 通过**。范围为全部 V23、ALFWorld Adapter 与相关 V22 回归；其中新增 9 项测试覆盖真实配置、最终 Skill、双组隔离、并行顺序、失败停止／恢复、冻结漂移拒绝、未知结果拒绝及 Token 统计。测试入口禁止网络和环境任务执行。

本次计划 268 个 Episode，每个最多 50 步：无重试时最多 13400 个 Actor 请求，计入每步最多 3 次请求的理论上限为 40200。实际成本以保存的 usage 为准。推理 Token 已包含于输出 Token，不重复相加。

训练 Campaign 的 3666 个文件在进程内保留原字节，评估结束后直接核对，没有创建新哈希机制。全部 Test 产物位于原正式实验根目录的 `evaluation/`，不会调用训练模块或把 Test 反馈写入 Memory。

## 必须保留的解释限制

- 本次比较 No Skill 与完整 V23 最终 Skill，不能单独归因于 Memory 或 Preconditioner。
- 单次 temperature=1 的配对仍受模型随机性影响；seed=42 不保证生成结果一致。
- 134 条 Test 在项目早期存在开发接触，不描述为历史上从未访问过的数据。
- 六轮训练中的 ACCEPT 不保证 Test 提升；不根据本次 Test 继续优化 Skill。
- 执行步数需结合成功率解释，不能仅据更少步骤声称能力提高。

## 真实执行停点：未完成正式比较

本次评估因真实网络传输中断停止，进程 exit 1。没有生成完整 S0/S1 比较结果，也没有成功率提升结论。S1 尚未执行。

| 状态 | S0 | S1 |
|---|---:|---:|
| 计划任务 | 134 | 134 |
| 已启动任务 | 75 | 0 |
| 合法完成 | 69 | 0 |
| 已完成中成功 | 58 | 0 |
| 已完成中正常失败 | 11 | 0 |
| 已完成任务执行步数 | 1080 | 0 |

S1 列的 0 表示尚未执行，不是能力或成功率为零。S0 已完成子集不能替代完整 134 条 Test 的成功率。未计算修复、退化或六类任务的完整配对统计。

### 技术中断与重试覆盖缺口

| Task | 已执行步骤 | 失败请求步 | 失败步实际尝试 | 错误 |
|---|---:|---:|---:|---|
| test:0066 | 27 | 28 | 1 | ChunkedEncodingError |
| test:0067 | 27 | 28 | 1 | ChunkedEncodingError |
| test:0069 | 11 | 12 | 1 | ChunkedEncodingError |
| test:0070 | 10 | 11 | 1 | ChunkedEncodingError |
| test:0073 | 5 | 6 | 1 | ChunkedEncodingError |
| test:0074 | 2 | 3 | 1 | ChunkedEncodingError |

这些请求约 45 秒后抛出 `requests.exceptions.ChunkedEncodingError`。客户端未获得完整 HTTP Response 对象，因此没有可保存的完整响应正文或 usage；已保存实际 messages、参数、请求时间、异常类型、耗时及中断前完整轨迹。无法由客户端证据确定服务端根因或未知费用。

现有 `src/adapters/alfworld/run_task_upstream.py:63` 仅捕获 `requests.Timeout` 和 `requests.ConnectionError`，未捕获 `ChunkedEncodingError`。因此这些失败步实际上只尝试 1 次，**不是三次重试耗尽**。这是正式运行暴露的异常重试覆盖缺口，已有离线测试通过不代表所有传输异常均已覆盖。

调度发现技术失败后立即停止提交后续任务，已启动任务继续安全结束。没有把技术中断记成普通失败，没有重跑已完成任务，没有启动 S1。未在运行中更改被冻结的 Actor 或隐式重新启动任务。后续需处理该异常的有限重试兼容，并经明确 resume 恢复；所有已有合法 Episode 应继续复用。

### 已知用量与保护核验

| 指标 | S0 已知值 |
|---|---:|
| requests | 1169 |
| input_tokens | 592579 |
| output_tokens | 998006 |
| reasoning_tokens | 914520 |
| cached_tokens | 16768 |
| total_tokens | 1590585 |
| retry_requests | 1 |
| unknown_usage_requests | 6 |
| technical_episode_attempts | 6 |

评估会话实际运行 1186.84 秒（19.78 分钟）。推理 Token 已包含于输出 Token；Cached 已包含于输入 Token。总 Token 是已返回 usage 的已知合计，不能把 6 次未知 usage 请求当作费用为零。

训练 Campaign **3666 个文件逐字节核对全部不变，无新增文件**。正式 R05 Skill、R06 Active Memory 与六轮结果均保留。

### 当前结果路径

- `evaluation/S0/partial_summary.json`：按冻结顺序排列的完整 Episode、实际状态和轨迹路径。
- `evaluation/S1/partial_summary.json`：明确记录未开始。
- `evaluation/comparison/partial_results.json`：未完成状态、全部技术中断、已知费用与档案保护核验；不是完整对照结果。
- `evaluation/S0/episodes/<task>/attempts/`：原始执行、请求、响应和失败证据。
- `evaluation/stop.json`、`sessions/001.json`、`test.log`：停止原因及运行信息。

最终 Skill 收益、副作用、修复与退化目前均不能由本次不完整比较得出结论。六轮 Gate 的训练结果不替代尚未执行完成的正式 Test。

补充重试审计：`test:0009` 的第 5 步曾返回 `finish_reason=length`，输出达到 16384 tokens，按既定规则重试一次后 `finish_reason=stop`。第一次消耗 16839 tokens、第二次 1971 tokens，均已纳入统计。该正常有限重试与随后六个未被捕获的断流异常不同。完整审计见 `evaluation/comparison/retry_audit.json`。

运行入口与所有 Actor 子进程均已退出。下一步需要补齐 `ChunkedEncodingError` 的有限请求重试覆盖，并核验与已冻结测试来源的兼容，再由明确的 `resume` 继续；不能直接静默改写本次 input 或已有轨迹。

## 用户授权的传输恢复（2026-10-19）

以下为原评估的恢复，前述首次停止及原始用量记录保留，不创建新实验。

- Actor 的可重试传输异常增加 `requests.exceptions.ChunkedEncodingError`，沿用同一步的首次请求加最多两次重试。未捕获全部 `RequestException`；模型参数、Prompt 和环境交互协议未变。
- 实际 `requests.Session.post` 默认读取完整正文后返回。新增故障注入在 HTTPAdapter/正文流边界抛出 ProtocolError，由 requests 转为 ChunkedEncodingError，验证同一步恢复、三次耗尽、未知 usage、环境动作时序和独立归档。Timeout、ConnectionError、429、截断回归通过，InvalidURL 不被盲目重试。
- 离线完整回归：**585 passed，19 subtests passed**（17.26 秒），禁止网络与环境执行。输出：`reports/test_transport_recovery_regression.txt`。
- `evaluation/recoveries/001.json` 通过现有 `contract_changes` 机制登记单行 Actor 修复，保存修复前后源码、评估运行器的精确改动，以及配对接口已有的 `implementation_review`。恢复只覆盖该传输修复，其他源文件、Prompt、配置和任务仍直接核对。训练 Campaign 内没有添加或修改恢复文件。
- 已显式执行原 `evaluate.py resume`。启动时合法完成 S0=69、S1=0；69 条直接复用。6 条原始中断保留在 `attempts/001`，从初始状态创建 `attempts/002`，不拼接轨迹。已观察到 8 个独立 Actor 子进程同时执行。
- 本次恢复日志：`test_resume_001.log`；会话：`evaluation/sessions/002.json`。最终结果以本节之后的实际完成或停止记录为准。所有已知用量继续累计，未知 usage 不记为零。

## 正式完整结果

本次两组各 **134/134** 完成，共 **268 个 Episode**；配对条件全部通过。程序正常退出，训练 Campaign 的 **3666** 个文件直接字节比对无变化、无新增文件。没有调用演化模块，没有修改最终 Skill 或 Memory。

| 指标 | S0 No Skill | S1 最终 V23 Skill |
|---|---:|---:|
| 成功任务 | 104 | 111 |
| 失败任务 | 30 | 23 |
| 总执行步数 | 2708 | 2434 |
| 成功 Episode 平均步数 | 11.615384615384615 | 11.567567567567568 |
| 成功 Episode 中位步数 | 9.0 | 9 |
| Success Rate | 77.61% | 82.84% |

成功率变化 **+5.22 个百分点**。这是本次实际单次配对结果，不等同于确定的因果效应。

### 配对变化

| 类型 | 数量 |
|---|---:|
| 修复 | 12 |
| 退化 | 5 |
| 共同成功 | 99 |
| 共同失败 | 18 |

全部修复 task_id：`test:0027`, `test:0046`, `test:0052`, `test:0057`, `test:0058`, `test:0067`, `test:0070`, `test:0096`, `test:0101`, `test:0102`, `test:0105`, `test:0117`。

全部退化 task_id：`test:0036`, `test:0041`, `test:0050`, `test:0075`, `test:0119`。

### 六类任务

| 类型 | 任务数 | S0 成功 | S0 SR | S1 成功 | S1 SR | 修复 | 退化 |
|---|---:|---:|---:|---:|---:|---:|---:|
| look_at_obj_in_light | 18 | 15 | 83.33% | 15 | 83.33% | 0 | 0 |
| pick_and_place_simple | 24 | 23 | 95.83% | 22 | 91.67% | 1 | 2 |
| pick_clean_then_place_in_recep | 31 | 21 | 67.74% | 26 | 83.87% | 6 | 1 |
| pick_cool_then_place_in_recep | 21 | 19 | 90.48% | 18 | 85.71% | 0 | 1 |
| pick_heat_then_place_in_recep | 23 | 14 | 60.87% | 18 | 78.26% | 4 | 0 |
| pick_two_obj_and_place | 17 | 12 | 70.59% | 12 | 70.59% | 1 | 1 |

### 用量、效率与失败记录

| 指标 | S0 | S1 |
|---|---:|---:|
| Actor HTTP 请求 | 2800 | 2437 |
| Input tokens | 1441524 | 3305572 |
| Output tokens | 2284500 | 710091 |
| Reasoning tokens（包含于 Output） | 2086844 | 535042 |
| Cached input tokens（包含于 Input） | 40829 | 1923200 |
| Total tokens | 3726024 | 4015663 |
| 技术重试请求 | 4 | 3 |
| 未成功请求 | 10 | 3 |
| 未成功请求已知 tokens | 21552 | 20698 |
| 技术中断 Episode 尝试 | 6 | 0 |
| 未知 usage 请求 | 6 | 0 |

S0 Episode 执行墙钟跨度：2977.33 秒（2026-10-19T02:30:52.737961+00:00 至 2026-10-19T03:20:30.064809+00:00）。

S1 Episode 执行墙钟跨度：746.71 秒（2026-10-19T03:20:31.241426+00:00 至 2026-10-19T03:32:57.951452+00:00）。

评估会话实际运行时长合计 **2978.12 秒（49.64 分钟）**，会话数 2。Token 汇总包含所有保存的尝试，Reasoning/Cached 都不额外加到总量。没有账户实际账单数据，因此不将估算货币金额称为实际费用。

### 与训练 Gate 的关系

训练 Gate：R01 9→10 ACCEPT、R02 6→7 ACCEPT、R03 7→6 RETAIN、R04 7→6 RETAIN、R05 7→9 ACCEPT、R06 6→5 RETAIN。正式 Test 读取 R05 Skill，保持 R06 Memory 不变。Gate 的训练配对只决定版本选择，不保证 Test 的每个任务或每种类型改善。

### 产物与读取

- `evaluation/comparison/results.json`：134 对完整核验结果、总体统计、六类统计、全部修复／退化 ID。
- `evaluation/S0/summary.json` 与 `evaluation/S1/summary.json`：按冻结顺序排列的每条 task_id、gamefile、成功状态、步骤、终止原因和轨迹路径。
- `evaluation/{S0,S1}/episodes/<task>/attempts/`：实际命令、日志、完整轨迹和逐步原始 HTTP 响应。
- `evaluation/input.json`：冻结实际配置、两组命令、最终 Skill 正文与执行文件来源。
- `evaluation/sessions/`、`test_launch.json`、`test.log`：运行、错误及恢复信息。
- `reports/test_transport_recovery_protection.json`：训练原始档案只读保护核对。

## 传输恢复最终核验

原 69 条合法完成 S0 全部零调用复用：未新增任务尝试，原结果文件及请求响应保持原字节。原 6 条中断轨迹保留，均从初始状态完成 attempts/002，没有拼接轨迹。已比对 1481 份既有评估产物和冻结配置文件，无变化；训练 3666 份文件无变化、无新增。

`reports/test_transport_recovery_protection.json` 保存核验结果；`evaluation/comparison/retry_audit_after_recovery.json` 列出全部失败及重试请求、已知或未知 usage 与响应状态。原先 6 次断流未知 usage 仍计为未知；已知 Token 总量不是完整账单金额。

恢复中 S0 前 69 条使用修复前执行源码，其余使用修复后源码。唯一 Actor 差异是断流异常覆盖，使用已有配对 implementation_review 明确登记，不改变 Task、Prompt、模型、Skill 或历史窗口；不能声称两组响应逐字可复现。

## 行为核查：观察到的收益与局限

本次净增加 7 条成功，来自清洁任务净 +5、加热任务净 +4、简单放置净 −1、冷却净 −1；灯下检查与双物体任务净变化为 0。12 条修复与 5 条退化同时存在，不能把所有任务都描述为提升。

以下引用均指 `evaluation/{S0,S1}/episodes/test_NNNN/result.json` 指向的合法完整轨迹，不使用已放弃的中断尝试代替正式结果。

| 案例 | 实际 S0 行为 | 实际 S1 行为 | 可以支持的观察 |
|---|---|---|---|
| test:0046，清洁 cloth 后放入 cabinet | 第 2 步取 towel，后续持有错误类别；第 26 步看到 cloth 后也未成功获取，50 步耗尽 | 第 4 步打开柜子发现 cloth，第 5 步获取，第 7 步 clean，第 9 步放入柜子并成功 | 精确目标类别及清洁流程与本例改善方向一致，但不是单独证明某条规则的因果作用 |
| test:0070，清洁 spatula 后放入 drawer | 多次返回 countertop 1/2、drawer 和 sinkbasin，未找到目标，50 步耗尽 | 第 3 步到 countertop 3，第 4 步拿取 spatula，第 6 步清洁，第 9 步完成 | 本例 S1 的实际搜索到达新位置并完成处理；不能推断所有搜索都改善 |
| test:0096，加热 apple 后放入 fridge | 第 6 步放进 microwave，后续反复开关，未执行 heat，50 步耗尽 | 第 9 步 `heat apple 1 with microwave 1`，第 11 步放入 fridge，成功 | 加热动作选择发生有利差异；Skill 未增加完整独立加热算法，不能把本例直接归因于 Memory 或某条单独更新 |
| test:0036，vase 放入 safe | 持续检查 shelf，至第 11 步到 shelf 10 找到目标，第 15 步完成 | 第 7 步转去 cabinet，之后反复回到 shelf 1/2、cabinet 和 drawer，未到达目标位置，50 步耗尽 | 跨类别搜索指导没有保证搜索覆盖，有限历史条件下重复访问仍发生 |
| test:0050，clean egg 放入 microwave | 第 5 步到 countertop 3 发现 egg，第 11 步完成 | 在 fridge、cabinet、countertop 1 等位置间重复搜索，未获取目标，50 步耗尽 | 清洁类总体提升仍有搜索退化反例 |
| test:0075，cool bread 放入 countertop | 第 26 步到 countertop 3，第 29 步 cool，第 31 步完成 | 多次回到 fridge、countertop 1/2 和 cabinet，未获取 bread，50 步耗尽 | 本例退化发生于找到目标之前，不能误称为观察到了冷却动作执行错误 |
| test:0119，两个 cd 放入 safe | 第 6、11 步分别完成两个 cd 的放置 | 第 16 步放入第一个 cd，之后转回搜索其他位置，没有返回取得第二个 cd，50 步耗尽 | 多物体任务中已发现位置的利用存在差异；不能假设 Actor 记得完整执行历史 |

这些是执行证据支持的行为差异，不是独立因果归因。最终 Skill 仍包含“未检查位置”“单次遍历”等超出最近两组历史即可可靠维护的要求；本次实际仍出现重复搜索。它是可解释的能力约束与行为现象，但本次没有消融或重复随机试验来证明该文本是每个退化案例的原因。灯下检查两组均为 15/18，没有观察到该类净提升。

两组成功 Episode 的平均步数几乎相同（S0 11.62，S1 11.57），中位数均为 9。总步数 2708→2434 与失败数减少同时发生，不能仅凭总步数下降声称每项任务效率均提高。

## 本次恢复的成本与技术结果

恢复会话正常退出，运行约 29.89 分钟；全部评估会话运行时长合计 49.64 分钟（不含中间停机等待及离线测试）。原始失败尝试、任务重新执行和所有有限重试均计入整体请求和用量统计。

- S0：2800 次请求，4 次额外步骤重试，6 次原始断流未知 usage，6 条旧技术中断尝试全部保留。
- S1：2437 次请求，3 次额外步骤重试，无技术中断、无未知 usage。
- 合计已知 **7,741,687 tokens**；Input **4,747,096**，Output **2,994,591**，其中 Reasoning **2,621,886** 已包含于 Output，Cached **1,964,029** 已包含于 Input。
- 7 个需要重试的步骤均在第二次请求获得合法回复：5 次空最终内容、2 次输出截断。失败响应已知用量合计 **42,250 tokens**，这不包含未知断流用量，也不代表重启任务的全部成本。
- 此次恢复没有再次出现 ChunkedEncodingError；新增断流处理的故障路径由离线真实 requests 正文读取故障注入验证，不能声称本次线上观察到了断流后重试成功。
- 账户实际货币账单不可从这些 usage 完整推算，不给出虚构金额。

本次仅比较 No Skill 与完整 V23 最终 Skill。单次 temperature=1、没有独立 Memory/Preconditioner 消融，且 Test 在项目早期有过开发接触；结果不能单独证明 Memory/Preconditioner 的因果收益或持续自进化的普遍有效性。没有将 Test 结果写入 Memory，也没有继续训练。
