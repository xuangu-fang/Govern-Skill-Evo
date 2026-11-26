# v27.1 独立实现与离线验收

2026-11-04：已实现独立 v27.1 链路。四份提示词已绑定运行器，其中三个模块的引用说明已与修复后的解析规则同步；正式六批训练已于 2026-11-04 13:20:25 启动，完成检查已安排；Test 未启动。设计阶段的 JSON 快照保持原样，本文件记录其后的实现状态。

## 实现范围

| 部分 | 实现与行为 |
|---|---|
| 独立运行器 | `src/skill_evolution/v27_1`；独立 method、stage、runtime、prompt、Gate、Memory 身份，不迁移旧运行目录 |
| LMB Actor | 本地 `lmb/protocol.py` 显式绑定 65,536；原生单轮消息和标签解析，技术失败/length 共六次尝试，恢复不重置 |
| 数据 | 复用 v27 `OptimizationDataset`；35+18 题、六批 10/10/10/10/10/3、124 题 Test、seed 42；保留原始/准备数据校验和选项映射 |
| 四模块 | Diagnosis 全批直接证据，无 Grouping/Checks；Preconditioner KEEP/REPLACE/WITHDRAW；Editor 逐 Update patch；Replay 只投影 EM 翻转 |
| Gate | Retain：G>0/L=0；Reject：G=0/L>0；其余 Defer。只组合 Retain，不把 Candidate 分数赋给新组合 |
| Memory | 全量有效提案和事件追加；顺序 commit ID，HEAD 原子发布 Memory 与 Selected；正常恢复读取已提交检查点 |
| 执行校验 | 当前 Actor 来源必须注册并通过原生日志/摘要校验；共享视图保留完整普通 content，隐藏推理不进入模块 |
| 方法重试 | 四模块各 32,768/300 秒/六次总尝试；输出错误只附最近一次普通输出和验证错误，事实版本标识为 LMB |
| Test | 独立入口只用最终 Selected；完整覆盖后发布 `summary.json`。技术失败/中断写 `report.json`，列出 pending/errors，EM/F1 为 null，不补零；成功恢复后更新报告 |

四模块、选择性组合和轻量提交逻辑来自 v28.3；LMB 的 Actor、评分和执行归档逻辑来自原生 v27。将需要绑定协议的代码放在独立目录，以避免修改历史版本或全局切换 Actor 预算。明确命名空间语法、patch 基础工具和存储辅助函数继续复用；自由文本执行引用使用 v27.1 本地解析器。没有引入新的全仓库源码哈希运行门槛。

## 数学符号重名修复

修复 Diagnosis、Preconditioner、Replay 将裸 `G1/P12/Q12` 误认作来源的问题；裸 `P1/P2` 不再隐式选择运行。保留结构化 basis、明确子引用/命名空间引用、历史引用及逐事件来源权限检查。Plan 筛选逐字段读取 basis 和 goal/text 的明确引用，不再扫描整个 JSON，Update ID 不参与来源筛选。

配置新增 `method.reference_policy=v27_1_explicit_prose_references_v1`，恢复时拒绝缺少该策略或采用旧策略的配置，避免同一运行静默切换解析语义。方法/提示词 ID 与请求预算不变，没有迁移已有运行或修改历史版本。

新增 7 项回归，覆盖三个模块的数学符号重名、明确来源权限、结构化 basis、引用列表/范围、Plan 路由及四阶段一次成功无纠错重试。解析器修复阶段未改提示词；随后经授权同步三个模块的引用说明，Editor 逐字不变。具体规则见 [CONTRACTS.md](CONTRACTS.md#3-无损共享与引用权限)。

## 引用说明同步

Diagnosis、Preconditioner、Replay 现在明确区分普通数学符号与来源引用：裸 `G1/P12/Q12` 和裸斜杠表达式不自动作为引用；自由文本使用 `P1:1`、`P1:outcome` 或单对反引号包围的 `Evidence:P1` 等明确标记。含子引用的列表仍逐项验证，历史来源及模块权限限制不变。Diagnosis 额外说明结构化 basis 的精确 ID 和 Plan 筛选边界；Preconditioner 澄清明确命名空间的类型；Replay 保留逐事件来源限制。

本次只同步引用协议说明及文档/来源差异，不改变方法职责、输出字段、解析代码、预算或提示词版本标识。运行记录仍冻结实际提示词原文，已有记录不能静默采用新文本。Editor 未修改，没有新增专门禁止 Group 的提示段落。

## 交付入口

- [可执行配置](../../../experiments/configs/v27_1_lmb53.json)
- [train/test CLI](../../../scripts/runs/run_v27_1_campaign.py)
- [实现源码](../../../src/skill_evolution/v27_1/README.md)
- [离线验收器](../../../scripts/verification/verify_v27_1_campaign.py)
- [机器可读验收结果](offline_acceptance/validation.json)及[详细日志](offline_acceptance/unittest.log)

配置将 Actor 固定为 deepseek-flash、thinking enabled、medium、temperature 1.0，Train/Test 并发 20/16。初始 Skill 使用原生 v27 初始文本；初始 Memory 为空。不会自动继承历史训练产物。

## 离线验收

联合验收包含旧 v27 的 98 项回归与 v27.1 的 141 项检查；以机器可读报告为最终结果。测试使用合成响应，阻断网络连接及子进程调用，不读取真实模型凭据。

覆盖完整合成 53/124 调度、原生评分与 fallback、隐藏字段隔离、完整批次来源校验、Plan 引用筛选、共享视图还原、调整动作、patch/子集组合、Gate 全部分支、追加与发布中断、请求额度、响应恢复、跨版本拒绝、Test 隔离和不完整报告。对真实数据只做成员、映射、原有内容校验和配置预检，不执行 Actor。

验收器同时比较设计时保存的 12 份来源快照，并确认验收期间受保护的源码和提示词未变化。运行器直接加载本目录当前四份提示词；设计静态检查结果仍单独保存在 `design_validation.json`，不计入实现测试数量。

在仓库根目录运行以下命令可重复离线验收：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/verification/verify_v27_1_campaign.py --output docs/methods/v27_1/offline_acceptance
```

只做真实数据/配置预检（不创建 campaign、不读 `.env`、不构造真实模型传输）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/runs/run_v27_1_campaign.py train experiments/campaigns/v27_1_lmb53_review --config experiments/configs/v27_1_lmb53.json --validate-only
```

## 后续实验边界

离线通过证明工程合同和恢复路径可执行，不能证明自然语言归因准确或数学成绩提高。下一步可先审阅本次实现与验收，再单独启动正式六批训练；训练完成后审阅最终 Selected，再显式执行 124 题 Test。两者没有自动串联。当前六批训练运行中，完整结果及最终 Selected Skill 待训练结束汇总，Test 未启动。
