# V22 一轮无历史更新：真实执行记录

日期：2026-10-14。状态：`candidate_evaluated`，离线产物核验通过，Candidate 仅进入 staging。

## 问题与范围

**Question：** 能否从 No Skill 的真实 Train 反馈形成有来源的 Diagnosis，由 Editor 落实为完整 Skill，再通过已有环境入口执行并核对？

**Hypothesis：** 单次 Diagnosis 与单次 Editor，加上程序化证据、要求映射、实际 diff 和执行身份检查，可以贯通这一最小路径。此轮不验证预条件化收益、泛化、持续学习或正式采用策略。

固定 `train:0000`（照明）和 `train:0012`（清洁放置），任务在 Parent 执行前声明；每次全新环境，最多 50 步。Parent 为 No Skill，Fusion 原样传递，Memory 为空；不调用额外的 Review／总结 Agent。Candidate 生成后不改写，同一内容在两项原定任务各执行一次。没有使用 Selection／Test。

- [原计划](../config/plan.json)
- [基础设施恢复计划](../config/plan_recovery.json)
- [实现说明](../../../../../docs/methods/v22/NO_HISTORY_ROUND.md)
- [机器报告](../../../../../artifacts/methods/v22/no_history_20261014/round/report.json)及[离线审计](../../../../../artifacts/methods/v22/no_history_20261014/round/audit.json)

## 实际产生的更新

两项有效 Parent 执行均成功，不能将本轮称为修复两个失败任务。照明 Parent 存在重复操作、一次不在合法列表内的动作，以及开灯后的重复检查；清洁 Parent 的七步流程提供保留行为证据。

[Diagnosis](../../../../../artifacts/methods/v22/no_history_20261014/round/diagnosis.json) 在一次调用中提出三项初步方案：

1. `p1`：按当前合法命令匹配动作，引用的对象无法定位时重新观察／导航，不猜实例编号。
2. `p2`：对“look at … under …”任务围绕灯具组织寻找、搬运、放置、开灯和拿取流程。
3. `p3`：开灯后直接进行目标交互，避免重复 `use`／`look`／`examine` 循环。

Diagnosis 保存目标、决策缺口、竞争解释、不确定性、相互关系和边界案例，明确清洁放置行为需要保留。`requirements.json` 原样传递方案，未进行预条件化变换。

[Editor](../../../../../artifacts/methods/v22/no_history_20261014/round/editor.json) 在一次调用中输出完整英文 [Candidate Skill](../../../../../artifacts/methods/v22/no_history_20261014/round/candidate/SKILL.md)，内容分为动作定位、灯具任务流程和保留行为三部分。全部非空白文本均有要求映射，程序从实际文件生成 [diff](../../../../../artifacts/methods/v22/no_history_20261014/round/candidate/actual.diff)；[lineage](../../../../../artifacts/methods/v22/no_history_20261014/round/candidate/lineage.json) 绑定输入证据、初稿、要求、Editor 输出和实际文件。

Candidate 内容身份：`sha256:8779a3f166d8ad42c7db82292a64a420746c723d586e2e8a73c9c78d1659ecc5`。没有人工改写模型输出，也没有生成第二个 Candidate。

## 执行结果与可核对行为

| 固定 Train 任务 | No Skill Parent | Candidate | 已记录条件 |
|---|---|---|---|
| `train:0000` 照明 | 成功，28 步 | 成功，7 步 | 匹配 |
| `train:0012` 清洁放置 | 成功，7 步 | 成功，8 步 | 匹配 |

照明 Candidate 实际执行：到桌子 → 拿闹钟 → 到架子 → 到柜子 → 放下闹钟 → 开灯 → 拿起闹钟，最后一步原生成功。轨迹没有出现 Parent 中的长段桌面操作与开灯后反复检查。

清洁 Candidate 实际执行保留了取物、清洁和放置的完整流程；在取物之后额外执行一次 `look`，因此步数从 7 增至 8。不能声称完全没有行为变化，也不能把这一步单独归因于某项条款。

两组检查包括任务与数据内容、模型／后端、协议与预算、执行源码、初始观察及返回模型，均匹配；实际注入 Skill 与保存 Candidate 一致。原始轨迹见机器报告中的 `comparisons[].candidate_trajectory`，Parent 来源见 [sources.json](../../../../../artifacts/methods/v22/no_history_20261014/round/sources.json)。

这只是同批 Train 的一次构造与执行检查。结果提供流程可运行及具体行为变化的观察，不是统计收益、单项因果贡献、泛化或预条件化效果证明。未实施正式 Gate，也未发布为下一轮活动 Skill。

## 基础设施异常与成本

照明 Parent 首次在第 29 次请求发生 `ReadTimeout`，此前 28 步已经执行；该尝试不能作为完整 Parent。失败记录保留，重试前另存恢复计划，仅用相同配置重试一次，随后在 28 步成功。清洁 Parent 没有重跑。失败尝试只用于核验和计费，不进入 Diagnosis 输入；不是按成功结果挑选多个正常运行。

| 阶段 | 请求／调用 | 已报告总 tokens | 墙钟秒数 |
|---|---:|---:|---:|
| 照明 Parent 首次超时尝试 | 29 | 104,845 + 1 次未知 | 1,361.85 |
| 照明 Parent 恢复执行 | 28 | 89,218 | 1,022.19 |
| 清洁 Parent | 7 | 5,006 | 32.66 |
| Diagnosis | 1 | 33,646 | 227.88 |
| Editor | 1 | 30,339 | 151.24 |
| 照明 Candidate | 7 | 11,792 | 91.36 |
| 清洁 Candidate | 8 | 10,982 | 41.17 |

共 79 次环境请求、2 次更新语义调用、81 次 HTTP 尝试；已报告 285,828 tokens，另有一次超时请求用量未知，不能计成零。阶段墙钟时间不能直接相加作为整体耗时，因为首次两个 Parent 并行运行。

Diagnosis／Editor 合计 63,985 tokens，约 379 秒；“只有两次调用”并不意味着已经轻量。Editor 当前仍收到完整本轮证据与 Diagnosis，输入为 16,376 tokens，后续应研究按引用组织必要上下文，保留可追溯补读能力，并评估推理与输出预算。

请求配置为 `deepseek-v4-flash`、temperature 1.0、thinking enabled、reasoning effort medium、`max_tokens=16384`、环境 seed 42，实际返回模型一致。网关报告 Diagnosis 的 `completion_tokens=21757`（其中 `reasoning_tokens=17165`）；这高于请求的 `max_tokens` 数值，当前尚未确认服务端计量与限额语义，因此按返回值记账，不宣称该参数已经提供了可验证的总 completion 硬上限。

## 语义复核发现与下一步

以下为对本轮产物的人工研究复核，不是已实现的 Replay／Memory 解释模块，也不回写已执行的 Candidate：

- **成功序列与必要机制仍需区分。** `p2` 将“放下—开灯—拿起”作为任务流程，且承认仅有一个成功样本；这不能证明每一步必要，后续需要有针对性的比较，不能直接固化成跨任务规律。
- **Editor 的语义保持仍需检查。** Diagnosis 的 `p3` 提到未访问过的容器，但当前 actor 没有完整访问历史；Editor 改成一般合法探索，未给出上游反馈。这可能放宽了回退条件，字面映射检查无法判断是否属于需要返回上游的实质变化。
- **反馈解释存在泛化风险。** Candidate 将零奖励与 `Nothing happens` 一起描述为非失败信号；前者可能是正常中间反馈，后者也可能提示动作无效，应在下一次设计中明确区分，不能因本次成功就认定该表述可靠。
- **范围与成本不能只看成功率／调用数。** 清洁任务仍成功但多一步；两次更新调用仍消耗较大。后续 Replay 应观察目标与保留行为、机会及实际响应，再把有来源且带限制的认识交给 Memory／Fusion。

因此，本阶段完成了无历史单轮入口和真实执行核对；下一步宜先补足行为观察与要求语义保持的验证，再在同一证据链上联合接入响应 Memory 和 Fusion 的实际变换。

## 验证与源码范围

新 V22 方法测试 61 项通过，既有 ALFWorld 适配器测试 35 项通过；真实轮次的离线核验输出 `artifact_valid=true`、`round_complete=true`、`candidate_executions=2`。运行源码 hash 与保存的 `method_implementation` 一致。

实现位于 `src/skill_evolution/v22/`，覆盖证据装配、Diagnosis／Editor 约定与校验、单次模型调用记录、轮次入口和离线核验。没有改动执行适配器 Python 源码或 V19／V20／V21 的代码、文档及实验结果；原实验日志仅追加本阶段记录。

```bash
python -m src.skill_evolution.v22.verify_round artifacts/methods/v22/no_history_20261014/round
python -m unittest discover -s tests/skill_evolution/v22 -q
```
