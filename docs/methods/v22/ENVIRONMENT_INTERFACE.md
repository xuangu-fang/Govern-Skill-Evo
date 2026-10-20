# V22 环境—方法接口与固定 Skill 最小执行路径

[返回 V22 索引](README.md) · [机制设计](DESIGN.md) · [ALFWorld 运行说明](../../../src/adapters/alfworld/README.md)

更新日期：2026-10-14。本阶段实现环境侧接口、No Skill／固定 Skill 注入、执行留痕和离线核验。后续独立增加[一轮无历史更新](NO_HISTORY_ROUND.md)连接 Diagnosis／Editor；完整 Fusion／Compiler、Replay 行为解释、Gate 和 Memory 仍待实现。本文所说的轨迹核验不等于上述 Replay 机制。

## 1. 本阶段问题与验收

**Question：** 在不引入 Skill 更新器的条件下，能否从 No Skill 开始，可靠执行指定任务；随后传入固定 Skill，并核对实际发送内容、执行条件、行为和原生结果？

**Hypothesis：** 复用现有 ALFWorld 上游基础协议，在每次请求的 system 消息追加固定 Skill 快照，并保存请求前记录和内容身份，足以形成供下一阶段 Diagnosis／Editor 使用的最小执行路径。这是工程假设，不预测固定 Skill 会提高成功率。

验收要求：

1. 省略 Skill 时不增加 Skill 文本，与上游 NoSkill 消息逐字一致。
2. 固定 Skill 只读取一次，实际全文、内容 hash 和每步请求对应；运行中源文件变化不改变快照。
3. API 失败仍保留请求；环境动作失败仍保留已收到响应；未完成执行不能伪装成正常任务失败。
4. 可以离线核对任务、Skill、协议、请求、动作投影和原生结果，并检查两次执行的已记录条件是否匹配。
5. 学习反馈只从允许的 Train 轨迹导出；Selection／Test 不进入该导出接口。

## 2. 最小实现边界

新增独立入口 `src.adapters.alfworld.run_task_skill`，复用 `run_task_upstream` 的基础提示词、最近两步前动作观察窗口、合法动作展示、模型请求参数、动作解析及 HTTP 重试策略。旧 NoSkill 运行器、旧评测入口和历史结果保持独立。

这不是对某篇方法完整 Skill 注入协议的复现，也不改变现有任务清单。新协议标识为 `govern_alfworld_fixed_skill_v1`，轨迹格式为 `alfworld_skill_execution_v1`。默认 No Skill 是合法初始状态；不需要先人工编写初始 Skill。

**No Skill 仍有环境操作提示词。** 它表示没有附加的、可演化的 Skill 文档，不表示模型没有任务说明或基础运行指令。

当前单位是单任务、单次、全新环境执行；不自动批处理、筛选候选、重跑正常失败、发布 Skill 或跨任务共享对话。后续方法调用该入口或 `run_episode`，不把更新模块塞入环境循环。

## 3. 输入契约

| 输入 | 当前约定 |
|---|---|
| 任务 | 读取固定 edition 的 `items.json`；`--task-id` 必须属于选定 split；默认取该 split 第一项 |
| 用途 | `smoke/train`、`learning/train`、`selection/val`、`final/test` 四种合法组合；默认 `smoke/train` |
| Skill | 省略 `--skill-file` 得到 `mode=none`；指定 UTF-8 文件得到 `mode=fixed`，保存原始换行与全文 |
| Skill 身份 | No Skill 的 `skill_id=none`；固定文件使用全文原始 UTF-8 字节的 SHA-256，路径仅作来源 |
| 非法输入 | 不存在、非 UTF-8 或空白 Skill 文件报错，不能静默降级为 No Skill |
| 模型 | 默认沿用 `deepseek-v4-flash`；保存请求名、每次实际返回名；服务地址只记录 hash，不保存凭据 |
| 单次预算 | 默认 50 步，可设 1–50；输出上限 16,384 tokens，thinking enabled、reasoning effort medium，沿用现有请求参数 |
| 环境 | TextWorld PDDL、`AlfredDemangler(shuffle=False)`、seed 42；每次启动全新实例并 reset 一次 |
| 预检查 | `--dry-run` 检查任务、Skill 和安装接口，不加载 `.env`、调用模型或创建输出 |

缩短步数是入口检查配置，会写入协议和比较指纹。不同步数的运行不视为条件匹配，短检查的成功／失败也不当作正式 benchmark 分数。

Train 反馈可供后续学习；Selection 用于后续事先约定的采用评价，本阶段不实现 Gate；Test 只作最终报告，不用于学习或选择。用途字段与导出检查是程序边界，后续更新器仍须遵守权限，不能绕过导出直接消费 Test 原始文件。

## 4. 注入与可见信息

No Skill 直接调用原 `build_messages`，保留 system/user 两条消息内容。固定 Skill 则在每一步的 system 消息末尾追加：

```text
<skill_knowledge>
{本次执行固定的 Skill 全文}
</skill_knowledge>
```

完整前后分隔符及基础提示词保存在协议中。Skill 不占用最近两步轨迹窗口，也不在执行中重新读取源文件。记录中保存的是实际发送消息，可以证明内容进入请求；这不能证明模型一定理解或遵循了它。

执行 Agent 可见当前观察、目标、实时合法动作和最近两步的前动作观察／动作。不注入隐藏事实、专家路径、PDDL 内容或 walkthrough。环境游戏文件只在执行侧使用并计算内容 hash。

`learning_feedback(record)` 对完成或不完整的 Train 轨迹先核验，再按白名单导出：任务 ID、Skill 快照、执行身份、模型与步数／token 预算、历史窗口、可见初始观察、每步请求／响应／动作／反馈、原生结果和错误阶段。保留预算是为了让 Diagnosis 能区分两步入口检查与完整任务执行，不能仅凭 `step_limit` 断言 Skill 有缺陷。它不导出游戏路径、Skill 本机路径、隐藏环境内容或后端地址。完整轨迹为审计材料，不能不加区分地全部拼入 Diagnosis 提示词。

## 5. 输出与可核对身份

每次执行创建独立 `skill_<时间>_<唯一后缀>/trajectory.json`，不覆盖已有运行。主要内容如下：

| 内容 | 用途 |
|---|---|
| `run_id`、schema、开始／结束时间 | 标识这一次执行及其完成状态 |
| 任务、split、purpose、access | 区分任务身份与反馈用途 |
| 清单与实际游戏文件 SHA-256 | 识别同一 ID 下的数据变化；不保存隐藏文件正文 |
| `skill` | 保存 No Skill／固定 Skill 模式、全文与内容身份 |
| `protocol`、`versions`、`implementation` | 保存基础模板、注入位置、模型配置、环境预算、依赖版本、Git HEAD 与实际执行源码 hash；未提交源码也可区分 |
| `context_fingerprint` | 汇总任务、用途、数据、模型、后端、协议、版本与实现；排除 Skill，供不同 Skill 的条件核对 |
| `execution_fingerprint` | 在上述条件上加入 Skill 身份；不等同于每次唯一的 `run_id` |
| `initial_observation` 与初始合法动作 | 检查 reset 后实际可见入口是否一致 |
| `steps` | 保存真实请求消息、响应、动作投影、环境反馈和执行阶段 |

每个步骤按 `requesting → responded → executed` 留痕。请求先落盘再发送，响应先落盘再调用环境；通过临时文件替换保存当前轨迹。

HTTP 尝试也在发送前记录，保存不含消息正文的请求参数、完整请求体 hash、返回码／错误类型、耗时和已知 usage。消息正文在步骤内保存，凭据、headers 和服务地址不写入记录。沿用原客户端最多六次同请求 HTTP 尝试；网络异常不自动重跑整项任务。失败或未报告的 usage 保留未知，离线汇总同时报告已知 token 和未知次数，不将未知费用算成零。

原子保存保障完整文件替换，不代表本阶段已实现进化轮次事务或任务自动恢复。进程被强制终止可能留下 `running`／`requesting`；已完成响应可能计费但尚未落盘，仍应保留未知。后续恢复机制需在第五步协议下另行实现。

## 6. 状态与核验边界

| 状态 | 解释 |
|---|---|
| `success` | 环境返回 `won=true` |
| `environment_ended` | 环境结束但未成功 |
| `step_limit` | 用完本次记录的步数，未成功；是正常任务失败 |
| `error` | 环境设置、reset、模型请求或环境执行发生错误，保存 `error_stage`／类型 |
| `interrupted` | 收到中断，保留此前真实完成内容 |
| `starting`／`running` | 尚未正常结算或进程被强制终止，不视为完整评价 |

离线核验器检查 Skill 内容/hash、用途、指纹、每步提示词、动作解析、状态与原生结果一致性。它不重新执行环境，也不证明原始记录来自可信硬件或排除所有外部变化。未知和错误不被补成行为无效。

双轨迹检查比较实际任务、数据、用途、模型、协议、依赖、实现、初始可见状态与服务返回模型；Skill 可以不同。返回 `recorded_conditions_match`，不输出编辑收益、采用建议或因果结论。相同 seed 也不保证模型采样和远端服务完全相同。

当前采用严格条件匹配：例如源码、用途、清单身份或环境记录变化时不会自动放宽。后续 Replay 若需复用不同协议的证据，应显式界定可比范围，不能仅因为任务 ID 相同就复用。

## 7. 使用路径

在项目根目录、已有 `alfworld` 环境中执行。默认不附加 Skill：

```bash
conda activate alfworld
python -m src.adapters.alfworld.run_task_skill --dry-run

# No Skill：初始状态；下面是缩短步数的 Train 接口检查
python -m src.adapters.alfworld.run_task_skill \
  --purpose smoke --split train --task-id train:0000 --max-steps 2

# 固定 Skill：只测试注入能力，fixture 不是默认初始 Skill
python -m src.adapters.alfworld.run_task_skill \
  --purpose smoke --split train --task-id train:0000 --max-steps 2 \
  --skill-file tests/adapters/alfworld/fixtures/fixed_skill.md

# 将下列占位路径替换为真实 trajectory.json；全程离线
python -m src.adapters.alfworld.verify_skill_run /path/to/trajectory.json
python -m src.adapters.alfworld.verify_skill_run /path/to/noskill/trajectory.json \
  --compare-with /path/to/fixed/trajectory.json
python -m src.adapters.alfworld.verify_skill_run /path/to/train/trajectory.json \
  --feedback-output /path/to/new_learning_feedback.json
```

核验合法的不完整轨迹可以正常返回，但报告 `episode_complete=false`、`native_success=null`；不能把 CLI 返回 0 当任务成功。双轨迹条件不匹配返回非零并列出差异。反馈导出拒绝已有目标文件和 Selection／Test 轨迹。

## 8. 与后续方法实现的交接

后续[一轮 Diagnosis／Editor](NO_HISTORY_ROUND.md)已建立独立方法层入口：Diagnosis 消费允许的当前 Train 反馈与 No Skill，Editor 产生固定 Candidate 文件，再通过同一执行入口收集 Candidate 轨迹。Parent 与 Candidate 的血缘、实际 diff、目标与更新要求由该方法层建立；环境入口本身只管理执行事实。

现有入口提供执行事实，后续 Replay 再分析目标、保留行为、机会与响应；Gate 再按明确协议决定采用；Memory 再学习更新作用。单任务原生成功不能替代这些机制，也不能据此声称预条件化已经实现。

## 9. 本阶段验证记录（2026-10-14）

离线运行 `python -m unittest discover -s tests/adapters/alfworld -v`，35 项测试全部通过。其中新增 20 项，覆盖内容快照、No Skill 消息兼容、用途权限、请求／响应前落盘、HTTP 重试与参数核验、错误／中断、条件匹配以及反馈导出；原有 15 项回归测试保持通过。No Skill 与固定 Skill 的真实环境 dry-run 均通过。

真实入口检查仅使用 `train:0000`，每种模式一次、每次最多两步，模型请求名及返回名均为 `deepseek-v4-flash`。temperature 请求值 1.0、thinking enabled、reasoning effort medium，协议见保存轨迹；Git HEAD 为 `7d4749541dab04397ea146e56dc762a26ba81a3b`，未提交实现以轨迹中的文件 hash 标识。

| 模式 | 实际动作数／HTTP 请求数 | 终止状态 | 已报告总 tokens | 离线核验 |
|---|---|---|---|---|
| No Skill | 2／2 | `step_limit`，未成功 | 1,226 | 通过 |
| 固定测试 Skill | 2／2 | `step_limit`，未成功 | 1,706 | 通过 |

两次实际动作均为 `go to desk 1`、`examine desk 1`；未发生 HTTP 重试，没有未知 usage。已记录执行条件匹配，Skill 身份不同，四次实际消息与各自快照一致；固定 Skill 来自通用注入测试 fixture，不包含任务答案。此检查只证明执行链与记录契约接通，不比较效果，也不据此选择 Skill。

完整审计结果：[validation.json](../../../artifacts/methods/v22/interface_20261014/validation.json)。原始轨迹和允许的学习视图位于同一 artifact 目录的 `noskill/`、`fixed/` 与 `*_learning_feedback.json`。没有执行 Selection／Test 或完整 benchmark，没有实现更新模块。
