# 有限反馈小规模真实验证 001

目标：先观察已知输出失败之后，增加上一份正文和定位诊断是否帮助下一次生成通过校验、减少相同错误。此实验是历史失败的续试，不是新 Campaign 的自然错误率评估。

- 选择三个仍被当前生产校验器拒绝、且正常结束的真实 Preconditioner Knowledge Only 响应：003/R03/003 的 JSON 错误、001/R03/001 的引用错误、007/R04/001 的 schema 错误。Replay 原引用失败现已通过校验，属于扫描器误判，不纳入模型纠错样本。样本在本次请求前固定。
- 每个案例两组各生成一次，共最多 6 次新请求，并发最多 2。原样组仅发送当前 system/user；反馈组额外发送原响应正文 assistant 消息和生产函数生成的诊断 user 消息。两组当前 Prompt 与事实完全相同；当前 user 输入与历史输入按解析后的内容核对一致。
- 两组都使用当前精简 Prompt，因此观察的差异是反馈消息的作用；不单独归因于 Prompt 精简。历史失败由较早 Prompt 产生，此限制保留。
- 使用现有 deepseek-v4.1-flash 路由、max_tokens=32,768、temperature=1.0、reasoning_effort=medium、thinking enabled、timeout=300 秒。每组本轮仅续试一次，不因失败追加请求。截断和传输错误单独记录，不按内容错误统计。中断后仅复用已保存响应，不重发已开始的请求。
- 调用生产解析器、完整输出校验、补丁应用与引用权限校验；有效结果从保存文件重新解析和校验。不自动修 JSON、不改变输出、不补证据。独立推理字段不加入反馈。
- 观察完整校验通过、相同错误是否重现、是否出现新错误；记录实际 usage。相同诊断只作为自动信号，另人工核查错误类别及 Update/字段。结构通过不代表 D/S/C 或新策略正确，只有 3 对样本不能证明整体错误率下降。
- 不运行 Actor，不发布 Skill 或 Memory，不修改原冻结实验、Prompt 或生产代码。真实 API 原始档案与冻结消息存入 `artifacts/methods/v23_5/feedback_smoke_001`。

运行：`PYTHONPATH=. python -u experiments/methods/v23_5/feedback_smoke_001/run.py run`

该小实验复用生产消息构造与校验函数，但不是 Campaign 三次有界重试流程的端到端实验；后者本轮仅有先前离线测试证据。
