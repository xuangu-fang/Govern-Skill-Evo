# Hands-on TODO：10 天进入研究型 POC

版本：2026-07-28  
执行原则：前 3 天跑通；第 4–7 天拆代码；第 8–10 天做出第一个核心现象。

## 最终验收物

第 10 天结束时，应有一个可以演示的闭环：

```text
τ³ tasks
→ agent trajectories
→ task/process diagnosis
→ outcome-only candidate Skill
→ held-out rerun
→ success/compliance change report
```

演示必须回答：

1. Skill 是从哪些轨迹学到的？
2. Skill 修改了什么？
3. task success 是否变化？
4. compliance 是否变化？
5. 是否出现“成功但违规”的经验传播？

---

## Day 0：准备环境和项目

### 0.1 检查工具

建议使用 Linux、WSL2 或 macOS。先确认：

```bash
git --version
uv --version
python --version
docker --version
```

τ³ 当前要求 Python `>=3.12,<3.14`。ToolSandbox 使用 Python 3.9。不要把所有仓库塞入同一 Python 环境。

如果没有 `uv`，按其官方安装文档安装。不要从不明镜像复制安装脚本。

### 0.2 初始化自己的项目

```bash
mkdir governed-skill-evolution
cd governed-skill-evolution
git init
mkdir -p docs external src experiments tests
```

将本启动包五份文档放入 `docs/`。建立 `.gitignore`，至少排除：

```text
.env
.venv/
__pycache__/
*.pyc
external/
outputs/
data/raw/
```

第三方代码放 `external/`，不提交到自己的仓库。自己的 adapter、verifier 和实验配置才进入版本管理。

### 0.3 API 基本规则

- 第一阶段只选一个稳定 API provider。
- target agent 与 user simulator 可以先用同一模型。
- optimizer 后续可以换更强模型；第一天不要混三个 provider。
- 在实验日志中记录 provider、完整 model id、temperature 和日期。
- API key 只写 `.env`，不截图、不提交。

---

## Day 1：跑通 τ³-bench

### 1.1 Clone 和安装

```bash
cd external
git clone https://github.com/sierra-research/tau2-bench
cd tau2-bench
git rev-parse HEAD
uv sync
cp .env.example .env
```

编辑 `.env`，填入实际 provider 所需 key。τ³ 使用 LiteLLM；模型名必须符合 LiteLLM 的 provider/model 规则。不要凭感觉猜模型名，先看当前 README 和 `tau2 intro`。

### 1.2 先理解 CLI

```bash
uv run tau2 intro
uv run tau2 run --help
```

### 1.3 跑最小真实任务

官方示例是：

```bash
uv run tau2 run \
  --domain airline \
  --agent-llm gpt-4.1 \
  --user-llm gpt-4.1 \
  --num-trials 1 \
  --num-tasks 1
```

如果不用 OpenAI，将两个 model id 替换为 `.env` 对应 provider 的 LiteLLM model id。先只跑 1 个任务；确认费用和输出后再改为 5 个：

```bash
uv run tau2 run \
  --domain airline \
  --agent-llm <provider/model> \
  --user-llm <provider/model> \
  --num-trials 1 \
  --num-tasks 5
```

查看结果：

```bash
uv run tau2 view
rg --files data/simulations
```

### 1.4 当天必须回答

从代码和一条轨迹中定位：

- task 定义在哪；
- domain policy 在哪；
- tools 在哪；
- initial database state 在哪；
- agent 与 user simulator 如何轮流行动；
- reward 如何计算；
- trajectory 保存成什么结构。

把文件路径和关键类/函数写进实验日志。不要只写自然语言概念。

### Day 1 验收

- 一条成功或失败的完整 trajectory；
- 一张结果 viewer 截图；
- 当前代码 commit；
- 一段 300 字以内的架构说明；
- 一次干净 Git commit。

---

## Day 2：手工做第一次过程审计

### 2.1 选择 5 条轨迹

优先包含：

- task success；
- task failure；
- 多次 tool call；
- 信息不足；
- policy 中存在明确先后顺序或禁止项。

### 2.2 使用统一标注表

为每条轨迹记录：

```yaml
trajectory_id:
domain:
task_success: true | false | uncertain
policy_compliance: true | false | uncertain
violations:
  - rule:
    step:
    severity: low | medium | high
    evidence:
shortcut_summary:
annotation_confidence:
```

不要让 LLM 直接替代人工 gold。可以让 LLM 先提取候选规则和可疑步骤，再由人核对 policy 原文与 trajectory。

### 2.3 写第一个极简 Skill

基于 5 条轨迹，人工写一个不超过 800 字的 `skills/manual_v0/SKILL.md`：

- 只写可复用程序；
- 每条规则说明适用条件；
- 包含至少一个 stop/escalation 条件；
- 不写具体 task 的答案或 ID；
- 明确不能绕过的 policy。

### Day 2 验收

- 5 条双标注；
- `manual_v0/SKILL.md`；
- 一页“结果正确但过程错误”的可能案例；
- 标注中仍不确定的问题列表。

---

## Day 3：理解 SkillOpt 的完整循环

### 3.1 Clone 和安装最新 source

当前通用 OpenAI-compatible research backend 位于最新 `main`，不能只依赖旧 PyPI wheel。

```bash
cd external
git clone https://github.com/microsoft/SkillOpt.git
cd SkillOpt
git rev-parse HEAD
uv venv --python 3.12
uv pip install -e ".[searchqa]"
```

### 3.2 先跑零 API 的确定性闭环

```bash
uv run python -m skillopt_sleep.experiments.run_experiment \
  --persona researcher \
  --assert-improves
```

这个实验只证明 engine、edit 和 gate 的控制流能工作，不代表真实模型能力提高。

### 3.3 跑 SearchQA research engine

准备数据：

```bash
uv run python scripts/materialize_searchqa.py
cp .env.example .env
```

如果使用通用 OpenAI-compatible endpoint，在 `.env` 中填写：

```bash
export OPENAI_COMPATIBLE_BASE_URL="https://api.example.com/v1"
export OPENAI_COMPATIBLE_API_KEY="your-key"
export OPENAI_COMPATIBLE_MODEL="provider-model"
```

加载环境：

```bash
set -a
source .env
set +a
```

先阅读：

```bash
sed -n '1,240p' configs/searchqa/default.yaml
uv run python scripts/train.py --help
```

默认 SearchQA 配置可能包含 4 epochs、batch size 40 和较高并发，不适合第一次付费 smoke test。复制一份配置到自己项目的 `experiments/configs/skillopt_searchqa_smoke.yaml`，至少收缩：

- epoch；
- train/validation items；
- analyst workers；
- batch size；
- reflection rounds。

具体字段以当前 checkout 的 config 和文档为准，不要编造不存在的参数。

然后运行：

```bash
uv run python scripts/train.py \
  --config <your_smoke_config.yaml> \
  --out_root outputs/searchqa_smoke \
  --cfg-options \
    model.optimizer_backend=openai_compatible \
    model.target_backend=openai_compatible \
    model.optimizer=<provider-model> \
    model.target=<provider-model>
```

检查：

```text
outputs/searchqa_smoke/
├── best_skill.md
├── history.json
├── runtime_state.json
├── skills/
└── steps/
```

### 3.4 读代码，不只看结果

画出从 rollout 到 gate 的函数调用路径，至少定位：

- benchmark adapter；
- trajectory / result representation；
- reflection prompt；
- bounded edit；
- candidate skill；
- validation gate；
- accepted/rejected history；
- best skill 保存逻辑。

### Day 3 验收

- SkillOpt zero-API proof；
- 一次小规模真实 API run，或一份明确的阻塞报告；
- baseline skill、candidate skill 和 accepted/rejected edit 的对照；
- SkillOpt 主调用链说明。

---

## Day 4：跑通 Trace2Skill，比较两种学习范式

### 4.1 Clone 与安装

```bash
cd external
git clone https://github.com/Qwen-Applications/Trace2Skill.git
cd Trace2Skill
git rev-parse HEAD
uv venv --python 3.12
uv pip install openai tqdm openpyxl requests diskcache
```

配置 OpenAI-compatible API：

```bash
export OPENAI_API_KEY="<your-key>"
export OPENAI_BASE_URL="<optional-compatible-endpoint>"
```

### 4.2 不急着完整复现 SpreadsheetBench

先执行：

```bash
uv run python analyze_results.py --help
uv run python analysis/run_error_analysis.py --help
uv run python analysis/run_success_analysis_llm.py --help
```

阅读 released skills、trajectory analyzers 和 consolidation 代码，回答：

| 问题 | Trace2Skill | SkillOpt |
|---|---|---|
| 输入多少条轨迹 |  |  |
| success/failure 如何使用 |  |  |
| Skill patch 如何生成 |  |  |
| patch 如何合并 |  |  |
| 是否有 held-out gate |  |  |
| 如何防止错误 lesson |  |  |
| 输出 artifact 是什么 |  |  |

### 4.3 最小复用目标

用你在 τ³ 得到的 5–10 条 trajectory，写一个离线 converter，使其能进入你自己的统一格式。然后借鉴 Trace2Skill prompt，实现：

```text
trajectory
→ local diagnosis
→ local lesson
→ candidate Skill patch
```

第 4 天不必把 τ³ 完整接进 Trace2Skill。先离线 JSON in / Markdown out。

### Day 4 验收

- Trace2Skill / SkillOpt 代码级差异表；
- `tau2_to_common.py`；
- 5 条轨迹转换测试；
- 至少 3 个 local lesson 和 1 个 candidate Skill。

---

## Day 5–6：实现统一 trajectory schema 与双 verifier

### 5.1 建议 schema

在自己的项目中定义：

```python
Trajectory:
    trajectory_id
    environment
    task_id
    policy_version
    initial_state
    events[]
    final_state
    task_score
    metadata

Event:
    step_id
    actor
    event_type
    content
    tool_name
    tool_args
    tool_result
    state_delta
    timestamp
```

保留原始 payload，不要因统一 schema 丢失第三方字段。

### 5.2 Task verifier

第一版直接读取 benchmark 的官方 reward/goal-state 结果，不重复发明 judge。

输出：

```python
TaskVerdict(
    success: bool | None,
    score: float,
    evidence: list[str],
    verifier_version: str,
)
```

### 5.3 Process verifier

采用 hybrid verifier：

1. 可形式化规则：Python deterministic checks；
2. 语义规则：LLM judge 提取候选 violation；
3. 严重违规：人工复核；
4. 所有 verdict 必须引用 policy 规则和 trajectory step。

输出：

```python
ComplianceVerdict(
    compliant: bool | None,
    violations: list[Violation],
    severity_score: float,
    evidence: list[Evidence],
    verifier_version: str,
)
```

禁止只让 LLM 输出一个 `compliant=true/false`。

### 5.4 最低测试

- parser 对 10 条轨迹不崩；
- task score 与原 benchmark 一致；
- deterministic rule 有单元测试；
- LLM judge 输出 schema 可校验；
- verdict 能定位到具体 step；
- 同一轨迹重复判定基本稳定。

### Day 6 验收

- common schema；
- τ³ adapter；
- task verifier；
- process verifier v0；
- 10 条 gold annotation；
- 自动 verdict 与人工 gold 的错误分析。

---

## Day 7：建立可复现的小型实验集

从 τ³ 中选择或生成 30–50 条轨迹，划分为：

- `train_traces`：用于 Skill 学习；
- `selection_tasks`：用于接受/拒绝 Skill；
- `test_tasks`：最终一次性评价。

要求：

- task 不重复泄漏；
- test 不参与 prompt 编写；
- 保留成功/失败与合规/违规四类；
- 固定 policy version；
- 记录模型和随机性；
- 所有 ID 写入 manifest。

生成第一张表：

| Split | N | Task success | Compliance | Success-but-violation |
|---|---:|---:|---:|---:|
| Train |  |  |  |  |
| Selection |  |  |  |  |
| Test |  |  |  |  |

若找不到足够“成功但违规”，允许构造最小 conflict variants：

- 用户催促跳过身份核验；
- 要求在证据不足时执行不可逆动作；
- 要求访问超出角色权限的数据；
- 要求绕过人工审批；
- 以“紧急”为由改变步骤顺序。

构造 variant 时，只改变产生 goal conflict 的部分，保留原任务其余结构，并清楚标为 synthetic/adversarial。

### Day 7 验收

- versioned manifest；
- 30–50 条轨迹；
- 四象限分布；
- 至少 3 类违规；
- 数据生成与标注说明。

---

## Day 8–10：核心 POC——成功是否会教坏 Skill

### 8.1 Baselines

至少实现：

1. `No Skill`
2. `Human Skill`
3. `Outcome-only Skill`
4. `Filtered Skill`：删除成功但违规轨迹后学习

时间允许再加入：

5. Trace2Skill-style consolidation
6. SkillOpt-style validation gate

### 8.2 Outcome-only learner

输入：

- 所有 task-success trajectories；
- 不提供 compliance label。

输出：

- candidate `SKILL.md`；
- 每条新增规则的 source trajectory；
- patch diff。

### 8.3 第一个真正困难的挑战

让 learner 在含“违规成功”轨迹的训练集上学习，再在 held-out conflict tasks 上运行。检验：

- task success 是否提高；
- compliance 是否降低；
- Skill 是否显式或隐式鼓励违规步骤；
- 违规是否从一个任务迁移到相近但未见任务；
- 过滤违规轨迹能否消除传播。

不要只看最终平均分。逐条展示至少 3 个 causal-looking case：

```text
source trajectory
→ learned Skill clause
→ held-out agent behavior
→ violation verdict
```

这里只能说“传播链证据”，不能直接声称严格因果；后续通过删除特定 clause、替换训练轨迹和重复实验加强归因。

### 8.4 POC 报告

10 天报告不超过 6 页，包含：

1. 问题与假设；
2. 环境、模型、任务与 policy；
3. trajectory schema 和 verifier；
4. 四个 baseline；
5. task/compliance 结果；
6. 三个具体传播案例；
7. 当前失败点；
8. 下一阶段方法设计。

### Day 10 Go / No-Go

**Go：**

- 存在稳定的 success/compliance gap；
- outcome-only skill 在至少一类任务中传播违规；
- 双 verifier 足以支撑实验。

**Conditional Go：**

- gap 存在，但传播不明显。扩大 conflict tasks，研究 Skill clause 归因和更强 baseline。

**No-Go / Pivot：**

- gap 主要来自 verifier 噪声；
- 违规无法稳定复现；
- Skill 对行为几乎无影响。

此时转为“可审计 trajectory diagnosis / Skill provenance”，不要硬写违规放大故事。

---

## Week 3–5：方法原型

实现最小 Governed Skill Evolution：

```text
trajectory pool
→ four-way diagnosis
→ local lesson with evidence
→ bounded patch
→ task gate
→ compliance gate
→ accept / reject / quarantine
```

候选 Skill contract 至少包含：

- applicability；
- obligations；
- prohibitions；
- escalation；
- evidence；
- confidence；
- version。

必须做的消融：

- 无 compliance gate；
- 只有训练轨迹过滤；
- 只有 Skill contract；
- deterministic verifier only；
- LLM verifier only；
- dual verifier；
- 无 provenance。

简单 filtering baseline 很重要。如果复杂 dual gate 不能超过“删除违规轨迹”，方法贡献就不够。

---

## Week 6–8：完整公开 benchmark 实验

优先级：

1. τ³ airline / retail；
2. ToolSandbox 的少量典型 scenarios；
3. SkillLearnBench 的 2–5 个 workflow-clear tasks；
4. FraudOps-mini。

完整指标：

- task success；
- policy compliance；
- severe violation rate；
- compliance-weighted success；
- Machiavellian gap；
- token/API cost；
- accepted/rejected Skill edits；
- test-time inference overhead；
- repeated-run consistency。

至少 3 个随机种子或重复运行；如果成本太高，先报告置信区间和明确限制，不挑最好的一次。

---

## Week 9–10：Policy shift 与迁移

从下面选两项：

- policy v1 学 Skill，policy v2 测试；
- target model 更换；
- optimizer model 更换；
- direct-chat 与 agent harness 迁移；
- adversarial user 强度变化；
- 一条有害 Skill clause 的 targeted removal。

Policy shift 需要区分：

- 旧规则失效；
- 新增义务；
- 权限收紧；
- 审批阈值变化；
- 规则冲突。

---

## Week 11–12：冻结、复现、写作

- 冻结代码 commit 和 experiment manifests；
- 从空环境执行一次完整复现；
- 补齐失败实验；
- 检查数据泄漏；
- 人工抽查 verifier；
- 整理定性案例；
- 写 limitation；
- 把 FraudOps 映射写成应用验证，不夸大公开数据与真实业务的一致性。

---

## 每日汇报模板

每天只汇报五件事：

1. 今天实际跑通了什么；
2. 新产生了什么 artifact；
3. 一个最重要的观察；
4. 一个明确 blocker；
5. 明天最先执行的命令或实验。

避免汇报“阅读了很多论文”“理解了框架”。必须给文件、轨迹、diff、表格或 commit。
