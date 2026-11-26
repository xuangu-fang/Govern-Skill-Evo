# V25 Preconditioner v3 完整训练

从原始 initial Skill、空 Memory、第一轮开始，120 题，8 批 × 15 题，1 epoch。
原任务顺序、API、模型、Actor 并发 4 / 32768 输出、30 次执行 / 每份程序 6 次请求、
无整题累计时限、API 300 秒、程序 600 秒以及无评分纠错反馈保持不变。
仅 Preconditioner 方法版本改为 v25_preconditioner_history_and_plan_v3，使用启动时源码。
旧实验保留；两轮单模块重放只用于分析，不作为本训练的结果或初始 Memory。
完成重放分析后启动完整训练，不自动启动最终 Test。
