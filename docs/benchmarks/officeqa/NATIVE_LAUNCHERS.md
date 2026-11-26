# OfficeQA SkillOpt / SkillAdam 训练入口

2026-10-29：新增 `scripts/runs/run_officeqa_baselines.py`。这是正式训练的启动入口，当前只完成离线验收，没有调用模型、执行真实题目 rollout 或启动实验。使用现有 `OfficeQA` conda 环境。

## OfficeQA SkillOpt 与 v26.9、SkillAdam 对照

从仓库根目录使用 `OfficeQA` Python。以下命令只解析正式配置、核对数据与源码，输出 JSON。运行目录参数用于解析未来的输出路径；preflight 不创建该目录。

```sh
/Users/didi/miniforge3/envs/OfficeQA/bin/python scripts/runs/run_officeqa_baselines.py preflight experiments/baselines/officeqa_skillopt_deepseek_flash --config experiments/configs/officeqa_skillopt_deepseek_flash.json
```

本配置使用冻结的 50 道 Train 和独立的 24 道 Selection，seed 42，4 个 epoch，每个 epoch 两个普通更新步骤（40 + 10）。公共 Actor 使用 DeepSeek Flash，训练 10 并发、独立测试 20 并发，默认输出 32768，训练 UID0007 和测试 UID0111 各为 65536。优化器使用同模型、thinking enabled、medium、16384。普通和慢更新均按 Selection EM 严格提升选优。训练结束时，入口完成末版 Selection 检查并在 result.json 中记录 best 的路径和 SHA-256。

以后正式训练时，使用同一入口和配置，将子命令换为 `train` 并显式传入 `--start --actor-key-env OFFICEQA_ACTOR_KEY`。Actor 和优化器分别从 `OFFICEQA_ACTOR_KEY`、`OFFICEQA_OPTIMIZER_KEY` 环境变量读取凭据。单独测试可以使用 `evaluate --arm skillopt --skill /path/to/best_skill.md`，入口自动采用 20 并发和 UID0111 的 65536 输出上限。使用 `--training-run <训练目录>` 时，入口从训练记录恢复设置并校验 best 哈希。已有测试使用 `--resume` 时沿用该次测试的冻结设置。独立测试每次使用单独的输出目录。

离线复核覆盖正式清单、请求参数、历史错答的反思输入，以及模拟数据上的完整四 epoch 训练与选优。

```sh
/Users/didi/miniforge3/envs/OfficeQA/bin/python -m pytest -q tests/skill_evolution/v26/test_officeqa_skillopt_profile.py
```

## 已绑定的执行协议

| 部分 | SkillOpt | SkillAdam |
|---|---|---|
| 原生训练器 | `skillopt.engine.trainer.ReflACTTrainer`，不是 SkillAdam 仓库的 SkillOpt 重实现 | `skilladam.methods.skilladam.SkillAdamRunner` |
| 数据 | prepared_v2 Train 50 / Selection 24 | 原 Train 50 + Validation 24 的固定 74 题优化池 |
| 方法逻辑 | 保留原生 Reflect、Aggregate、Select、Update、gate、slow update、meta skill；参数来自上游默认值加显式 native 配置 | 保留原生 patch、采样、gate、Momentum、轨迹压缩、优化器历史与重试；参数显式配置 |
| 初始 Skill | 已选定的 SkillOpt `initial.md` 快照 | 同一快照，不调用 Stage0 |
| Actor | `TrainingSkillOptAdapter → SkillOptAdapter → 公共 Runtime` | `TrainingSkillAdamRunner → TrainingSkillAdamBackend → SkillAdamBackend → 公共 Runtime` |
| Actor 并发 | 每题一个线程池任务，对照配置训练 10、测试 20，按完成顺序写日志 | 训练 10、测试 20；原生评分器可按输入 ID 重排聚合结果 |
| Actor 请求 | 直接 HTTP，300 秒，六次总尝试，临时格式反馈，恢复不补额 | 相同 |
| 最终 Skill | 原生 best Selection；保留末轮 Skill 的最终 Selection 比较与提升 | 原生 final Skill |
| 最终 Test | 训练器不执行 Test；统一 `evaluate` 的固定 172 题、EM/F1 | 相同 |

OfficeQA SkillAdam 的训练 rollout 和同批验证使用 10 个 Actor worker，独立 Test 使用 20 个。旧 SkillOpt 模板使用 4 个 Actor worker，DeepSeek Flash 对照配置使用 10 个。SkillOpt `analyst_workers` 属于优化器并发，保留其原生配置。Actor 与优化器可以使用不同模型、输出额度和请求参数。没有新增统一的 16384 输出上限，也没有把 V26 的严格 EM gate 强加给两套原生优化器。

SkillOpt 子类显式返回 `_env_name='officeqa'`，保留 OfficeQA 专用 analyst Prompt，并传入原生 analyst_workers、minibatch_size、failure_only、edit_budget、seed。原生 `eval_test` 开关还包住最后一次 Selection；launcher 在关闭原生 Test 后单独完成相同评分与严格 best 提升，使用原生 `compute_score` / `select_gate_score` / `skill_hash`。Selection 技术失败会阻止导出，不能当作已有最终结果。

## 配置与命令

配置模板：

- `experiments/configs/officeqa_actor.example.json`：五组比较应引用同一个填写完成的 Actor JSON。
- `experiments/configs/officeqa_skillopt.example.json`：SkillOpt 原生配置覆盖。
- `experiments/configs/officeqa_skilladam.example.json`：SkillAdam 原生配置。

模板中的模型、路由、输出额度和训练预算必须填写；`null` 是待确认项，不是默认实验设置。路径按启动时工作目录解析，建议填写绝对路径。优化器凭据只通过配置指定的环境变量读取，不读取 `.env`，不在归档保存密钥。SkillOpt launcher 目前支持其原生 OpenAI-compatible backend；SkillAdam 同样使用自身 OpenAI-compatible backend。两者优化器 SDK 和应用层重试不统一；SkillOpt 启动时清除既有 ALFWorld 补丁相关的进程重试覆盖，恢复其原生每次调用重试参数和 SDK 默认行为。

下面是使用模板，不是本次执行过的训练命令：

```sh
conda activate OfficeQA
python scripts/runs/run_officeqa_baselines.py preflight /absolute/run/skillopt --config /absolute/skillopt.json
python scripts/runs/run_officeqa_baselines.py preflight /absolute/run/skilladam --config /absolute/skilladam.json

# 只有显式 train --start 才会启动训练请求。
python scripts/runs/run_officeqa_baselines.py train /absolute/run/skillopt --config /absolute/skillopt.json --actor-key-env OFFICEQA_ACTOR_KEY --start
python scripts/runs/run_officeqa_baselines.py train /absolute/run/skilladam --config /absolute/skilladam.json --actor-key-env OFFICEQA_ACTOR_KEY --start
```

`preflight` 不创建 provider、不发请求、不写训练目录；校验任务/页面、Actor 参数、原生配置、安装包与本地源码内容，并生成配置摘要。`train` 冻结 plan、初始 Skill、数据/文档/源码哈希与实际安装包来源；已有目录必须显式加 `--resume`。CLI 不在导入时启动训练。

SkillAdam 优化器使用原生 `create_generation_transport`，仅绑定生成接口；工具执行由公共 Actor 负责。优化器 `base_url` 显式写入 recipe，并覆盖传给原生 transport 的环境映射，防止恢复时仅更换环境变量就静默切换路由；无需另外导出该 URL 环境变量。

## 恢复目录与边界

SkillOpt 沿用原生目录：`native/selection_eval_baseline`、`native/steps/step_NNNN[/batch_K]/rollout`、`selection_eval`、slow/meta 的 prev/curr 子目录以及 `native/final_selection_eval`。每个目录都有独立公共 Actor 日志；禁止把根目录直接用作 rollout 目录。

SkillAdam 公共 Actor 日志位于 `actor/iter_NNN/training`、`validation_parent`、`validation_candidate`；原生 checkpoint、Prompt 交换、Momentum 和 usage 位于 `native/`。即使两个阶段题目和 Skill 相同，也不共用 Actor 日志。每道题恢复仍遵守公共 Actor 的六次总额度及工具执行状态。

恢复重复原命令并加 `--resume`。原生优化器继续使用各自 checkpoint 语义，没有另加优化器重试或改成 V26 的七模块恢复协议：

- SkillAdam 首轮决策前可能没有 checkpoint。此时保留整个部分输出到 `bootstrap_archives/native_NNN`，重新进入原生首轮；`actor/` 不移动、不清空，因此先前请求额度仍有效。
- 原生优化器可能重新生成尚未 checkpoint 的候选。若候选内容改变，已有同阶段 Actor 身份检查会拒绝复用/覆盖，不能自动删目录补额度。此时应保留归档检查原因，而非宣称可以无条件从任意中断继续。
- SkillOpt 末轮 Selection 提升有单独 receipt，跨 best 文件/状态/summary 写入中断可重放已保存决定；不会重新消费 Actor 请求。
- 完成的 `result.json` 可在身份核对后无凭据读取；不宣称两套训练器都具备 V26 的完整 `archive-only` 模式。

## 五组最终测试

`evaluate --arm` 只负责选择 Skill，然后转交现有 `src.skill_evolution.v26.cli evaluate`；不新增评分器或 Actor。V26 原 CLI 仍可直接使用。五组使用同一个 Actor JSON、prepared_root、parsed_root，每组使用独立输出目录。

| arm | Skill 来源 |
|---|---|
| `no_skill` | 自动传 `--no-skill` |
| `initial_skill` | 自动使用已选定的初始 Skill 快照 |
| `v26` | `--skill` 指定 Campaign 最终选定 Skill |
| `skillopt` | `--training-run` 读取训练 receipt 的 best Skill，或显式 `--skill` |
| `skilladam` | `--training-run` 读取训练 receipt 的 final Skill，或显式 `--skill` |

```sh
python scripts/runs/run_officeqa_baselines.py evaluate /absolute/test/skillopt \
  --arm skillopt --training-run /absolute/run/skillopt \
  --actor-config /absolute/actor.json --actor-key-env OFFICEQA_ACTOR_KEY \
  --prepared-root /absolute/data/officeqa/prepared_v2 \
  --parsed-root /absolute/data/officeqa/corrected_v2/treasury_bulletins_parsed
python scripts/runs/run_officeqa_baselines.py report /absolute/test/skillopt
```

使用训练 receipt 时核对方法名称、Skill 哈希及训练/测试 Actor 参数；显式 Skill 文件路径允许单独评测，调用者应确保比较各组使用同一 Actor 配置。恢复与无凭据报告沿用已有 evaluate 规则，Test 结果不进入优化器更新。

## 离线验收

测试运行真实原生训练循环，模型边界用固定合成响应替代，并禁止网络及 provider client。覆盖公共 Actor 路由、固定并发参数、阶段目录隔离、原生 Prompt、候选 Selection、最终提升、首次迭代与 Momentum 中断恢复、六次耗尽不补额、配置漂移拒绝、五组 evaluate 转发。

验收报告：`artifacts/methods/v26/native_launchers_20261029_001/report.json`。真实数据只做输入、文件及页面检查；模型/网关连通性和正式预算仍待确认。
