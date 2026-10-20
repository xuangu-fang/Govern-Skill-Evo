# Evidence-Grounded Update Transformation：固定材料验证

仅替换 Preconditioner 第一节中上一轮的两段支持范围要求，以四段统一表述检查实质性的新增、删除与改变，以及各自的证据或可检验假设。允许合理 Keep、大幅修改和新策略探索，不新增字段或审核模块，不恢复第一项可执行性实验规则。

- [完整候选 Prompt](config/preconditioner_prompt.md)
- [相对正式冻结 V23 的 Diff](config/v23.diff)
- [相对 response_alignment_001 的 Diff](config/alignment.diff)
- [冻结配置与当轮 Memory IDs](config/plan.json)
- [离线测试](reports/offline_tests.txt)
- [三版本完整输出](reports/OUTPUTS.md)

[run.py](run.py) 仅以独立路径配置复用上一轮验证编排，旧文件不改；实际模型调用、输入、契约、技术重试和确定性编译仍由既有 V23.2 局部入口与 V23 模块负责。每轮使用正式 R04/R05/R06 实际 Preconditioner 调用时的材料和容量恢复配置，原始轨迹、证据选择、Parent、Original Plan、Memory、模型参数不变。

最多三次逻辑调用，每组首次加最多两次技术重试；合法语义不理想不重采样。新结果进入独立 artifacts 目录，目录存在时拒绝重跑。不调用 Editor、Candidate、Replay、Actor 或 ALFWorld，不写 Memory，不执行 Gate或六轮实验，不使用最终 Test 轨迹。

分析分别判断 A 原始更新取舍与 B 替代 Update 的具体构造，并单列 C 过度保守、过强修改及连带限制。旧 R06 行为验证仅是研究背景，不回灌本次固定输入，也不冒充本次新 Update 的执行证据。默认配置仍引用原 V23。

已完成并停止：169 项离线测试通过；3 次逻辑调用、4 次 HTTP，R05 一次引用契约错误后技术重试成功。总 1,772,298 tokens、243.89 秒；11,805 个历史保护文件未变。R04/R05 有局部合理变换，但关键 R06 保留类内穷尽和进度保证，没有延续上一轮的策略差异识别；不晋升为下一优先候选。详见[完整报告](reports/REPORT.md)，A、B、C 分别判断。
