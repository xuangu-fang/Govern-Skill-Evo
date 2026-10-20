# V23 Grouping 实现与验证报告

- 日期：2026-10-18，Asia/Shanghai。
- 范围：Grouping 装配、转换、提示词、调用、校验、保存及复用。
- 结果：102 项测试及 19 个子测试通过；24 条真实历史执行转换通过；一次真实模型调用获得结构有效、可复用的分组。
- 边界：零新增环境执行，未启动完整 Skill 自进化，未修改其他演化模块核心算法。

## 1. 实现

| 文件 | 作用 |
|---|---|
| [actor_prompt.py](../../../../../src/adapters/alfworld/actor_prompt.py) | 共用精确过滤与 Actor Prompt 渲染，保留其他命令内容、顺序和重复项 |
| [run_task_upstream.py](../../../../../src/adapters/alfworld/run_task_upstream.py) | 原 Actor 构造入口委托共用渲染函数，行为保持一致 |
| [facts.py](../../../../../src/skill_evolution/v23/facts.py) | 从实际记录提取 Parent、背景与事实，逐步比较记录中的完整 Prompt，转换前后状态并保留环境合法性 |
| [grouping_prompt.md](../../../../../src/skill_evolution/v23/grouping_prompt.md) | 原样采用已确认的英文提示词 |
| [grouping.py](../../../../../src/skill_evolution/v23/grouping.py) | 解析、引用和分区校验，一次 HTTP 调用、失败归档、精确输入复用、下游读取及 CLI |
| [test_grouping.py](../../../../../tests/skill_evolution/v23/test_grouping.py) | 合成离线测试，覆盖转换、非法输出、网络失败、持久化及无调用复用 |
| [validate_grouping_history.py](../../../../../scripts/analysis/v23/validate_grouping_history.py) | 独立逐字段核对真实原记录与新表示，确认源文件字节不变 |

复用既有 `parse_json_response` 和原子 JSON 写入 `write_record`。旧 `semantic_call` 强制计算和保存哈希，因此未直接复用该包装器；新调用入口使用现有 requests 调用方式，只发一次请求并保存原始响应，不引入哈希或重试。

统一模型输入仅包含 `parent`、`command_sets`、`runs`，背景装入总提示词。程序侧保存实际 run_id／task_id 与步骤来源，不整体发送给模型。过滤先于候选列表共享；原始环境动作合法性仍按未过滤菜单核对，并保留在步骤反馈中。

连续步骤菜单恢复的前提是顺序连续、上一动作已执行且未终止，并且下一步实际 Prompt 与对应观察、历史及菜单精确一致。没有最后一步行动后菜单时保留 null。当前转换器针对 V22 实际记录格式，不猜测其他运行器的自定义后状态字段。

## 2. 离线测试

环境：Python 3.13，pytest、requests、python-dotenv。本次使用 `/tmp/gse-v23-py313/bin/python`；以下命令从仓库根目录执行。

```bash
/tmp/gse-v23-py313/bin/python -m pytest -q \
  tests/skill_evolution/v23 \
  tests/adapters/alfworld \
  tests/skill_evolution/v22/test_grouped_representation.py
```

结果：**102 passed, 19 subtests passed**。其中 V23 新增 58 项，相关回归 44 项；未通过项目为零。

覆盖精确 help 过滤、大小写／空白／重复项、过滤后共享、不同执行身份、初始与相邻状态、末步 null、空列表、原始环境合法性、无 Skill、固定 Skill、技术中断和未知结果、未执行请求、非法引用与重复成员、截断输出、HTTP 失败原文保存、预算提前停止、同轮复用及改变输入／提示词／输出后的拒绝。

## 3. 真实历史轨迹转换

使用 V22 第 23 组五轮实验已有 Parent 原始记录，没有重新执行环境。

```bash
/tmp/gse-v23-py313/bin/python -m scripts.analysis.v23.validate_grouping_history \
  --records artifacts/methods/v22/23_alfworld57_five_round/formal_run/rounds/r1/parent_runs/*/skill_*/trajectory.json \
  --output artifacts/methods/v23/v23_grouping_001/history_r1

/tmp/gse-v23-py313/bin/python -m scripts.analysis.v23.validate_grouping_history \
  --records artifacts/methods/v22/23_alfworld57_five_round/recovery_04/rounds/r2/parent_runs/*/skill_*/trajectory.json \
  --output artifacts/methods/v23/v23_grouping_001/history_r2
```

以上输出目录已经存在，重复审计时需指定新目录，避免覆盖档案。

| 历史批次 | 执行数 | 已执行步数 | 恢复的行动后列表 | 末步 null | 结果 |
|---|---:|---:|---:|---:|---|
| R1，无 Skill | 12 | 171 | 159 | 12 | 12 成功 |
| R2，固定 Skill | 12 | 208 | 196 | 12 | 10 成功，2 步数耗尽 |
| 合计 | 24 | 379 | 355 | 24 | 22 成功，2 步数耗尽 |

379 个实际请求均通过完整 Prompt 重建比较。动作、前后观察、过滤后候选、反馈、原始动作合法性及结果逐字段对应。379 处步骤菜单各过滤一个精确 help；候选列表去重后 R1 为 97 份，R2 为 101 份。原始源文件读取前后字节相同。

技术中断、正常终止失败和未知结果在本次合成测试覆盖；这两批真实数据不包含这些结果，不能称为真实中断轨迹验证。

证据：[R1 报告](../../../../../artifacts/methods/v23/v23_grouping_001/history_r1/report.json)、[R2 报告](../../../../../artifacts/methods/v23/v23_grouping_001/history_r2/report.json)。

## 4. 一次真实 Grouping 调用

事前选定 R2 按任务编号排序的前四条 Parent：train:0012、0013、0014、0015，没有根据 Grouping 输出换样本或重试。四条轨迹共 93 步，包含同一实际 Parent Skill；三成功，一步数耗尽。

```bash
/tmp/gse-v23-py313/bin/python -m src.skill_evolution.v23.grouping \
  --records artifacts/methods/v22/23_alfworld57_five_round/recovery_04/rounds/r2/parent_runs/train_001[2345]/skill_*/trajectory.json \
  --output artifacts/methods/v23/v23_grouping_001/live \
  --round-id v23_grouping_001 \
  --model deepseek-flash --max-tokens 8192 --timeout 180 \
  --max-input-chars 100000
```

| 项目 | 实测 |
|---|---|
| 端点 | https://api.deepseek.com/chat/completions |
| 请求／返回模型 | deepseek-flash／deepseek-flash |
| 调用时间 | 2026-10-18 00:32:26—00:33:05，Asia/Shanghai，约 39 秒 |
| HTTP 请求 | 1，零重试、零修复调用 |
| 序列化输入 | 81,233 个字符，低于声明的 100,000 字符上限 |
| 输入 Token | 23,342 |
| 输出 Token | 7,964，其中 reasoning_tokens 为 7,142 |
| 总 Token | 31,306 |
| 结束原因 | stop，未截断；输出接近 8,192 上限 |
| 结构校验 | 通过；五字段、成员覆盖、排他性与显式引用有效 |

未查询或估算金额费用。完整原始请求、HTTP 响应、模型输出、校验及运行信息保存在 [live 档案](../../../../../artifacts/methods/v23/v23_grouping_001/live/)。[实际分组 JSON](../results/grouping.json)与存档有效结果完全一致，没有人工修正。

| 组 | 成员对应关系 | 实际比较主题 |
|---|---|---|
| G1 | P1＝train:0012；P4＝train:0015 | 取得目标后清洁再交付，以及目的地是否需要打开 |
| G2 | P2＝train:0013；P3＝train:0014 | 未找到目标时，搜索哪些位置以及何时扩展到未检查位置 |

## 5. 分组语义核对

这是本次开发中的人工逐步核对，没有新增审核模型调用。

有依据的部分：

- G1 的取物、清洁、交付步骤引用正确；P4:11 确实先打开柜子，P1 的桌面交付无需该动作。
- P4:5 确实是原始环境菜单外的动作，反馈为 Nothing happens；输出没有把它当作有效到达。
- G2 同时包含失败与成功执行，比较点是重复搜索与扩展搜索，不是简单的成败分组。
- P3:19 发现 dishsponge 3，P3:20 取物、P3:22 清洁、P3:24 交付；P2 在 50 步预算结束时仍未取得目标。
- 没有新增 Skill 规则、历史 Memory 适用性判断或独立因果结论。四条执行全部归组一次。

原始输出中的问题保留如下：

1. **时间顺序表述不准确。** G2 的 shared_basis 先概括 P3:1–P3:17，再使用 then 描述 P3:10 的 shelf 4 访问。引用本身有效，但第 10 步并不发生在第 17 步之后。
2. **初始状态概括超出直接观察。** G2 称 P2 初始房间包含 many closed cabinets；初始观察只枚举柜子，部分柜子的关闭状态是在后续步骤才观察到。不能把这些后续状态直接写成初始可见事实。
3. **G1 问题范围偏宽。** 同时包含清洁顺序和交付前开门，属于有关联的连续决策，但作为单一分组问题仍可更聚焦；不据此声称已确定过度合并。G2 也共享对象名，虽然有具体搜索行为支撑，单次样本不能排除更广泛的对象名偏置。

没有发现明确的过度拆分，但只验证了这一小批。结构校验不判断自然语言时间关系和事实蕴含，因此这些问题不会被程序自动改写或隐藏。原始输出不作为无误的事实摘要；下游仍应结合完整轨迹判断。

## 6. 复用与 Diagnosis 交接

对同一真实输入再次调用 `run_grouping`，提供一个被调用即抛错的生成函数，成功读取已有有效结果；新增模型调用为零，档案文件字节不变。实际配对任务映射为 train:0012→G1、0013→G2、0014→G2、0015→G1，Candidate 无需也不会重新分类。见 [复用核验](../../../../../artifacts/methods/v23/v23_grouping_001/reuse_check.json)。

`load_grouping` 返回共享 facts、background、grouping、程序侧 sources 和 round_id，可作为 V23 Diagnosis 的正式数据接口。当前没有实现或接入 Diagnosis 算法。接口与持久化交接已可用，本次模型分组仍带有上述语义限制，不能当作已证明正确的诊断或事实替代品。

当前适配范围是保留实际 Prompt 和已知两步历史协议的 V22 ALFWorld 记录。缺少初始状态、Prompt 不可重建或能力配置不同的记录明确拒绝，不启发式补造。只验证了一次真实分组调用，不宣称稳定分组质量或 Skill 自进化收益。
