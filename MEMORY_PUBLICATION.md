# v28 Memory 完整发布复用与 R09 离线验收

2026-11-02，在独立开发目录 `/Users/didi/Desktop/Govern-Skill-Evo-memory-opt-20261102` 实施。
原实验、Prompt、模型输入格式、数据、评分及 Gate 均未修改；未启动真实 Actor、模型或 Gate 运行。

## 实现

`evolution._finish_replay` 提取并保留真实的 Replay 后发布路径：知识记录、Memory 准备、提交、view 写入、轮次结果和正式 state 写入。整个路径共享一个 `MemoryOperation`。

- 首次加载完整验证历史 bundle、Replay 结果、提交链、Active 快照和原始 Actor 归档。
- 准备目标目录时，精确核对源/目标提交内容及 Active 索引，才复用源快照。保留原有硬链接/复制策略；对本次硬链接导致的合法 ctime 变化作窄范围核对。
- 提交继续使用 v27 的纯合同、条目规范化、引用绑定和原子 JSON 写入格式。用已验证的 archive/contexts/view 计算本轮状态转换，避免重新扫描全部历史。
- 完整构造并验证新 view 后，再写 immutable commit、原子替换 Active，并在本次操作内登记精确的新状态。
- 生成 view 和发布读取同一个已验证状态。正式 campaign state 写入前复核源码、数据、Actor 归档、Memory 文件、目录成员、Active、view、base 收据及选中 Skill。
- 缓存不跨发布操作保留。退出、异常或中断后丢弃；后续恢复重新从磁盘建立证据。

v27 源码未改动，归档格式未改变。新增 v28 提交协调代码保留：目录锁、重复提交一致性、未知 pending commit 拒绝、相同 pending commit 恢复、修订旧条目、单调分配 Memory ID、先 commit 后 Active 的崩溃恢复顺序。

## R09 完整流程结果

| 指标 | 结果 |
|---|---:|
| Replay 后完整发布耗时，含分析器及依赖复核 | **17.204 秒** |
| CPU 时间 | 14.520 秒 |
| 完整 Memory 加载 | **1 次** |
| 历史提交链扫描 `_archive` | **1 次** |
| 完整 Actor 记录校验 | **540 次** |
| 批次签名构建 | **18 次** |
| 源码身份重建 | **1 次** |
| 文件打开 | 36,466 次 |
| 新适配器、空缓存的只读发布审计 | 10.413 秒 |

这次测量从已完成的 Replay 结果开始，实际执行生产 `_finish_replay`，写入独立 campaign 的正式 state；包含知识记录、准备、提交、view、结果收据及最终依赖检查。归档注册和测试夹具复制发生在计时前；没有重新执行 Actor/Gate 或请求模型。

原 R09 归档中，知识记录生成至 `before_publish` 的时间戳区间为 1,620.986 秒，约 27.0 分钟。它是历史运行间隔，不是此次同条件重跑基线；不能把第一阶段的单次加载 461.98 秒或 11.92 秒当作完整发布基线，也不承诺固定加速倍数。

## 一致性及故障验收

- R09 新 commit、全部历史 commit、Active、Memory view、知识记录均与原归档逐字节一致。
- 最终轮次结果、正式 state 和选中的 Skill 与原 R09 一致；输入 bundle、Replay、Gate 未被修改。
- 仅 `base.json` 的源目录路径按隔离 campaign 的真实位置调整，原提交链和状态值不变。时间戳属于本次实际运行。
- 使用新适配器及空缓存只读审计已发布目录，检查后所有文件内容不变。
- 在 `memory_prepared` 中断，正式 state 保持 R09 发布前状态；新适配器恢复成功，结果与原 R09 一致，无重复提交。
- 在 `before_publish` 分别篡改 Active、view、历史 commit、Skill、Actor 响应、冻结源码合同，6 项全部拒绝；正式 state 均未推进。
- 完整离线回归 **111 项全部通过**，包括直接与继承的 v27 commit 输出比较、commit/Active 间中断恢复、pending 和 `.tmp` 恢复、返回值隔离、此前缓存失效及各阶段恢复测试。
- 原实验 **7,214 个保护文件、389 项启动清单、81 个 campaign 冻结源码均未变化**。

## 冻结身份边界

优化版的正常入口仍拒绝旧源码身份。离线脚本首先核对原始源码、冻结清单和仅允许的六个变化文件，然后在测试中显式映射执行身份及 campaign 源码文本，才能让新代码读取旧 R09 证据。实际依赖检查、文件变化检测和结果比较仍启用。此映射不在生产代码中，不能用于混用源码恢复原冻结 campaign。

## 复现和交付

在本隔离目录执行，输出目录应不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:external/SkillAdam \
  /Users/didi/miniforge3/envs/SearchQA/bin/python \
  scripts/verification/verify_v28_memory_publication.py \
  --original-root /Users/didi/Desktop/Govern-Skill-Evo \
  --campaign /Users/didi/Desktop/Govern-Skill-Evo/experiments/campaigns/v28_searchqa600_batch30_20261102_022539 \
  --launch-manifest /Users/didi/Desktop/Govern-Skill-Evo/experiments/comparisons/searchqa_v28_skilladam_batch30_20261102_022539/launch_manifest.json \
  --output artifacts/verification/r09_publication_new
```

- 完整发布报告：`artifacts/verification/r09_publication_full/summary.json`。
- 调用明细：同目录 `stats.txt`、`publication.prof`。
- 完整回归：`artifacts/verification/memory_publication_regression/validation.json`、`unittest.log`。
- 合并前两阶段的完整补丁：`artifacts/v28-memory-publication.patch`。
- 第一阶段代码和补丁快照：`artifacts/phase1-source/`；第一阶段报告：`MEMORY_OPTIMIZATION.md`。

本次只完成隔离实现和验收，没有将补丁应用到原实验。
