# 现有 Verifier／Repair 链路实测

本目录承接五份已完成的新版 Replay 输出，只运行当前生产代码的 Verifier／Repair 链路。用户要求仅分析这一版的最终结果，不做原 Replay、Verifier 判决、Repair 后输出的三阶段对照。

## 执行约束

- 直接调用原生 `knowledge_review.review`，证据提取、目标选择、历史原始来源加载、Prompt、输出验证和确定性合并均不改动。
- 五份输入独立；原 Replay 提案、相应原始执行证据与原 Memory 均冻结。
- 当前规则选择 37/39 条 Knowledge 核验，2 条因与历史完全一致而跳过。
- 原模型/API、阶段输出上限、输入预算和请求重试规则不变。最多两份链路并行，阶段预算持久保存，语义结果不满意不重采样。
- 截断只作请求重试，不用于质量或成本评价；保留原请求供审计。
- Repair 仅处理真实 Verifier 的 CONFLICT。没有注入人工问题、预期判决或离线评价说明。
- 不调用 Replay 或 Actor，不修改生产源码，不提交/发布 Memory，不启动新训练。

## 文件

- `manifest.json`、`contract.json`：调用条件、当前源码及输入文件哈希。
- `preflight.json`：本地预检，无模型调用。
- 各样本的 `final_knowledge.json`：本次待分析的最终 Knowledge。
- 各样本的 `knowledge_review/`、`verifier/`、`repair/`：原生链路归档，仅供追溯。
- `completion.json`：完成状态与源文件完整性。
- `FINAL_REVIEW.md`、`final_assessment.json`：完成后的最终结果分析。

本测试验证现有链路的实际表现，不预先证明其能覆盖所有知识质量要求。结构有效不等于语义正确，未作第二次模型语义验证是现有机制本身的边界，不在此次实测中临时改变。
