# v29 第三阶段：训练主循环、调度恢复与联合发布

2026-11-02 试跑后确认：后续运行采用 Actor 32768、Grouping/Editor 16384、Diagnosis/Preconditioner/Replay 32768；超时沿用 300 秒。正式配置为 `experiments/configs/v29_docvqa_optimization160.json`。首批试跑已完成；按用户要求，其临时配置、执行归档及专用验收输出已删除。

以下待定配置及未启动说明记录第三阶段离线验收时的状态。

2026-11-02。沿用已确认的 DocVQA 设计、v28 阶段顺序与恢复规则，以及 v29 Replay 响应去重和 Memory 单次操作复用修复。所有验收响应均为本地合成；未调用模型、启动真实训练或 Test。

## 配置和边界

- 使用已下载的固定 revision 和原 534 题划分；Train 107 题后接 Validation 53 题，组成 160 题优化池。顺序不变、不打乱、不跨批并行；单次遍历为 10×15＋1×10。
- 初始 Skill 固定为 SkillOpt DocVQA 原始 initial.md，初始 Memory 为空，无 Stage0。Actor API、deepseek-flash 和既定参数保持不变；单批 workers 上限 60，实际并发不超过批次题数。
- 当前正式配置已明确五模块输出额度与超时。`campaign_config()` 默认将每个模块的 max_tokens/timeout_seconds 设为 null；配置验证允许审阅未定配置，执行验证会在任何新 Actor 请求前拒绝它。
- 测试 fixture 中明确给出的额度/超时仅用于模拟请求身份和容量计算，不是正式预算建议或默认值。未复制 v28 batch=30 的预算。
- 新请求需要调用方显式提供 Actor transport 和方法 generate；没有读取 API key、创建 HTTP 客户端或启动训练的隐式路径。独立 Test 编排已接入，执行前必须确认最终 Parent 和全部训练轮次已完成。

## 主循环

每批执行 Parent → Grouping → Diagnosis → Preconditioner → Editor → Candidate → 配对 → hard Gate → Replay → Memory → 发布。五模块输入边界、D/S/C、Plan、补丁、Knowledge Only 和整条 MemoryEntry 修订不变。Replay 继续使用 v2 精简展示，审计保留完整文本。

Diagnosis no_change、全部 Update 撤回、Editor 空 patch 都是合法无更新：保留 Parent/Memory，继续下一批。Editor patch=null 是语义阻塞，记录 stop 后停止；恢复不通过重采样寻找另一份 Editor 输出。没有 Verifier、Repair 或新增判断模块。

Gate 仅比较同批 hard 成功数，严格增加才 ACCEPT；ANLS 不改变选择。ACCEPT 和 RETAIN 都执行 Replay 并提交 Knowledge。即使 Gate 为 ACCEPT，Replay 或 Memory 失败也不会发布 Candidate。

## 请求、反馈和恢复

Actor 使用既有单题与单批恢复接口。五模块阶段使用持久化 slots 001–006，技术失败、length 和识别出的输出合同错误共享六次尝试。有效 no_change/null 不被当作格式错误重试。

技术/length 重试沿用当前请求上下文；输出合同错误只追加最近一次失败的普通响应和定位反馈，不累计所有历史错误，不将反馈作为任务证据。输入/归档错误和未知实现异常停止，不伪装成模型输出错误。

每个方法阶段保存完整 input.json 与独立的 base_messages.json；实际 messages、请求开始记录、响应、解析结果及候选文件保存于尝试目录。结果标记指向已经通过合同的具体 slot。

- 有完整保存响应：恢复同一 slot 的解析与派生文件，不再请求。
- 已开始但响应未知：占用原尝试次数；后续从下一 slot 继续。
- 仅准备请求、尚未写入开始标记：复用同一 slot。
- 已有已选结果：只读重建与核对，不重采样；失败记录与反馈来源也要复核。
- 耗尽六次后恢复不重置额度。API 参数、Prompt 消息、输入及请求身份变化会拒绝混用旧结果。

campaign 启动时先审计已发布轮次，再恢复当前轮次。技术停止或未完成轮次要求显式 resume；语义停止不允许直接恢复重采样。批次摘要丢失时，只有每题 Actor 已完整结束才允许无 transport 重建摘要。

## Parent / Memory 联合发布

官方 state.json 是选择状态的唯一入口，包含 next_round、parent、active_memory。每轮先准备不可变结果与完整 Memory，最后原子替换该文件。准备完成但尚未切换官方 state 的 Candidate/Memory 仍未正式生效。

Replay 后的历史加载、目标 Memory 准备、提交、view 写入和 state 切换共享一个 MemoryOperation。目标目录复用经过精确比较的历史副本；正常发布只做一次完整历史链遍历，每个涉及的 Actor 批次只完整验证一次。目录复制先写临时文件再替换，提交继续遵守先 archive 后 Active 的既有顺序。

发布前核对选中的 Skill、阶段记录、原始 Actor 记录、Memory 的 base/view/Active/commit 与官方游标。中断后丢弃内存复用结果，新适配器从磁盘恢复；已提交的相同 Memory 结果幂等，未完成提交按原规则完成。正常路径的复用没有扩展为跨运行缓存。

`final_parent()` 重建已发布依赖链，要求全部 11 批已结束才返回最终 Skill 路径，不调用模型，不写优化结果。文件一致性使用原文比较，没有引入额外的源码身份框架。

## 接口和验收

正式入口补充验收：108 项全部通过，包含新增模块局部复用测试和 6 项训练/Test 入口测试；534 题静态数据检查通过，离线网络及模型请求数均为 0。报告从已确认配置读取 Actor/五模块额度及超时，清除了旧的预算待定状态。报告见 [validation.json](../../../artifacts/verification/v29_formal_entrypoints_20261102/validation.json)。真实正式训练另存于 `experiments/campaigns/v29_docvqa160_epoch1_20261102_184845/`，其状态不由离线报告代替。

现已补齐 Grouping 请求构造和完整 Replay bundle 构造的局部复用入口，分别在 `grouping_call()` 与 `build_replay_from_editor()` 内自动开启现有 MemoryOperation。公开函数直接调用和主循环调用均覆盖；没有把作用域扩大到模型请求期间。两题合成批次的完整批次验证分别由 8→1、16→2，输出内容与未复用路径一致。新增回归覆盖嵌套作用域、异常/中断释放、调用间归档变化、缓存命中后传入记录变化及退出时依赖检查；结果见 [validation.json](../../../artifacts/verification/v29_evidence_entry_reuse_20261102/validation.json)。

该补充的完整离线验收为 97 项通过（原 92 项加 5 项入口复用回归），0 失败、0 错误；网络及模型请求数均为 0，未启动真实训练或 Test。已有 Memory 发布单次历史遍历和 Replay 消息/输出校验复用检查继续通过。

后续补齐普通 Replay 的局部验证复用：`replay_call()` 的消息构造、`complete()` 的 bundle/输出校验分别使用现有 MemoryOperation，独立调用结束即释放，不在模型等待期间保存作用域。有外层同适配器作用域时保持既有嵌套行为。两批各两题且没有历史来源的合成例中，这两个步骤各验证两次完整批次；涉及历史时按实际不同批次数计算。两步之间的归档变化会被重新检查，作用域退出时的依赖错误继续归类为技术错误，不转成模型输出反馈。该调整没有改变 Prompt、请求内容、评分、Knowledge 或发布合同。

这次补充的验收报告独立保存在 [validation.json](../../../artifacts/verification/v29_replay_validation_reuse_20261102/validation.json)与 [unittest.log](../../../artifacts/verification/v29_replay_validation_reuse_20261102/unittest.log)，保留第三阶段原始验收记录。

入口位于 `src/skill_evolution/v29/`：config.py、campaign.py、stages.py、output_feedback.py、evolution.py。调用在 `with CampaignAdapter(...).using():` 中执行；提供 initialize、run_campaign、run_round、resume_round、final_parent。正式训练及最终 Test CLI 已由 `scripts/runs/run_v29_campaign.py` 接入；使用 `train`/`test` 子命令及显式 `--resume`，默认读取已确认的正式配置。

默认待配置记录见 [v29_docvqa_optimization160_pending.json](../../../experiments/configs/v29_docvqa_optimization160_pending.json)。该文件保留为未填模板，不是正式运行配置；正式入口使用 `v29_docvqa_optimization160.json`。

离线验收覆盖前两阶段及修复回归、方法请求恢复、160 道合成题的完整 11 批调度、ACCEPT/RETAIN、多种无更新、六次耗尽、14 个阶段/发布中断位置、Memory commit/Active 间中断、只读最终审计及发布前依赖变化拒绝。完整发布的历史遍历次数也单独断言为 1，覆盖 prepare、commit、view 与 state 更新。

最终 84 项检查全部通过（前两阶段及修复回归 55 项＋第三阶段 29 项），0 失败、0 错误。真实 534 题和 439 张图片仅做静态读取检查。验收屏蔽网络与子进程，网络及模型请求数均为 0；结果见 [validation.json](../../../artifacts/verification/v29_campaign_phase3_20261102/validation.json)和 [unittest.log](../../../artifacts/verification/v29_campaign_phase3_20261102/unittest.log)。

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_campaign.py --output artifacts/verification/v29_campaign_phase3_20261102
```
