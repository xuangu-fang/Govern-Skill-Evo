# 首轮冻结实验状态与定向修订

日期：2026-10-21（Asia/Shanghai）。用户在 R06 首次尝试加三次重启均失败后，要求讨论并优化 Preconditioner Prompt 和 Check 引用校验。本记录区分旧实验结果与之后的实现修正，不更改旧响应、失败状态或选中记录。

## 旧实验实际执行到的位置

源码修改前的 [AUDIT.json](AUDIT.json) 已重解析所有选中结果，核对冻结输入/源码、HTTP 请求、首次合法选择、Effective Plan 交接、Candidate 和实际 Diff。

| 阶段 | HTTP 次数 | 结果 |
|---|---:|---|
| R05 Preconditioner | 1 | 结构通过；语义仍有搜索强度和历史依据对应方面的疑点 |
| R05 Editor | 1 | 结构通过；动作检查/直接动作回退置于非 desklamp 章节，存在适用范围偏移 |
| R06 Preconditioner | 4 | 全部技术失败，没有 Effective Plan，没有调用 Editor |
| A3 Preconditioner | 1 | 结构通过；用户发来修订意见时，已经发出的请求正常完成，尚未完成语义审查和 Editor |

共 4 个逻辑阶段、7 次 HTTP、3 次技术重启，3 个结构有效阶段。API 返回的用量合计为 prompt 1,308,968、completion 139,653、total 1,448,621 tokens；无费用数据。没有 HTTP 429 或长度截断，未触发输出预算升级。完整第五步尚未完成：A3 Editor、A5、证据变化案例和独立 Replay 未执行；新版 Diagnosis 链路也未启动。没有 Actor、Gate 或 Active Memory 提交。

R06 的四次首个错误依次是：

1. Patch 旧文本不匹配：遗漏无末尾换行标记。
2. reason 中存在未用单反引号包围的证据 ID。
3. Patch 旧文本不匹配：遗漏无末尾换行标记。
4. reason 引用了合法的 Original Check `c1`，旧允许集合却未包含 Check ID；此外，该响应的 u1 Patch 也缺少无末尾换行标记。

第 4 次不是虚构了 `c1`。它暴露了校验器的结构对象引用范围缺口。按新校验器离线重检**未改动的**原始响应后，错误推进到 `Parent context/deletion text differs at declared position`。这不是成功结果，也不能据此把旧失败改标为成功。

## 本次最小修订

- Prompt 明确：检查解码后的 Original 是否以 LF 结束；若没有，旧末行后必须紧跟 `\ No newline at end of file`；新文本无末尾换行时也须标记，并展示 JSON 中反斜杠转义正确的可执行示例。
- 理由允许引用 Original Plan 与完整替换 Checks 中的合法 Check ID，以解释保留、修订、替换或删除。Check ID 是结构对象，不加入证据集合或派生 basis。
- 未声明 Check ID、重复/冲突 ID、失效 Update 关联继续拒绝。严格 Patch 引擎、D/S/C 方法、v2 JSON 形状均未改动，没有自动补换行、修补响应或降级 Keep。
- 同步输入输出契约。V23.4 离线测试 **151 passed**，其中本次增加 13 项：合法 Check 引用与 basis 隔离、无效引用/Checks 拒绝、四种末尾换行组合和 Prompt JSON 示例实测。

## 冻结与后续边界

修改前的两个源码文件按原路径保存于 [baseline_sources](baseline_sources/manifest.json)，其 SHA256 与原 [freeze.json](config/freeze.json) 一致。旧冻结文件和全部运行产物保持原样；源码修订后，旧入口的 freeze 校验会按设计拒绝继续发送，不能覆盖原哈希来冒充同一条件。

后续真实调用应建立新的明确冻结版本，记录本次改动，并明确剩余阶段与重试预算。R06 的旧三次重启预算已耗尽，本次未隐式重置，也没有追加任何 API 请求。Prompt 明确化是否降低真实生成错误率仍待验证。

本实验使用正式 Prompt/校验/编译函数及独立归档适配器，没有验证生产加载器的完整调用链。R05/R06 消息分别为 967,809 / 885,412 字符，超过生产 Preconditioner 默认 100,000 字符限制；正式接入需要显式配置输入预算，不能据此宣称默认配置已可直接运行。
