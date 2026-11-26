# v27 LMB 实现与离线验收

2026-10-31当前修订：[两路共用Actor截断自动重试](actor_length_retry_20261031/README.md)。当前配置采用新协议；历史实验结果不追溯变更。下文各日期的历史验收记录保留。

2026-10-30，已根据 [review_01 设计包](draft_20261030_001/README.md)实现，并补齐五项审查修复、Actor 完成标记丢失的恢复修复及有明确规模边界的离线验收。本次没有启动真实实验、调用真实模型或评估真实 Test 题目。

## 实现范围

| 部分 | 实现与保留内容 |
|---|---|
| 核心迁移 | [v27 核心](../../../src/skill_evolution/v27/README.md)：沿用 v26 的阶段冻结、输出校验反馈、六次方法请求上限、恢复、Plan 编译、无更新/阻塞分支、Gate 与原子发布；v24.1/v25 的共同契约继续保留 |
| 五个模块 | Grouping、Diagnosis、Preconditioner、Editor、Replay；复制修订稿 Prompt 原文字节，输出 schema 和职责不变。Preconditioner 整项 KEEP、D/S/C、原 ID 与 basis 继承不变；Replay 保留逐 Knowledge evidence 和每 entry 的 Diff＋执行证据并集要求 |
| LMB 适配 | [独立 adapter](../../../src/skill_evolution/v27/benchmarks/lmb/adapter.py)、[Actor](../../../src/skill_evolution/v27/benchmarks/lmb/actor.py)、[事实层](../../../src/skill_evolution/v27/benchmarks/lmb/facts.py)、[评分](../../../src/skill_evolution/v27/benchmarks/lmb/scoring.py)，无 OfficeQA 运行依赖 |
| 数据 | [数据视图构造](../../../src/skill_evolution/v27/training.py)：当前内容 revision，35＋18 合并 53 优化／124 Test，固定六批；保留 source_split 和映射、来源哈希；独立导出，不覆盖 raw/prepared_v1 |
| 运行条件 | 使用已有独立 LMB 环境；deepseek-flash、thinking enabled、medium、temperature=1、Actor 16384 输出、300 秒/10 秒超时、六次技术尝试；优化并发20，Test并发16。stop错误答案或格式不合规不补答；length按原消息重试，与技术错误共用六次总额度 |
| 证据权限 | 普通 content 白名单；raw response 不进入模块输入。Editor 动态输入只有 parent/plan；完整基础协议和运行约束在 system 中。历史 Knowledge 可仅保留历史引用 |
| 评估 | 独立冻结 Skill 与124 Test；初始/v27最终/SkillAdam最终可复用同一入口。Test 无反馈回流。正式最终 Parent 必须完成所有冻结批次 |
| 首版关闭 | Verifier/Repair 接口保留但配置拒绝启用；没有重新设计这两个 Prompt，也未引入 Stage0 |

原始65个文件的来源清单保留历史字节；截至2026-10-31，其中64个当前文件一致，v25/config.py 的 Review 开关变更已单独审查并保存前后快照与差异。详见 [来源核对修订](source_reconciliation_20261031_001/README.md)。`resources/migration_sources.json` 保存迁移底稿哈希。五份 Prompt 当前为v5，运行文本与 actor_length_retry_20261031 快照逐字相同；此前v4快照保留。

五项修复、数据／证据契约补充、C01 完整容量结果和验收边界见 [审查修订记录](REVIEW_FIXES_20261030.md)。后续恢复缺口与回归覆盖见 [Actor 恢复修订记录](ACTOR_RECOVERY_FIX_20261030.md)。复审的两种边界已固化为回归测试；原33／43／49测试报告作为历史记录保留。

## 数据视图

独立视图已写入 `data/livemathematicianbench/v27_skilladam53_v1/`：`manifest.json` 记录来源、成员和哈希，`items.json` 保留原始记录及 source_split/effective_split、确定性选项映射。运行 loader 从受校验的 prepared_v1 构造同一视图，不直接将完整数据行传入 Actor。

固定内容 revision 为 `6f53c5ff7227633ea954b2847cd590314d582047`。`202512:46` 属于 Selection，并进入53题优化池。177题规范化、打乱选项和正确标签均与 SkillAdam 原生函数离线逐题核对通过。

## 验收结果

当前截断重试修订：[v27 64项通过](../../../artifacts/verification/v27_actor_length_retry_final_20261031/validation.json)、[SkillAdam 31项通过](../../../artifacts/verification/lmb_skilladam_actor_length_retry_20261031/validation.json)，两套均零真实模型请求、零网络连接尝试。

使用 `/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python` 执行离线入口，未安装或修改其他环境。

- 历史 [2026-10-31来源核对验收](../../../artifacts/verification/v27_offline_source_reconciliation_20261031/validation.json)：56项测试全部通过，失败0、错误0、跳过0；原53项测试加3项来源核对回归。此前来源冻结失败报告保留，未覆盖或回写。
- 107项设计清单均有测试映射，报告逐项列出对应自动检查的状态；10项历史人工样例仅作补充，本轮未重新执行。不能据此宣称107项语义场景已全部实质验证。
- 完整合成更新链路、ACCEPT/RETAIN、三种 no-change、Editor null、Replay 失败不发布、发布前后中断及恢复均已覆盖。
- Actor/方法请求恢复、六次额度不重置、响应已落盘时不重发、完成记录丢失响应时停止、原始隐藏字段不进入后续模块均已覆盖。
- 完成标记部分丢失时，Campaign Parent／Candidate、Test 和直接 Actor 均停止且零新增请求；混合批次在任何 worker 启动前完成预检。新增“待执行题最前、损坏完成题最后”和“仅有 result 完成标记且内容损坏”两项测试，均覆盖 Campaign／Test，并断言创建线程池前拒绝。真正未完成请求仍可恢复，完整响应落盘后不重发。
- 三组各124道**合成** Test 用例验证独立评估、冻结 Skill、恢复和无 Memory 更新；没有对真实124题发起作答。
- 真实模型请求0、网络连接尝试0、实验启动0；原始数据和 prepared_v1 哈希前后相同。

最新来源核对与测试明细见 [修订说明](source_reconciliation_20261031_001/README.md)。以下保留2026-10-30运行配置验收的历史证据：

- [机器可读报告](../../../artifacts/verification/v27_offline_runtime_config_20261030/validation.json)
- [逐项107场景结果](../../../artifacts/verification/v27_offline_runtime_config_20261030/acceptance.json)
- [C01 容量与超限报告](../../../artifacts/verification/v27_offline_runtime_config_20261030/capacity.json)
- [逐测试状态](../../../artifacts/verification/v27_offline_runtime_config_20261030/test_results.json)
- [测试日志](../../../artifacts/verification/v27_offline_runtime_config_20261030/unittest.log)
- [测试与人工样例映射](../../../tests/skill_evolution/v27/acceptance_map.json)
- [离线验收入口](../../../scripts/verification/verify_v27_offline.py)

## 实现中明确的边界

保留 v27 对诊断 Parent 的复用：正常10题更新为20次 Actor任务执行。SkillAdam 对照的30次来自其训练执行＋两次 Gate 执行的源码核对，本次没有运行 SkillAdam 训练。

当前模块输入采用无损原始 JSON，没有启用去重压缩。容量检查使用实际序列化字符/UTF-8上限，并记录预留输出；正式配置已按用户要求沿用旧版本4,000,000字符／6,000,000字节上限，`context_window_tokens` 改为可选且当前未设置。C01 已构造十题完整配对、增长 Skill／Memory 和完整错误反馈：每 run 8,192字符的固定场景可容纳；16,384字符的较大 Replay 场景被请求前拒绝。测试预算不代表已确认的服务窗口，UTF-8框架估计也不是 provider tokenizer 实测值。

本次未生成正式实验 campaign，也未选择要启动的实验目录。后续运行前可通过 `cli validate` 只读检查显式配置；CLI 的真实运行入口与离线验收入口分开。

当前配置已保存为 [v27_lmb53_epoch1_deepseek_flash.json](../../../experiments/configs/v27_lmb53_epoch1_deepseek_flash.json)，独立环境补装 `python-dotenv==1.2.4`。配置和合成凭据入口均已离线验证；详见 [运行配置对齐记录](RUNTIME_CONFIG_20261030.md)。未创建正式实验 campaign 或发起模型调用。

当前输出协议已采用 [文字描述元素的 DeepSeek 适配](answer_element_words_20261030/README.md)，五个方法 Prompt 版本为 v4；旧 draft 保留历史。

2026-10-31后续修复：[请求及失败尝试归档校验](ACTOR_ARCHIVE_FIX_20261031.md)。配置和主要输出契约不变；最新报告见该修订说明。

当前Actor输出上限为49,152，其他预算不变，见[48k修订与验收](actor_49152_20261031/README.md)。
