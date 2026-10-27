# V23.5 ALFWorld：Initial Skill / V23.4 六轮训练流程

## 2026-10-27 当前材料状态

R01–R03 已完成，R04 Editor 原 001–006 与追加 007–012 均已用尽，记录停在第 4 轮；未发现最终 Test 归档。

正式 config/、任务 data/ 原样保留；以下结果来自已有文件，本次没有运行实验或测试。

[逐轮汇总](results/round_summary.json) · [优化逐任务指标](results/optimization_task_metrics.json) · [原状态](evidence/S1/state.json) · [停止记录](evidence/S1/stop.json)

| 轮次 | 状态／决策 | Parent / Candidate 成功数 | 原轮次结果 |
|---|---|---|---|
| R01 | RETAIN | 10/10 → 7/10 | [result](evidence/S1/rounds/R01/result.json) |
| R02 | RETAIN | 7/10 → 7/10 | [result](evidence/S1/rounds/R02/result.json) |
| R03 | ACCEPT | 6/10 → 8/10 | [result](evidence/S1/rounds/R03/result.json) |
| R04 | 未完成 | 尚未完成同批 Gate | [stop](evidence/S1/rounds/R04/stop.json) |

[停止时已发布的 Skill（不是完整六轮最终结果）](evidence/S1/rounds/R03/editor/attempts/002/candidate.md)。state 中 active_memory 的完整 commits 仍在原归档，证据区只保留 active 索引、发布候选及对应审计结果，不是可恢复运行目录。

各完成轮次保留 Parent、Editor 候选与实际 Diff、Gate 逐任务配对、Replay 输出；启用知识核验的轮次另保留 Verifier、Repair、knowledge_review 候选。原 result.json 选择路径与原尝试编号保留，未把失败输出改成成功结果。

[R04 Editor 12 次尝试证据](evidence/S1/rounds/R04/editor/attempts/)和[追加额度](evidence/S1/amendments/editor_retry_v1/grant.json)分别保留原 001–006 与授权追加 007–012。HTTP 401 恢复的授权摘要和历史验证记录见 [修订记录](evidence/S1/amendments/)。下方旧 PID 和“继续重试”是历史恢复时点，不代表当前进程仍在运行。

当前通用脚本 [run_v23_5_alfworld.sh](../../../../scripts/runs/run_v23_5_alfworld.sh) 默认指向 alfworld_action_feedback_001；下方旧入口说明保留历史阶段含义，通用脚本不会自动恢复旧目录。本次未执行任何入口。

[原始归档](../../../../artifacts/methods/v23_5/alfworld_initial_skill_001/)继续保存完整输入、HTTP、轨迹、Memory、日志及源码快照；研究副本不参与运行恢复或自动更新。仅克隆 Git 不包含这些原始数据。

## 历史说明（保留原阶段记录）

当前状态：**2026-10-24 北京时间 10:40:02 已按用户要求继续 R04 Editor 重试**。
新主进程 PID / 进程组为 `96193`，主进程和 Actor 均使用 `alfworld` 环境。
R03 已完成 ACCEPT（Parent 6/10，Candidate 8/10）；R04 Editor 原六次请求耗尽后，
本次仅为 R04 Editor 追加六次请求，编号 007–012；启动核对已进入 007 并引用 006 的错误反馈。
恢复记录为 `artifacts/methods/v23_5/alfworld_initial_skill_001/resume_002.json`，日志为同目录 `resume_002.log`。
此前 HTTP 401 恢复记录及日志保存在 `resume_001.json`、`resume_001.log`。
原 00:23:57 启动的进程 `69718` 在 R03 因 HTTP 401 退出；原 `launch.json`、`train.log` 和失败轨迹保留。
此前 00:13:17 启动的运行已终止并删除全部输出；本次从 initial skill 重新开始。
initial 未重测，最终 Test 使用独立入口，尚未启动。下文验收描述为各次准备时点的历史记录。

准备日期：2026-10-23。按用户最新要求，训练流程沿用 V23.4：39 Train + 18 Selection
合并为 57 条优化数据，按原顺序分成 10/10/10/10/10/7，共六轮，只遍历一次。
起点和模型参数参考 SkillOpt，保留 V23.5 同批 Gate。
此目录为独立实验配置；准备过程没有调用模型、启动 Actor 或执行 Test。

参考已完成运行：`artifacts/baselines/skillopt/alfworld_deepseek_v23_4_formal_20261023/`。
以该运行实际保存的 `config.json` 和 `skills/skill_v0000.md` 为依据，
不是仅按 YAML 默认值推断。初始快照与上游 `skillopt/envs/alfworld/skills/initial.md`
逐字节一致，SHA-256：`01bd29e825b81715e7b592e135a9a9d6d0f812a5e84dcd56b51cc1075247f941`。

## 固定条件

| 项目 | 本次配置 |
|---|---|
| 方法 | V23.5，Knowledge Only，有限输出校验反馈 |
| 起点 | SkillOpt 原始 initial skill，空 Memory |
| Actor Skill 注入 | `skillopt_user_v1`：system 保持角色说明，user 前部使用 SkillOpt 原始 `## Skill Knowledge` 包装、引导文字及换行 |
| 优化数据 | 39 Train + 18 Selection，共 57 个固定任务；1 次遍历 |
| 批次 | 每轮最多 10 条，10/10/10/10/10/7，共 6 轮、57 次任务呈现 |
| 顺序 | 与 V23.4 campaign.json 的 batches 逐项相同；先 Train 后 Selection，不 shuffle；保存到 data/batches.json |
| Selection | 原 18 条纳入优化、同批 Gate 和 Replay；不另设独立 Selection 选优 |
| Test | 保留原 134 条 held-out 清单；准备阶段不执行 |
| 模型 | Actor 与全部方法模块均为 deepseek-v4.1-flash |
| API | http://llm-proxy.intra.xiaojukeji.com/chat/completions |
| 请求参数 | temperature=1、thinking=enabled、reasoning_effort=medium、stream=false |
| 单次输出 | Preconditioner、Replay：32,768 tokens；Grouping、Diagnosis、Editor、Actor：16,384 tokens；各模块固定预算，不自动扩容 |
| 超时 | 连接 10 秒、读取 300 秒 |
| 执行 | 每任务最多 50 步，Actor 并发 8，环境 seed=42 |
| 重试 | 方法调用/Actor 单步最多 5 次重试，即首次请求 + 5 次重试 = 6 次总尝试；格式反馈与技术错误共用额度 |
| Gate | 当前优化批次 Parent/Candidate 成功数严格提高才 ACCEPT，否则 RETAIN |
| Memory | 合法 Replay 在 ACCEPT/RETAIN 后发布；六轮持续积累 |
| 最终 Skill | 最后一轮正式发布的 Parent；全部 RETAIN/no_change 时仍为 initial skill |

方法主进程和 Actor 均使用 `alfworld` conda 环境：
`/Users/didi/miniforge3/envs/alfworld/bin/python`。
当前 Python 3.9.23、ALFWorld 0.4.2、TextWorld 1.7.0、NumPy 1.26.4、
requests 2.32.5、python-dotenv 1.2.1；运行时冻结包版本和源码/Prompt。
本次补装 pytest 8.4.2 及测试依赖，用于在实际运行环境中验证。
与已完成 SkillOpt 所用的 Python/NumPy/requests 版本不同，比较结果需记录该环境差异。

## 对比边界

SkillOpt 的 slow update、meta skill、reflection minibatch=8、edit budget=4
属于它的方法实现，不映射为 V23.5 的学习模块。本次训练流程不对齐 SkillOpt 的
4 epochs / 39 条整批训练，而是沿用 V23.4 的 57 条、六轮流程。
本次优化上限为 57 Parent + 57 Candidate episodes；模型调用数、Actor 执行量
和 token 成本不与 SkillOpt 等同。SkillOpt 还使用独立 Selection 选优及额外的 slow/meta 阶段。

按用户要求，V23.5 的 Skill 注入已对齐 SkillOpt：

```text
\n\n## Skill Knowledge\n
Below is a skill document with learned strategies. Use these guidelines to inform your decisions:\n\n
{Skill 原文}\n\n
{任务提示词}
```

以上 `\n` 表示实际换行；实现保留 Skill 原文，不 trim。训练 Parent、同批 Gate
Candidate 和最终 Test 共用 `evolution.actor_command` / `run_task_skill`，统一提示、
历史窗口、动作解析、请求参数、50 步限制和每步六次总请求额度。旧 `system_v1`
仍为通用运行器默认选项，本实验在配置与命令中显式选择新协议，不改写旧轨迹。

离线测试直接读取本机 SkillOpt 的包装函数、任务模板、历史渲染代码，在相同
Skill、观察、合法动作和历史输入下逐字比较完整 system/user 消息，覆盖首步及
1、2、4 步历史。不同运行的实际轨迹可能不同，不要求实际消息序列相同。

剩余方法外差异：V23.5 对空响应、截断、HTTP 故障采用严格响应校验及有界重试，
SkillOpt 保留其模块重试与 `look` 回退；当前 conda 运行环境也不同。
未声称完整失败恢复策略与 SkillOpt 一致。

用户决定不重新测 initial。复用 SkillOpt 已有 initial Test 成绩 **117/134，87.31%**
作为参考，并在 `config/initial_baseline_reference.json` 固定来源、文件哈希和标签；
不将它标为 V23.5 Actor 的新实测结果。最终 Test 仅运行本方法最终已发布 Parent，
入口 `src.skill_evolution.v23_5.evaluation`，在六轮训练完成前拒绝执行。
最终结果保留上述参考来源，不自动把跨 Actor 的分数差解释为纯优化收益。

## 使用

在仓库根目录执行离线准备/核对，不读取密钥、不发出网络请求：

```bash
bash scripts/runs/run_v23_5_alfworld.sh check
```

准备器核对全部 191 条任务身份、数据文件、SkillOpt 初始快照、V23.4 六轮批次和运行环境。
已存在的准备文件有差异时拒绝覆盖。密钥不进入配置；启动时从环境或已忽略的 `.env`
读取 `OPENAI_API_KEY`、`OPENAI_BASE_URL`，进程环境优先，内部代理加入 NO_PROXY。

以下为训练启动、状态查询与恢复命令：

```bash
bash scripts/runs/run_v23_5_alfworld.sh run
bash scripts/runs/run_v23_5_alfworld.sh status
bash scripts/runs/run_v23_5_alfworld.sh resume
```

六轮全部完成后，执行最终 134 Test（不运行 initial、不学习、不更新 Memory）：

```bash
bash scripts/runs/run_v23_5_alfworld.sh test
bash scripts/runs/run_v23_5_alfworld.sh test-status
bash scripts/runs/run_v23_5_alfworld.sh test-resume
```

Test 输出为 `artifacts/methods/v23_5/alfworld_initial_skill_001/evaluation/final/`。
执行前核对训练配置、最终 Parent、Actor 源码/Prompt、运行环境、134 个 Test 身份及
文件哈希；每步核验保存的实际消息、请求参数与响应归档。技术失败停止并保留轨迹，
不会通过剔除失败任务生成最终分数。resume 复用完成任务并再次校验。

输出目录：`artifacts/methods/v23_5/alfworld_initial_skill_001/S1/`。
首次 run 冻结 initial skill 全文、配置、源码/Prompt 与运行环境。重复 run 拒绝，
恢复使用 resume；不得修改冻结配置继续运行。普通 resume 不追加耗尽的模块请求预算。

## 实现验证

`tests/skill_evolution/v23_5/test_initial_epochs.py` 覆盖 initial 起步的 ACCEPT、
RETAIN、no_change、多 epoch 同任务隔离、完整重载、发布前中断恢复、初始文件篡改/
缺失拒绝、epoch 内重复或缺任务拒绝，以及未显式配置 epoch 时继续拒绝重复任务。
这些离线测试不证明真实 API 可用性、完整训练稳定性或模型效果。

2026-10-23 验证结果：V23.5 全套离线测试 **458 passed**（包含新增的 12 项
initial/epoch 验证）；shell 语法和离线配置核对通过。未启动正式 Campaign。
Actor 携带真实 initial skill 的 `--dry-run` 和 SkillOpt 环境 `pip check` 通过。
仅核对 `.env` 中凭据与用户指定值一致，没有执行真实 API 鉴权请求。

同日按用户纠正更新：撤销本次准备中的四 epoch 计划，配置不再设置 `epoch_schedule`。
旧的未启动准备文件保存在
`artifacts/methods/v23_5/preparation_history/alfworld_initial_skill_001_skillopt_4epoch/`，
没有修改任何已启动 Campaign。多 epoch 的通用实现保留，本实验不使用。
更新后离线核对通过：六轮批次和 57 条任务身份与 V23.4 完全一致，原有环境快照内容
一致，134 Test 与优化任务不交叉；Selection 任务携带 initial skill、以 optimization
用途进入 Actor 的 `--dry-run` 通过。本次仅调整准备配置，未重新运行模型实验。

2026-10-24 注入修订：旧的未启动 system 注入准备文件保存在
`artifacts/methods/v23_5/preparation_history/alfworld_initial_skill_001_system_injection/`。
这次新增独立 Actor 协议标识和最终 Test 入口；未启动训练、基线或 Test。
共享代码增加新协议校验支持，已有 Campaign 的源码冻结规则不豁免；旧 Campaign
仍需使用其原冻结源码恢复或评测，不应在当前工作区跳过冻结检查。

本次验证：**660 passed，4 subtests passed**，覆盖 ALFWorld Actor、共享事实/Gate
相关验证、V23.4 Campaign 回归和 V23.5 全套测试。SkillOpt 包装函数、任务模板和
历史渲染源码的哈希与其正式运行前验收记录一致；8 个消息对齐样例通过。
最终 Test 新协议 dry-run、shell 语法与离线配置检查通过。报告见
`reports/actor_alignment_validation.json`；没有新增真实模型请求或 initial 基线评测。

2026-10-24 输出预算修订：按用户要求设置
`module_max_tokens={"preconditioner":32768,"replay":32768}`。
默认 `call_config.max_tokens=16384` 保留，训练/Gate/Test Actor 仍为 16,384。
方法模块的首次调用、校验反馈重试、技术重试和恢复均使用该模块冻结的预算；
该次输出预算修订没有修改重试额度；之后的六次总尝试修订见下文。
不启用 V23.4 的截断后自动扩容策略。
此前未启动的统一 16K 配置存于
`artifacts/methods/v23_5/preparation_history/alfworld_initial_skill_001_all_modules_16k/`。

2026-10-24 环境与重试修订：主进程、训练 Actor、Gate Actor、最终 Test 全部使用
`alfworld` 环境；`max_attempts=6`、`actor_request_attempts=6`，表示最多五次重试。
旧配置的 3 表示三次总尝试（两次重试），不是首次请求之外再重试三次。
格式修正、可重试技术失败与截断共用六次请求额度；永久错误或合法语义停止不会
为凑满次数而重试。默认反馈协议的普通 resume 不重置耗尽的方法调用额度。
Actor 限额作用于单步，不是自动重跑整条 episode；显式恢复中断的 Actor 任务
仍沿用既有任务恢复规则。已完成任务不重新采样。
六轮优化首次执行上限更新为 Actor 34,200 次 HTTP 请求、方法模块 180 次 HTTP 请求。
此前配置保存在
`artifacts/methods/v23_5/preparation_history/alfworld_initial_skill_001_skillopt_runtime_3attempts/`。
本次仅准备与离线验证，不启动训练或 Test。

本次在 `alfworld` 环境运行 ALFWorld Adapter 与 V23.5 全套回归：**539 passed**。
依赖检查、启动脚本语法、配置重复检查和 Train/Selection/Test Actor dry-run 均通过；
验证第六次成功、六次失败耗尽及方法模块恢复不重置额度。未发出真实模型请求，
已删除的训练目录仍不存在。记录见 `reports/runtime_retry_validation.json`。

2026-10-24 HTTP 401 恢复修订：用户明确要求重启 R03 并允许 HTTP 401 最多五次重试。
Actor 单步、方法调用均与其他可重试错误共用六次总尝试，不增加单次输出预算。
原始配置和源码快照保留，变更记录及批准源码另存于 Campaign 的
`amendments/http_401_retry_v1/`。已完成模块、Parent 和 Candidate 任务复用；
中断的 `train:0024` 从 episode 起点重新执行，旧的 14 步轨迹和第 15 步 401 响应保留。
R03 的旧/新 Actor 配对明确记录这次 HTTP 错误处理差异；后续轮次及最终 Test
采用相同的新请求策略。历史截断、Skill 注入、Gate 和方法 Prompt 均未修改。
本次离线回归 **563 passed**；恢复后核对 60 份既有轨迹及 5 份原始冻结文件的哈希均未改变。
原停止记录存入变更目录的 `stop_before_resume.json`；批准源码和校验记录也保存在该目录。

2026-10-24 R04 Editor 追加请求：在用户明确要求继续重试后，针对该轮 Editor
批准额外六次请求（007–012）。原始配置和前六次记录不变，其他轮次与模块仍使用
原六次总尝试额度；Editor 输出上限仍为 16,384。原有反馈继续传递，成功后接续
Candidate、Gate、Replay 和后续训练；普通 resume 不会再次重置已耗尽额度。
批准源码、单轮额度、历史文件哈希、原停止记录保存在
`S1/amendments/editor_retry_v1/`。本次 v23.5 回归 **515 passed**，
已核对恢复后所有既有轨迹、冻结配置和前六次 Editor 请求文件哈希不变。
