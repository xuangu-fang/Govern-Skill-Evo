# A组输出格式澄清验证

用户授权在Prompt补充格式说明后重试A。仅在原Output Format中补充一段，明确Adjustment与replacement Update的字段归属、非空证据/解释，以及逗号分隔当前引用。保留原输出Schema、策略规则、Prompt其他文本、Original Plan、当前证据、空Memory、Actor背景、模型和参数。

原A/B system完全相同；本次A的system改变，因此不与原B声称严格Memory单变量对照。B不重跑，不改变正式默认配置。一次HTTP，零自动重试，不人工修改输出；合法输出即接受，不按策略好坏择优。

四次完整A均把basis/reason放入to条目，原A另有一次读取超时。B仅一次成功，不能证明有Memory能够保证格式可靠性。字段映射混淆和生成随机性是解释候选，不声称已证明模型内部机制。

验收：实际请求与本次冻结一致，除了system外与原A完全一致；原解析器/编译器接受。即使接受，也只说明这次格式通过，不证明Prompt稳定改善或Memory/Skill性能提升。
