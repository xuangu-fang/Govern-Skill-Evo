# 传输修订重跑决策

**已按 `(60, 300)` 完成 A/B 真实重跑。两组均 HTTP 200、无重试；但均返回 length 且最终 content 为空，仍未形成有效模型更新对照。**

本次两次逻辑调用、两次 HTTP 请求；没有重做 Diagnosis。正文实际分别为 1,629,326 和 1,632,149 字节，发送时 socket timeout 实测均为 60 秒。完整请求、响应、超时记录及完整性失败堆栈均已保存。

新的阻碍是输出预算：每组 completion=16,384，全部计为 reasoning，没有可解析的最终 Update。未提高 max_tokens、改 Thinking 设置、修 Prompt 或继续重采样。

因此对原研究问题仍不能作优劣判断：

- **更新粒度是否改善：** 未获得实际 Patch/替代文本，未知。
- **历史是否参与修改决定：** 相同历史已发送，但没有最终决定，未知。
- **策略质量与探索是否改善：** 无 Effective A/B，无法评价。

下一步应把输出/思考预算作为单独的运行配置问题处理，事先统一两组参数并冻结新预算后再授权实验；当前结果不支持先改算法 Prompt。原多行 Diagnosis 与共同证据可继续复用。没有有效候选，暂不进入 Editor 或 Candidate Replay。

本次已返回总用量 **982,834 tokens**（prompt 950,066，completion 32,768；reasoning 32,768 已包含其中），货币费用未知。

只新增本重跑目录，旧实验、P0—P2、正式源码与 Prompt、Memory、Parent 及用户既有修改保持不变。未提交、暂存或重置；[保护检查](results/final_checks.json)和 [Git Diff](results/experiment.diff)已归档。

报告：[预注册修订](P3A_RETRY_PROTOCOL.md)、[执行与超时实测](P3A_EXECUTION_REPORT.md)、[独立评价和对照边界](P3A_UPDATE_COMPARISON.md)。

**停止。未执行 Editor、Actor、Replay、Gate、Memory 更新或完整进化。**
