# ALFWorld SkillOpt：原生优化流程、共享 Actor、仅 Best Test

三次独立训练均已完成。每次训练用 18 道 Selection 题选择 Best Skill，随后在同一组 134 道留出题上首测。默认入口执行离线检查。

| 训练 | Best 首测 |
|---|---:|
| [2026-10-30](../../../experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_20261030_001/README.md) | 120/134 |
| [2026-11-23](../../../experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_repeat_20261123_001/README.md) | 117/134 |
| [2026-11-24](../../../experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001/README.md) | 122/134 |

11 月 24 日的 Best Skill 经三次复测，分别成功 116、120、118 题。逐轮对照图取这三次的中位数 118/134。

## 实现与来源

- 入口：`scripts/runs/run_skillopt_alfworld_native.py`。
- 接入代码：`src/skillopt_alfworld_native/`。
- 已准备配置：`experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_20261030_001/`。
- 上游：`https://github.com/microsoft/SkillOpt`，commit `7da46ae693ee0329b80225c0128a37d65db10e9e`。
- 配置包内的 `upstream/` 从这个 commit 的 Git 对象导出，不从带本地改动的工作区复制。现有 `external/SkillOpt` 不变。
- `upstream_source.json` 保存原始文件哈希；唯一修改的上游文件是独立副本中的 `skillopt/engine/trainer.py`，差异保存在 `best_only.patch`。
- 新入口不导入旧 ALFWorld SkillOpt launcher、桥接模块或旧专用配置。共享 Actor 及公共任务清单继续复用。

## 从 Git 检出恢复冻结的上游源码

三份实验配置各自保存了上游提交号、原始文件 SHA-256 和 Trainer 补丁。首次从本分支检出时，在仓库根目录使用以下命令恢复缺少的 `upstream/`。运行需要上述固定提交已存在于本地 `external/SkillOpt`，以及配置记录的 Python 和 ALFWorld 环境。已有完整实验包可直接执行下文的离线检查。

```sh
(
  set -eu
  skillopt_tmp=$(mktemp -d)
  skillopt_python=/Users/didi/miniforge3/envs/skillopt/bin/python
  "$skillopt_python" -B scripts/runs/run_skillopt_alfworld_native.py prepare --experiment "$skillopt_tmp/prepared"
  for run in experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_20261030_001 \
             experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_repeat_20261123_001 \
             experiments/methods/skillopt/alfworld/skillopt_alfworld_native_best_only_third_20261124_001
  do
    if [ ! -e "$run/upstream" ]; then
      cp -R "$skillopt_tmp/prepared/upstream" "$run/upstream"
    fi
    "$skillopt_python" -B scripts/runs/run_skillopt_alfworld_native.py check --experiment "$run"
  done
)
```

`prepare` 从固定 Git 对象导出源码，并生成实验使用的 Best Test 版本 Trainer。`check` 对照各自当时的 manifest 校验文件。历史配置保存了原机器的绝对路径。

训练入口从 `experiments/methods/skillopt/alfworld/<训练ID>/` 读取配置，把正式运行写入 `artifacts/methods/skillopt/alfworld/<训练ID>/campaign/`。逐轮补测保留原 ID，集中在同一训练的 `evaluations/` 下。冻结的配置和历史回执保留当时的路径，由仓库路径映射定位。

## 对齐的已完成实验

Actor 配置、Python runtime 和 Initial Skill 读取自：

`experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/config/`

并与以下 v24.1 配置逐字段核对：

`experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/config/campaign.json`

共享 Actor 源码还与已完成 SkillAdam 实验的 manifest 哈希比较；环境文件与 v24.1 保存的原文比较，冻结为 SHA256。Initial Skill 逐字节复制，不加载任一历史实验的最终 Skill 或优化状态。

| 项目 | 设置 |
|---|---|
| Actor | 官方 `deepseek-flash` / `https://api.deepseek.com` |
| 调用 | temperature=1、thinking enabled、medium、stream=false |
| 输出 / 连接 / 读取 | 16384 tokens / 10 秒 / 300 秒 |
| 执行 | 50 个环境步、10 workers、环境 seed=42 |
| Prompt | `action_only_v1`、最近两步历史、`skillopt_user_v1` 注入 |
| Actor 重试 | 原共享实现每步最多 6 次请求，严格响应校验、无效动作错误反馈 |
| 环境 | 原 `/Users/didi/miniforge3/envs/alfworld/bin/python` 和 `/Users/didi/.cache/alfworld` |

`actor.json` 只提取 Actor 字段，不复制来源配置中与优化器有关的旧字段。

## 原生优化器

| 项目 | 设置 |
|---|---|
| Train / Selection / Test | 39 / 18 / 134，清单与上游及共享 Actor 查找清单一致 |
| 训练 | 4 epochs、batch=40、accumulation=1、seed=42；每 epoch 实际 39 题，共 4 次普通更新 |
| 反思 | minibatch=8、merge batch=8、analyst workers=16、max analyst rounds=3、成功和失败均分析 |
| 更新 | 原生 patch，cosine 编辑预算 4 至 2 |
| 普通 Gate | 原生 hard 严格提升规则 |
| Slow Update | 启用、samples=20、mixed pairs；按用户约定 `slow_update_gate_with_selection=true` |
| Meta Skill | 启用，保留上游触发时机、上下文与持久化 |
| 扩展选项 | 保持原生关闭的 skill-aware reflection 与 semantic density |

适配器显式返回 `_env_name="alfworld"`；离线检查实际成功/失败反思文本与上游 ALFWorld 文件相等。其他优化器 prompt、采样、模块回退及更新机制均保持上游实现。

优化器也采用官方 `deepseek-flash`，temperature=1、thinking enabled、medium、stream=false。传输层只注入供应商参数并记录请求/响应，不增加重试。各阶段调用额度沿用上游；后端上限为 64000，防止默认 8000 截断原生请求，当前 patch 主要阶段实际请求 16384。

保留上游模块传入的 `retries` 和 SDK 默认重试。冻结的 `openai==2.50.0` 默认 `max_retries=2`；原生一次 `retries=3` 后端调用在持续可重试错误下最多产生 9 次 HTTP 请求。这个数字不是整个模块或整个训练的总预算。解析失败和合并回退仍由上游处理；Actor 的六次预算不套到优化器。不会加载旧启动器的 MAX_ATTEMPTS 覆盖。

## 仅 Best Test

独立 Trainer 副本新增 `eval_initial_skill` / `eval_final_skill` 两个默认保持原生行为的开关，本配置均设为 false；`eval_test=true`。

- 保留 Initial Selection、普通 Gate、Slow Update Selection Gate、末尾 Final Selection 及 Best 晋升。
- 只允许 `campaign/test_eval` 下的 Best Skill 运行完整 134 题 Test。
- 不创建 Initial Test、Final Test 输出；相关分数及相对 Initial Test 的提升均为 null，不伪造基线成绩。
- 末尾 Selection 失败会停止，不使用未经完整选优的 Skill 继续测试。
- 原生历史、各步 Skill、Best 均保存；完成后另存 `final_skill.md`。Initial 保留在配置包的 `initial_skill.md`。

训练、Selection、纵向比较和 Best Test 的所有 rollout 都调用同一共享 Actor CLI。轨迹转换只保留实际动作、反馈与成功状态，不补写 `<think>` 正文。Actor 技术中断不会变成普通任务失败，也不会被优化器的异常回退吞掉。

## 离线检查与运行

只读离线检查（不会读取密钥或执行 Actor）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skillopt/bin/python -B scripts/runs/run_skillopt_alfworld_native.py check
```

离线测试（模拟 HTTP 和 episode，含原生四 epoch 完整控制流）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skillopt/bin/python -B -m unittest discover -s tests/adapters/alfworld -p test_skillopt_native.py -v
```

`prepare --experiment <全新目录>` 可离线重建配置包，拒绝覆盖已有目录。显式指定 `run --start` 后，入口先检查冻结输入，再加载仓库 `.env` 中的官方凭据。训练结束后只做 Best Test。

显式恢复入口为 `run --start --resume`，要求相同输入绑定和原生 checkpoint。已完成 episode 在完整验证后复用；缺失/未完成记录会停止，不从头重抽题目。未加入人工追加请求或自动恢复授权。锁阻止同一配置包并行启动；已完成运行不能再次恢复。

正式调用审计位于 `campaign/model_calls/`，包括逻辑调用参数及每个 SDK HTTP 请求/响应，不记录认证头或密钥。Actor 原始响应保存在各 rollout 的 episode 目录。`request_usage.json` 分别汇总两类调用的实际 HTTP 数、已知 token 用量及未知用量次数，包含失败尝试。

## 对照口径与验证边界

本接入对齐 Actor、环境和 Initial Skill；原生 39 Train + 18 Selection、4 epochs 与 v24.1/SkillAdam 的 57 题合并优化池、6 批不同，因此不声称训练预算相等。

离线测试覆盖 Actor 消息/错误反馈一致性、六次请求预算、实际 SDK 两层重试、原生解析回退、专用反思 prompt、Gate、末尾 Best 晋升、仅一次 134 题模拟 Best Test、技术中断保护及历史轨迹无请求复用。报告位于配置包 `verification/`。三次正式训练的成绩分别见页首实验记录。
