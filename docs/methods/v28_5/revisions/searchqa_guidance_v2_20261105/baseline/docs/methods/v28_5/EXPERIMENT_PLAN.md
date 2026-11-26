# v28.5 固定实验边界与后续验证设计

当前方案：600 题按原顺序分为 10×60，训练并发 60，测试并发 15，Editor max_tokens=65,536。配置为 [v28_5_searchqa_train600_batch60.json](../../../experiments/configs/v28_5_searchqa_train600_batch60.json)。按用户要求，刚短暂启动的 batch50 实验已终止并删除；新配置检查后从头训练，再运行 Test 和比较。更早实验保持暂停。

## 1. 当前实验参数

| 项目 | 当前值 |
|---|---|
| 优化数据 | 原 Train 400 + Validation 200 构成的 600 题优化池；ID、内容、顺序保持 |
| 批次 | 10×60（原 20×30），单遍、不打乱，effective split=train；来源 split 保留 |
| 初始 Skill / Memory | 原 104 字符占位 Skill；`{"rounds":[]}`；不用任何已训练 Skill 热启动 |
| Test | 原 1,400 题与顺序，只评估最终 Selected，不用于 checkpoint 选择 |
| Actor 与四个方法模块 | deepseek-flash；原 endpoint；thinking enabled；reasoning_effort=medium；temperature=1.0 |
| Actor max_tokens | 32,768 |
| Diagnosis / Preconditioner / Replay max_tokens | 各 65,536 |
| Editor max_tokens | 65,536（原 32,768） |
| Actor timeout / connect timeout | 300 / 10 秒 |
| 方法模块 timeout | 600 秒；连接与传输行为沿用原实现 |
| 每调用总请求上限 | 6，技术错误/length/校验反馈共享原额度，不语义重采样 |
| Actor / 方法重试间隔 | 原 1 / 2 秒策略；Actor SDK retries=0 |
| Train / Test workers | 60 / 15（原 15 / 15） |
| 输入限制 | 4,000,000 字符，6,000,000 UTF-8 字节；不截断证据 |
| 其他 | continue_no_change=true；knowledge_review=disabled_v1；原评分器、EM Gate、恢复与归档策略 |

独立运行仅隔离方法/Prompt/contract/view 身份及目录，具体值见 [source_map.json](source_map.json)。参数、数据或初始化的其他变更需要单独记入方案，不能混入这次对照。

## 2. 第一阶段：静态定稿（本次）

冻结基线，形成四份完整 Prompt、diff、合同和审阅材料。检查快照字节一致、diff 可还原目标、公共 Actor/证据边界保持、输出结构不变、文档引用可定位。完成情况见 [design_validation.json](design_validation.json)。不设置独立验收场景或训练前固定输入模型对照，也不以静态结果代替真实训练与测试结果。

## 3. 第二阶段：实现后直接训练与测试

1. 独立实现 v28.5，绑定本目录已定稿的四份 Prompt，保持接口、Memory 和 Gate（已实现）。
2. 完成必要的配置、输入传递、输出解析、patch 应用及运行正确性检查；不额外调用模型做场景验收（结果见实现说明）。
3. 按冻结参数运行完整 600 题、10 轮训练（当前已授权使用新配置从头启动，Editor 压缩修改已撤回）。
4. 训练完成后运行最终 Selected Skill 的 1,400 题 Test（尚未执行）。
5. 汇总与 v28.3 的结果比较，并结合真实训练轨迹分析 Preconditioner 调整、Editor 落实和 Replay 记录（尚未执行）。

不增加训练前固定输入对照或单独验收阶段。整版训练相对 v28.3 同时包含 Prompt、批次、训练并发与 Editor 预算调整，只能说明版本整体结果，不能独自证明各模块的独立收益。

## 4. 结果记录与比较

独立 campaign、Memory、日志和 Test 目录；保持原数据及除批次、训练并发和 Editor 预算以外的运行参数。完成训练后再显式进行最终 Test。报告最终 EM/F1、Skill 字符/实际 tokens、重复与冲突审阅、语义阻塞和实施偏差；列表项数量不等于规则复杂度，KEEP/REPLACE 比率不等于质量。

已经查看过的 Test 只用于描述既有结果；新 Prompt 不注入 Test 题目、答案、ID 或从 Test 反推的具体规则。未来同一 Test 比较应披露这一开发背景，不包装为完全未接触的盲测。历史审阅依据来自训练归档。

## 5. 不改变选择机制的后果

Gate 仍要求 G>0 且 L=0 才 Retain。行为保持的纯压缩 0/0 仍 Defer，因此本版目标是让有证据的修正减少冗余和冲突，不保证单独的全局整理能够被采用。

Selected patch 子集可能既不同于 Parent 也不同于完整 Candidate。保留原来源标记，不增加子集复测或新依赖机制；不声称完整 Candidate 自查可保证所有子集都合理。自然语言预条件与实施要求的改善，是待验证的质量假设。
