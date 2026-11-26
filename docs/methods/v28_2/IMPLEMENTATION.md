# v28.2 实现与离线验收

2026-11-04。第 4—5 步已交付；正式训练和正式 Test 未启动。当前 Diagnosis / Preconditioner 已升级 Prompt v2，其他 Prompt 和运行合同不变。本轮独立验收见 [修订记录](revisions/prompt_v2/README.md) 与 [报告](revisions/prompt_v2/offline_acceptance.json)；下方 777 项是初始 v1 实现的历史结果，不冒充本轮重跑结果。

## 当前 Prompt v2 验收

本轮离线验收 **274 / 274 全部通过**：v28.2 118 项（含新增 4 项修订测试），SearchQA v28/v28.1 回归 156 项；失败、错误、跳过均为 0。另有 16 项原文/结构范围核对全部通过。网络/子进程访问触发 0，真实模型请求 0，新增正式 v28.2 实验目录 0。

## 初始实现验收记录（Prompt v1）

初始实现的两组验收全部通过，共 **777 项**，失败/错误/跳过均为 0：

| 测试组 | 通过 / 总数 |
|---|---:|
| 新 v28.2 | 114 / 114 |
| SearchQA v28 / v28.1 回归 | 156 / 156 |
| DocVQA v29 / v29.1 / v29.2 / v29.3 回归 | 507 / 507 |

网络与子进程访问被禁止，触发次数 0；真实模型请求 0；各次验收期间保护文件变化 0，新增正式 v28.2 训练/Test 目录 0。初始实现验收时，五份提示词与当次实现任务开始时逐字节一致。SearchQA 验收约 196 秒，DocVQA 回归约 134 秒；运行时间只表示本次离线验证开销。

## 运行链路

独立方法包为 [`src/skill_evolution/v28_2`](../../../src/skill_evolution/v28_2/)，入口为 [`run_v28_2_campaign.py`](../../../scripts/runs/run_v28_2_campaign.py)，正式参数文件为 [`v28_2_searchqa_train600_batch30.json`](../../../experiments/configs/v28_2_searchqa_train600_batch30.json)。方法身份为 `v28_2_campaign_v1`。五个模块直接加载本目录 `prompts/` 的定稿，Diagnosis / Preconditioner 使用 Prompt v2；原 v1 文本及本轮差异保存于 `revisions/prompt_v2/`，其他三个 Prompt 不变。

| 层 | 实现与责任 |
|---|---|
| SearchQA 适配 | `actor_io.py`、`campaign.py`：复用 v28 的纯文本 Actor、数据、原生 EM/F1、完整执行归档及无哈希校验模式；独立方法 provenance，禁止调用旧整包 Gate |
| 五模块 | `grouping.py`、`diagnosis.py`、`preconditioner.py`、`editor.py`、`replay.py`：落实新合同、引用权限及完整输入重建 |
| 无损投影 | `execution_input_view.py`、`replay_input_view.py`：共享重复 system 文本；Replay 只投影 EM 翻转；可恢复原始可见内容 |
| Gate | `gate.py`：按非空 patch 的当前轮归因事件计 G/L；仅 Retain 进入 Selected Skill；新组合不继承 Candidate 分数 |
| Memory | `memory.py`、`memory_operation.py`：顺序提交 `000001` 起；来源重算、字节比较、追加历史、写锁与原子 HEAD；Selected Skill 与 Memory 一起发布 |
| 请求与恢复 | `stages.py`、`output_feedback.py`：六次总额度、仅最新无效输出反馈、来源错误停止、保存响应恢复、合法 null 语义停止不重采样 |
| 编排与最终评估 | `evolution.py`、`evaluation.py`：20 轮单遍；先 Memory HEAD 后轮次游标；冷恢复与审计；最终 Test 仅使用完成后的 Selected Skill |

通用 patch、JSON、容量和传输基础设施继续使用 v27 工具；通用引用语法复用当前 v29.2 的纯解析函数，权限与事实验证仍在 v28.2/SearchQA 内完成。本任务未改写旧方法源码、入口和配置。v28.2 不继承旧实验的 Skill、Memory、Actor 缓存或自动恢复策略。

## 固定参数

- 原优化池 600 题，20×30；最终 Test 1,400 题；原顺序及原始 104 字符 Skill，空 Memory。
- Train/Test 并发 15/15；Actor 32,768 / 300 秒。
- Grouping 32,768；Diagnosis 65,536；Preconditioner 65,536；Editor **32,768**；Replay 65,536；方法请求超时 600 秒。
- thinking enabled、medium、temperature 1.0；原模型和 endpoint。
- 方法/Actor 分别保留 2×/1×尝试序号秒延迟；各六次总尝试，恢复不重置；无语义重采样。
- 输入上限 4,000,000 字符 / 6,000,000 UTF-8 字节；不截断证据，不引入 context window 或 Skill 长度上限。

真实配置只在本地做只读校验，不需要 `.env`、凭证或 provider。合成测试均使用临时目录、虚构问题与手写响应，结束后删除；合成 600/1,400 只是验证规模与调度，不是正式 benchmark 执行。

## 可复现离线命令

在仓库根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/SearchQA/bin/python \
  scripts/verification/verify_v28_2_offline.py --with-regressions \
  --output docs/methods/v28_2/revisions/prompt_v2
```

该命令运行 v28.2 与既有 SearchQA v28/v28.1 回归。验收器禁止网络和子进程，输出 [本轮报告](revisions/prompt_v2/offline_acceptance.json) 与 [完整日志](revisions/prompt_v2/offline_acceptance.log)。报告中的成功计数和错误明细以实际执行结果为准。v28.2 集成测试用会失败的 SHA/digest 替身验证没有哈希调用；旧版本回归保留各自原有校验方式。

DocVQA 回归使用已有 DocVQA 环境（SearchQA 环境不含 Pillow），另存报告，避免更改任何环境依赖：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/DocVQA/bin/python \
  scripts/verification/verify_v28_2_offline.py --docvqa-only \
  --output docs/methods/v28_2/regressions_docvqa
```

[DocVQA 回归报告](regressions_docvqa/offline_acceptance.json) 与 [日志](regressions_docvqa/offline_acceptance.log) 单独记录当前工作区旧版本的回归结果。工作期间观察到既有 DocVQA 文件的并行修改，见 [workspace_observations.json](workspace_observations.json)；本任务未覆盖或回滚这些修改，未迁入这些运行器变更。验收器另外检查各次测试期间的源码字节与提示词是否变化。

仅校验正式配置，不创建 campaign、不读取凭证、不执行 Actor：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/SearchQA/bin/python \
  scripts/runs/run_v28_2_campaign.py train /tmp/v28_2_preflight_only \
  --config experiments/configs/v28_2_searchqa_train600_batch30.json --validate-only
```

`train` 和 `test` 是两个显式子命令。正式运行时，训练使用独立 campaign 目录；恢复加 `--resume`，不能替换配置/提示词或扩大额度。训练结束只导出 `final_skill.md` 和 `training_summary.json`，不会自动启动 Test。`test CAMPAIGN --output SEPARATE_DIRECTORY` 必须在训练完成后显式调用；Test 不创建方法模型 transport、不修改 Memory、不用于选 checkpoint。此处说明入口行为，**本轮未执行正式调用**。

## 关键验收场景

- KEEP / 全文 REPLACE / WITHDRAW 保持 ID、goal、basis；无 Checks；Editor 只接收 Effective Updates 的 id/text。
- patch 原 Parent 定位、共享上下文、同一行不交叠修改、冲突、空/null、CRLF/EOF、子集合法性与精确文本来源。
- SearchQA 浮点 EM、原生冠词标点归一化、F1=1 但 EM=0；F1-only 无 Replay；完整批次先校验再过滤。
- 事件恰好覆盖所有翻转，保留原 P/Q 编号；null 不投票；净收益为正但兼有退化仍 Defer；历史事件不参加当前 Gate。
- Reject/Defer/空 patch 仍按合同记录提议；无变化/全部撤回不追加；无翻转追加无事件轮。
- Memory 重复提交幂等、来源/记录损坏拒绝、旧 head 拒绝、HEAD 原子发布、游标落后一个提交时无 transport 恢复。
- 15 个编排中断位置；Actor/方法请求已保存响应不重发，未知请求占用额度，六次耗尽后恢复不重置。
- 合成 20×30 与独立 1,400 最终评估；Test 隔离、固定 Selected Skill、全覆盖后汇总；原版本回归与源码保护。

离线验收证明合同、接线与恢复行为；不能证明模型判断质量、归因因果性或 SearchQA 成绩提升。未执行的 Selected 子集仍记录 `selected_execution_source=null`，训练摘要不填写其 EM/F1。

`design_validation.json`、根目录初始验收与 `diffs/` 保留历史记录。当前来源索引和审阅说明为 `source_map.json`、`PROMPT_REVIEW.md`；它们的修订前快照保存在 `revisions/prompt_v2/baseline/`。
