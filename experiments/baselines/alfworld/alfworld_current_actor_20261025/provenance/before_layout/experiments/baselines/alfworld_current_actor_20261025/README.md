# ALFWorld 新对照实验：配置已准备，未启动

实验日期标识：2026-10-25。准备阶段不执行训练、环境任务或模型请求。

本组固定 39 Train / 18 Selection / 134 Test。18 个 Selection 是用户明确
选择的本地数据协议；论文描述为 140 个，因此本组是“当前数据和 Actor 条件下、
方法参数按论文描述对齐的 SkillOpt 对照”，不是论文原始实验的逐项复现。

## 文件与运行入口

- `actor.json`：两组共享的 Actor 配置，以 `alfworld_verified_feedback_001` 为参照。
- `noskill.json`：仅 Test，Skill mode 为 `none`，不注入文档或占位 Skill。
- `skillopt.yaml`：完整、独立的 SkillOpt 配置，不继承可变的上游默认 YAML。
- `initial_skill.md`：当前方法的初始 Skill 原文快照。
- `splits/`：冻结任务清单及顺序。
- `manifest.json`：配置、执行源码、原实验关键结果和 191 个环境文件的哈希。
- `offline_validation.json`：离线检查结果；不是实际 API 或训练烟雾测试。

从项目根目录检查（默认行为；不读取密钥、不访问模型、不启动环境）：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skillopt/bin/python scripts/runs/run_alfworld_aligned.py
```

`noskill` 或 `skillopt` 参数单独使用也只检查。只有显式加 `--start` 才执行。
本次没有执行该选项，也未配置定时启动。未来正式执行仍需用户发出启动指令。
入口拒绝覆盖已有输出目录，不会自动恢复、重抽失败任务或挑选成功结果。

输出目录分别为：

- `artifacts/baselines/noskill/alfworld_current_actor_20261025`
- `artifacts/baselines/skillopt/alfworld_current_actor_20261025`

## 与 10 月 23 日 SkillOpt 的差异

| 项目 | 旧实验 | 新实验 |
|---|---|---|
| Slow Update Selection Gate | false，慢更新直接接受 | true，严格通过 Selection Gate 才接受 |
| 最后 Skill 的额外 Test | 开启，若与 Best 不同则另跑 | 关闭；保留 Skill 文件、最终 Selection 与 Best 晋升 |
| Actor 每步请求总额度 | 后端最多 3 次 | 共用最多 6 次，含首次 |
| Actor 正文输出要求 | think + action | action_only_v1；内部 thinking 仍开启 |
| 缺失／不可用动作 | 旧解析与 look 回退 | 返回最近失败正文及具体诊断；未执行动作，不推进历史 |
| 空响应／截断／技术异常 | 旧后端行为，失败后可能回退 look | 当前共享 Actor 校验和重试，额度耗尽保存现场并停止 |
| 初始 Skill | 原始输出格式要求 | 仅将输出要求对齐 action-only，策略内容沿用当前初始 Skill |
| Actor 执行实现 | SkillOpt 原 batch rollout | 当前方法同一 `src.adapters.alfworld.run_task_skill` CLI |
| Actor 调度 | 一批内等全部动作返回后推进 | 最多 8 个独立任务工作进程，与当前方法一致 |

新入口将原始轨迹转换成 SkillOpt 原有 `conversation.json` 和结果格式。
不生成虚假的 think 正文，也不向 Actor 注入参考答案或训练诊断。
合法动作执行后的任务失败不会触发动作重采样。
技术错误／中断不伪装成任务失败交给优化器；批次停止，已有现场保留。
每次 HTTP 的原始响应和 usage 包括被拒绝的响应均保留；未知 usage 单独计数。

共享 Actor 的其余配置保持：deepseek-v4.1-flash、内部代理、temperature=1、
thinking=enabled、medium、16384 输出 tokens、300 秒读取／10 秒连接超时、
最近两步 observation/action、50 个环境步、8 个并发任务、环境 seed=42。

优化器模块仍使用原有最多 3 次后端 HTTP 尝试、16384 输出上限、300 秒超时。
Actor 的 6 次额度不套到 Analyst/Merge 等模块，也不引入本方法的
Preconditioner/Replay/Verifier。R06 Verifier 的 65536-token 特例不适用于本组。

## 方法参数核对

依据：https://arxiv.org/html/2605.23904v2 （§3.6、§4 默认超参数、附录 C）。

| 参数 | 新值 | 相比旧实验 | 依据 |
|---|---|---|---|
| num_epochs | 4 | 不变 | 论文默认 |
| batch_size / accumulation | 40 / 1 | 不变 | 默认 batch 40；保留本地 accumulation |
| Train / Selection / Test | 39 / 18 / 134 | 不变 | 用户选定；Selection 与论文 140 有区别 |
| minibatch / merge batch | 8 / 8 | 不变 | 论文默认 |
| analyst_workers | 16 | 不变 | 论文默认 |
| max_analyst_rounds | 3 | 不变 | 论文允许最多 3 轮细化 |
| failure_only | false | 不变 | 同时反思成功与失败 |
| edit_budget / min_edit_budget | 4 / 2 | 不变 | 论文默认 |
| lr_scheduler / lr_control_mode | cosine / fixed | 不变 | fixed 表示使用预设调度器，非恒定预算 |
| skill_update_mode | patch | 不变 | 论文默认 |
| use_gate | true | 不变 | 严格提升，平分拒绝 |
| use_slow_update / samples | true / 20 | 不变 | 论文明确启用 |
| slow_update_gate_with_selection | true | **false → true** | 论文要求慢更新经过验证 |
| longitudinal_pair_policy | mixed | 不变 | 保留改善、退化、持续失败、稳定成功 |
| use_meta_skill | true | 不变 | 论文明确启用，指导优化器而非部署 Actor |
| use_skill_aware_reflection | false | 不变 | 避免加入论文未描述的额外机制；非论文直接列出的参数 |
| gate_metric / use_semantic_density | hard / false | 原隐式默认显式写入 | 保持只按原生任务成功率选模 |
| eval_final_skill | false | **新增开关，旧行为为 true** | 用户要求，Initial 与 Best Test 保留 |

39 个训练任务、batch 40 意味着每个 epoch 一次普通优化，共四次；原调度预算
为 4、3、2、2。拒绝 buffer 每个 epoch 清空，因此此设置没有同 epoch 下一步
读取拒绝反馈的机会；Meta Skill 仍可跨 epoch 传递经验。按用户要求保留该设置。

最终比较四组：No Skill、Initial Skill、SkillOpt Best，以及已有的本方法
120/134（89.55%）。本次计划新执行 3×134=402 个 Test episode，不能复用旧协议
下的 117/134 Initial 测试。Best 只按 Selection 选择，Test 不参与优化或挑选。

## 必要实现适配

`scripts/runs/alfworld_aligned_common.py` 和 `run_alfworld_aligned.py` 是新入口，
只在显式启动后执行任务。它们复用共享 Actor，不修改共享 Actor 源码。
SkillOpt 原训练器仅新增独立 Final Test 开关，缺省 true，维持旧入口行为；
配置加载器增加对应键。改动另存 `skillopt_optional_final_test.patch`，便于审阅，
当前 checkout 已应用，不应重复应用。旧结果文件和旧 YAML/启动器没有覆盖。

配置和源码冻结后如有变更，离线检查会拒绝启动，需要重新核对并冻结。
离线验收覆盖真实 dataloader 的 39/18/134 规划、共享 Actor 调用参数、
Final Test 关闭但 Initial/Best/最终 Selection 保留，以及旧配置缺省行为。
