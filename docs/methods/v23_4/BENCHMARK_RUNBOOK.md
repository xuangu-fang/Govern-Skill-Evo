# V23.4 Campaign 集成与运行说明

历史运行说明保留原有时间点；后续已保存状态及结果见 [正式实验入口](../../../experiments/methods/v23_4/v23_4_alfworld_formal_001/README.md)，全部材料见 [版本索引](../../../experiments/methods/v23_4/README.md)。

## 2026-10-23 用户授权的输出预算修订

以下原始冻结说明保留作历史依据。自本次修订启用起，所有模型模块和 Actor 单步请求采用
`length_retry_double_v1`：每个新调用从 16,384 输出 token 开始；同一预算连续 6 次
`finish_reason=length`（原 3 次加 3 次）后，将该调用预算翻倍，继续按同一规则处理。
其他错误仍最多 3 次，不触发扩容；永久 API 错误立即停止；语义结果不重采样。
没有更改模型、Prompt、输入容量、任务顺序、50 步限制或 Gate。

当前 R03 Preconditioner 已有 6 次 16,384 token 截断，因此下一次从 32,768 开始。
模块扩容只对当前轮次、当前模块生效；下一模块/轮次重新从默认预算开始。
Actor 扩容只对当前步骤生效，保持当前环境状态，不重启 episode；下一步恢复默认预算。
更高预算如果被代理拒绝，按原永久错误处理停止，不切换模型或自动缩减输入。

原始 `config.json`、`initial_config.json`、`contract.json` 和既有结果不修改。
用户授权、修订源码快照及差异在 Campaign 的 `amendments/output_budget_v1/` 保存；
运行时仍逐次核对修订后的源码快照。每次模块请求保存 `output_budget.json`，
Actor 保存策略及每次实际请求参数、原始响应和用量。
R03 的旧 Parent 与新 Candidate Actor 实现差异通过明确的 source review 进入 Pair 审计；
本修订是实验执行条件变化，结果报告不得描述为全程相同的 16K/3 次请求预算。

启用命令（只在用户明确授权后执行；须无正在运行的 Campaign）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m src.skill_evolution.v23_4.evolution enable-output-budget-recovery --campaign artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1
```

之后使用下方既有 `resume` 命令。该策略也会进入未来 Test 配置，但本次不启动 Test。

更新：2026-10-22。总运行器与离线验收已完成；真实优化与 Test 尚未启动。

## 冻结的方法

`v23_4_campaign_v1`：Grouping → V23.4 Diagnosis → D/S/C Preconditioner → Editor → 同批 Parent/Candidate 执行 → Gate + Replay → 原子发布下一轮 Parent/Memory。

- Preconditioner：v2 扁平 Adjustment，所有 Original Update 恰好一次处理。全部 Keep 继续 Editor；全部撤回不生成 Effective Plan。
- Memory：`entries_sources_multi_knowledge_v1`。提交、重载、Preconditioner、Patch 编译、Editor 交接和 Replay 全部显式采用同一契约。
- Memory 视图：v3；Replay 使用真实历史归档 Pair 和当前配对完整轨迹。
- Replay 主学习 Prompt：P4 `v23_4_replay_multi_knowledge_v1`。没有启用 V2/V3 实验 Prompt，没有修改已有 Prompt。
- Gate：Candidate 成功数严格高于 Parent 才 ACCEPT，否则 RETAIN。
- Memory 发布：结构与引用校验通过的 Replay 在 ACCEPT、RETAIN 两种结果下都提交；从下一轮开始使用。无候选时不调用 Replay。正式实验不人工筛选、修补或按语义结果重采样 Memory。技术合法不代表知识语义正确，语义偏差属于实验结果。
- Parent 与 Active Memory 在整轮完成后共同发布。失败不会变成 Keep，也不会提前更新正式状态。

## 冻结的运行配置

依据原 v23 正式 Campaign 最终生效配置，包含两次输入容量恢复。用户在 2026-10-22 明确指定 V23.4 改用内部代理模型；因此模型/接口与历史 v23 不完全相同，未来结果比较应注明这一差异。

| 项目 | V23.4 冻结值 |
|---|---|
| 接口 | `http://llm-proxy.intra.xiaojukeji.com/chat/completions` |
| 模型：全部模块与 Actor | `deepseek-v4.1-flash` |
| 优化 | 39 Train + 18 Selection，原顺序，无 shuffle |
| 批次 | 10 / 10 / 10 / 10 / 10 / 7；1 epoch |
| 初始状态 | No Skill，空 Memory |
| Actor | 并发 8，每任务最多 50 步 |
| 模型参数 | temperature=1，reasoning_effort=medium，thinking=enabled，stream=false |
| 单次输出上限 | 16,384 token；不自动升级到 32K/64K |
| 超时 | 300 秒；连接超时按现有实现 10 秒 |
| 本地输入容量 | 4,000,000 字符 / 6,000,000 UTF-8 消息字节 |
| 模块重试 | 每次运行会话最多 3 次总尝试；技术/格式失败可重试，语义结果不重试 |
| Actor 重试 | 每一步最多 3 次请求；没有自动整任务重采样 |
| Test | 134 条，与优化集无 ID/gamefile 重叠；只执行冻结最终 Parent |

显式 `resume` 在保留已完成结果的基础上给予新的有界技术尝试预算，与 v23 一致；这不等于首次请求之外再自动重启三次。截断、超容量或持续格式错误达到预算后停止。配置和源代码不能原地修改后继续运行；本轮不提供跨版本恢复豁免。

v23 的 `config.json` 残留两轮 pilot 的预算说明；新配置仅将这一元数据改为正式 57 条规模，运行控制参数不因此改变。优化首次会话上界：114 episodes、17,100 Actor HTTP 请求、90 模块 HTTP 请求。S1 Test 上界：134 episodes、20,100 Actor HTTP 请求。这些不是成本预测，也不包含显式 resume 新增预算。

## 文件和冻结边界

- 配置与任务清单：`experiments/methods/v23_4/v23_4_alfworld_formal_001/`。
- 正式优化输出：`artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1/`。
- 正式 Test 输出：`artifacts/methods/v23_4/v23_4_alfworld_formal_001/evaluation/`。
- 验收报告：`experiments/methods/v23_4/campaign_integration_001/REPORT.md`。

`config.json` / `initial_config.json` 冻结配置；`contract.json` 冻结 V23.4、共享 v23/v23.3、JSON parser、Actor 实现及提示资源；`runtime.json` 冻结实际 Python 与四项包版本。配置目录保存 v23 原配置、恢复记录哈希、任务身份、环境文件及差异说明。运行和复用均检查冻结来源；已有历史归档不迁移。

之前尚未启动的官方接口配置中，完整配置快照已归入 [旧路由归档](../../../artifacts/methods/v23_4/campaign_integration_001/superseded_official_route/)；替换原因、源码快照与小型记录仍在 [集成验收目录](../../../experiments/methods/v23_4/campaign_integration_001/README.md)。仅供追溯，不能作为执行入口。

## 入口命令

从仓库根目录运行。以下真实运行命令仅供后续明确启动时使用，本次没有执行。

离线预检：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m src.skill_evolution.v23_4.benchmark verify
```

启动 57 条优化：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m src.skill_evolution.v23_4.evolution run --campaign artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1 --config experiments/methods/v23_4/v23_4_alfworld_formal_001/config/campaign.json
```

查看或显式恢复：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m src.skill_evolution.v23_4.evolution status --campaign artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m src.skill_evolution.v23_4.evolution resume --campaign artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1
```

完成全部轮次后启动 134 条 Test：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m src.skill_evolution.v23_4.evaluation run
```

Test 默认只运行 S1，不额外重跑 No Skill。若要新跑 S0，须另行明确指定 `--groups S0 S1` 并使用独立输出目录。Test 不学习、不提交 Memory；最终 Skill 从已发布状态解析，不能选择最后一个未被 Gate 接纳的 Candidate。

真实调用前检查 `.env`/进程环境的接口与冻结接口相符，且有 API key；不会输出密钥。当前路由一致性已检查，但没有发起鉴权、模型或 Actor 网络请求。

## 验收边界

离线合成响应验证程序契约和故障恢复，不验证模型语义收益或长程稳定性。57 条清单的六轮合成闭环、134 条 Test 合成执行，不应被称为真实 Benchmark 结果。真实实验中的输出容量、HTTP 可用性、Replay 错误积累等仍需实际记录。
