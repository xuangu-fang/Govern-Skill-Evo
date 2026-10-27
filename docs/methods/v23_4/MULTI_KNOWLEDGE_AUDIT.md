# 多 Knowledge P1：依赖审计与兼容性基线

日期：2026-10-22。范围：统一契约、现有依赖、旧格式兼容边界与后续验收清单。**本轮没有实施 P2–P4，没有启动模型或提交正式 Memory。**

## 1. 审计方法与材料

对 `src/tests/scripts/experiments` 中 rg 可见的 Python/Markdown 做检索，并对 Python imports 做静态反向依赖闭包，种子为 `v23.memory` 和 `v23_3.memory_view`。V23/V23.2/V23.3/V23.4 的字段访问、结构示例、版本与调用匹配同时列入清单；历史 source/baseline 快照也标记但不修改。随后人工检查生产链路，并只读加载实际 R05/R06 Memory、旧 Replay 和已冻结实验输入。

[DEPENDENCIES.json](../../../experiments/methods/v23_4/multi_knowledge_contract_001/DEPENDENCIES.json) 保存路径、行号、匹配类型、代码片段、静态导入关系和 SHA256。扫描 2,893 个文件，清单包含 560 个：生产目录 36、测试 34、历史实验及快照 490。该数量包括 Prompt/README、通用 evidence 字段和间接依赖，**不代表要修改 560 个文件**。

静态扫描不能证明动态执行分支全部覆盖；本报告通过下列逐接口核对补充。仓库内同名的 V19/V21 Memory 使用不同契约，不属于本次升级。脚本目录未发现直接依赖这两个 Memory 核心的额外调用链；例如 V23 grouping 分析脚本不消费 Memory。

## 2. 生产依赖与后续处理

路径均相对仓库根目录；函数定位与精确匹配行号可从清单核对。

| 位置 | 已核实的旧格式依赖 | P2/P3 需要做什么 |
|---|---|---|
| `src/skill_evolution/v23/memory.py::validate_memory` | Active Entry 精确字段 id/knowledge/evidence；knowledge 必须字符串；每 Entry 必须同时有 diff 和执行引用 | 按明确契约分别校验旧/新结构；新格式逐 Knowledge 校验，Entry 证据并集检查类型，不把合法引用当语义支持 |
| 同文件 `validate_entries` | Replay Entry 精确 revises/knowledge/evidence；拒绝重复修订 Active ID | 新输出为 revises/knowledge；保留 Memory 级修订关系；失败原子化，旧默认不静默接受新输出 |
| 同文件 `_archive` | 所有 commit 用同一旧校验器；stored Entry 顶层 evidence 逐项加 context；精确比较 stored 与 proposal 派生值 | 每个提交按自身版本验证，再做新读旧投影；逐 Knowledge 限定引用；保留链路与 Active 顺序验证 |
| 同文件 `load_memory` | 提取 id/knowledge/evidence，遍历 entry.evidence 装载完整 sources | 新路径归一化 Active Entry，再汇总每条证据；旧路径返回旧形状。禁止直接修改默认返回值导致所有旧消息变化 |
| 同文件 `commit_memory` | `context.payload.memory == load_memory(root)`；validate_payload 间接调用旧验证；存储时只重写顶层 evidence | 同版本快照精确比较；新写旧目录副本时比较归一化快照；新增显式 commit 契约，限定每条证据；保持锁、不可变归档、原子索引、pending 恢复、幂等检查 |
| `src/skill_evolution/v23_3/memory_view.py::compact_memory` | 直接读 entry.evidence 构建锚点，复制原 entries，使用旧 validate_memory | 汇总全部 Knowledge 引用；entries 原样保留绑定；固定 ±2、完整 trace、菜单去重不变；旧单条投影精确兼容 |
| 同文件 `project_payload/project_messages` | v3/legacy 视图选择，固定追加同一 FORMAT_PATH | 贯通 Memory 契约和版本化格式说明；不直接覆盖共享说明，否则旧 PC/Replay 消息无法重建 |
| `src/skill_evolution/v23/replay.py::validate_payload/build_replay_from_editor` | 七字段事实校验末端调用 validate_memory；由 Editor/配对事实构建完整 bundle | 新路径必须贯通新 Memory 验证，事实/配对算法不变；旧 API 默认行为保留 |
| 同文件 `load_replay/run_replay` | 原始响应与 parsed/replay 精确相等；用当前模板重建 messages；旧输出校验 | 保留旧归档路径；新 Replay 使用显式契约及模板版本，不能先转换旧响应再比较或把旧输出当新结果 |
| `src/skill_evolution/v23_4/replay.py` | 导入旧 validate_entries；messages_for、validate_bundle、run/load 多处复用旧 payload 验证；只识别现有 Prompt | 增加新契约 opt-in 装配/校验/重载；记录新版本，不覆盖默认 Prompt；一次调用不变 |
| `src/skill_evolution/v23_4/replay_view.py::history_pair_sources` | `load_memory(directory) == memory` 精确快照比较 | 新读取路径比较同一表示；保留来源 path/SHA，不把旧归档原地转换 |
| 同文件 `_historical_pairs/model_input` | 旧 validate_memory、旧 archive payload 验证与 compact_memory；source 内容精确匹配 | 读取每个历史 commit 的版本、验证原始上下文；新 entry 表示与来源独立；Pair 校验、未知配对和完整当前轨迹规则不变 |
| `src/skill_evolution/v23/preconditioner.py::preconditioner_input` | 构造六字段输入前 validate_memory | 新格式不能只在序列化时处理，必须在入口验证通路贯通；不改变当前执行筛选或 Plan |
| 同文件 `compile_effective_plan` | 再次 validate_memory，消费返回的事实引用集合与 Memory ID | 共享编译器是间接阻断点。按契约得到相同身份集合，D/S/C/Update/Check 编译算法不变，不拼接知识伪装成旧格式 |
| `src/skill_evolution/v23_4/update_patch.py::normalize_update_patches` | validate_memory + project_payload，然后调用 V23 编译器；按可见源检查 reason 引用 | 契约传递贯穿投影与编译；Memory ID 与源引用仍用原语法，不添加 Knowledge ID |
| `src/skill_evolution/v23_4/preconditioner.py` | read/run/load 依赖旧输入/投影；memory_contract 固定 entries_sources；重建 input/messages/派生输出 | 显式新 memory_contract；精确重建对应视图与说明；D/S/C contract_version 不变 |
| `src/skill_evolution/v23_3/preconditioner.py/update_patch.py` | 共享输入、投影和编译器；历史版本与旧消息比较 | 作为回归保护对象，不自动启用多 Knowledge；共享函数的默认行为保持不变 |
| `src/skill_evolution/v23_4/editor.py`、V23/V23.3 Editor loaders | Editor 不直接读 Knowledge；load_editor 会重载整个 Preconditioner 上游 | 验证新上游链可加载即可，不改 Editor 模型接口或策略；需区分既有 Prompt 漂移问题 |
| `src/skill_evolution/v23/evolution.py` | 硬编码旧模块、加载/复制 Memory、调用 Replay 后 commit、切换 Active | 本次不接管默认 evolution；保护旧流程，不因共享 Memory 函数升级而意外采用新格式或发布实验结果 |

生产代码直接对 `knowledge/evidence` 做字面字段读取的核心只有 `v23/memory.py` 和 `v23_3/memory_view.py`；这不意味着只改这两个文件就能跑通，其余严格校验、版本与精确比较同样需要适配。

`diagnosis.py` 的 fields/links 是通用严格结构与引用工具，不需要改为宽松接受新字段。Diagnosis、Grouping 和 Gate 的 evidence 不是 MemoryEntry 顶层 evidence，不得全仓替换。Actor 不消费 Memory。

## 3. Prompt 与版本依赖

- `v23_4/replay_prompt.md`：默认仍是单 Knowledge 输出；新主 Prompt 应独立版本化，不覆盖当前默认。
- `experiments/methods/v23_4/replay_prompt_candidate_001/candidate_prompt.md`：最近单 Knowledge 正式候选，是 P4 设计参考，不是已实现的新契约 Prompt。
- `v23_3/memory_view_prompt.md`：共享视图说明；原文字节需为旧消息重建保留。新路径补充知识数组语义时，不改变原压缩边界。
- `v23_4/replay_view_prompt.md`：当前仍说 output contract unchanged；新路径需明确对应多 Knowledge 契约，不能破坏原实验冻结说明。
- `v23_4/preconditioner_prompt.md`：方法和输出不变，只在新输入格式说明中告知逐 Knowledge 与证据绑定；不用增加 Knowledge ID 或重新生成 D/S/C 标签。
- `v23/prompts.py::render_prompt` 要求模板恰好有一个 execution_context 占位符；候选实验目前自行追加 execution_context。P4 要明确新主模板如何沿用这条装配边界，并确保背景只出现一次。
- 当前历史加载器多用“现用模板重建并比对”，并不天然拥有任意旧 Prompt 的版本注册表。新版本要显式保留可信旧模板/加载规则，不能用取消比对或盲目信任归档 Prompt 来宣称兼容。

## 4. 测试与历史脚本

### 直接字段依赖的测试/fixture

`tests/skill_evolution/v23/test_replay_memory.py`、`v23_4/offline_cases.py`、`v23_4/test_diagnosis_replay.py`、`v23_4/test_offline_cases.py` 直接构造、修改或读取旧 knowledge/evidence。应保留旧案例的回归意义，另增明确新契约案例，不全部改写为新格式后失去兼容覆盖。

其他重点链路测试：

- `v23_3/test_memory_view.py`：五份 accepted v3 视图逐值一致、legacy 重建、版本/篡改拒绝。
- `v23_4/test_replay_view.py`：Pair 不猜测、当前完整事实、来源 SHA、预算、视图重建、Memory 后续投影。
- `v23_4/test_preconditioner.py/test_update_patch.py`：新 Memory 经原 D/S/C 决策与共享编译器，不修改输出含义。
- `v23_4/test_empty_action_evidence.py`：无效空动作仍是合法执行证据，不能因形状升级误删。
- `v23/test_evolution.py/test_capacity_recovery.py` 及模型路由等：旧默认流程、重试和发布职责不变化。
- JSON 形状测试不足以代替真实引用、历史限定、混合版本提交、快照一致性与语义遗漏测试。

### 直接字段访问的历史脚本/冻结副本

以下 17 个文件被扫描命中；保留原实验实现，不就地批量适配。需要新实验时使用独立目录与新契约入口：

1. `experiments/methods/v23/v23_replay_memory_001/config/source/src/skill_evolution/v23/memory.py`
2. `experiments/methods/v23_2/v23_2_memory_evidence_audit_001/audit.py`
3. 同目录 `write_reports.py`
4. `experiments/methods/v23_2/v23_2_preconditioner_commitment_analysis_001/analyze.py`
5. `experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/freeze_inputs.py`
6. 同目录 `write_reports.py`
7. `experiments/methods/v23_3/memory_compaction_offline_001/audit.py`
8. 同目录 `compact.py`
9. 同目录 `test_compact.py`
10. `experiments/methods/v23_4/r05_replay_memory_001/check_memory.py`
11. `experiments/methods/v23_4/r06_replay_memory_001/baseline_sources/src/skill_evolution/v23/memory.py`
12. `experiments/methods/v23_4/r06_replay_memory_001/check_memory.py`
13. `experiments/methods/v23_4/replay_input_view_live_001/check_memory.py`
14. 同目录 `review_facts.py`
15. `experiments/methods/v23_4/replay_prompt_candidate_001/check_memory.py`
16. 同目录 `review_facts.py`
17. `experiments/methods/v23_4/semantic_generation_001/run.py`

最后一项的共享真实运行器将 Replay 输出交给旧 validate_entries；P6 必须显式接入新校验，不得只把 Prompt 换成数组示例便开始调用。

间接调用和旧形状 fixture/文案的完整路径、行号见 DEPENDENCIES.json，包括 V23.2 分析实验、V23.3 压缩实验以及各轮 run/check 脚本。静态闭包纳入的历史脚本不等于当前生产入口。

## 5. 已执行的只读基线

[BASELINE.json](../../../experiments/methods/v23_4/multi_knowledge_contract_001/BASELINE.json) 保存结果和原 Memory 文件 hashes。

| 检查 | 结果 |
|---|---|
| R05 原 Memory（正式 S1/R04） | load_memory/validate_memory 通过，与冻结实验输入相等；原 JSON hashes 不变 |
| R06 原 Memory（正式 S1/R05） | 同上 |
| 新提案形状交给现有旧 validate_entries | 两轮均明确拒绝：`Memory proposal: unexpected fields`，证明当前尚未支持新契约 |
| 旧正式 S1/R03 Replay `attempts/001` | 原加载器成功重载，3 条旧提案 |
| 四个相关旧实现测试文件 | **104 passed，2 failed**；没有隐去失败或先排除再声称全通过 |

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q -p no:cacheprovider \
  tests/skill_evolution/v23/test_replay_memory.py \
  tests/skill_evolution/v23_3/test_memory_view.py \
  tests/skill_evolution/v23_4/test_replay_view.py \
  tests/skill_evolution/v23_4/test_diagnosis_replay.py
```

两项失败分别是 `test_frozen_real_readonly_interfaces` 和 `test_old_archive_and_editor_still_reload`，都在 Editor 历史消息重建时报 `Saved Editor prompt/input differs`。本轮生产代码未修改，属于升级前已有的兼容基线问题；这也说明不能笼统承诺“所有历史归档当前均可重载”。P2/P5 需要把新 Memory 兼容回归与已存在的 Editor Prompt 漂移分开报告，不能改旧归档、关闭完整性核验或靠多 Knowledge 转换掩盖它。

上述检查证明的是现有链路状态与新旧接口不兼容位置，不是新机制已通过离线验收。

另已检查 [JSON Schema](../../../experiments/methods/v23_4/multi_knowledge_contract_001/contract.schema.json) 本身合法，并执行 [17 个契约形状示例](../../../experiments/methods/v23_4/multi_knowledge_contract_001/EXAMPLES.json)，结果见 [CONTRACT_CHECK.json](../../../experiments/methods/v23_4/multi_knowledge_contract_001/CONTRACT_CHECK.json)。包括完整数组替换示意、旧格式只读包装、空更新、禁止空 Knowledge/重复顶层 evidence/Knowledge ID 等；未知来源、跨 Entry 重复修订与缺少 Diff 被明确列为需要运行时验证的情况，未伪称 JSON Schema 能完成这些检查。

交付前哈希核对确认审计清单中的 560 个原文件、上一轮候选实验冻结文件及 R05/R06 原 Memory 均未改变，见 [INTEGRITY.json](../../../experiments/methods/v23_4/multi_knowledge_contract_001/INTEGRITY.json)。本轮只有新增 P1 文档/契约材料和文档索引更新，没有模型调用、生产模块或默认 Prompt 改动。

## 6. P1 决定与交接

统一规则以 [MULTI_KNOWLEDGE_CONTRACT.md](MULTI_KNOWLEDGE_CONTRACT.md) 为准：

1. 保留用户给定的两层数组结构；每条 text/evidence，Entry 无重复顶层 evidence。
2. 非空 Knowledge 数组；完整替换与 Memory 级 revises；程序不自动补回旧认识。
3. 显式新 memory_contract 只在程序元数据中登记；旧默认读取/写入与消息重建保留，新路径 opt-in。
4. 旧提交先按原版本核验，再只读归一化给新消费者；新快照比较和历史 Pair 来源验证采用一致表示。
5. v3 仅适配证据入口，保留原窗口/trace/menu 算法与逐 Knowledge 证据绑定。
6. Preconditioner 输入、引用验证和共享编译器都必须贯通；不通过拼接大字符串绕过新格式。
7. P6 原事实与原 Memory 内容冻结，但 Memory 表示和 Prompt 将改变，不能声称 User 消息逐字不变。

下一阶段是 P2 的新格式与兼容存储实现。P3–P6 的验收项已列入契约；本轮不提前实现、不发布新默认、不声称语义效果改善。
