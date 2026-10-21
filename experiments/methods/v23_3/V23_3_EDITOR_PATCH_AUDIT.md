# V23.3 P0：Editor Patch 核查

结论：**文本应用核心可直接处理 Original Update，无需新补丁引擎；完整 Update 撤回使用既有 `to: []`。** Editor 阶段运行器与其归档加载不能直接当作 Update 修改器。

证据：[editor.py](../../../src/skill_evolution/v23/editor.py) 的 `apply_patch/actual_diff/validate_editor/run_editor/load_editor`；[Editor Prompt](../../../src/skill_evolution/v23/editor_prompt.md)；[既有测试](../../../tests/skill_evolution/v23/test_editor.py)。

## 1. 八项审计回答

| 问题 | 源码事实与结论 |
|---|---|
| 1. 格式是什么？ | 模型 JSON 严格为 `patch/reason`。非空 patch 是单文件标准 Unified Diff；`""` 为无需编辑，`null` 为需上游修订。空白字符串非法 |
| 2. 如何定位？ | 固定头 `--- a/SKILL.md`、`+++ b/SKILL.md`；null Parent 改用 `/dev/null`。Hunk `@@ -old_start,old_count +new_start,new_count @@` 指定原/新行位置，并逐字比较上下文与删除行。不是搜索字符串锚点 |
| 3. 如何增删替换？ | 空格行为上下文，`-` 删除，`+` 添加；替换由删+增组成。支持零长度插入/删除范围；计数省略表示 1。不使用另一个 operation 字段 |
| 4. 多项修改？ | 一个 patch 可有多个有序 Hunk；原坐标均相对同一原文，新坐标须匹配此前输出。按 cursor 拷贝间隙，不把后一项应用到前一项新生成的原文上 |
| 5. 如何报错？ | `require` 抛 ValueError：头/格式/UTF-8/NUL、越界、乱序或已消费区间重叠、新坐标错误、计数不符、上下文不一致、截断、EOF 标记不合法、空白或未变结果均拒绝。无模糊匹配、偏移修复或自动重试。全部 Hunk 在内存成功后才保存 Candidate；后段失败不发布部分 Candidate |
| 6. 能否直接作用于 Update？ | 能。`apply_patch(original_update_text, patch)` 只读字符串，不解析 Markdown 标题、Skill 章节或文件系统。固定 `SKILL.md` 头可作为内存文本的虚拟文件标签，目标 ID 由既有 `from` 选定，不由文件路径决定 |
| 7. 最小适配？ | 不改应用函数/文件头；外围选择 Original ID，调用原函数，再把返回值放入 `to.text`。撤回不能靠删除全部文本实现，因为原引擎拒绝空结果；用既有 `to: []` 即可。无需增加引擎选项 |
| 8. 如何编译？ | 确定性恢复原 `decision/reason/adjustments/checks`；每个 patch 生成一个一对一 `from:[u] → to:[{id:u,text:result}]`，撤回保留 `to:[]`；原 `compile_effective_plan` 处理剩余结构、引用、Checks 和 Goal |

对于多个零长度插入，原函数不一概拒绝“同一原坐标”：如果按给定顺序且新坐标一致，可能合法。这是已定义的行序，不应夸称存在通用冲突检测。不同 Update 的依赖矛盾、同一行内的语义冲突均不由 Patch 解决。

## 2. 精确文本与输出语义

- `_lines` 仅按 LF 切分，保留 CR、尾空格和无末尾换行；`_read_text/_write_text` 避免通用换行转换。
- 无末尾 LF 的行必须使用标准 `\ No newline at end of file`。不能为了方便自动给 Original 补换行。
- `actual_diff(parent,candidate)` 从实际文本重算审计 Diff，不覆盖模型 Patch。
- `apply_patch` 不接受空字符串/null 作为 Keep。它们由 `validate_editor` 在 Editor 层解释。V23.3 的 Update Keep 直接省略 Adjustment；不要将 Editor 的三个状态机械搬进 `to`。
- `run_editor` 保留 response/raw/patch/validation/run；解析或应用错误是技术失败，不转换为语义 no_change/need_evidence。`load_editor` 重算补丁结果并核对保存内容。

## 3. 重要局限：七条 Update 均为单行

直接读取 P1-B R04/R05/R06 原始 JSON，七个 `text` 的 LF 数量全部为 0，长度分别为 939/1176、1072/514、874/774/566 字符。

因此修改一个子句通常需要 Unified Diff 删除整条旧行并写入整条新行。原程序能保证**未触及行和未修改 Update**精确保留；不能保证被替换行中的其他句子不变。全文替换时该 Update 没有受程序保护的原文区域。

本设计接受此限制，不增加句子切分、专用锚点或字节协议。P1 不宣称 Patch 自动解决 P3-B 的附带承诺问题；算法必须决定每项行为改变的依据，后续评价以实际语义差异为准，不以 Hunk 数或文本长度为准。

## 4. 本次离线验证

2026-10-20，在禁用 socket 连接、关闭 pytest cache 与 Python 字节码写入的进程中运行以下**已有**测试，共 **99 passed in 0.52s**：

- `test_editor.py`：`test_exact_patch_examples`、`test_invalid_patch_is_rejected_without_repairs`、`test_eof_marker_without_final_framing_newline`、`test_no_semantic_validation_or_automatic_revision`。
- `test_preconditioner.py`：`test_compilation_and_lineage`、`test_simultaneous_order_independent_adjustments`、`test_keep_preserves_deep_copy_and_original_goal`、`test_contract_errors`。

部分编译测试使用现有本地固定响应回调构建夹具，不访问模型服务。没有新增测试代码、Preconditioner 实现、模型调用或环境执行。

这验证的是正式 V23 已有能力，不是尚未实现的 V23.3 适配器。尤其既有语义风险测试明确接受“记住完整历史”等字符串，证明格式正确不等于能力条件正确。
