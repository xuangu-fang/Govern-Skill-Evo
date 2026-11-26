# 新默认配置：Diagnosis 修订与条件性 Preconditioner 验证

用户明确授权在新默认配置下尝试；旧配置验证单独保留，不恢复或混入本轮结果。
使用当前 baseline.configuration 生成并严格验证完整配置；Diagnosis 32,768、Preconditioner 49,152 输出 tokens，每阶段六次总请求、300 秒超时。
Diagnosis 用户消息与此前固定 R05 输入完全一致，历史 Actor 环境仍按原轨迹事实保留，不伪造为当前默认 Actor 环境。
先人工核查 Diagnosis 无违规 fallback，再将真实新计划交给当前未改的 Preconditioner，使用 R05 原 Memory。
判据提前冻结，不进入模型输入；不做语义重采样，不调用 Actor、Editor 或完整训练。
当前使用原生运行器，包含原生时间线说明；与最初独立四案例运行器的系统消息有此差别，且本轮输出预算提升，不能作仅改一句 Prompt 的因果消融。
