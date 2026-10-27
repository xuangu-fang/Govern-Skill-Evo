# P4 候选冻结、接入与离线验收

日期：2026-10-22。本轮完成用户授权的前三项：固定候选文本、登记独立版本、离线验收并构建冻结 R05/R06 待发送消息。**没有启动真实模型、Actor 或 Replay 学习实验，没有发布正式 Memory。**

## 交付

- [原稿](original_prompt.md)：用户文件原始字节副本。
- [候选](candidate_prompt.md) 与 [文字差异](prompt_changes.diff)：只作两处修订，分别澄清新增/修订可并存，以及历史细节不足不等于反驳。
- [调用与兼容说明](../../../../docs/methods/v23_4/MULTI_KNOWLEDGE_P4.md)。
- [输入检查](INPUT_CHECKS.json)、[冻结清单](freeze.json)、[离线构建/核验脚本](prepare_inputs.py)。
- R05：[messages](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/cases/R05/messages.json)、[模型视图](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/cases/R05/model_input.json)、[完整 bundle](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/cases/R05/replay_bundle.json)。
- R06：[messages](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/cases/R06/messages.json)、[模型视图](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/cases/R06/model_input.json)、[完整 bundle](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/cases/R06/replay_bundle.json)。

## 接入方式

登记 `prompt_version="v23_4_replay_multi_knowledge_v1"`，必须同时显式采用 `memory_contract="entries_sources_multi_knowledge_v1"`。旧默认不变；新 Memory 未指定 Prompt 时仍选择 P3 结构模板。三个版本均可重建归档，拒绝未知版本、契约不匹配和跨版本复用。

生产代码只修改 `v23_4/replay.py` 的版本选择、装配和重载边界，增加候选模板；未修改 Memory Schema、D/S/C、压缩算法、Actor、Editor 或 Gate。相对本轮开始状态的代码差异见 [code_changes.diff](code_changes.diff)。

P4 主文不加占位符，由程序追加 Actor 背景、Memory v3、Pair 和多 Knowledge 说明；每段只出现一次。输出仍为一次调用中的 `entries[{revises, knowledge[{text,evidence}]}]`。

## 冻结输入检查

| 内容 | R05 | R06 |
|---|---:|---:|
| 当前 Pair / 完整轨迹 | 10 / 20 | 7 / 14 |
| 原 Memory Entry / 兼容包装 Knowledge | 7 / 7 | 7 / 7 |
| 请求字符数 | 995,446 | 965,240 |
| 继承的字符预算 | 1,200,000 | 1,200,000 |
| 实际 input tokens | 未测量 | 未测量 |

实际编辑、Plan、当前轨迹、历史事实与原 Knowledge 文本/Evidence 均未变。仅对旧 Entry 作单项数组包装，不提前语义拆分。相对旧单 Knowledge 输入，只改变 memory.entries 表示；相对 P3 新格式输入，User 消息逐字一致。模型配置及原有最多三次技术重启等调用限制从上一轮冻结配置原样继承，本轮不执行它们。

冻结文件总计 62 个，包含代码、模板、输入、历史 Pair 归档来源和实际 Editor 产物。`prepare_inputs.py verify` 重算全部哈希并重建 messages，已通过。

### 原实验归档边界

R05/R06 不是生产 Editor 的 run.json 归档。初次尝试生产血缘加载时遇到缺少 run.json，随后按旧实验已有的专用归档方式核验：原始 response 与 parsed 一致，严格应用 Editor Patch 得到 Candidate，actual.diff 与 bundle 一致，Plan/background 与冻结 material 一致。没有为其补造 run.json，也没有放宽生产校验。

因此待发送消息已准备好，但不能宣称这两份旧 bundle 通过了生产 `validate_bundle`。后续 P6 应沿用原实验调用路径，并为原样输出显式选择新契约校验；生产版本化运行器的完整链路由本轮合成测试独立验证。

## 离线验收

- 新增 P4 测试 **25 passed**，2.24 秒；见 [p4_tests.xml](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/p4_tests.xml)。
- V23/V23.3/V23.4 完整回归：**987 项，977 passed、1 failed、9 errors**，80.82 秒；见 [pytest.xml](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/pytest.xml) 与 [TEST_RESULTS.json](TEST_RESULTS.json)。
- 10 个失败/错误节点与 P3 完全相同：9 个正式评估冻结源码检查、1 个 Gate 历史 Editor Prompt 检查。未跳过测试、修改冻结记录或放宽这些校验。
- **11,549 个受保护文件 hash 未变**，包含正式历史 Memory、旧实验、旧默认与 P3 Prompt、用户原稿。见 [INTEGRITY.json](INTEGRITY.json)。

测试覆盖：两处文字修订、装配唯一性、三版本重载、空 Memory 版本拒绝、错误视图/模板/归档/配置拒绝，以及同一 Replay 输出同时新增和修订后，经隔离提交、重载、Preconditioner Adjustment/Patch、Effective Plan 到 Editor 的交接。测试使用人工响应，不能据此判断模型是否会保留重要历史认识。

初轮测试发现测试夹具误用了已有 pc/editor 目录，已改为独立 next_pc/next_editor；未修改生产代码来绕过复用保护。修复后定向与完整回归结果如上。

## 尚未验证

重要历史比较是否保留、Knowledge 粒度是否合理、每条 Evidence 是否充分、是否出现事实混淆及冗余膨胀，仍需真实 R05/R06 实验。P4 候选准备和本轮离线技术验收完成，不代表 P6 的语义要求已经满足。
