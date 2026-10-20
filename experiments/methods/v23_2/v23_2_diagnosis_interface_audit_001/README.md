# V23.2 P1-C：Diagnosis—Preconditioner 接口只读审计

本目录是独立分析归档，不是新方法版本、模型实验或默认配置。模型调用0，环境执行0，未生成新的Original Plan、有效策略或Candidate。

- [接口与真实数据流](reports/P1C_INTERFACE_AUDIT.md)
- [逐案例责任矩阵](reports/P1C_CASE_MATRIX.md)
- [最低职责与研究决策](reports/P1C_DECISION.md)
- [历史请求、未发送P1-B装配及编译契约结果](results/interface_audit.json)
- [具体步骤及pre-action候选证据索引](results/evidence_index.json)
- [历史文件保护](results/protection.json)
- [前次保护告警现状](results/prior_drift_review.json)

`audit.py`在禁网下复用既有纯函数；验证3组正式Preconditioner请求／输出、原Editor输入、当轮Active Memory及sources正文，重建27条当前Parent、663个行动步骤，并只在内存中装配3组P1-B未发送payload。保存其哈希和来源，不复制整套历史轨迹。3组各做10项正向编译契约检查及4项拒绝检查；夹具复用原文字，只测结构权限，不评价生成策略。

如需重复只读核验，在仓库根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python -m experiments.methods.v23_2.v23_2_diagnosis_interface_audit_001.audit
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py
```

这些命令仅更新本目录分析产物；不调用任何`run_round`、`run_stage`或模型／环境入口，不修改Active Memory。正式Test只参与字节哈希保护，未读取其中轨迹作研究依据。

开始时记录已有Git修改。前次重试报告的`.gitignore`与`experiments/methods/v23/README.md`当前哈希仍与前次after一致；前者的当前Git差异为生成记录忽略规则等，后者记录23项V23生成记录的本地保留政策，且位于Git当前未跟踪目录，不能伪造其相对HEAD差异。此前保护告警原样保留，未回滚或推断作者。结束保护结果以`results/protection.json`为准。

本次停在P1-C；P1-D、P2、P3均未开始。
