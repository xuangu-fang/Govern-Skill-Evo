# v28 Memory 校验复用：隔离实现与 R09 验收

这是第一阶段的历史记录。当前代码已完成跨准备、提交、view 和发布的复用；最新范围、完整发布测量及复现方法见 [MEMORY_PUBLICATION.md](MEMORY_PUBLICATION.md)。

开发目录：`/Users/didi/Desktop/Govern-Skill-Evo-memory-opt-20261102`。
分支：`codex/v28-memory-validation`。该目录是包含当前未提交 v28 代码的独立快照；原实验目录未修改。

## 实现范围

前三项优化已接入 `SearchQAMethod.load_memory` 的一次只读操作：

1. 源码身份完整计算一次，Actor Prompt 模板内容复用。
2. 每个已完成批次只构建一次签名和完整记录索引，保留任务顺序、覆盖、唯一身份、Skill 和配置检查。
3. 同一执行的完整原始归档验证只做一次。每次引用仍比较传入记录和注册记录；命中缓存还须与已验证的精确 JSON 内容一致。返回值继续深拷贝。

`validation.py` 用 ContextVar 保存操作级上下文。结束或异常都会释放；不同适配器不共用上下文。未进入操作的校验仍走原路径。

未修改 `commit_memory` 或 `evolution.py` 的发布调度，未跨多个 load_memory 共享状态，未缓存 Memory view，未改变 Replay 输入、Prompt、评分、Gate 或 Memory 格式。这是前三项的首个实施边界，不代表完整发布流程已经优化或测量。

## 依赖变化处理

首次访问前记录源码、数据、Memory 和已完成 Actor 批次的文件内容哈希及目录成员；操作结束再次核对。文件元数据只补充检测替换/恢复，不单独作为信任依据。

缓存命中属于操作内部的暂时结果：文件在命中后变化，会使整个操作在返回成功之前失败。不会在同一次操作中混用新旧证据。下次操作从磁盘重新建立依据。

保留对绑定数据和 Actor 配置的前后检查；返回值修改不会污染缓存。模板读取保留 Path.read_text 的通用换行转换行为。

## 冻结身份与离线比较

优化版的正常入口仍然拒绝旧源码身份的 R09 归档。

`scripts/verification/verify_v28_memory_optimization.py` 仅在离线测试中使用显式身份映射。它先核对原始冻结代码和四个允许变化的实现文件，再把本次计算的身份映射为原归档身份以进行差分验收。原始响应、记录、Memory 和源码哈希文件均不重写；正式实现没有兼容开关或跳过身份检查的入口。

验收禁用网络和子进程，不调用真实模型，不执行提交/发布。故障注入使用独立 R09 批次副本；源码注入仅在隔离目录临时修改后恢复。

## 复现

在本隔离目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/SearchQA/bin/python \
  scripts/verification/verify_v28_campaign.py \
  --output artifacts/verification/memory_opt_regression_new

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/SearchQA/bin/python \
  scripts/verification/verify_v28_memory_optimization.py \
  --original-root /Users/didi/Desktop/Govern-Skill-Evo \
  --campaign /Users/didi/Desktop/Govern-Skill-Evo/experiments/campaigns/v28_searchqa600_batch30_20261102_022539 \
  --launch-manifest /Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/searchqa_v28_skilladam_batch30_20261102_022539/launch_manifest.json \
  --baseline /tmp/v28_r09_memory_profile_20261102/summary.json \
  --output artifacts/verification/r09_memory_new
```

性能脚本要求输出目录不存在，避免覆盖验收结果。基线是用户提供的旧实现实测，并非本次重新执行的旧实现。

## 验收材料

- 最终完整回归：`artifacts/verification/memory_opt_final_regression/validation.json`、`unittest.log`。
- 最终 R09 验收：`artifacts/verification/r09_memory_final/summary.json`、`stats.txt`、`r09_load_memory.prof`。
- 可审查补丁：`artifacts/v28-memory-validation.patch`。

单次 load_memory 的测试包括依赖快照和结束复核，但不包括之前的归档注册，也不包括提交/发布。不得将本次耗时写成“27 分钟发布已缩短为该秒数”。

## 最终结果（2026-11-02）

| 指标 | 原始基线 | 优化版 |
|---|---:|---:|
| 单次 R09 load_memory，包含 cProfile 与打开统计 | 461.979 秒 | 11.915 秒 |
| 完整 Actor 记录校验 | 20,286 | 540 |
| 批次签名构建 | 20,286 | 18 |
| 源码身份完整重建 | 20,286 | 1 |
| 文件打开 | 3,509,526 | 16,199 |
| 两个 Actor 模板各自读取次数 | 710,010 | 5 |

本次带分析器的单次加载加速约 38.8 倍。不同文件路径由 4,448 增至 5,025，是因为新增依赖快照还覆盖数据文件及完整批次目录。源码身份只完整重建一次，但操作结束仍逐文件复核依赖内容、元数据与成员关系。

逻辑 validate_record 入口仍调用 20,286 次，其中底层完整验证仅 540 次。没有删除调用方的事实、引用或沿革检查。Memory 保持 13 个条目、549 个 sources，精确 JSON 序列化内容一致，SHA-256 为 `80444fd99929165ae5b64ffef46783069d5fd06b883b48c94ab989bd49735861`。

最终完整回归 105 项通过；独立 R09 副本上 4 类篡改（原始响应、批次顺序、Skill、源码身份）分别在操作前和缓存命中后注入，8 项全部拒绝。原实验的 7,214 个保护文件、389 项启动清单和 81 个 campaign 冻结源码均未变化。网络被禁止，未调用模型。

原始基线副本保存在 `artifacts/verification/r09_memory_baseline/`；初版及最终验收分目录保留，以上数字只引用 `r09_memory_final/summary.json`。旧源码身份映射仅用于离线验收，不能用于恢复运行中的冻结 campaign。
