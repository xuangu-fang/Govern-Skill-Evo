# V23.2 第一项改进：固定材料可执行性验证

状态：**实现与验证完成，通用可执行性问题尚未解决，按边界停止。** 5 次逻辑调用、9 次实际请求，完整结论见报告。

范围：两处短 Prompt 替换、离线回归、最多五次逻辑模型调用。没有 Editor 调用、Candidate 或 ALFWorld 任务，不写入历史 Memory。

- [设计与继承关系](../../../../docs/methods/v23_2/README.md)
- [Prompt 精确差异](config/prompt.diff)
- [冻结调用配置与来源](config/plan.json)
- [新增实现冻结快照](config/implementation.json)：仅新增模板、局部适配和本实验入口；V23 依赖直接核对既有 S1 contract／recoveries，不复制框架。
- [离线结果](reports/offline_tests.txt)：595 passed，19 subtests passed；禁用外部网络与环境执行。
- [验证报告](reports/REPORT.md)
- [实际进度日志](reports/live.log)
- [完整产物](../../../../artifacts/methods/v23_2/v23_2_executability_001/)

调用分为 R03／R05／R06 固定 Plan Preconditioner，以及 R05 Diagnosis → Preconditioner 串联。旧 V23 输出只读复用；每个逻辑阶段最多三次既有规则允许的技术尝试。合法结果和合法停点结束本阶段，不进行语义重采样。若 Diagnosis 未返回 revise，串联 Preconditioner 不调用。

准备和首次运行入口：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_executability_001/run.py prepare
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_executability_001/run.py run
```

运行后不重复执行以上命令。既有输出目录拒绝重新分配调用预算；中断记录保留，不隐式重开五次调用。`prepare` 在实验开始后也拒绝覆盖冻结配置。

V23.2 的 `load_attempt` 校验新模板、输入、原始响应、结构及重新编译的 Effective Plan。有效结果可经既有 Editor 输入函数交接；本次只在离线测试中验证纯数据交接，不调用 Editor。自然语言语义由报告逐项核查，不由程序关键词过滤或打分。

`comparison.json` 保存全部 Original Plan、V23／V23.2 调整及 Effective Plan。每次技术尝试各自保存请求、HTTP 原文、解析和错误；`summary.json` 汇总已知 Token、实际耗时与停点，`protection.json` 对原 V23 源码和正式档案作直接字节核验。
