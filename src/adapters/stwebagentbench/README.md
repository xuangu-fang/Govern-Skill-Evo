# ST-WebAgentBench SuiteCRM Adapter

本目录保存 ST-WebAgentBench 在 SuiteCRM 环境中运行任务所需的程序，包括恢复数据库、运行任务、检查结果和生成汇总。

这里有两套不同用途的流程：

1. **Autonomous GSE v0.1 正式实验**：由一个统一入口自动完成三步演化，日常应优先使用这一入口；
2. **Day 8–10 手工 POC**：分别运行训练、生成 Skill 和选择评测，主要用于复现较早的手工实验。

两套流程共用 SuiteCRM 和底层任务运行程序，但配置、结果目录和运行入口不同，不能把它们的命令或结果混在一起。

## 常用名称

- **Runner（任务运行程序）**：调用 Agent 完成任务，并写入数据库和任务记录。
- **trajectory（任务记录）**：Agent 完成一个任务时留下的一次完整交互。
- **formal（正式运行）**：按照锁定配置产生可用于实验结论的正式结果。
- **partial（运行中预览）**：允许任务尚未全部完成，只做临时检查，不形成最终结论。
- **strict（完整检查）**：要求计划中的任务全部完成且有效。
- **S0**：没有附加 Skill 的起点。
- **Parent（当前版本）**：当前已经接受、下一步继续使用的 Skill。
- **Candidate（候选版本）**：新提出但尚未被接受的 Skill。
- **checkpoint（评测基准）**：当前版本在固定18个评测任务上的锁定结果。

## Day 8–10 手工实验设置

手工 POC 使用以下已经锁定的实验清单：

```text
experiments/manifests/stweb_suitecrm_poc_v01.json
```

计划的任务数量为：

```text
训练：     51个任务，只运行无 Skill 版本，用于生成学习经验
选择评测：18个任务 × 4种方法 = 72条任务记录
独立测试：保持封存，不运行
```

## 程序分别做什么

| 文件 | 类型 | 作用 |
|---|---|---|
| `reset_suitecrm_db.sh` | 写数据库 | 使用冻结 SQL 快照恢复 SuiteCRM，并检查 Contact、Account 和 Lead 数量。每条轨迹运行前由 Runner 自动调用。 |
| `run_manifest.py` | 调模型、写数据库和任务记录 | 手工 POC 的训练程序。运行51个训练任务和无 Skill 版本，支持中断后继续，并保留失败记录。 |
| `validate_train_run.py` | 只读 | 检查51条正式训练记录的任务、模型、运行程序、数据库快照、结果和安全报告是否一致，并统计指标。 |
| `prepare_learning_inputs.py` | 读取任务记录；完整模式会写索引 | 从训练记录生成两种学习输入。`--partial` 只预览；不加该参数时要求数据完整并写入输入清单。 |
| `run_selection.py` | 调模型、写数据库和任务记录 | 手工 POC 的选择评测程序。用18个固定任务比较四种方法，支持中断后继续，并保留失败记录。 |
| `run_evolution_train.py` | 调模型、写数据库和任务记录 | Autonomous GSE 内部训练程序。只运行 Controller 指定的17个任务，并根据当前版本决定是否注入 Skill。 |
| `run_evolution_selection.py` | 调模型、写数据库和任务记录 | Autonomous GSE 内部评测程序。用固定18个任务重新评测候选版本，供演化门槛比较。 |
| `validate_selection_run.py` | 只读 | 检查四种方法共72条正式评测记录。`--partial` 允许尚未全部完成；完整模式要求72条全部有效。 |
| `summarize_selection.py` | 预览模式只读；完整模式写报告 | 数据检查通过后，统计整体结果、分组结果、模板平均结果和同任务上的方法差值。 |

Skill 生成程序不在本目录，位于：

```text
src/learners/stwebagentbench/generate_skill.py
```

## 手工 POC 数据如何流转

下面的 `Outcome-only` 表示只根据任务结果筛选经验；`Filtered` 表示进一步排除有违规记录的经验。

```text
冻结 manifest + SuiteCRM 数据库快照
                    │
                    ▼
             run_manifest.py
                    │
                    ▼
       51条 Train No-Skill 轨迹
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
validate_train_run.py  prepare_learning_inputs.py
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
         21条 Outcome-only        10条 Filtered
                  │                       │
                  └───────────┬───────────┘
                              ▼
        learners/stwebagentbench/generate_skill.py
                              │
                  ┌───────────┴───────────┐
                  ▼                       ▼
        Outcome-only Skill         Filtered Skill
                              │
                              ▼
                      run_selection.py
                              │
                              ▼
                 4 methods × 18 Tasks
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
 validate_selection_run.py       summarize_selection.py
```

## 共用运行环境

激活已有环境：

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
conda activate stwebagentbench
```

内部模型服务必须绕过本地网络代理：

```bash
export NO_PROXY='localhost,127.0.0.1,::1,llm-proxy.intra.didiglobal.com,.intra.didiglobal.com'
export no_proxy="$NO_PROXY"
```

SuiteCRM Docker 服务必须已经启动。所有 Runner 共用一个数据库，因此运行任务时不能手动恢复数据库，也不能同时启动第二个 Runner。

## Autonomous GSE v0.1

Autonomous GSE 不要求人工依次调用训练和评测程序。正式入口 `src.skill_evolution.autonomous_gse_benchmark_runtime` 会统一安排三步实验：

```text
当前已接受版本 + 本步固定的17个任务
  → run_evolution_train.py
  → 整理同时带有任务结果和合规判断的经验，并提出候选版本
  → 如果候选版本有效，用 run_evolution_selection.py 重新评测
  → 与当前版本的评测基准比较，并决定接受或拒绝
```

程序会根据当前版本决定是否注入 Skill：`S0_no_skill` 保留基准测试默认提示词，不注入学习得到的 Skill；候选版本或已接受版本则从登记的 `skill.md` 加载。运行前必须核对文件的 SHA-256 内容指纹，确保文件没有被替换。每个任务开始前，`reset_suitecrm_db.sh` 都会把数据库恢复到同一个锁定快照。

### 应该使用的日常命令

```bash
# 只读计划
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime plan

# 重新运行18个S0评测任务，并生成初始评测基准
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime initial-checkpoint

# 只读状态
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime status

# 仅在状态为READY_TO_RUN时执行完整的三步正式实验
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime run
```

`rollout` 是程序内部运行单批任务的入口，不是日常人工命令。正式结果按照用途分层保存：

```text
artifacts/autonomous_gse_v01/
├── raw/
│   ├── train/<parent-or-candidate>/task_*/trial_01/trajectory.json
│   └── selection/<parent-or-candidate>/task_*/trial_01/trajectory.json
└── formal/
    ├── checkpoints/       # 当前版本与候选版本的固定评测证据
    ├── candidates/        # 候选Skill及其来源证据
    ├── steps/             # 各步训练任务、学习经验、模型调用记录和门槛汇总
    └── campaign_report.json
```

### v0.1 已完成的正式结果

实际正式报告显示，本次三步实验已经完成：

- 第1步：候选提议格式无效（`INVALID_PROPOSAL`），继续使用 S0；
- 第2步：候选版本通过评测（`ACCEPT`），成为 S1；
- 第3步：候选提议格式无效（`INVALID_PROPOSAL`），继续使用 S1；
- 最终版本：S1；
- 共运行87条任务记录，调用 Learner 3次；
- 没有运行 Test，也没有遗留失败记录。

适合进入 Git 的正式报告副本位于 `experiments/results/autonomous_gse_v01/campaign_report.json`；完整本机产物位于 `artifacts/autonomous_gse_v01/formal/`。

### 运行安全要求

- 所有程序共享 SuiteCRM 数据库，任何时候都不能并行启动第二个训练、评测或正式实验程序；
- Runner 运行期间不能手动重置数据库；
- v0.1 不能可靠地从中断处继续。如果 `status` 显示 `RUNNING_OR_INTERRUPTED` 且主进程已经退出，不要直接重跑、删除或覆盖中间文件；
- `plan` 和 `status` 只读；`initial-checkpoint` 与 `run` 会调用模型、浏览器、数据库并写入正式文件；
- Test 在 v0.1 中没有获得授权。

## 复现 Day 8–10 手工 POC

以下命令属于较早的手工实验，不是 Autonomous GSE 的日常入口。

### 运行51个训练任务

正式运行51个训练任务：

```bash
python src/adapters/stwebagentbench/run_manifest.py \
  --all \
  --formal \
  --model openai/gpt-5.6-terra
```

运行过程中进行只读检查：

```bash
python src/adapters/stwebagentbench/validate_train_run.py \
  --partial \
  --model openai/gpt-5.6-terra
```

全部完成后进行完整检查：

```bash
python src/adapters/stwebagentbench/validate_train_run.py \
  --model openai/gpt-5.6-terra
```

检查通过后，生成两种学习输入：

```bash
python src/adapters/stwebagentbench/prepare_learning_inputs.py \
  --model openai/gpt-5.6-terra
```

输出：

```text
artifacts/stweb_suitecrm_poc_v01/learning_inputs/
├── outcome_only_manifest.json
├── filtered_manifest.json
└── eligibility_summary.json
```

### 生成两种学习得到的 Skill

`Outcome-only` 使用全部21条成功任务记录；`Filtered` 只使用其中10条成功且没有违规的记录。两次 Learner 调用使用相同的提示词、模型和参数，区别只在输入经验。

正式生成：

```bash
python src/learners/stwebagentbench/generate_skill.py \
  --dataset outcome_only \
  --model openai/gpt-5.6-terra

python src/learners/stwebagentbench/generate_skill.py \
  --dataset filtered \
  --model openai/gpt-5.6-terra
```

选择评测比较以下四种方法：

| Method | Skill |
|---|---|
| `no_skill` | 不注入任何学习得到的 Skill |
| `human_skill` | `experiments/results/stweb_suitecrm_poc_v01/human_skill.md` |
| `outcome_only_skill` | `experiments/results/stweb_suitecrm_poc_v01/skills/outcome_only_skill.md` |
| `filtered_skill` | `experiments/results/stweb_suitecrm_poc_v01/skills/filtered_skill.md` |

### 依次运行四种选择评测

### 正式运行

四种方法共用数据库，必须按顺序运行，不能并行：

```bash
python src/adapters/stwebagentbench/run_selection.py \
  --method no_skill \
  --all \
  --formal \
  --model openai/gpt-5.6-terra

python src/adapters/stwebagentbench/run_selection.py \
  --method human_skill \
  --all \
  --formal \
  --model openai/gpt-5.6-terra

python src/adapters/stwebagentbench/run_selection.py \
  --method outcome_only_skill \
  --all \
  --formal \
  --model openai/gpt-5.6-terra

python src/adapters/stwebagentbench/run_selection.py \
  --method filtered_skill \
  --all \
  --formal \
  --model openai/gpt-5.6-terra
```

如果手工 POC 的评测批次中断，可以重新运行同一条命令。Runner 会先核对锁定输入，再跳过内容兼容的已完成任务，从下一个未完成任务继续。此续跑能力只适用于这里的手工 POC，不适用于前述 Autonomous GSE v0.1。

正式输出：

```text
artifacts/stweb_suitecrm_poc_v01/raw/selection/
├── no_skill/
├── human_skill/
├── outcome_only_skill/
└── filtered_skill/
```

### 检查并汇总选择评测

运行过程中进行只读检查：

```bash
python src/adapters/stwebagentbench/validate_selection_run.py \
  --partial \
  --model openai/gpt-5.6-terra
```

运行过程中只读预览临时汇总：

```bash
python src/adapters/stwebagentbench/summarize_selection.py \
  --partial \
  --model openai/gpt-5.6-terra
```

72条任务记录全部完成后，先做完整检查，再生成正式汇总：

```bash
python src/adapters/stwebagentbench/validate_selection_run.py \
  --model openai/gpt-5.6-terra

python src/adapters/stwebagentbench/summarize_selection.py \
  --model openai/gpt-5.6-terra
```

正式汇总输出：

```text
experiments/results/stweb_suitecrm_poc_v01/selection/
├── summary.json
├── task_results.json
└── method_summary.csv
```

## 如何理解二维状态转移分析

从 Day 9 开始，结果同时从整体和逐任务两个角度分析：

- 整体指标比较任务成功率、合规率和 CuP 的变化，用于判断候选版本是否可以继续演化，以及是否达到部署要求；
- 逐任务矩阵把同一个任务在两个版本下的结果分成“违规失败、违规成功、合规失败、合规成功”，用于定位具体哪些任务变好、变差或发生取舍。

生成分析文件：

```bash
conda run -n stwebagentbench python -m src.skill_evolution.two_dimensional_gate \
  --results experiments/results/stweb_suitecrm_poc_v01/selection/task_results.json \
  --reference no_skill \
  --candidate human_skill \
  --candidate outcome_only_skill \
  --candidate filtered_skill \
  --output experiments/results/stweb_suitecrm_poc_v01/selection/two_dimensional_transitions.json
```

演化门槛允许这样的候选版本继续参与后续实验：所有整体指标都没有下降，并且任务能力或合规性至少一项有所提高。部署门槛更严格，还要求 CuP 明确提高。

当前 ST-WebAgentBench 结果没有本项目定义的违规严重度标签，因此“没有严重违规”这一项无法评测，会记录为 `not_evaluated`。缺少这项证据时，两个门槛都会返回 `quarantine`，意思是结果只能保留研究用途，不能直接部署。

## 预览、正式运行与完整检查的区别

| 模式 | 是否调用模型 | 是否修改数据库 | 是否写正式结果 | 用途 |
|---|---:|---:|---:|---|
| 检查或汇总程序加 `--partial` | 否 | 否 | 否 | 批次运行过程中查看进度和临时指标 |
| Runner 加 `--formal` | 是 | 是 | 是 | 生成可用于正式实验的任务记录 |
| 检查或汇总程序不加 `--partial` | 否 | 否 | 汇总程序会写报告 | 全部任务完成后的最终验收和汇总 |

## 手工 POC 的运行安全约定

- 正式批次开始后，不修改对应的任务运行程序、实验清单、数据库快照或 Skill。
- 不并行运行两个 SuiteCRM Runner；它们共享同一个数据库。
- Runner 运行时不要手动执行 `reset_suitecrm_db.sh`。
- `validate_* --partial` 和 `summarize_selection.py --partial` 是只读操作，可以在 Runner 运行时查看。
- `Test` 在 Selection 结束、结果分析和最终设置冻结前保持封存。
- 出现失败后必须保留失败记录；修复问题并运行同一命令后，最终检查程序会区分尚未恢复和已经恢复的失败。
