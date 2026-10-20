# P1调用前设计

P0完成并冻结后才生成本候选。以正式冻结V23 Diagnosis为唯一模板基线，在第三节替换Goal定义与具体策略表达两处要求；全文见[diagnosis_prompt.md](../config/diagnosis_prompt.md)，[精确Diff](../config/v23.diff)。不叠加第一项的可执行性补丁，不沿用任何Preconditioner候选文字。

Goal承载行为改善、保留行为及必要任务／执行约束；具体实现选择进入Updates，使后续替换或撤回策略时Goal仍成立。Update依然要明确策略、条件、范围、强度、依赖与保留要求，允许有当前证据动机的新策略和大幅调整。通过原reason／有用Checks区分观察和预期，不把预期写成已证实或保证效果，一个改善动机也不自动支持附带强制要求。没有把Update改成含糊建议，没有指定任何搜索答案。

保持Grouping→Diagnosis及全部字段、Actor背景、能力要求和判断职责。Diagnosis无Memory输入，Preconditioner无新调用；没有goal_override或编译器修改。本次只以显式prompt_path选择独立配置，默认入口仍使用V23。原src/v23_2历史Prompt不覆盖。

复用local_validation.run_stage、原解析与校验、原HTTP生成器。最小实验适配直接读取原Diagnosis input及request，通过调用前生效的恢复记录确定容量；每个案例最多一个HTTP请求，暂时关闭实验调用范围内的自动重试，不修改共享重试源码。结构失败、截断或网络失败保留原始档案并停止该案例，仍可完成其他案例；合法no_change／need_evidence也不重采样。

按P0的A–E逐项评价，结果不反向修改Prompt。确定性回归覆盖显式模板加载、原始请求一致、Memory缺席、原字段解析与下游输入装配、纯编译兼容、严格一次请求及旧档案保护；不增加语义评分器。测试中的模拟返回仅在pytest临时目录，不能作为真实实验结果。离线测试和配置冻结完成后才执行R04/R05/R06三个真实请求。

本阶段不执行下游模型、Editor、Candidate、Replay、Gate、Actor或ALFWorld。结果只能说明单次固定输入下Diagnosis输出边界是否改善，不证明下游更新或Skill性能改善。若未满足P1验收，报告残留问题并停止，不自动进入P2。
