# v28 完整调度与方法阶段恢复

实现入口为 `src/skill_evolution/v28/evolution.py`、`stages.py`、`campaign.py`、`config.py`、`evaluation.py` 与 `cli.py`。v27 原文件保持不变；迁移来源已经包含在 `v27_contract_sources.json` 的固定源码哈希中。五模块 Prompt、EM-only Gate、Actor 六次尝试规则不变。

## 固定调度

正式数据从 `data/searchqa` 的既有锁和优化视图读取，原 Train 400 题接原 Val 200 题，不重排。一个 epoch，共 40 批，每批 15 题；训练／Test Actor 并发均为 15。每批完整执行 Parent 和 Candidate 同一组题，再比较 EM 成功数。F1 仅记录。

`campaign_config` 要求调用方显式提供初始 Skill，构造配置不启动 campaign。用户已选定 SkillOpt SearchQA 原始 initial.md；逐字副本和来源哈希位于 `experiments/configs/v28_searchqa_initial_skill.md` 及同名 provenance.json。正式配置校验拒绝漏题、重复题、错序、Test 混入、变更重试预算或模型参数。`run_round` 可限定本次只完成一轮；总调度仍由同一冻结配置决定。

## 方法阶段尝试与恢复

- Grouping／Editor 输出上限 16,384；其余三模块 32,768。DeepSeek、temperature=1、thinking enabled、reasoning_effort=medium 与 v27 一致。
- 技术错误、length 和已识别的输出合同错误共用六次总尝试；SDK 不另行重试。失败间隔为 2×尝试序号秒。
- 仅已识别的输出校验错误可以附加“上一份完整输出＋校验反馈”；技术重试不增加任务证据，也不堆叠全部历史输出。保留最近一次有效反馈。
- 输入错误、归档损坏及未知实现异常不能伪装成模型输出错误；非可重试失败停止。
- 保存完整响应但未完成解析时，在同一槽位恢复，不重发。HTTP 原文已保存时可以恢复解码。
- 请求已开始但结果未知，原槽位计入额度；仅准备消息、尚未写开始标记的槽位可复用。恢复不重置预算、不扩大输出限制。
- 每阶段冻结配置、源码／Prompt 身份、内部输入、基础消息、实际请求消息和容量记账；恢复重新校验派生结果与 Editor 产物。
- 输入字符、UTF-8 字节与输出预留预算在请求前校验，不截断输入。本次正式配置按用户要求不设置 `context_window_tokens`，与 v27 实验一致；只保留字符／字节检查和输出预留记账。可选 token 窗口检查功能仍保留，但未启用，不作为待完成配置项。

## 控制分支和发布

Diagnosis no_change、所有 Update 撤回，以及 Editor 空 patch 都保留 Parent／Memory 并继续下一批。Editor `patch=null` 是语义停止，resume 不能重新采样绕过它。

Candidate 完成后执行配对验证、Gate、Replay 和 Memory 提交。Gate RETAIN 仍执行 Replay／Memory；Gate 决策不传入 Replay 模型输入。Verifier／Repair 仍禁用。Replay 或 Memory 失败时，即使 Gate 已为 ACCEPT，也不发布 Candidate。

每轮先准备不可变结果和新的 Memory 快照，最后原子更新官方 `state.json`。发布前后中断可恢复。恢复与最终 Skill 审计会逐轮重建已经发布的依赖链，核对原 Actor 归档、方法结果、Gate 和 Memory，再接受官方游标。一个 campaign 使用排他写锁，禁止在运行中改源码、预算或配置。

## 独立 Test

Test 必须独立显式调用，使用固定 Skill 和冻结的全部 1400 个 Test ID。Test 不自动接在训练后面，不回写优化状态或 Memory；不允许输出到 campaign 内。支持既有 Actor 归档恢复和无模型调用的报告重算。只有完整覆盖预期 ID 才报告整体 EM/F1；未完成不补零分。

## 离线验收

```sh
conda run -n SearchQA python scripts/verification/verify_v28_campaign.py --output artifacts/verification/v28_campaign_20261101
```

验收工具阻断网络连接与子进程，使用合成 Actor 响应和确定性方法输出，覆盖全部既有组件、多轮 ACCEPT／RETAIN、三种 no-change、Editor 语义停止、Replay 六次耗尽、40×15 合成调度、阶段边界及发布前后中断、方法请求恢复与 Test 隔离。正式数据只做本地身份、顺序和配置检查，不运行题目。

本次 89 项测试全部通过，失败和错误均为 0；网络／子进程尝试为 0，数据与 v27 源码保持不变。报告路径：`artifacts/verification/v28_campaign_20261101/validation.json`。这项验收不能证明模型生成质量或线上服务容量。初始 Skill 已选定，用户已确认与 v27 一样不设置 `context_window_tokens`；既定配置已完成，真实训练尚未显式启动；本次不创建真实 campaign，不读取凭据，不启动训练或真实 Test。

## CLI 环境与只读入口

从项目根目录运行 CLI 时，显式加入本地冻结的 SkillAdam 源码路径；不需要另行下载或安装另一版本：

```sh
PYTHONPATH=.:external/SkillAdam conda run -n SearchQA python -m src.skill_evolution.v28.cli validate --config /absolute/path/to/campaign_config.json
```

`configure --initial-skill <path> --output <path>` 只构造配置；`validate --config <path>` 只检查配置；`audit <campaign>` 重验完整已发布链；`report <test-directory>` 重算归档报告。它们均不读取 API 密钥。只有显式调用 `run` 或 `evaluate` 才创建真实请求 transport，密钥由 `--api-key-env` 指定的环境变量提供（默认 `OPENAI_API_KEY`）。本轮仅验证只读入口，没有调用真实 run/evaluate。
