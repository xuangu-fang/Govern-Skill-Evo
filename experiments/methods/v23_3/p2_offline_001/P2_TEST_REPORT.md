# V23.3 P2 测试报告

最终本轮回归：**434 passed in 38.84s**，禁止入口尝试为 0。见 [日志](results/P2-D-01.log)和[逐项结果](results/P2-D-01.json)。这些是离线工程测试，不是 434 个策略、任务或独立算法实验。

## 顺序门控及修复记录

| 阶段/运行 | 实际结果 | 处理 |
|---|---|---|
| A-01 | 216 passed，2 failed | 护栏误拦既有测试构造 Mock HTTP adapter；无真实请求。改为拦截实际 `Session.send` 和 socket，保留既有 `Session.post` Mock |
| A-02 | 218 passed / 4.79s | A 通过，开始 B |
| B-01 | 44 passed，35 setup errors | 研究 Diagnosis 元数据没有 `grouping_directory`；改用已核验的正式 R05 Grouping attempt 002，明确输入预算 |
| B-02 | 78 passed，1 failed | Prompt 契约断言受 Markdown 换行影响；断言归一化显示空白，Prompt 规则不变 |
| B-03 | 79 passed / 13.95s | B 通过，开始 C |
| C-01 | 284 passed / 26.26s | C 通过，开始 D |
| D-01 | 434 passed / 38.84s | D 通过，无未解决失败 |

所有运行日志和 JSON 记录都保留在 [results](results/)，没有覆盖失败结果或用重复成功数增加实验样本量。阶段计数有重叠，也不与此前 99/119 项相加。

## 最终回归构成

| 文件 | 本次通过数 | 责任 |
|---|---:|---|
| 新 `test_update_patch.py` | 44 | 三例六种人工方案、Keep/撤回/停点、非法结构/引用/补丁、精确换行、语义风险反例 |
| 新 `test_preconditioner.py` | 35 | 单次 Mock 调用、完整真实冻结 Memory 输入、响应分层、缺失/篡改、失败不重试、配置/预算 |
| 新 `test_handoff.py` | 32 | 多行 Diagnosis、旧单行不迁移、版本匹配、Editor 应用、跨阶段恢复和失败 |
| 新 `test_integration.py` | 11 | 单行/关联/跨 Update/大范围/Keep/撤回/停点/风险/旧单行的完整交接 |
| 正式 V23 Diagnosis | 73 | 原输入、Schema、引用和归档回归 |
| 正式 V23 Preconditioner | 74 | 原 compiler、停点、引用、归档及 Mock HTTP 失败回归 |
| 正式 V23 Editor | 100 | 原 Patch、校验、归档、边界错误与 Mock HTTP 失败回归 |
| P1-R 兼容测试 | 65 | 原人工多行夹具及纯函数兼容回归 |

## 场景验收与边界

- 单项、多个关联行、多 Hunk、跨 Update、大幅修改均验证 exact text、Goal、Checks 与未改项。原编译器保留原 basis，不把历史 Adjustment basis 擅自写进 Effective Update。
- Keep=`ready + [] + null`；部分撤回需有效 Checks；全撤回=`no_change + 全撤回 + []`；`need_evidence=[]/null`。停点时 Editor 生成计数为 0、无 Candidate 目录。
- JSON/Schema/非法 Diff/错误引用/截断/模拟异常会保留错误与已有原始材料，不发布有效派生结果；再次调用失败目录只重载并拒绝，不重新生成。
- loader 从响应解析、重新应用 Patch 和编译，再比较磁盘派生文件；Original、Parent、Goal、Memory 或 Editor upstream 不一致拒绝。
- 原文本的 LF、CRLF、无末尾 LF、Unicode 和尾空格按原引擎精确保留；旧单行替换不声称保护行内其他语义。
- 人工加入“每个类别采样一次即可结束”可以到达 Candidate；测试属性明确 `semantic_validity=NOT_VERIFIED`。这是程序能力边界的反例，不是方法正确性成绩。

## 可重载样例

[mock_chain/manifest.json](mock_chain/manifest.json) 标记 `HUMAN_MOCK_NOT_LLM_OR_BEHAVIOR_RESULT`。使用真实冻结 R05 Parent/Grouping/当轮 Memory，Diagnosis 为 P1-R 人工多行副本，Preconditioner 为人工 cross Patch，Editor 为人工拼接文本的 Skill Patch。

首次三环节各调用 Fake 一次；第二次运行构建器三个 Fake 调用数均为 0，恢复核对成功。样例 Candidate 仅为接口材料，不能计为 Editor 正确落实策略或真实行为收益。

复现命令（仓库根目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_3/p2_offline_001/run_tests.py D
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_3/p2_offline_001/build_mock_archive.py
```

网络传输有拒绝护栏，Replay/Gate/evolution 入口在测试进程中被拦截；测试只选上述离线文件，不加载真实环境。测试进程护栏不改变仓库源码。正式源文件、历史归档与已有用户修改的最终检查另见 [final_checks.json](results/final_checks.json)。
