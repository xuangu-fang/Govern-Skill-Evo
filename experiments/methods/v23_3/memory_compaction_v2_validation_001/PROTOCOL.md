# Memory v2：离线等价检查与同批事实读取验证

用户授权先离线验证显式 before/after 与全局命令表直接引用两项修改，再用同批事实检查真实模型。仅新增本目录；原源码、v1 输入、旧失败记录和 Memory Archive 不改写。

## 固定变更与离线门

- 仍使用 v1 的全部 active entries、source 集合、±2 窗口、完整 action/feedback trace、结果及缺失范围。不得新增/删减事实或按成功与否挑选证据。
- 每个详细步骤带完整原始 step 身份、action、before、after，不再让模型根据 after 数组推导 before。窗口仅保留 start/end 作为覆盖元数据。
- 每个状态的 commands_ref 直接指向原全局 command_pool。相同命令列表仍共享，局部 C-ID 映射只保存在审计文件，不放入模型输入。
- 不添加预计算题目答案、来源总数或窗口步数等额外模型提示，不修改计数问题。
- 离线验证 R04/R05/R06 和 P3-A/B 的原始观察、动作、反馈、结果、引用覆盖及解析后的命令列表与 v1 相等。保存 token 成本估算；精确模型计数以随后返回 usage 为准。

## 真实调用预算

离线测试与内容一致性通过后：

- 固定 R05 11 题、R06 14 题，共最多 **2 次逻辑调用、2 次 HTTP 请求**，每例一次；不重试、不补采样、不因一例失败跳过另一例的独立检查。
- 模型/采样/思考参数与 v1 探针相同：内网 deepseek-v4.1-flash，temperature=1、thinking enabled、reasoning_effort=medium、max_tokens=16384、stream=false。
- timeout=(60,300)，禁重定向，禁环境代理。最多配置 32768 completion tokens，不含输入；未返回费用不推算货币成本。
- 保存实际发送正文大小、socket 超时、HTTP 原始响应、最终输出、usage、逐题评分和异常堆栈（若发生）。
- **不执行生产 Preconditioner/Patch 生成、Editor、Actor、Replay、Memory commit 或正式接入**；本轮只验证两项表示修改及读取表现。

## 题目可比性

题目 ID、顺序和要核查的历史事实保持不变，评分仍要求所有字段、类型和值正确并正常结束。

两处题目文字适配：

1. 原“分别读取两个来源的同名局部 C ID”改为“读取这两个相同命令表所对应的明确状态引用”，因为局部 C ID 已从模型视图移除；两个目标列表与原题完全相同。
2. operation_precondition 说明 v2 的 commands_ref 本身就是全局 ID，输出的 pool_ref 同样填写这个 ID。

window_start、inside_window、operation_precondition 三题的 commands_ref 参考值随地址表示变成全局 ID。将这些地址恢复为原局部 ID 后，全部参考答案必须与旧冻结答案逐字段相等；命令内容、观察、合法性、动作、顺序、覆盖和语义答案没有变化。

本地问题差异与地址映射单独保存；发送给模型的只有新格式说明、问题和 payload，不包含参考答案或旧模型回答。

## 通过与解释

两个探针均正常完成、全部答对，才称本轮格式读取检查通过。失败、截断照实归档；不事后放宽阈值。

即使通过，也只说明已知开发案例上的定向事实检查成功，不证明未见样本泛化、策略质量、压缩无信息损失或生产 Patch 契约通过。两项表示同时修改，且模型存在随机性与返回 reasoning 用量差异，不能单独归因某一修改的效果。

根据结果给出是否值得进入后续生产生成验证的建议，然后停止。
