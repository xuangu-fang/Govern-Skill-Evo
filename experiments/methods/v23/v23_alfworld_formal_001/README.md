# V23 ALFWorld 正式实验准备

2026-10-19：**READY，仅准备；没有启动正式运行或 Test。**

- [准备报告与完整六轮任务表](reports/PREPARATION.md)
- [冻结共同协议](config/protocol.json) · [六轮 Campaign 配置](config/campaign.json)
- [No Skill Test 配置](config/no_skill_eval.json) · [V23 最终 Parent Test 配置](config/v23_eval.json)
- [预算](config/budget.json) · [57 条有序优化任务](data/optimization_pool.json) · [六轮分批](data/batches.json) · [134 Test](data/test.json)
- [来源与本地核对](data/verification.json) · [开发任务交集](data/development_overlap.json) · [离线日志](reports/offline_tests.txt)

用户已确认采用 SkillAdam 官方顺序：Train 后接 Selection，10/10/10/10/10/7，**不 shuffle**；保留 seed=42。官方当前数据 profile、SkillOpt 清单与本地清单逐条相同。

`prepare.py` 从已保存公开来源重建/比较准备文件，不联网、不执行任务；`run_offline_tests.py` 禁止外部请求和环境执行；`test_commands.py` 只打印未来 Test 命令，S1 只接受全部六轮完成后的正式 Parent。正式启动命令及恢复边界见报告，本次未执行。

2026-10-19 用户授权：清理已中断的首次 S1，新增 `actor_max_workers=8` 后在同一路径从零 `run`。542 项测试与 19 个子测试通过。冻结任务/参数不变；只并行 Parent/Candidate Episode，顺序交接不变。此前外部用量已发生，不纳入新 S1 统计。当前运行状态以 `artifacts/methods/v23/v23_alfworld_formal_001/S1/state.json` 为准；本目录保留原准备记录。

### R02 输入容量恢复

2026-10-19：通过显式恢复记录将运行中所有模块本地输入容量改为 1000000 字符／1500000 UTF-8 字节；初始冻结配置保留。输出预算仍为 16384。原 S1 已从 R02 Preconditioner 恢复；详情与准确进度见 [恢复报告](reports/INPUT_CAPACITY_RECOVERY.md)，实时状态以 S1 档案为准。

### R04 容量恢复与六轮完成

2026-10-19：原 S1 经显式容量覆盖恢复，本地上限为 4000000 字符／6000000 UTF-8 字节，输出仍 16384 tokens。六轮已全部完成，正式 Parent 为 R05 Candidate，Active Memory 来自 R06；未执行 Test。详见 [R04 恢复、用量和最终结果](reports/R04_INPUT_CAPACITY_RECOVERY.md)。

### 正式 Test：当前技术停点

新增 `evaluate.py run|resume|status`，复用冻结 Test 配置、最终正式 Skill、既有 Actor 及并行任务恢复。离线 577 tests、19 subtests 通过后已真实启动。S0 现完成 69/134，另 6 条网络断流中断；S1 未执行，完整对照尚未完成。发现既有 Actor 未重试 ChunkedEncodingError，需修复兼容并明确 resume，不能把部分结果当作最终成功率。

见 [正式 Test 停点报告](reports/FINAL_TEST.md)。产物位于 `artifacts/methods/v23/v23_alfworld_formal_001/evaluation/`，训练目录保持不变。

### 正式 Test：传输修复后完成（最新状态）

用户授权将 ChunkedEncodingError 纳入同一步最多 3 次请求，并通过明确源码兼容记录恢复原 evaluation。585 tests、19 subtests 通过；原 69 条 S0 零调用复用，6 条原始中断保留。S0/S1 均完成 134 条：104/134（77.61%）→111/134（82.84%），+5.22 个百分点；12 修复、5 退化。已知 Token 合计 7,741,687，仍有原始 6 次未知 usage。训练 3666 文件、既有评估及冻结配置 1481 文件直接字节核对不变。

完整结果、六类统计、全部修复／退化 ID、费用及局限见 [FINAL_TEST.md](reports/FINAL_TEST.md)。机器结果：`artifacts/methods/v23/v23_alfworld_formal_001/evaluation/comparison/results.json`。前文技术停点为历史记录，现已正常完成。
