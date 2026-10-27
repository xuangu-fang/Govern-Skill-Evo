# V23.4 第五步：修订后 R06 重启

用户在简化 EOF Prompt 并修复合法 Check 引用后，明确要求继续第五步，首先重启 R06。本轮建立新冻结和新尝试目录，保留 semantic_generation_001 的四次失败及其旧冻结，不把旧失败重标为成功。

本轮范围为 R06 Preconditioner，若形成合法 Effective Plan，则检查语义并执行 R06 Editor；最多两个逻辑阶段。其他第五步材料虽由复用的 prepare 一并保存，本入口不发送它们。完成本轮后记录是否适合推进剩余阶段。

R06 Original、Parent、当前执行、Memory 和调用参数与首轮完全相同，发送前逐项核对。变化仅为已获用户认可的 Prompt EOF 简明说明/JSON 示例，以及合法 Original/替换 Check ID 的理由引用校验。D/S/C 算法和输出形状不变。旧单行且没有末尾 LF 的 Original 不作预处理。

沿用 deepseek-v4.1-flash、temperature=1、thinking enabled、reasoning_effort=medium、stream=false，连接/上传 60 秒、读 300 秒；初始输出 max_tokens=32768，仅 finish_reason=length 后增加到 65536。保持完整输入（独立实验适配器，无生产入口默认字符限额）；不将此调用冒充默认生产入口验证。

每个阶段首次尝试加最多三次技术重启，最多四次 HTTP；本轮总上限八次。可重启条件、15/30/60 秒退避和首次结构合法选择沿用首轮实现：限流、可恢复 HTTP/网络错误、长度截断和程序性契约错误。相同消息重新发送，不人工修补失败响应或追加修复提示。合法 Keep/撤回、Editor 空/null Patch、语义问题不触发技术重启。无效输出不得降级成 Keep。

先核验结构、引用与严格 Patch，再人工审查 D/S/C—历史—change—Effective Update 的对应及与冻结 Goal 的一致性。Editor 接收最终 Effective Plan，审查 Candidate 和真实 actual.diff 的忠实性。语义问题保留，不能用结构通过或单次采样声称可靠性/性能提升。不增加 Judge，不执行 Actor、Gate 或提交 Memory。
