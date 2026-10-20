# Evidence-Calibrated Update：独立固定材料实验

已完成：[最终报告](reports/REPORT.md) · [五版本全文及全部原始尝试](reports/OUTPUTS.md)。171项离线测试通过；3次逻辑调用、5次HTTP、2次技术重试，2,095,957 tokens、257.366秒。R06有局部取舍和限制校准改善，R05却出现类内完成优先倾向；不晋升下一优先候选或默认。11,964个历史保护文件未变。已停止，未追加Prompt补丁或行为实验。

先完成[已有版本离线分析](reports/OFFLINE_ANALYSIS.md)，再完成[统一原则设计](reports/DESIGN.md)并冻结。仅替换原V23 Preconditioner一处相关要求，默认配置与其他模块均不变。

- [完整Prompt](config/preconditioner_prompt.md)、[相对V23精确Diff](config/v23.diff)
- [相对alignment](config/alignment.diff)、[construction](config/construction.diff)、[symmetric](config/symmetric.diff)
- [调用前冻结记录](config/freeze.json)、[冻结内容](config/implementation.json)、[配置与来源](config/plan.json)
- [历史真实全文](reports/HISTORY.md)、[历史读取核验](config/offline_read_receipt.json)
- [离线测试日志](reports/offline_tests.txt)

`run.py`只设置独立实验配置并复用既有三轮验证入口。R04/R05/R06各最多一次逻辑调用，每次最多首次加两次技术重试；合法结果立即结束该组，不语义重采样。使用正式Original Plan与当轮Memory，不使用前版Effective或后续Memory。旧目录及结果不覆盖。

`analyze.py`只读核验响应、配置与编译结果，生成五版本全文对照；没有新语义评分器。最终分别评价A取舍、B策略／范围／强度、C探索与无据限制。不得把文本变化当作行为收益。

不运行Editor、Candidate、Replay、Actor、ALFWorld、Gate或正式六轮，不写Memory，不使用最终Test轨迹。三组结束后停止，不按输出修改Prompt。
