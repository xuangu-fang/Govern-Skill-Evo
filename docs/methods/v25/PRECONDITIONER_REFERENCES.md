# Preconditioner 显式引用契约

2026-10-27：显式引用从 `v25_preconditioner_explicit_references_v4` 引入；
当前默认 Prompt 为 `v25_preconditioner_evidence_decision_boundaries_v7`，输出契约仍为
`v25_explicit_references_v2`。本页记录引用识别与校验，
不改变 D/S/C 决策、输入证据范围、输出 JSON 字段、Gate 或其他优化模块。

## 模型输出中的写法

| 类型 | 显式引用 | 权限 |
|---|---|---|
| Memory | `` `Memory:M1` `` | 输入中的 active Memory |
| Group | `` `Group:G1` `` | Original Update basis 已携带的 Group，仅为上游来源 |
| 当前证据 | `` `Evidence:P1:outcome` `` | 当前输入包含的运行、初始、尝试或 outcome ID |
| 历史证据 | `` `Evidence:campaign_R01/Q1:2` `` | Knowledge evidence 数组中已经出现的完整 ID |
| Update | `` `Update:u1` `` | Original Update |
| Check | `` `Check:c1` `` | 原始或完整替换 Checks |

保留内部短 ID；`target`、`id`、`update_ids`、`basis`、Memory 和证据归档不改名。
解析出的合法引用映射回原 ID，当前引用继续按原规则进入内部 adjustment basis；
历史引用不因此获得扩大权限。引用存在与类型正确不代表语义支持已经验证。

普通文字和代码排版，例如 `A2:M70`、`=G2*H2`、`=$M$70`、`delete_rows`，
不会产生引用。裸 ID 也不是正式引用；模型需要引用对象时必须使用上表语法。
五种命名空间前缀在输出文字中是保留标记，缺反引号、类型不符、ID 不存在、
引用未提供历史尝试或自行扩展范围均拒绝。

规范化与编译复查共享同一个解析器，覆盖 reason、change、补丁应用后的 Update
正文和 Check question。补丁本身仍按字面精确应用，不扫描裸单元格地址；
行为正文不应为了提供来源而加入引用，来源应写在 reason 中。

## 版本与旧归档

新请求默认使用 v7 Prompt 和显式引用契约；v4、v5、v6、v7、v8 Prompt 的原模板保留，
读取其旧归档时使用相同显式引用契约。旧版 `history_and_plan_v3` +
`v25_unnumbered_updates_v1` 保存了独立 Prompt 副本和原解析规则；加载时按归档
元数据选择，拒绝 Prompt/契约错配。旧 Preconditioner 和 Editor 的交接对象保持
原形状。更早的 Prompt 不因本修复自动获得兼容支持。

本修复不修改旧 campaign，也不使旧冻结实验可以在新源码下直接续跑。
后续完整训练应重新准备并冻结配置；每批 15 题模板已同步新版本。

默认回退依据及兼容验证见 [v7 默认回退说明](PRECONDITIONER_V7_DEFAULT.md)。
v8 作为实验版本保留，其局部语义调整、旧模板保留和验证范围见
[修改说明](PRECONDITIONER_SCOPE_AWARE_KEEP.md)。

## 离线验证

`tests/skill_evolution/v25/test_explicit_references.py` 覆盖普通地址和公式、
五种类型、输入权限、损坏标记、混排、内部 basis 映射、编译复查、输出错误分类、
新旧 Preconditioner 与 Editor 归档重载。测试使用固定响应和临时合成任务，
不调用模型，不执行真实 benchmark 训练。
