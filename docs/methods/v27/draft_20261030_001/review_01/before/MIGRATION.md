# v27 模块迁移清单

以下路径相对于项目根目录；目标路径均为未来实现位置。本次只编写设计文件。源码精确内容以 source_manifest.json 的逐文件 SHA-256 为准，Git HEAD 不能代替存在工作区修改的文件身份。

| 模块 | 主要底稿 | 保留内容 | 必须适配 | 未来位置 |
|---|---|---|---|---|
| benchmark 绑定 | `src/skill_evolution/v26/benchmark.py` | 显式绑定、ContextVar、worker 上下文传播；不按路径猜 benchmark | 类型及版本身份；去除任何 OfficeQA 私有依赖 | `src/skill_evolution/v27/benchmark.py` |
| Campaign | v26 `evolution.py`, `stages.py`, `storage.py`, `resources.py` | 冻结、阶段产物、恢复校验、Parent 复用、原子发布、无更新/阻塞/失败分支 | LMB actor 调用、身份、完成判定和快照；不得导入旧领域 adapter | v27 同名模块 |
| 配置 | v26 `config.py` | method freeze、显式预算、重复任务与批次校验 | 新 53 题 pool、LMB EM、六批次；移除 OfficeQA 74 题和逐题例外预算 | v27 `config.py` |
| 数据合并 | v26 `training.py`；SkillAdam `cli.py` 的 `_optimization_cases` | 独立合并视图、source_split、Test 隔离 | 35＋18、字符串排序、Train 后接 Selection；不照搬 74 题资源 | v27 LMB `data.py` |
| Actor | SkillAdam `benchmarks/lmb/{manifest,choices,rollout,evaluation,adapter}.py`；已有 LMB 接入脚本 | 单轮、固定消息协议、逐题确定性选项打乱、答案解析 | durable 请求记录、六次总额度、stop/length 分类、证据投影；无 SDK 隐藏重试 | v27 LMB `actor.py`, `transport.py` |
| 初始 Skill | 已安装 SkillOpt 干净快照中的 LMB `skills/initial.md` | 原文字节和哈希 | 无策略改写；单独冻结外层 Actor 协议 | v27 LMB 资源引用 |
| facts/protocol | v26 OfficeQA `facts.py`, `protocol.py`, `evidence.py` | 身份校验、显式证据引用、真实消息和事后 outcome 分离 | LMB 单轮 schema、正确选项映射、content-only；删除文档/页码/工具证据 | v27 LMB `facts.py`, `protocol.py`, `evidence.py` |
| Grouping | v26 `modules.grouping_call`、OfficeQA `evidence.validate_grouping`、`prompts/grouping.md` | 全批次恰好一次覆盖、允许单例、直接执行引用、五字段 group | 数学选择题比较；只有标签时不虚构推理错误 | v27 `modules.py`＋LMB `prompts/grouping.md` |
| Diagnosis | v26 `modules.diagnosis_call`, `contracts/diagnosis.py`, `prompts/diagnosis.md`；对照 v24.1 同名契约 | revise/no_change、Plan/Update/Check、直接证据与 Group 成员约束 | 数学假设、量词、结论强度、格式、能力限制的证据边界 | v27 同名模块＋LMB Prompt |
| Preconditioner | v26 `modules.preconditioner_call`, `update_patch.py`, `explicit_references.py`, `plan.py`, `memory_view.py`, `prompts/preconditioner.md` | adjustments/checks、每项一次、D/S/C、显式命名空间、KEEP/patch/撤回、原 ID 与 basis、确定性编译 | LMB 引用集合；领域语言；不暴露旧编译器 decision/need_evidence 为模型 schema | v27 同名模块＋LMB Prompt |
| Editor | v26 `modules.editor_call/validate_editor`, `unnumbered_patch.py`, `contracts/editor.py`, `prompts/editor.md` | 精确无行号 diff、null/空/非空语义、actual_diff、只读 Effective Plan | 数学逻辑与标签包装的范围；不能改固定 Actor/scorer | v27 同名模块＋LMB Prompt |
| Gate | v26 `contracts/gate.py`；SkillAdam LMB `gate.py` 作对照 | candidate_success > parent_success；配对完整及身份一致 | success iff LMB EM=1；stop/length 都可为 completed，技术失败不是 0 分 | v27 LMB gate 适配 |
| Replay | v26 `modules.replay_call`, `replay.py`, `contracts/replay.py`, OfficeQA evidence 构造、`prompts/replay.md` | actual_diff、当前 pairs、去 basis 的计划投影、Knowledge Only、entries schema | 单轮可见 content 比较、返回标签与格式差异、禁止隐藏推理展开 | v27 同名模块＋LMB Prompt |
| Memory | v26 `contracts/memory.py`, `memory_view.py`, `knowledge_evidence.py` | multi-Knowledge、逐项 evidence、完整 entry 替换、历史来源、归档与活动索引 | sources 必须为许可事实视图，不能保存可解引用到隐藏正文的引用 | v27 同名模块 |
| Verifier/Repair | v26 `knowledge_verifier.py`, `knowledge_repair.py`, modules 对应入口 | 可选能力、授权 targets、定向修复与 merge | 首版 disabled；如启用需独立 Prompt 评审，仍不得访问隐藏推理 | v27 保留接口，首版不调用 |
| 方法传输/反馈 | v26 `transport.py`, `output_feedback.py`, `json_response.py`, `stages.py` | 显式模型配置、结构错误反馈、六次总请求、无语义重采样 | LMB 字段权限；错误反馈不泄露排除字段；方法 32k 不能被 Actor 16k 上限裁剪 | v27 同名模块 |
| 评估/监控 | v26 `evaluation.py`, `monitoring.py`；SkillAdam LMB evaluator | 冻结 Skill 独立评估、来源核验、usage 与状态报告 | 初始/v27/SkillAdam 三组 124 Test、同一 content-only 解析规则 | v27 同名模块＋LMB 评估适配 |

模块判断原则以 v25／v26 的当前版本为主；v24.1 用于对照共同契约和不更新边界，不拼接其 ALFWorld Prompt。v26 的 `config.py`、`modules.py`、`training.py`、Prompt renderer 仍有 OfficeQA 直接导入，不能仅复制 benchmark.py 后宣称独立适配完成。

保留语义身份：`v25_explicit_references_v2`、`unnumbered_diff_v1`、`entries_sources_multi_knowledge_v1`、`memory_knowledge_only_v1`、`previous_output_validation_error_v1`。未来代码即使保留契约 ID，也必须重新冻结 v27 源码及资源身份；不得用旧 campaign 自动恢复。

新增草案身份：`v27_lmb_facts_v1`、`v27_lmb_pairs_content_v1`、`v27_lmb_content_input_v1`、`v27_lmb_skilladam53_v1`、`v27_lmb_em_v1`，五个 Prompt 分别为 `v27_lmb_<module>_v1`。这些是设计标识，尚未注册为运行能力。

对照差异明确保留：v27 复用诊断 Parent，SkillAdam 重新执行 Gate Parent；v27 完整六批，SkillAdam 保留其早停；各自优化器和历史组织不同。共同配置是数据、Actor 条件、初始 Skill 和 scorer；六次 Actor 尝试和 length 处理是本实验的共同覆盖设置，不称为 SkillAdam 原生默认。
