# P1-R：多行 Patch 兼容核查

**无需新增 Patch 引擎。** 正式 V23 `apply_patch` 已能直接处理多行 Update.text，精确保留未改行；原 `compile_effective_plan` 与 Editor 纯输入接口接受修改结果。

## 1. 真实能力与限制

源码：[editor.py](../../../../src/skill_evolution/v23/editor.py) 的 `apply_patch/_lines/actual_diff/editor_input`；[preconditioner.py](../../../../src/skill_evolution/v23/preconditioner.py) 的 `compile_effective_plan`。既有测试：[test_editor.py](../../../../tests/skill_evolution/v23/test_editor.py)。

| 核查问题 | 源码与本次测试结果 |
|---|---|
| 多行与单行定位 | 按 LF 切行，Hunk 旧坐标定位 Original；只替换指定行可保留其他行。重复文字不导致搜索匹配歧义，因为根本不做搜索 |
| 增、删、替换 | `+/-/空格` 的标准 Diff；三例分别覆盖新增一行、删除一行、替换一行、大范围替换；另各有一个在同一 Patch 中增/替/删的坐标测试 |
| 多 Hunk | 支持；原坐标相对同一 Original，新坐标必须计入前面增删的偏移。三例均验证两关联行；R06 的非相邻行明确用两个 Hunk |
| 未修改行 | 按原行直接复制；18 份人工方案逐项比较未改行的 UTF-8 字节及对应新位置。未改 Update、Goal、Checks 另外比较整个对象 |
| 定位失败/冲突 | 错误上下文、原坐标越界、新坐标错误、重叠/乱序、截断均拒绝；不做偏移修复或模糊匹配。后 Hunk 失败不会返回部分文本 |
| 上下文与插入 | 上下文同样占用已消费原区间，重叠 Hunk 应合并；同一原坐标零长度插入不被一概禁止，需符合原函数的顺序与新坐标规则。不宣称通用语义冲突检测 |
| EOF/格式 | 支持 LF、无末尾 LF、CRLF、Unicode、尾空格。无末尾 LF 用标准 EOF 标记。不同换行/空格不自动视为相同，不 strip 或归一化 |
| Update 直接复用 | 输入只是字符串，固定 `a/SKILL.md → b/SKILL.md` 为虚拟标签，不依赖 Skill Markdown 结构、不读写该文件 |
| 编译与下游 | 人工把 `apply_patch` 返回值放入既有 `to:[{id,text}]`，原 compiler 与 `editor_input/messages_for` 均通过；没有新适配器 |

删除全部文本会被拒绝，整项撤回继续用已有 `to:[]`；相应 Check 失效时原 compiler 拒绝，提供完整合法 Checks 后通过。空 Patch、null 的 Editor 状态含义不搬入 Update 替换项；仍沿用 P1 设计的 Keep/撤回/停点表达。

新生成多行文本使用 LF 与一个尾 LF；旧文本原样处理。`@@ -old_start,old_count +new_start,new_count @@` 计数与 body 一致，不能把显示折行当真实行。相邻要求可合并为一个 Hunk，分离要求可多 Hunk；不要求每个行为固定一个 Hunk。

## 2. 测试结果与复现

执行：

```sh
PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_3/p1r_multiline_001/run_tests.py
```

最终 **119 passed in 1.92s**，其中 **65 项本轮人工兼容测试 + 54 项既有 Editor 纯函数测试**。网络及模型阶段、Replay/Gate 入口均设置拒绝；禁止入口尝试数为 0。没有 LLM、Actor、ALFWorld、Replay 或 Gate 调用。

| 本轮测试类别 | 数量 | 验证内容 |
|---|---:|---|
| 表示与原文 | 3 | 原始副本逐字节匹配来源，text 外字段一致，多行 Keep 保持 |
| 六种人工方案 × 三例 | 18 | 单行、关联两行、插入、删除、大范围、跨 Update；每项包含原编译器与 Editor 纯输入/消息交接 |
| 六类失败 × 三例 | 18 | 错位、越界、新坐标、重叠、截断、后段失败；错误正文保留 |
| 四类文本格式 × 三例 | 12 | LF/无尾 LF/CRLF/Unicode 与尾空格 |
| 整项撤回与 Checks | 3 | 悬空引用拒绝，合法替换和全撤回通过 |
| 更新 Checks 与异常 handoff | 3 | 合法 Checks 更新；偷偷变更 Goal 的 handoff 被重编译比较拒绝 |
| 原始 Patch 不是正式 Adjustment | 3 | 原 compiler 拒绝 `{id,patch}`，证明转换边界仍须 P2 实现 |
| 混合增删替换 × 三例 | 3 | 新行坐标随前序插入/删除调整，同一字符串多 Hunk |
| 语义风险反例 | 2 | 新增一行、在替换行内夹带类别一次出口：均结构通过，均不计为语义批准 |

结果：[pytest.log](../../../../artifacts/methods/v23_3/p1r_multiline_001/results/pytest.log)、[tests.json](results/tests.json)；首轮 115 项通过后补充混合坐标与行内风险测试，首轮日志保留为 [pytest_initial.log](../../../../artifacts/methods/v23_3/p1r_multiline_001/results/pytest_initial.log)。测试源码：[test_compatibility.py](test_compatibility.py)、[run_tests.py](run_tests.py)。

## 3. 最小适配及未完成部分

仍采用 P1 方案：模型产生 Update Patch → 程序按 Original ID 应用 → 恢复原 Adjustment → 原 compiler → 原 Editor 接口。本次只是测试中显式构造标准 Adjustment，没有实现 `normalize_update_patches`、本版 Preconditioner、模型输出解析、持久化重载或薄 Editor runner。

P2 还需实现原始 Patch 响应与派生 Adjustment 分离归档、重新应用校验、旧 loader 耦合处的薄入口，以及未来本版 Diagnosis 的多行输出组织说明。原 `diagnosis.load_diagnosis` 也按旧 Prompt 核验消息，故本版 Diagnosis 的消息/归档加载与 Preconditioner 上游入口须同步匹配，不能把“Schema 相容”当作“整个旧 runner 可直接复用”。这些是已知衔接工作，不是多行补丁能力缺失；正式 V23 文件均未改动。

特别是 `editor_input` 检验 Goal 等于编译结果，**不能判断 Goal 内的实现绑定是否合理**。119 项通过不证明策略优越、不证明模型遵循规则，也不证明完整 P2 运行链已经接通。
