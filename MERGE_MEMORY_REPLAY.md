# Memory 与 Replay 优化合并验收

2026-11-02，已将独立目录中验收通过的 Memory 与 Replay 优化合并到原目录 `/Users/didi/Desktop/Govern-Skill-Evo`。
20 个补丁文件与已验收版本逐字节一致；所有生产源码哈希一致。验收实际从原目录加载代码，不是继续运行独立目录的实现。

根目录 `MEMORY_OPTIMIZATION.md`、`MEMORY_PUBLICATION.md`、`REPLAY_SHARING.md` 保留独立目录阶段的历史验收记录；其中“尚未合并”的表述描述当时状态。当前合并状态以本文为准。

## 合并后的离线结果

- 全部 **119 项测试通过**，无失败、错误或跳过；另核对 2,000 条数据、4,000 种 Actor 消息构造。
- R01–R10 Replay 输入的内容、引用权限与归档输出校验通过；生成的十轮展示消息与此前独立目录验收结果逐字节相同。
- R10 完整消息：**2,576,022 → 574,568 字符，减少 77.7%**，包含新增 Prompt 说明。没有新的 API token 测量。
- R09 在独立副本中完成真实发布流程，耗时 **16.142 秒**，包含分析器及依赖复核；这不是与历史运行同条件的加速倍数测量。
- Memory 完整加载 **1 次**、历史扫描 **1 次**、完整 Actor 记录校验 **540 次**、批次签名 **18 次**、源码身份计算 **1 次**，保持已验收基线。
- commit、历史提交、Active、view、知识记录、选中 Skill 和最终状态均与原归档一致。冷启动审计、中断恢复和六项篡改拒绝检查全部通过。

## 归档与运行状态

- 现有 **230,943 个实验文件**的路径集合、大小和修改时间保持不变；当前 v28 实验 **6,650 个文件**的 SHA-256 全部保持不变。
- 原启动冻结清单文件、campaign 配置及状态未改写；原有 8 处已跟踪工作区修改保持原样。
- 正式游标仍为 `next_round = 10`，Parent 为 `rounds/R09/editor/attempts/001/candidate.md`，Active Memory 为 `rounds/R09/memory`。
- 两个既有 v28 进程保持暂停状态。未发送进程信号、未调用模型、未恢复训练。
- 本次没有迁移旧实验的冻结源码身份，也没有改写旧请求。正常入口仍拒绝将新源码直接作为旧冻结实验的原身份续跑。

## 验收方式与证据

旧源码与 R01–R10 归档在合并前复制到独立测试副本；测试清单只在副本中重定位文件路径。原清单不变。现有验收脚本使用限定改动白名单的测试身份映射读取旧证据，生产验证保持原样。所有发布及故障注入写入专用验收目录。

- [合并汇总](artifacts/verification/merged_20261102_125536/summary.json)
- [原目录代码加载与源码身份](artifacts/verification/merged_20261102_125536/merged_code_identity.json)
- [119 项回归](artifacts/verification/merged_20261102_125536/regression/validation.json)
- [R01–R10 输入检查](artifacts/verification/merged_20261102_125536/replay_inputs/summary.json)
- [R09 发布、恢复与篡改检查](artifacts/verification/merged_20261102_125536/r09_publication/summary.json)
- [复现参数](artifacts/verification/merged_20261102_125536/verification_commands.txt)

合并前目标文件备份在 `artifacts/verification/merged_20261102_125536/rollback_files/`；新增文件清单及合并前工作区记录在同目录 `premerge.json`。测试用完整旧目录副本位于 `/tmp/v28_merge_20261102_125536/before`，不替代原实验归档。

已保留原 Memory 补丁、Replay 增量补丁和组合补丁。组合补丁反向检查通过，但未执行回退。没有创建新的提交或改动已有分支。
