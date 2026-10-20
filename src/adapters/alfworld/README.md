# ALFWorld 大模型单任务运行

从项目根目录执行，使用已有的 `alfworld` conda 环境。额外依赖为 `requests` 和 `python-dotenv`；后者已在本机环境安装。API 从项目根目录 `.env` 读取 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，已有进程环境变量优先；不会把密钥写入轨迹。

```bash
conda activate alfworld
python -m pip install requests python-dotenv
export ALFWORLD_DATA="/Users/didi/.cache/alfworld"

# 离线检查配置和任务路径，不调用模型
python -m src.adapters.alfworld.run_task --dry-run

# 默认运行固定 Train 清单的第一个任务
python -m src.adapters.alfworld.run_task --model deepseek-v4-flash

# 指定另一个 Train 任务；ID 见基础清单
python -m src.adapters.alfworld.run_task \
  --model deepseek-v4-flash --split train --task-id train:0001
```

每次命令只运行一个任务。默认 50 步、每次模型输出上限 1024 tokens、temperature 0.2、DeepSeek thinking disabled、环境 seed 42。模型每轮读取初始目标和完整交互历史，输出单条 `<action>...</action>` 命令。环境返回新观察后继续调用模型。

入口使用 ALFWorld 文字环境的 TextWorld PDDL backend 和 `AlfredDemangler` 名称映射。模型不接收合法动作候选、隐藏事实、专家计划或 `traj_data.json` 答案。此版本没有附加 Skill，也不优化模型权重或 Skill。它是项目自己的基础 Agent，不是 SkillOpt/SkillAdam runner 的逐项复现。

配置的 base URL 后直接追加 `/chat/completions`，与 OpenAI SDK 的 base URL 语义一致；若服务要求 `/v1`，应在 `.env` 的 `OPENAI_BASE_URL` 中包含该路径。内部 `.intra.` 服务绕过系统代理。HTTP 429 以相同对话内容等待 10/20/40 秒，最多重试 3 次，成功响应记录 `api_attempts` 和 `rate_limit_retries`。其他 API 故障或动作格式失败保存已有记录并结束，不自动切换模型或重生成有效输出。

输出保存在每次新建的目录：

```text
artifacts/benchmarks/alfworld/llm_<UTC时间戳>/trajectory.json
```

轨迹包含任务身份、模型请求名称、服务返回模型名称、版本、提示词、预算、初始观察、每一步模型输出／动作／反馈／usage，以及终止状态。`success` 以环境 `won` 为依据；`step_limit`、`environment_ended`、`error` 和 `interrupted` 分别记录，不把运行错误当作正常任务失败。退出码 1 表示运行错误或中断，正常结束的任务是否成功应读取 `won`。

`--max-steps`、`--max-tokens`、`--env-file`、`--output-root` 可以覆盖默认参数。`--split val` 和 `--split test` 会调用模型执行相应划分，只应在实验协议允许时使用。本节入口保持 NoSkill；固定 Skill 已由下文独立入口支持，学习流程尚未接入。

## 独立 Test 集 NoSkill 基线

`eval_test` 固定读取上述 edition 的全部 134 个 Test 任务，每任务执行一次。它调用相同的单任务 Agent；每个任务在独立子进程中重置环境，默认并行 4 个。不同任务不共享对话或记忆。

```bash
# 只检查配置、134 个游戏路径和环境版本
python -m src.adapters.alfworld.eval_test --dry-run

# 新运行：输出目录必须不存在
python -m src.adapters.alfworld.eval_test \
  --model deepseek-v4-flash --workers 4 \
  --run-dir artifacts/benchmarks/alfworld/noskill_deepseek_v4_flash_test_20261013

# 中断后：使用同一配置继续，跳过已有 result.json 的任务
python -m src.adapters.alfworld.eval_test \
  --model deepseek-v4-flash --workers 4 \
  --run-dir artifacts/benchmarks/alfworld/noskill_deepseek_v4_flash_test_20261013 \
  --resume
```

不要同时对同一输出目录启动两个评测进程。除了单个 HTTP 429 请求的有界等待重试，失败的整个任务不自动重跑；已有错误结果在续跑时也保留。若任务没有写出 `result.json`，续跑会从干净环境重新运行该任务，保留此前的时间戳轨迹目录。

对 HTTP 429/500/502/503/504 和网络超时／连接失败，可显式补跑；先确认原进程已经退出，再使用较低并发：

```bash
python -m src.adapters.alfworld.eval_test \
  --model deepseek-v4-flash --workers 1 \
  --run-dir artifacts/benchmarks/alfworld/noskill_deepseek_v4_flash_test_20261013 \
  --resume --retry-runtime-errors
```

补跑从干净环境重新开始，之前的轨迹和日志保留在 `previous_attempts`；总 token 用量包含这些中断的尝试，计分只使用每个任务最后一次结果。模型格式错误和步数超限不在补跑范围内，不能通过重跑它们挑选成功轨迹。

输出目录包含：

- `config.json`：任务清单、模型、完整提示词和固定预算；不含凭据。续跑拒绝模型、清单或协议漂移。
- `summary.json`：运行中持续更新，记录进度、成功数、全部 134 任务分母的成功率、正常终止任务成功率、错误和任务类型分组。
- `task_results.csv`：全量结束后生成的逐任务结果。
- `tasks/test_XXXX/result.json`、`run.log`、`llm_*/trajectory.json`：逐任务结果、控制台日志和完整轨迹。

`all_tasks_attempted` 表示 134 个任务均有结果。模型输出格式无效或被 token 预算截断，计为任务失败，不重试；`model_output_failures` 单列其数量。`runtime_errors` 单列 API、环境等运行故障。`evaluation_valid` 要求全部任务已评测且无运行故障；若有运行故障，全部任务分母的分数仍保留，并明确标记评测未完整有效。不把仅正常终止任务的成功率当作完整 Test 指标。

此基线沿用本项目的提示词、完整历史、50 步、1024 输出 tokens、temperature 0.2、thinking disabled 和环境 seed 42。它是 DeepSeek 下的项目 NoSkill 结果，不是对 SkillOpt 原文模型、提示词和全部参数的严格复现。Test 结果只用于本次基线报告，不用于调整提示词或学习 Skill。

固定任务清单：[39 Train / 18 Selection / 134 Test](../../../benchmarks/alfworld/editions/skillopt_39_18_134/README.md)。

## 上游协议 NoSkill（独立 v2）

`run_task_upstream` 使用固定 SkillOpt commit `343db229dbd5ddaf9df6b1d5540d8bcdb2604d5c` 的原始 `rollout_no_history.md` 和 `rollout_with_history.md`，文件和来源记录保存于基础清单的 `protocol/skillopt_native/`。基础任务清单不变。模型不附加 Skill 文档。

每步构建新的 system/user 两条消息，包含实时合法动作（排除 `help`）、当前观察、任务目标／步数和最近两条动作前的观察及动作；不传入完整旧对话或过去模型推理。首步按上游无历史模板构造。动作仍由模型生成；与上游一致，不强制映射到候选列表。缺失 action 标签或空输出回退为 `look` 并消耗一步，保留原始输出，不提前结束整个任务。

请求固定为 50 步、16,384 输出 tokens、temperature=1.0、thinking enabled、reasoning_effort=medium、300 秒 API 读超时、环境 seed 42。参数取自 SkillAdam 的公开主结果比较协议；DeepSeek 官方将 medium 映射到 high，且 thinking 模式下 temperature 不生效。这些是模型 API 的语义差异，不声称与 GPT 的推理计算量相同。日志记录独立推理内容字符数和服务返回的模型名；不将独立推理内容注入后续消息。

瞬时 HTTP 429/500/502/503/504 最多重试 5 次，发送完全相同的消息。持续 API 故障单列为运行错误，不用 `look` 隐藏服务不可用；续跑只补基础设施中断，成功或正常失败的任务不重新抽样。

```bash
# 上游协议：单个 Train 任务
python -m src.adapters.alfworld.run_task_upstream --task-id train:0000

# Train 入口验证：每种任务类型的首个任务
python -m src.adapters.alfworld.eval_test --runner upstream --split train \
  --task-ids train:0000 train:0005 train:0012 train:0021 train:0027 train:0034 \
  --workers 2 --run-dir artifacts/benchmarks/alfworld/upstream_noskill_train_check_20261014

# Selection 入口验证：每种任务类型的首个任务
python -m src.adapters.alfworld.eval_test --runner upstream --split val \
  --task-ids val:0000 val:0003 val:0006 val:0010 val:0013 val:0016 \
  --workers 2 --run-dir artifacts/benchmarks/alfworld/upstream_noskill_selection_check_20261014

# 入口验证通过后：新的独立 Test 评测，全部 134 个任务
python -m src.adapters.alfworld.eval_test --runner upstream --model deepseek-v4-flash \
  --workers 8 --run-dir artifacts/benchmarks/alfworld/noskill_deepseek_v4_flash_upstream_test_20261014
```

续跑仍使用相同命令和目录，追加 `--resume`；若有瞬时 API 中断，追加 `--retry-runtime-errors`。不要省略 `--runner upstream`。新协议不覆盖旧的 58.21% 运行。Train／Selection 入口检查用于核对调用和环境接口，不根据 Test 结果选择提示词或参数。验证方案和结果位于 `artifacts/benchmarks/alfworld/upstream_protocol_20261014/`。

本次入口检查结果：Train 4/6 成功、Selection 5/6 成功；12 个任务均正常终止，242 步请求逐项匹配固定模板。它们是覆盖六类任务的入口检查，不是全量 Train／Selection 分数。

全量结束后离线核验（不调用模型）：

```bash
python -m src.adapters.alfworld.verify_upstream_run \
  artifacts/benchmarks/alfworld/noskill_deepseek_v4_flash_upstream_test_20261014
```

核验会重算结果，检查任务身份、每步提示词、窗口、动作投影、预算及环境成功标志，并保存 `validation.json`。运行错误会让核验失败；不能通过剔除错误任务生成最终成功率。

## V22 环境接口：No Skill／固定 Skill 单任务执行

新增 `run_task_skill` 复用上游基础消息与动作协议，提供明确的 Skill 快照和独立轨迹格式。默认 No Skill；固定 Skill 在每步 system 消息末尾注入。旧 `run_task`、`run_task_upstream` 与批评测入口不变，新格式用 `verify_skill_run` 核验。

```bash
# 不读取凭据、不调用模型、不写输出
python -m src.adapters.alfworld.run_task_skill --dry-run

# 默认 No Skill，Train 两步入口检查
python -m src.adapters.alfworld.run_task_skill \
  --task-id train:0000 --max-steps 2

# 固定 Skill 文件可选；此 fixture 仅用于验证注入
python -m src.adapters.alfworld.run_task_skill \
  --task-id train:0000 --max-steps 2 \
  --skill-file tests/adapters/alfworld/fixtures/fixed_skill.md

# 替换为实际输出路径，离线核对；Train 可导出下一阶段的学习输入
python -m src.adapters.alfworld.verify_skill_run /path/to/trajectory.json \
  --feedback-output /path/to/new_learning_feedback.json
```

每次执行保存任务与游戏内容身份、Skill 全文/hash、协议/源码版本、实际请求及 HTTP 尝试、动作和原生结果。请求先保存再调用模型，错误和未知用量单列。No Skill 消息保持上游内容不变；固定 Skill 为新增注入协议，不声称复现上游方法的完整 Skill 机制。

用途与 split 必须匹配：默认 `smoke/train`，另外支持 `learning/train`、`selection/val`、`final/test`。只有 Train 允许学习反馈导出。两条轨迹可用 `--compare-with` 核对已记录条件，不输出因果或收益判断。

详细契约、权限、状态和验证记录见 [V22 环境—方法接口](../../../docs/methods/v22/ENVIRONMENT_INTERFACE.md)。此环境入口不包含更新决策；独立的 [V22 无历史更新入口](../../../docs/methods/v22/NO_HISTORY_ROUND.md) 负责 Diagnosis／Editor、候选构造与调用本入口执行，尚无完整 Fusion、Memory 或自动采用逻辑。
