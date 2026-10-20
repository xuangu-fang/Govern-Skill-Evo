# 同格式Prompt的B补充验证

复用已成功A_format_001的完整system Prompt和模型参数；B仅保留原B真实R05 Memory M1/M2/M3/M6/M7/M8/M9及sources。相对原B只改变system，完全采用A已冻结格式修复，不新增策略规则。相对合法A唯一主动输入变量为Memory。

本次仅B一次HTTP、零自动重试；A不重新调用，其他原始失败和格式实验保留。返回后用原解析器/编译器，合法输出不因语义不理想重采样；技术失败保留，不人工修补。

若有效，将合法A_format与本次B_format用于新报告。同Prompt控制恢复，但单次采样、上下文长度、时点和此前非对称技术失败仍限制稳定因果结论。B原有合法输出只作历史参考，不替代本次B。没有Editor/Replay/Actor/环境调用。
