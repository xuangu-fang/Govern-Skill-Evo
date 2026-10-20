# P1-B 冻结与调用边界

冻结时间：2026-10-20T05:56:56.431570+00:00（UTC）。Prompt SHA-256：`5f77ec0f1d73d417c6de08d8cc4173c6138db4cb4ac9f0e7bd9a7eaa4f6bde8c`。

- [完整Prompt](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/config/diagnosis_prompt.md)
- [相对P1精确Diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/config/p1.diff)／[相对正式V23 Diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/config/v23.diff)
- [冻结清单](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/config/p1_freeze.json)（沿用P1入口的文件名，stage明确为P1-B）
- [P0固定配置原样副本](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/config/cases.json)
- [设计](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/reports/P1B_DESIGN.md)
- [调用前测试收据](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/config/call_receipt.json)

冻结后禁网测试179 passed；记录时间2026-10-20T05:57:15.172115+00:00，耗时6.320秒。8项实验检查和171项既有契约／局部验证测试，未执行模型。测试报告包含同一冻结哈希；运行入口验证后才允许调用。

正式V23模板与默认模块未变。P1 Goal定义原样保留，本候选只替换策略表达和成功行为保留两段，不新建章节。每例一次实际请求，最多3次，无自动重试；失败亦不修补、不重采样。

准备阶段首次冻结检查因3个共享README哈希变化而中止，未调用模型，未变更候选。入口快照与变化记录均保留；按当前README状态重新核验后冻结。见[准备记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/setup_notes.md)和[漂移记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_construction_001/results/pre_freeze_drift.json)。正式方法、历史输入输出均没有该漂移。
