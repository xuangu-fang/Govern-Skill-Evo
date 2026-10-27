# R06 change / Patch 一致性单次生成

日期：2026-10-22（Asia/Shanghai）。用户要求仅强化已有双向一致性表述，并以相同 R06 输入重新生成一次 Preconditioner。

本轮将原对应段落替换为用户给出的两句话：

> Every substantive added action, prerequisite, or ordering must be specified in `change`. The patch must implement these decisions without introducing additional behavioral requirements.

不增加 fallback 合理性机制、不改变 Goal 冻结与 Checks 规则、不修改校验器。R06 Original、Parent、当前事实、Memory、用户消息和 API 参数逐项与 semantic_generation_002 核对相同。旧输入中的单行 / 无末尾换行保持原样；仅 system Prompt 的这一段发生变化。旧响应不修补，旧 Prompt 已保存快照。

仅生成一次 Preconditioner 逻辑结果，取首次结构合法输出；不发送 Editor、Diagnosis、Replay、Actor 或 Judge，不接纳 Candidate 或提交 Memory。技术错误沿用用户已授权的首次加最多三次重启，15/30/60 秒退避；相同消息发送，不附加修复提示。语义不一致不得触发重采样。

沿用已有模型与配置：deepseek-v4.1-flash，temperature=1，thinking enabled，reasoning_effort=medium，stream=false；连接/上传 60 秒、读 300 秒；初始 max_tokens=32768，仅 finish_reason=length 后可增至 65536。HTTP/网络和程序性失败分类沿用首轮运行器。最多一个逻辑阶段、四次 HTTP。复用 prepare 保存的其他案例不在本轮发送范围。

逐 Update 人工核对：

1. change 是否明确表达相对 Original 的所有实质行为变化。
2. Patch 是否完整落实 change，包括条件、许可/强制程度、保留边界和顺序。
3. Patch 是否新增 change 未声明的动作、前提或顺序。

保留要求可通过 change 的明确保留表述覆盖，不以逐词复述作为标准；原有未改行为不误计为新增。若实现仍有偏差，如实保存并定位，不事后重写 change 为 Patch 辩护。本轮不设计 fallback 合理性机制；一致性通过也不等于策略有效、Goal 冲突已解决或单次改 Prompt 存在因果收益。
