# V23.4 条件性认识学习候选实验

本轮只重组 Replay 学习 Prompt；候选版本 `v23_4_replay_multi_knowledge_conditional_v2_candidate`，文件 replay_conditional_learning_v2.md。生产注册表和默认 Prompt 不变。

以 P4 学习 Prompt 的 P6 首份合法真实输出为基线：R05 attempt_002、R06 attempt_001。不重跑基线。候选 R05/R06 各一次，顺序 R05、R06。不根据语义结果追加调用或迭代 Prompt。

事实来自原 P6 实际 HTTP 请求：完整 User 字符串保持相同，仅用候选替换 System 的学习主 Prompt 前缀；Actor 背景、Memory v3、Pair、多 Knowledge 说明后缀完全不变。Diff/Plan/轨迹/Memory/原始冻结归档不变。候选输出契约原样复制 P4，使用原 validate_entries 和 MULTI_KNOWLEDGE_CONTRACT。

模型和初始调用配置保持 P6：deepseek-v4.1-flash、temperature=1、thinking enabled/medium、max_tokens=32768、非流式、相同端点与传输超时。复用既定运行器，最多三次技术/格式重启（每案例最多四次 HTTP）。429、可重试网络/服务错误、JSON/引用/结构校验错误按原规则处理；遇到 finish_reason=length 时沿用原规则把后续 max_tokens 提高到65536并记录，不隐瞒参数偏离。没有语义失败重采样，不修补输出。第一份结构合法输出即停止该案例。

技术与格式错误的重启不证明语义改善。基线 R05 本身也经历一次格式失败；比较合法结果，同时报告全部调用成本。两组单次候选不能证明统计显著或稳定。

评价在调用前固定为四方面：

1. 条件性认识：实际编辑、范围、机会、行为与结论之间是否保持关系；未触发/未知不变成无效，未找到不变成全局不存在，总数不替代局部响应。
2. 历史保持与校准：保留重要历史正负与能力保持比较，纠正明显过强解释；完整替换不遗漏有效经验，不机械复制错误。
3. D/S/C 潜在价值：有无更有证据约束的方向、条件/范围、条款相互作用认识。只评潜在价值，不运行下一轮 Preconditioner/Actor，也不宣称实际收益。
4. 成本：新提案与替换后 Active 的条目/Knowledge/长度/引用；原样提交到隔离预览后，比较 Memory v3 与同一固定 Preconditioner 探针的消息字符数。输入字符是离线尺度，不冒称精确 tokens；真实 Replay tokens 使用服务 usage。

明显事实/证据错误仍记录其对采用的影响，不逐案例发明新机制。采用判断：明显改善且历史保持不退化、无严重问题，可保留下一阶段候选；收益接近则优先 P4；有局部错误判断是否会实质误导更新；明显退化不采用。本轮结束必须给明确建议，不自动新迭代。

输出、隔离 Memory、报告全部在本目录；生产、旧 Prompt、旧实验、正式 Active Memory 原样保护。
