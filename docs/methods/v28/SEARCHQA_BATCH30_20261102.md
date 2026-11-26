# SearchQA：v28 与 SkillAdam 的 30 题批次实验

状态：用户于2026-11-02授权启动；北京时间02:29两路正式训练已启动，分别完成后接对应Test。运行控制目录为 `experiments/comparisons/searchqa_v28_skilladam_batch30_20261102_022539/`，每30分钟审查、每路最多3次累计恢复。

## 数据、调度与初始状态

- 使用已有固定版本的本地 `data/searchqa`：Train 400 + Validation 200 合成 600 题优化池，独立 Test 1,400 题。
- 不修改数据正文、数据锁、旧视图 manifest 或题目顺序。新调度将相邻两个旧的 15 题批次合并为一个 30 题批次。
- 两路完全相同的 20 个批次、单 epoch、无重复无遗漏、不打乱；Gate 使用当前批次的相同 30 题。
- 两路均从 `experiments/configs/v28_searchqa_initial_skill.md` 开始，这是此前固定的 SkillOpt initial skill。
- 新建实验目录，不从旧 checkpoint、最终 skill、Memory、Momentum 或优化器历史恢复。旧的 15 题实验保持“已中断／未完成”，不补跑旧 Test。
- SkillAdam 的 `train_size`、`validation_size`、未启用的 `stage0_size` 均为 30；`min_iterations=max_iterations=20`。Stage0 仍禁用。

## 配置文件

- v28：`experiments/configs/v28_searchqa_train600_batch30_epoch1_deepseek_flash.json`
- SkillAdam：`experiments/configs/searchqa_skilladam600_batch30_epoch1_deepseek_flash.json`

旧的无 `batch30` 后缀配置不改写。默认入口仍兼容旧配置；新实验必须显式传入上述新配置。

## 模型与预算

两路 Actor 与优化器均继续使用 `deepseek-flash`，thinking enabled、reasoning_effort=medium、temperature=1.0。训练／Test 并发均为 15／15。

| 阶段 | max_tokens | 请求超时（秒） |
|---|---:|---:|
| 两路 Actor | 32,768 | 300 |
| v28 Grouping | 32,768 | 600 |
| v28 Diagnosis | 65,536 | 600 |
| v28 Preconditioner | 65,536 | 600 |
| v28 Editor | 16,384 | 600 |
| v28 Replay | 65,536 | 600 |
| SkillAdam Patch | 32,768 | 600 |
| SkillAdam Momentum | 65,536 | 600 |

输出预算包括推理 token。Actor 连接超时仍为 10 秒；技术错误和 length 共用六次尝试，SDK 重试为零；六次耗尽停止且不赋零分。v28 方法阶段仍为六次尝试、2 秒乘尝试编号的等待。SkillAdam 保留官方 SDK 重试 2、patch attempts 3；Momentum 的算法和错误传播行为不改，失败后停止分析，恢复复用 Actor/Gate。

v28 不设置 `context_window_tokens`，保留 4,000,000 字符／6,000,000 UTF-8 字节输入保护，不截断证据。SkillAdam 保持 `optimizer_context_limit=200000`、`optimizer_history_turns=null` 和官方确定性轨迹压缩。200,000 是历史清理估算阈值，不是完整请求的硬 token 上限，也不包含输出预留。

## Gate 与算法

- v28：Candidate EM 成功数严格大于 Parent 才接受，F1 仅记录。
- SkillAdam：`(ΔEM >= .04 OR ΔF1 >= .025) AND ΔEM > -.04 AND ΔF1 > -.05`。保持 main-result profile，不按题数缩放。
- 30 题下单题 EM 变化为 1/30：多对一题不足以单独触发 SkillAdam 的 EM 提升条件；少对一题仍可能在 F1 达标时接受。这是原阈值的直接结果，不是新的 Gate。
- SkillAdam 保持官方 Momentum、adaptive edit budget（base=4、minimum=1、beta=.9、v_max=.05）、max_consecutive_failures=10、same_batch、seed=42。20 轮最小迭代数使本次完整单遍不因连续拒绝提前结束。
- v28 五模块方法指令、引用和执行证据契约、Memory 发布、Gate 身份校验不变。五模块渲染时仅把 Actor 运行说明里的输出上限从 49,152 更新为 32,768；Actor 任务 Prompt 本身不变。

## 输入规模依据与限制

下表取自旧的 15 题未完成实验的 provider usage；右列是原峰值的两倍容量参考，不是新 30 题请求的实测值或上界。

| 阶段 | 旧实验最大输入 tokens | 两倍参考 |
|---|---:|---:|
| Grouping | 89,034 | 178,068 |
| Diagnosis | 90,787 | 181,574 |
| Preconditioner | 53,707 | 107,414 |
| Editor | 3,224 | 不按题数直接翻倍 |
| Replay | 206,724 | 413,448 |
| SkillAdam Patch | 62,589 | 125,178 |
| SkillAdam Momentum | 11,969 | 23,938 |

Grouping/Diagnosis 读取整批执行证据；Preconditioner 读取引用证据与 Memory；Editor 主要读取 Skill 和有效计划；Replay 从 30 条 Parent/Candidate 轨迹增加到 60 条。SkillAdam Patch 还受累计历史影响，Momentum 受当前问题列表影响。未来真实轨迹、Memory、修改计划和重试反馈尚未产生，因此离线验证不能保证未来每个请求的精确 token 数。

## 归档与恢复

- 批次调度 SHA、Actor 预算、阶段预算、数据身份及源码快照参与新实验校验，禁止混用旧批次缓存或旧实验状态。
- 将旧实验中已验证的问题列表顺序恢复逻辑纳入本地 Runner：仅按原始 Momentum 请求恢复顺序，随后继续严格比较完整请求；内容变化不能借此绕过校验。
- 新 SkillAdam 配置启用每次 HTTP 原始响应记录，保存请求正文、响应正文、finish_reason、usage 和摘要，发生解析错误时也可查到；不记录认证请求头。
- Patch 与 Momentum 使用独立的固定预算，生成完成或抛错后恢复底层配置，防止 Momentum 预算泄漏到 Patch。
- 官方 SkillAdam 源码、旧实验文件、旧配置及固定数据不修改；新增本地适配代码会形成新实验源码身份，旧实验不能用新源码冒充原快照恢复。

## 离线验证与执行入口

解释器：`/Users/didi/miniforge3/envs/SearchQA/bin/python`。
从仓库根目录设置 `PYTHONPATH=.:external/SkillAdam`。

只读预检（不会调用模型或创建训练目录）：

```bash
python -m src.skill_evolution.v28.cli validate --config experiments/configs/v28_searchqa_train600_batch30_epoch1_deepseek_flash.json
python scripts/runs/run_searchqa_skilladam.py preflight --config experiments/configs/searchqa_skilladam600_batch30_epoch1_deepseek_flash.json
```

本次真实执行已经授权并由独立控制入口启动，不要再手动重复启动。v28 的 run 必须传新配置；evaluate/report 也可传同一 `--config`，确保 Test 使用 32,768 Actor。SkillAdam 的 run/evaluate 同样必须传新配置。Test 只评估完整训练后的固定最终 skill，不参与选择或优化；训练失败时不接 Test。

离线验证覆盖：两路 20×30 调度、全部 2,000 题的 Actor Prompt 对齐、数据不变、Gate 边界、真实 SDK 加 mock HTTP 的阶段预算和原始响应、Actor length 重试、完整五模块流程、Momentum 中断恢复不重跑 Actor/Gate，以及旧 15 题配置的回归验证。

证据目录：`artifacts/verification/searchqa_batch30_20261102/`。其中所有模型响应均来自测试替身；不代表真实训练结果。

重新执行完整离线验收可使用 `python scripts/verification/verify_searchqa_batch30.py --output artifacts/verification/<新的验证目录>`；该入口阻断网络和子进程，不启动真实训练。首次验收为 110 项主检查及 2 项补充检查，修正两处测试夹具后定向复测，最终 112 项均通过。
