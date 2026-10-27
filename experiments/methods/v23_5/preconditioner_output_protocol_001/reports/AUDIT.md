# V23.5 Preconditioner 输出协议完善与 HTTP 正文核查

本次只做离线代码修改、测试及已有响应核查。问题是：能否用少量统一措辞减少输出协议歧义，并让现有拒绝结果直接定位错误？假设是定位更清楚，格式错误率是否下降仍需以后单独实验验证；本次不启动真实模型或 Actor。

## 修改范围

两版 Preconditioner Prompt 在原有第 5、6、7 节统一补丁、引用、JSON 要求，合并开头与结尾重复的输出格式说明。未增加结构示例，保留原来的两个 JSON 代码块。D/S/C、Keep／撤回／修改、输出字段及各自历史可见性要求未变。

引用错误现在指出 Update、字段和违规片段，区分未按单反引号标注的 ID、反引号内容不在允许引用集合内、引号不完整等情况。不推断不可用引用一定是普通文字。定位片段最多取原文 120 个字符，以 repr 显示换行等字符；不输出整段证据。

补丁异常添加 Update 和 to.patch 定位，保留精确匹配数量与 hunk 编号；后续错误 hunk 头、结果中间的缺失换行标记也标出 hunk。文件头、编码等尚不能归属单个 hunk 的问题明确标作 patch-level validation；整体空结果标出参与的 hunks。没有模糊匹配、自动排序、自动修复或部分应用。

JSON 使用原来的解析器，Preconditioner 只在既有 JSONDecodeError 上增加行、列、字符位置和短原因。位置指原解析器完成 strip／完整围栏处理后的 JSON body；原有完整 JSON 围栏兼容、重复键拒绝、非有限数拒绝均保留。没有抽取正文末尾 JSON 的回退。比较运行器的 Preconditioner 分支使用同样的诊断，Replay 分支不变。

输入视图、引用允许集合、保存后重载及重试规则未变。所有已冻结实验目录仅作读取，没有改写输入、参数、Prompt、响应或结果，也没有执行会更新旧报告的 summarize／resume。

## 两次 JSON 失败的原始 HTTP 核查

| 保存位置 | message.content 字符数 | reasoning_content 字符数 | thinking_blocks 数量 | 本地提取及保存 |
|---|---:|---:|---:|---|
| single_round_001 / R03 / preconditioner / memory_v3 / attempts/001 | 58,676 | 22,352 | 1 | response_value(HTTP) 等于 response.json；raw_output 等于 message.content |
| single_round_002 / R03 / preconditioner / memory_v3 / attempts/002 | 51,240 | 25,184 | 1 | 同上，逐字一致 |

完整相对路径和核查元数据见 [http_audit.json](../results/http_audit.json)。核查文件不复制整段模型正文或推理。

两个 HTTP message 都包含 content、role、reasoning_content、thinking_blocks、provider_specific_fields；provider_specific_fields 中还包含 citations、thinking_blocks。存在独立推理字段并不能证明这些字段与正文之间在代理内部如何转换。

本地路径已检查：

1. v23/grouping.py 的 live_generator 保存收到的 HTTP bytes，再对同一个 HTTP response 调用 json()。
2. response_value 只取 choices[0].message.content，不拼接 reasoning_content、thinking_blocks 或 provider_specific_fields；content 缺失／为空时返回空字符串，不回退到推理字段。
3. comparison.finish_response 和 Preconditioner 保存该 content，再交给 JSON 解析器。没有再次包装成正文，也没有拼接消息。
4. 原解析器只处理首尾空白及完整 JSON 围栏，再严格解析一个对象。收到的额外正文不会被删除；两次保存的失败响应经新诊断路径检查后仍然被拒绝。

**已确认额外文字来自收到的 API 正文；尚不能区分模型未遵守输出协议与代理转换问题。**

没有访问代理内部实现，也没有据此认定代理存在缺陷。HTTP 提取函数本身未修改；新增的模拟 HTTP 测试覆盖独立推理字段、空正文、额外正文和合法正文，验证不拼接、不错误回退、不重复包装。

## 验证

离线测试结果见 [validation.json](../results/validation.json)。测试同时覆盖两种历史视图的引用权限、错误片段长度限制、JSON 接受／拒绝规则、精确列表与空白保留、多 hunk 定位、原子失败、无额外调用和重载。

本次没有测量模型格式错误率，没有形成新方案的成功率结论。

## 2026-10-27 材料整理说明

两份失败回答、原校验记录和 HTTP 分界摘录现可从 [目录说明](../README.md) 查看。原始输入与 HTTP 仍留在来源归档；以上测试和审计结论是历史记录，本次没有重跑。
