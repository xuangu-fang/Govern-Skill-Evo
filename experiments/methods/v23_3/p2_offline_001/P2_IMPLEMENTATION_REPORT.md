# V23.3 P2 实现报告

2026-10-20。四阶段顺序通过，完成后停止。正式 V23、V23.2、Memory、Replay 契约与默认运行配置不变。

## 阶段与代码

| 阶段 | 实现 | 阶段门 |
|---|---|---|
| A | [update_patch.py](../../../../src/skill_evolution/v23_3/update_patch.py)：按冻结 Original ID 精确应用补丁，恢复 `id/text`，原编译器一次编译；无输入突变或部分返回 | [218 项通过](results/P2-A_GATE.md)，才开始 B |
| B | [preconditioner.py](../../../../src/skill_evolution/v23_3/preconditioner.py)、[Prompt](../../../../src/skill_evolution/v23_3/preconditioner_prompt.md)：单次生成、响应条件化决定、原始/派生归档分开、重载重算 | [79 项通过](results/P2-B_GATE.md)，才开始 C |
| C | [diagnosis.py](../../../../src/skill_evolution/v23_3/diagnosis.py)、[Prompt](../../../../src/skill_evolution/v23_3/diagnosis_prompt.md)、[editor.py](../../../../src/skill_evolution/v23_3/editor.py)：版本匹配的多行生成说明与加载入口 | [284 项通过](results/P2-C_GATE.md)，才开始 D |
| D | [完整集成测试](../../../../tests/skill_evolution/v23_3/test_integration.py)、[人工样例构建器](build_mock_archive.py)、原版本与 P1-R 回归 | [434 项通过](results/P2-D_GATE.md) |

阶段数字是各次实际运行数，有重叠，不相加。最终一次运行包括 122 项新增测试、247 项既有 V23 测试、65 项 P1-R 兼容测试。

## 响应条件化决策的实现落点

独立 Preconditioner Prompt 不只把 `text` 改成 `patch`：

| P1 决定机制 | 本版落实位置 | 可观察的预期改变 |
|---|---|---|
| 匹配真实编辑及其条件化混合响应 | Prompt §2，先 actual Diff，再收益/退化、条件与归因限制 | 不能仅用 Memory summary、任务名称或总成功率支持整段替换 |
| Keep / 收窄 / 放宽 / 替换 / 撤回 | §3 分别给触发依据与边界 | 反例限制强度；排除有用选项可放宽；未知最优仍允许可检验探索 |
| Actor 可见条件与必要关联 | §4 范围投影及保留旧要求的反事实检验 | 目标修改不自动授权其他改动；独立探索有自己的问题动机 |
| 先选择要求，再写补丁 | §5，直接定位 Original 原行 | 允许大幅修改，不先自由全文生成再补理由，不优化行数 |
| 证据与观察闭环 | §6，沿用 basis/reason/checks | 来源限制和未验证假设可审阅；真实效果留待后续执行 |

这里实现的是一次模型生成应遵循的决策程序及工程载体。Fake 输出由人工指定，不能证明模型实际遵守这些语义分支。程序没有语义评分器、独立审核器或隐藏的第二次模型调用。

## 最小复用与必要重复

复用原 `diagnosis_input/validate_diagnosis`、`preconditioner_input`、Memory 校验、`parse_json_response`、`write_record`、`editor.apply_patch`、`compile_effective_plan`、Editor 的消息/输入/校验/diff/归档检查。模型请求继续使用已有 `generate(messages, directory)` 注入契约；没有新 HTTP 客户端。

三个旧 runner 将 Prompt 或 upstream loader 固定在模块中，且旧 Preconditioner 要求模型响应等于正式 Adjustment。因此本版保留三个阶段特定的调用/保存骨架，替换版本边界；未复制 Patch 引擎、compiler、Editor 策略或整套 evolution 框架。原 Editor `load_editor` 在本版 wrapper 先重载 Preconditioner 后继续使用。没有全局 monkeypatch 生产模块。

源码只新增四个 Python 文件和两份 Prompt，修改本版 README；新增测试与本目录归档。P0/P1/P1-R 文档及归档保留原样。开始状态见 [baseline.json](baseline.json)，最终范围与 Git 差异见 [final_checks.json](results/final_checks.json)、[implementation.diff](results/implementation.diff)。

## 明确限制

- 仅同 ID 单源替换或撤回；多 Update 同时调整可用，不支持结构合并/拆分/新 ID。
- 多行是生成规范，不是语义分句器或强制行数校验；旧单行仍按整行处理。
- loader 依赖归档记录的上游路径仍存在；不是可任意搬迁的独立包。Memory 是冻结输入快照，未新增外部检索或数据库。
- 技术错误不重试，不回退全文；失败目录保留，不能作为有效 handoff 恢复。持久化中断可能留下不完整文件，但有效性标记及重载核验不允许其被认作成功。
- 未接入默认 CLI/完整 `evolution.run_round`，没有运行模型、Actor、环境、Replay、Gate 或最终 Test。
