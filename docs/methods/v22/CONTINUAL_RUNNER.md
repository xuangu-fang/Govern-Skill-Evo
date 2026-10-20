# V22 单主线两轮运行器

[返回索引](README.md) · [两轮协议](GROUPED_TWO_ROUND_PROTOCOL.md) · [共享接口](CONTINUAL_INTERFACES.md) · [08 配置](../../../experiments/methods/v22/08_grouped_continual/config/plan.json)

日期：2026-10-15。08 两轮均为7/10→8/10、Gate ACCEPT，第二轮已通过独立Memory恢复完成Skill／Memory共同发布。恢复前声明输出上限65536，保留原输入，仅新增一次Pro调用、零环境执行；Memory由3条更新为5条。第二轮Replay实测并行峰值8。两轮链路已完成，但包含明确恢复，历史预条件化的独立收益仍未证明；一项复合限制的退役范围边界见恢复报告。见[最新Memory恢复报告](../../../experiments/methods/v22/08_grouped_continual/reports/MEMORY_RECOVERY_REPORT.md)；[调度说明](PARALLEL_SCHEDULING.md)区分旧v2、显式修订和后续默认v3。

## 1. 已接通的路径

```text
已发布 Skill / Memory
  → 全批 Parent 执行
  → 程序摘要 → 一次全局分类并冻结
  → 独立 Diagnosis
  → Fusion / Compiler（R1 程序恒等，R2 一次正常构造）
  → Editor → 一份统一 Candidate
  → 同批 Replay → 整体成功率 Gate
  → 一次行为解释 / Memory 更新
  → 原子发布 Skill / Memory → 从发布文件读取下一轮 Parent
```

主入口是 [`continual_runner.py`](../../../src/skill_evolution/v22/continual_runner.py)。它调用已有共享表示、D/S/C、Editor、Effect 和状态接口，复用已记录请求的 `semantic_call` 与单任务 ALFWorld 执行入口。没有 Direct、Selection／Test、逐组 Skill 或额外复核模型。

Actor 默认最多8个任务并行，Parent和Candidate Replay共用有界调度；任务可乱序完成，交给下一阶段的材料保持冻结任务顺序。技术错误后停止补发，收齐已派发任务并保存全部成本，不进入下一语义阶段；正常原生任务失败仍继续整批。两轮各十个不同Train，每轮同一任务上的Parent／Candidate各执行一次。显式旧v2计划保持原串行行为。

## 2. 三个命令入口

从仓库根目录使用已安装 ALFWorld 的 Python。以下是入口操作说明；本次实际档案与独立调度修订见08报告，不使用下面的示例目录。

```bash
# 仅读取配置、依赖、任务文件并保存运行快照；不创建/重置环境，不请求模型。
/Users/didi/miniforge3/envs/alfworld/bin/python -m src.skill_evolution.v22.continual_runner preflight \
  --output-dir artifacts/methods/v22/08_preflight

# 真正开始两轮实验，会调用模型和环境；必须使用尚不存在的输出目录。
/Users/didi/miniforge3/envs/alfworld/bin/python -m src.skill_evolution.v22.continual_runner run \
  --output-dir artifacts/methods/v22/08_run

# 仅读取已保存档案，重算确定性衔接；没有模型或环境调用。
/Users/didi/miniforge3/envs/alfworld/bin/python -m src.skill_evolution.v22.continual_runner verify \
  --output-dir artifacts/methods/v22/08_run
```

默认读取 08 的 `config/plan_parallel8.json`（v3）；可用 `--plan` 显式指定保留的 `config/plan.json`（v2串行），关键预算、二十项不重复 Train、模型参数及来源须通过核对。`--env-file` 默认仓库 `.env`，凭据不会进入快照。`run` 只接受已标明实现就绪的配置。

`preflight` 与 `run` 分别使用新目录，真实运行会重新冻结当时的源码／配置／提示和环境身份。已有目录一律拒绝，不覆盖、不续跑。失败后不会另建目录刷新预算或补采；后续如需恢复，须单独明确协议和已有失败成本。

08 后续已获得两次明确恢复授权，均使用独立目录与配置，不改写通用运行器的零自动重试规则。第一次按 [recovery_r2.json](../../../experiments/methods/v22/08_grouped_continual/config/recovery_r2.json) 复用 R1 状态与 R2 Parent，只将分类请求的输出上限／timeout 改为 32768／600；其余阶段仍为 16384／300。分类与 Diagnosis 成功、Fusion 失败，事实和成本保留在[恢复报告](../../../experiments/methods/v22/08_grouped_continual/reports/RECOVERY_REPORT.md)。第二次按 [fusion_resume_r2.json](../../../experiments/methods/v22/08_grouped_continual/config/fusion_resume_r2.json) 复用已成功的分类／Diagnosis，保持失败 Fusion 的完整 messages 不变，仅允许一次新的 Fusion，然后至多一次 Editor、十条 Candidate Replay 和一次 Memory。两次旧失败均保留，累计上限调整为 40 episodes／11 Pro，不重新计入复用调用的费用。此入口不是通用自动重试或按结果改写 Candidate 的能力。

Python 层的 `run_campaign(bundle, output_dir, generate, execute, offline=True)` 支持合成测试。`offline` 是档案标记及预检边界，**不会自动替换传入回调**；测试必须提供本地合成回调，不能将真实回调误称为模拟。

## 3. 预算和冻结由程序负责

[`continual_runtime.py`](../../../src/skill_evolution/v22/continual_runtime.py) 核对配置、任务清单和实际 Train 条目，保存未提交源码的复制快照、基础 Actor 模板、配置、五个语义阶段的系统提示、序列化版本及依赖版本。真实模式还核对预定任务文件和环境接口是否可用，不提前执行任务。

每轮分类、Diagnosis、Editor、后处理至多一次；R1 的 Fusion 为零调用程序恒等，R2 即使 Memory 为空也走正常 Fusion，允许 Keep。总上限仍为 40 episodes、2,000 Actor 请求、9 Pro、2,009 逻辑请求；已有客户端每个逻辑请求最多六次传输尝试。不增加语义修复、续写、返工或 episode 重试。

实际完整语义 messages 在发送前检查 400,000 Unicode 字符上限，包括系统提示和输出形状。超限保存输入后停止，不截断、不拆分类、不增加摘要调用。每次调用检查系统提示与冻结正文一致，运行期间源码、配置、Skill 或已冻结证据变化也会停止。

冻结发生在分类输入、分类结果、Diagnosis 初稿、Fusion 有效要求、Candidate／执行观察问题和 Gate 后学习输入等交接处。它们是程序 hash 清单，不增加模型字段或推理调用；检查使用最新的累计清单，避免反复核对多个重复前缀。

Editor 复用已有确定性格式处理：相同继承 watch 去重、已有编号摘录规范化；不改条件、策略或要求，也不额外调用模型。原始输出与规范化输出分开保存。若 Candidate 与 Parent 字节完全相同，则规范化为 `no_change` 并继续检查其余字段；不重复执行同一 Skill。

`effective_plan.json` 保存 Editor 之前的编译要求；`execution_plan.json` 再合并 Editor 新增 watch，避免将两者混写。后处理遗漏这些新问题仍会阻止 Memory 发布。

## 4. 停点与发布

| 情况 | 程序行为 |
|---|---|
| 完整同批成功率严格提升 | Gate ACCEPT；Memory 有效后发布 Candidate 和新 Memory |
| 完整同批持平或下降 | Gate RETAIN；Memory 有效后发布原 Parent 和新 Memory |
| Diagnosis 无修改／缺证据，Fusion 或 Editor 合法待修订 | 保留原始决定和原因；无候选结算 `RETAIN/no_change`，不填写虚构 Candidate 成绩 |
| 无候选且 Memory 为空 | 程序产生合法空学习增量；未执行观察问题保留未知，不增加模型调用 |
| 无候选但有历史 Memory | 最多一次 Parent-only 后处理，可修订既有认识，不能新增本轮编辑效应 |
| Parent 不完整、分组无效、解析／引用错误、输入超限 | 保存错误及已发生消费，停止；不包装为语义 no_change |
| Candidate 不完整或条件不匹配 | 不产生有效 Gate，不正式学习／发布 Memory，不进入下一轮 |
| Memory 处理或发布失败 | 保留待发布 Gate，最后一次有效 Skill／Memory 保持不变 |

Gate 只比较整批原生成功率；局部退化不会额外否决整体提升，也不会因 ACCEPT 而被从 Memory 中删去。合法 RETAIN／no_change 结算后可以进入第二轮；技术失败没有自动恢复分支。

下一轮重新读取磁盘发布状态，再生成 Parent Skill 文件和轮初上下文。不会直接把上轮内存中的 Candidate 当作已经采用，也不会用新 Skill 搭配旧 Memory 继续。

## 5. 保存什么，怎样核对

根目录保存 `runtime_freeze.json`、源码／配置复制快照、`state0.json` 和总体 `report.json`。每轮在 `rounds/r1`、`rounds/r2` 下保存：

- 实际 Parent／Memory、分组输入和结果、初稿／有效要求／执行 Plan。
- `inputs`、`messages`、`calls`、`raw_outputs`、`outputs`，保留解析失败前的原始文字和传输记录。
- Parent／Candidate 轨迹、实际 Skill／diff 和各阶段冻结清单。
- Gate、学习包、Memory 增量结果、receipt；完成结算后才创建不可变 `state.json`。

总体报告累计两轮的 dispatch、实际保存请求、HTTP 尝试、已报告 tokens 和未知用量；失败阶段不丢失消费。没有返回可读轨迹或调用记录的 dispatch 单独计数，不能因为缺少档案就被当成零成本。步骤上限和请求上限由现有客户端实际执行；未用预算不补跑。

[`continual_verify.py`](../../../src/skill_evolution/v22/continual_verify.py) 离线核对冻结档案、调用输入输出以及已发布轮的分组、要求变换、Editor、Gate、Memory 和状态继承。历史源码使用保存的复制快照核对，不要求工作区永远停留在旧版本。完成启动冻结后的未完成轮如实报告未完成，损坏或错配的档案不能获得有效核验结果。仅 `preflight` 目录不是 campaign，不能交给此核验命令。若启动预检就失败、尚未形成运行快照或 `state0.json`，则保留错误产物；它也不构成可供完整核验的 campaign。

## 6. 验证与下一步

新增 30 项运行器／运行时／核验测试，当时V22共311项离线测试通过；后续并行及显式调度修订增加8项，完整319项通过，合入主工作区后14项相关测试通过。离线测试使用实际预定的二十个任务条目，但轨迹和模型输出均由合成回调产生。覆盖完整两轮、整体提高且伴随局部退化、第二轮同分 RETAIN、历史 Effect 参与要求替换、空 Memory／Keep、字节相同无修改、合法阻断、超限、分类无效、执行／Memory 失败、冻结篡改及档案核验。

本机只读 `preflight` 已通过，保存了二十项任务文件、依赖、源码／提示和配置身份，未创建或重置环境、未发送模型请求。该预检不证明模型服务可用或环境 episode 一定能完成。真实运行经明确恢复已完成两轮Replay、Gate、Memory及共同发布，见最新Memory恢复报告。后续仍须分别报告：版本是否正确继承、历史响应实际改变了哪些更新决定，以及真实行为是否支持这些决定；不能将本次合成贯通当成这三个问题的实验证据。

## 仅恢复 Gate 后的 Memory

08 的第二轮已完成 Replay 与 Gate，但原 Memory 请求因输出截断未能发布。单独的[Memory 恢复声明](../../../experiments/methods/v22/08_grouped_continual/config/memory_recovery_r2.json)允许复用冻结输入，只补一次 `post_gate_learning`，不调用环境、分类、Diagnosis、Fusion 或 Editor。独立入口为 `artifacts/methods/v22/08_memory_recovery_control_20261015/recover_memory.py`，支持 `preflight`、`run` 和 `verify`；已有恢复目录会拒绝再次执行。

此声明将 Memory 的输出上限从 16,384 提高到 65,536、读取超时从 300 秒提高到 600 秒，消息、模型及推理配置保持一致；600 秒不是整次调用的墙钟上限。这是显式恢复专用配置，不改变普通运行器默认预算。原失败和用量保留，恢复新增调用单独计费，再加入累计账目。

发布仍使用原有 `learn_grouped_memory → finish_round → write_state`：只有完整响应通过认识、引用、限制继承和 Gate 绑定校验后，才把已选定 Skill 与新 Memory 写入一个不可覆盖的原子状态文件。失败不会把第二轮 Skill 与第一轮 Memory 混合发布。历史运行目录不改写，新的正式状态通过恢复报告的 `latest_state` 引用。
