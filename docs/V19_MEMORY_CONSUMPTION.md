# 共享 Memory 消费边界 v19.1

Memory Review 与 Evidence Review 共用 `memory_consumption_v19.py`，不增加模型阶段。
档案保持完整；消费视图是派生对象，不覆盖已提交 Memory。

## 契约与状态

`state_view` 读取已有历史判断和 edit 状态，去除完全相同的重复记录；保留不同或
矛盾判断、Gate、联合归因、不确定性和未归因上下文。它不是新的 LLM 总结器，
不把不同 edit 或不同适用范围凭文本相似性合并，不以最新记录覆盖旧反证。
目前尚未实现语义上的“同一问题历轮摘要合并”。不同经验持续增加时，摘要可能
达到上限并停止；因此这是有界消费与安全停止，不是无限轮次自动推进的保证。

来源引用是溯源关系，不自动要求加载全文。两个消费者共用 10,000 个本地代理
summary token 上限；成本基于已有可逆表示测量。单条/总摘要无法容纳时明确失败，
不切字符串、不把未知结论转为 NO_EDIT。完整请求另受原有总预算约束。

## 原文选择

`select_originals` 使用完整 pair/trajectory 单元：保留已引用事件及其可识别调用/
结果。已知反证单元优先，其余按稳定来源顺序选择，历史原文上限 6,000 代理
 token。不将 outcome 正负当作 edit 因果效果，不切断单元以填满预算。

选择记录保存 source digest、加载引用、遗漏数量及遗漏引用摘要。完整来源保留
在 canonical case，可以离线重建全部未加载项，未加载列表不会随历史增长进入
 prompt。遗漏已知反证原文时，Evidence Review 校验禁止 VERIFIED。其他必要
证据不足仍由审阅返回 NO_EDIT；自动选择不保证语义覆盖所有适用条件。

Memory Review 使用摘要及来源索引，不读取历史原文；Evidence Review 使用同一
摘要边界并通过原文选择器加载局部证据。当前 Finding 证据不被历史预算裁剪。
旧 source_findings 正文不重复传入，来源仍保留在档案与引用中。

## 验证与恢复

增长测试覆盖 10,000 条重复记录、2/20/200 个历史证据单元、不同新判断超限、
超大反证、原始档案不变、未加载反证禁止 VERIFIED；相关测试合计 78 项通过。

离线实际数据报告：
- `artifacts/v19_shared_memory_review_001/profile.json`：7 个 edit Memory Review。
- `artifacts/v19_shared_memory_002.json`：8 个 Evidence Review。
- `artifacts/v19_shared_memory_migration_readiness.json`：原始 3 个完成结果复验与阻塞项。

当前 3 个完整 Evidence Review 输入仍超过 32,000，不能恢复。旧结果按原始输入
校验通过，但不得将它们称为按新协议重审的结果。尚未修改正式运行检查点或执行
迁移；后续迁移需显式记录协议混用的复用边界。全部检查离线执行，模型调用为零。

## 真实观察入口（2026-09-28）

Evidence Review 的 32,000 改为观察阈值，默认工程保护上限为 64,000，
不代表 API 硬上限。首次请求及唯一修复共用该检查，不增加 Budget Manager。
已有可逆引用、正文去重和共享消费边界保持不变，不针对具体议题裁剪。

`retry_v19_evidence_reviews.py` 在独立目录完整复制并校验原 local-reviews，
保存代码/来源摘要；复验并保留已完成结果，只请求从未发送的剩余议题。
使用 --execute 才发送请求，结束停在 Compiler/Editor 前。它不是正式 campaign
的 resume 替代品；新结果回接完整闭环需要后续明确迁移。

## 摘要观察阈值修正

10,000 summary token 仅作日志观察阈值，不再阻断；默认摘要工程保护上限
为 64,000，可通过现有 limit 参数配置。没有按本次 10,353 样本裁剪，也没有
新增 Budget Manager。完整请求仍受各阶段已有请求预算限制，因此这项修改
不等于自动放宽 Memory Review 完整请求的 28,800/32,000 检查。

本次没有迁移正式运行检查点或启动请求；源码绑定变化后不能直接原样 resume。

## 完整 Memory Review 请求预算简化

首次请求和唯一一次 repair 统一使用 64,000 本地估算 token 工程保护上限。
取消首次 28,800 限制及固定 3,200 修复预留。32,000 仅为观察阈值，
请求与 profile 记录是否超过，不因此停止，也不追加压缩/检索调用。
摘要仍按上节使用 10,000 观察阈值与 64,000 工程保护。
这些均不是模型/API 硬上限；原始证据、校验契约及最多一次 repair 不变。

第三轮离线复算见 artifacts/v19_round03_relaxed_memory_budget_001/profile.json。
本次没有更改正式实验检查点，没有启动模型。恢复前仍需显式迁移源码绑定。
