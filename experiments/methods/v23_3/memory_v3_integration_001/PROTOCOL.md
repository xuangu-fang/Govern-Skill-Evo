# v23.3 Memory v3 正式接入与首次可用 A/B

用户授权：按既定顺序接入模型输入层，保留完整 Memory 校验，离线验证后执行一次真实 B 组生产生成，通过后恢复相同压缩输入的 A/B。

## 固定接入

新 v23.3 Preconditioner 默认发送 memory_evidence_view_v3；完整原始 Memory 仍保存在 input.json/run.json，编译器消费完整数据。model_input.json 保存实际视图，memory_view 记录版本。加载时重新计算视图、重建请求、重解析原始响应并重新编译。无版本旧归档按 entries_sources 恢复；旧 v23 默认行为不改。

离线门：正式实现与五组已验收视图逐字段相等；输入不变；新旧归档和 Editor handoff 可恢复；视图篡改及版本不匹配被拒绝；现有 v23/v23.3 相关回归通过。实验代码不作为正式模块依赖。

发送前离线结果：v23.3 134 项通过；v23 543 项通过、9 项 setup errors。9 项均属于旧正式评估冻结检查，涉及的五个 V23 文件与本轮开始快照完全相同，属于接入前已经存在的冻结不匹配；原冻结不改写，也不将这些检查报告为通过。该旧评估问题不阻断已通过本轮投影/编译/恢复检查的新 B 输入验证。证据保存在 results/offline_tests.json。

## 真实输入与预算（发送前冻结）

复用 p3a_first_live_comparison_001 的真实有效 Diagnosis，不重新生成；复用同一 Grouping、Parent、当前执行、Original Plan 与完整 Memory。不是人工理想 Plan。

A 使用原 V23 自由替换 Prompt 与 to.text，B 使用 v23.3 Prompt 与 to.patch；两组都经同一个正式投影器，system 均追加相同格式说明，user content 逐字符串相等。不同之处仅为既定决策 Prompt/输出契约。A 使用实验适配层，不修改 V23 正式默认。

同一内网 deepseek-v4.1-flash，temperature=1、thinking enabled、reasoning_effort=medium、stream=false、timeout=(60,300)。

**两组 max_tokens 均固定为 32768**：此前 16384 已两次被 reasoning 耗尽，本轮为实际 Patch 生成预留较大 completion 总预算。上限同时包括 reasoning 与最终输出，不保证一定生成成功。该变化在发送前同时冻结，不根据输出追加预算或重采样。

最多 2 次逻辑调用 / 2 次 HTTP（B 一次，门通过后 A 一次），没有技术重试、语义重采样或额外 Judge。B 的首次生产结果直接成为 B 臂，不再重跑一个 B。

## 顺序与门

先执行 B 的正式 run_preconditioner，要求 HTTP 成功、finish=stop、JSON/Schema/Patch/引用校验及 Effective Plan 编译通过，并用正式 load_preconditioner 重载一致。合法 Keep 可以通过该门，但不能声称实际修改了 Update。no_change/need_evidence 停点、无 Effective Plan 或技术失败均停止 A；照实归档，不强迫产生 Patch。

B 门通过后执行 A，一次返回后独立验证其原输出契约与编译结果。先落盘 B 的人工评价，再运行 A 并独立评价，最后比较。评价者为当前同一分析者，不声称盲评、独立双评或模型评审。

## 评价与边界

沿用首次 P3-A 的六类评价维度：有效更新、合理但未验证探索、可纠正而未修正问题、新增无依据承诺、必要行为保留、当前不可判断效果。针对实际 Original/Effective/Diff 及证据逐项核查，少改行数或 Patch 合法不直接记为策略更优。结合动作前条件，历史联合修改及单次结果不作因果证明。

分别回答更新粒度、历史是否参与决策、策略质量。没有 no-Memory 对照，历史引用仅是可追溯线索。单个已知开发案例不代表稳定优越性。16/17 的来源计数误差已由用户接受为非阻断，不据此放宽错误步骤、状态、动作、命令内容或引用。

不调用真实 Editor、Actor、Replay、Memory commit 或最终 Test。编译有效不代表 Skill 已落地或任务成功率提高。保留所有原始响应与失败，费用缺失记未知，不展示内部 reasoning。

## 归档

保存修改前源码/测试与既有文件摘要；仅调整本轮所需 v23.3 代码、测试、文档，旧实验不改写。冻结生产源码、Prompt、请求、协议与输入；新增真实结果不覆盖历史结果。仅记录非密请求配置，不保存 Authorization。
