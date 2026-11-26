# SkillAdam / V25 SpreadsheetBench 对照实验

计划北京时间 **2026-10-26 04:12:52** 启动。准备阶段只进行离线检查，不调用真实模型。

参照实验：`experiments/methods/v25/training/v25_full120_timeline_actor32k_w4_20261026_002/campaign`。
这是共享 V25 实验环境的 SkillAdam 对照，不是官方原始 Actor 的复现实验。

## 已确认的对照边界

统一实验环境；除用户明确指定的训练规模、初始 Skill、任务顺序和重试策略外，保留 SkillAdam 自带的方法参数。方法的任务执行次数可以不同。

| 条件 | 本实验设置 |
| --- | --- |
| 数据 | 同一 Verified-400；80 Train + 40 Val 参与优化，280 Test 隔离 |
| 顺序与规模 | 与 V25 的 batches 完全相同，8 批 × 15 题，1 个 epoch，不打乱 |
| 初始 Skill | V25 原始 initial_skill.md 逐字相同，跳过 SkillAdam Stage0 |
| API 与模型 | 相同内部代理与 deepseek-v4.1-flash；从本机环境加载凭据 |
| Actor | 直接复用 V25 Actor、Prompt、预览、代码提取及持久化实现 |
| Actor 并发与输出 | 并发 4，单次输出上限 **32768 tokens** |
| Actor 预算 | 每题最多 30 次代码尝试，600 秒任务时限；API 300 秒；程序最多 600 秒且受剩余任务时间限制 |
| Actor 重试 | 相同实现，每次代码尝试最多 6 次 API 请求；按 V25 可重试分类与等待策略执行；恢复不重置预算 |
| Actor 反馈 | 仅执行/格式错误；不提供标准答案、错误单元格、评分或答案纠错反馈；成功生成有效工作簿即提交，之后才评分 |
| 执行环境 | 同一 Docker 镜像 ID、Python/库版本，2 GiB 内存、1 CPU、禁网及同样挂载隔离 |
| 评分 | 直接复用 V25 保存值评分，无额外公式重算；hard 与 per-cell 指标精度不变 |
| 预览 | 每表 5 行、20 列、单元格最多 40 字符、总预览最多 100000 字符 |
| Actor 输入容量 | 与 V25 相同：4000000 字符、6000000 UTF-8 字节；超限不静默截断 |
| 优化器基础采样 | 同一 API/模型；SkillAdam 官方 temperature=1、reasoning_effort=medium；代理适配 thinking=enabled |
| 优化器输出 | SkillAdam 官方 **16384 tokens**；不映射 V25 各模块的 32768 配额 |
| 优化器重试 | 用户明确要求对齐 V25：每个逻辑生成阶段最多 6 次总请求，包含技术、截断及格式校验失败；不叠加 SDK 或原生外层重试 |
| 优化器重试输入 | 技术故障/截断保持请求不变；完整输出校验失败携带上一份输出及校验错误，保留原始输入；等待 2×已用尝试编号秒 |
| 训练结束 | 保存最终 Skill、Gate、Momentum、用量和原始轨迹；不自动启动 280 题 Test |

Actor 的请求错误分类和优化器的请求错误分类分别复用 V25 各自实现，二者本来就不完全相同。优化器通过 V25 `request_failure` 识别 HTTP/网络错误，不将未知程序错误或磁盘错误当作模型错误重试。

## 保留的 SkillAdam 方法机制

- 官方 `spreadsheetbench-main-result` 提示词、原生 Skill diff 应用、LLM 轨迹压缩。
- `optimizer_context_limit=96000`、`optimizer_history_turns=null`。96000 是按字符/3.5 估计的历史上下文重置阈值，不是 96000 字符硬截断，也不是整个请求的硬 token 上限。
- Momentum、自适应编辑预算：base=4、minimum=2、beta=0.9、v_max=0.1、metric=hard。
- 原生 Gate：hard 增益≥0.06 或 per-cell 增益≥0.03，同时 hard 降幅<0.08、per-cell 降幅<0.06。
- 每批独立执行训练轨迹、baseline 验证、candidate 验证；不复用 V25 的已运行轨迹。因而原生正常路径最多 8×15×3=360 次任务执行，与 V25 不要求相同。比较效果时同时报告实际请求数与 token 用量。
- SkillAdam 内部 seed=42 保留。V25 使用显式固定任务顺序，没有请求 API seed；本实验也不添加 API seed，不能据此宣称模型采样可逐次复现。

显式覆盖项：官方 15 次迭代改为 8 次、关闭任务池打乱、Stage0 改为用户指定 initial Skill、使用共享 Actor/评分环境、使用统一重试策略。`feedback_loop.patch_attempts=1` 只是关闭第二层重试；桥接器已先调用相同的原生 JSON/patch 校验器，将重试统一限制为每阶段 6 次总请求，不是只允许一次模型请求。

## 证据与反馈边界

共享 Actor 的 `actor_state.json`、`trajectory.json`、请求、模型响应、实际代码、执行日志与 `score.json` 完整保留。向 SkillAdam 原生 condenser 提供证据时，执行记录和实际 Actor 反馈分别标记为 `harness_execution_not_actor_feedback` 与 `actual_feedback_to_actor`；这只是证据格式转换，不会改变 Actor 请求。查询中明确说明最终评分是提交后的证据，Actor 未看到。

不向 Actor 或优化器输入黄金工作簿内容/路径；优化器使用原生指标和执行证据。Task 元数据中的答案区域是原始题目输入的一部分，和 V25 相同。SkillAdam 的原生确定性截取和 LLM 压缩仍然存在；这不是 V25 无损时间线投影的复用。

Momentum 原生工具调用使用 `finish_reason=tool_calls`，在该阶段视为完整输出。重试沿用 V25 的“上一输出＋校验错误”方法，说明文字适配其原生工具输出契约，不要求 Momentum 改为 V25 的 JSON 输出格式。工具调用先在内存副本中校验，通过后才交给原生 Momentum 提交。

## 文件与启动

- `shared_config.json`：完整复制的参照 campaign 配置。V25 方法字段仅作为参照归档，不用于 SkillAdam 算法。
- `skilladam.json`：实际 SkillAdam 方法及传输配置。
- `alignment.json`：配置分类和例外清单。
- `manifest.json`：冻结的脚本、共享源码、SkillAdam 源码、配置、优化数据及依赖指纹。
- `preflight.json`：本地预检与离线测试结果。
- `campaign/`：启动后由原生 SkillAdam 创建；准备阶段不存在。

```sh
/tmp/govern-skill-v25-venv/bin/python scripts/runs/run_skilladam_spreadsheetbench_aligned.py --check
/tmp/govern-skill-v25-venv/bin/python -u scripts/runs/run_skilladam_spreadsheetbench_aligned.py --start
```

启动器在预定时间前拒绝启动；默认仅预检。正式运行独占 `campaign.lock`，拒绝覆盖已有 campaign。仅在存在原生检查点且确认可安全恢复时显式使用 `--start --resume`；未保存完整结果的优化器请求需要先检查归档，不自动重置或重发。此轮延迟启动任务不改变已有 V25 每小时监控范围。
