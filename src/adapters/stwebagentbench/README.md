# ST-WebAgentBench SuiteCRM Adapter

本目录保存 `stweb_suitecrm_poc_v01` 的 SuiteCRM 数据库恢复、轨迹运行、校验和结果汇总脚本。

本实验使用冻结的 manifest：

```text
experiments/manifests/stweb_suitecrm_poc_v01.json
```

数据规模为：

```text
Train：     51 Tasks，只运行 No Skill，用于学习
Selection：18 Tasks × 4 methods = 72 trajectories
Test：      当前保持封存
```

## 文件说明

| 文件 | 类型 | 作用 |
|---|---|---|
| `reset_suitecrm_db.sh` | 写数据库 | 使用冻结 SQL 快照恢复 SuiteCRM，并检查 Contact、Account 和 Lead 数量。每条轨迹运行前由 Runner 自动调用。 |
| `run_manifest.py` | 调模型、写数据库和轨迹 | Train Runner。只展开51个 Train Task，只运行 `no_skill`，支持正式运行、断点续跑和 failure 保存。 |
| `validate_train_run.py` | 只读 | 校验51条正式 Train 轨迹的 Task、模型、Runner、数据库快照、outcome 和 Safety Report 一致性，并统计 Train 指标。 |
| `prepare_learning_inputs.py` | 只读轨迹；strict 时写索引 | 从正式 Train 轨迹生成 Outcome-only 与 Filtered 学习输入。`--partial` 只预览；strict 模式写入 learning-input manifests。 |
| `run_selection.py` | 调模型、写数据库和轨迹 | Selection Runner。只允许18个 Selection Task和四种 baseline，注入对应 Skill，支持正式运行、断点续跑和 failure 保存。 |
| `validate_selection_run.py` | 只读 | 校验四种方法共72条正式 Selection 轨迹；`--partial` 允许批次尚未完成，strict 模式要求72条全部有效。 |
| `summarize_selection.py` | partial 只读；strict 时写报告 | 在 validator gate 通过后，统计整体、subset、模板宏平均和方法间配对差值。 |

Skill 生成不属于 Adapter，位于：

```text
src/learners/stwebagentbench/generate_skill.py
```

## 数据流

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

## 运行环境

激活已有环境：

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
conda activate stwebagentbench
```

内部 LLM Proxy 必须绕过本地网络代理：

```bash
export NO_PROXY='localhost,127.0.0.1,::1,llm-proxy.intra.didiglobal.com,.intra.didiglobal.com'
export no_proxy="$NO_PROXY"
```

SuiteCRM Docker 服务必须已启动。不要在 Runner 运行时手动恢复数据库或启动第二个 Runner。

## Train 流程

正式运行51条 Train 轨迹：

```bash
python src/adapters/stwebagentbench/run_manifest.py \
  --all \
  --formal \
  --model openai/gpt-5.6-terra
```

运行中只读检查：

```bash
python src/adapters/stwebagentbench/validate_train_run.py \
  --partial \
  --model openai/gpt-5.6-terra
```

全部完成后严格检查：

```bash
python src/adapters/stwebagentbench/validate_train_run.py \
  --model openai/gpt-5.6-terra
```

生成两种学习输入：

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

## Learned Skill

Outcome-only 使用全部21条成功轨迹；Filtered 只使用其中10条成功且零违规轨迹。两个 Learner 运行使用相同 Prompt、模型和参数。

正式生成：

```bash
python src/learners/stwebagentbench/generate_skill.py \
  --dataset outcome_only \
  --model openai/gpt-5.6-terra

python src/learners/stwebagentbench/generate_skill.py \
  --dataset filtered \
  --model openai/gpt-5.6-terra
```

当前四种 Selection 方法为：

| Method | Skill |
|---|---|
| `no_skill` | 不注入 Skill |
| `human_skill` | `experiments/results/stweb_suitecrm_poc_v01/human_skill.md` |
| `outcome_only_skill` | `experiments/results/stweb_suitecrm_poc_v01/skills/outcome_only_skill.md` |
| `filtered_skill` | `experiments/results/stweb_suitecrm_poc_v01/skills/filtered_skill.md` |

## Selection 流程

### 正式运行

四种方法必须顺序运行，不能并行：

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

如果批次中断，重新运行同一条命令。Runner 会校验冻结输入，跳过兼容的已完成轨迹，并从下一个未完成 Task 继续。

正式输出：

```text
artifacts/stweb_suitecrm_poc_v01/raw/selection/
├── no_skill/
├── human_skill/
├── outcome_only_skill/
└── filtered_skill/
```

## Selection 校验与汇总

运行中的只读校验：

```bash
python src/adapters/stwebagentbench/validate_selection_run.py \
  --partial \
  --model openai/gpt-5.6-terra
```

运行中的只读汇总预览：

```bash
python src/adapters/stwebagentbench/summarize_selection.py \
  --partial \
  --model openai/gpt-5.6-terra
```

72条全部完成后，先严格校验，再生成正式汇总：

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

## `--partial` 与正式运行的区别

| 模式 | 是否调用模型 | 是否修改数据库 | 是否写正式结果 | 用途 |
|---|---:|---:|---:|---|
| Validator/Summarizer `--partial` | 否 | 否 | 否 | 批次运行过程中查看进度和临时指标 |
| Runner `--formal` | 是 | 是 | 是 | 生成冻结实验轨迹 |
| Validator/Summarizer strict | 否 | 否 | Summarizer 会写报告 | 最终验收和结果汇总 |

## 运行安全约定

- 正式批次开始后，不修改对应 Runner、manifest、数据库快照或 Skill。
- 不并行运行两个 SuiteCRM Runner；它们共享同一个数据库。
- Runner 运行时不要手动执行 `reset_suitecrm_db.sh`。
- `validate_* --partial` 和 `summarize_selection.py --partial` 是只读操作，可以与 Runner 同时执行。
- `Test` 在 Selection 结束、结果分析和最终设置冻结前保持封存。
- failure 发生后保留 failure 文件；修复后运行同一命令，最终校验器会区分未恢复和已恢复 failure。
