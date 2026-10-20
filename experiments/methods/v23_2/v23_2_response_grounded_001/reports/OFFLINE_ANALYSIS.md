# 调用前离线依据

本次复用并核对[最新推导核查](../../v23_2_response_inference_analysis_001/reports/REPORT.md)及其[证据索引](../../v23_2_response_inference_analysis_001/reports/EVIDENCE_INDEX.md)。15组正式有效输出均与真实原始响应、当轮输入及确定性编译一致；无效技术尝试不列入有效对照。[读取凭据](../config/offline_read_receipt.json)记录来源与哈希。本阶段没有模型调用。

| 材料 | 实际观察与可支持认识 | 构造中的越界或合理探索 |
|---|---|---|
| R04 M4／u1 | R03配对轨迹出现持物直接heat/cool及减少设备操作；当前动作候选也支持相应动作 | 对应条件下可形成明确操作；联合编辑、单次轨迹不能证明全部步数收益由这条规则造成，也不能保证任务成功 |
| R04 u2 | 当前P6/P8有剩余精确实例并成功回源 | 优先已知剩余实例有当前依据；不能把无反馈重复概括成所有回访无效。symmetric的every listed扩大、calibration的considered once均有边界问题 |
| R05 M6／u2 | R03 Q2漏countertop3且失败，Q4到diningtable后成功，Q6晚取得目标；实际Diff并未隔离换类触发 | 支持兼顾同类其他实例，不证明遗漏由换类导致。alignment保留这种区别；construction近期启发式可探索但不是全局访问记录；symmetric少量批次有动机而尺度未说明；calibration把穷尽认识转成换类顺序，最终文本仍有歧义 |
| R06 M10／u2 | R05实际Diff反对穷尽／循环一类，Q6/Q8到此前漏查位置后成功，Q10增步；Parent也到过countertop1，M10的“新类别”概括不完全准确 | 支持改善覆盖，不唯一支持类内穷尽或轮换。V23与construction未充分处理原案调度及保证；alignment另加每类采样终止；symmetric扩成完整全局排序；calibration预算采样有动机但尺度／次序未充分定义 |

共同问题主要是“能够支持的认识→具体策略”，部分先在“观察→原因”发生扩大。R04有同条件下的具体正向动作和可用候选，搜索反例多数只说明遗漏／太晚／重复，不能唯一决定替代调度。合理探索不等于历史已经验证；合理问题动机也不能自动支持整个方案的附带约束。

既有Parent已有all plausible receptacles inspected once，不能将所有后续单遍终止都算新增错误；alignment的类别采样替代位置覆盖才是清楚的新边界变化。Checks不是Actor指令；不能把calibration R05 Check的强措辞直接当作Effective的无歧义禁令。固定批次、排序也不是天然错误，缺少的是与具体规定相匹配的问题理由和可检验预期。

本次由此研究理解到构造的连接，不再枚举更多后验检查项。旧行为实验仅说明alignment R06新旧Candidate均5/7，不能证明稳定搜索收益；该行为结果不进入本次模型输入。未使用正式Test。
