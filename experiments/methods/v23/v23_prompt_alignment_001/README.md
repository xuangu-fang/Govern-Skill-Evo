# V23 Grouping 与 Diagnosis Prompt 统一验证

日期：2026-10-18。直接更新当前 V23 正式源码，未创建平行算法版本。

- [实现与验证报告](reports/REPORT.md)：改动、共享背景、字段迁移、测试和语义核查。
- [本次 Grouping JSON](results/grouping.json)与[本次 Diagnosis JSON](results/diagnosis.json)：原始有效输出，未修正或重新采样。
- [用量与复用汇总](results/summary.json)、[调用前冻结配置](config/plan.json)。
- 完整正式 Prompt：[Grouping](config/current/grouping_prompt.md)、[Diagnosis](config/current/diagnosis_prompt.md)、[共享背景](config/current/execution_context.md)。
- 修改前模板：[Grouping](config/before/grouping_prompt.md)、[Diagnosis](config/before/diagnosis_prompt.md)；[Grouping 差异](config/grouping_prompt.md.diff)、[Diagnosis 差异](config/diagnosis_prompt.md.diff)。这些是实验快照，不是第二套运行模块。
- [本地完整档案](../../../../artifacts/methods/v23/v23_prompt_alignment_001/)保存实际渲染消息、请求、HTTP 响应、Token、解析、校验和测试日志。

210 项测试、19 个子测试通过。四条已有 Parent、93 步、零新增环境执行。Grouping 和 Diagnosis 各实际调用一次 deepseek-flash，均通过结构与引用校验；同输入及同配置复用不新增请求。模型分别生成两个组和含 3 项 Update、3 项 Check 的 revise Plan。

本次仍观察到分组事实概括不准、重复基础协议和更新对全局搜索历史的隐含依赖；新策略也未经过执行验证。原文保留，详情见报告。单次随机调用不能证明 Prompt 的因果改善。没有开发 Preconditioner、Memory、Editor 或 Replay。
