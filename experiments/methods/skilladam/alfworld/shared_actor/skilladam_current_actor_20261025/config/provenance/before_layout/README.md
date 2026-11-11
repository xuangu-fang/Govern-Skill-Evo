# SkillAdam：当前 Actor 条件下的独立对照

本目录是自定义受控对照配置，不是官方 GPT-5.5 结果的逐项复现。
官方代码固定为 `b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1`，不修改上游源码。
独立 Python：`/Users/didi/miniforge3/envs/skilladam/bin/python`。

## 冻结输入

- `initial_skill.md`：直接复制当前方法及 No Skill/SkillOpt 对照使用的初始 Skill。
  与 `alfworld_verified_feedback_001` campaign 中的原文严格相等；不生成 Stage 0。
- `actor.json`：与已准备的 No Skill/SkillOpt Actor 配置完全相同。
- `splits/`：39 Train、18 Selection、134 Test；沿用现有清单与环境文件。
- `optimization_items.json`：按照当前方法 campaign 的六个 batch 展开，共 57 项。
- `skilladam.json`：正式六轮参数；`smoke.json`：独立的一轮两任务验证参数。
- `manifest.json`：输入、桥接代码、官方源码与提示词、共享 Actor 源码、环境文件的 SHA-256，
  以及独立环境的关键依赖版本。执行与恢复前均检查，输入漂移拒绝运行。
- `pip_freeze.txt`：安装本适配器所需 `python-dotenv==1.2.2` 后的依赖快照。

## 正式配置

| 项目 | 设置 |
|---|---|
| 初始 Skill | 当前方法原文，Stage 0 关闭 |
| 优化池 | Train 39 + Selection 18；不含 Test |
| 数据顺序 | 与当前方法完全相同，不 shuffle |
| 轮次／batch | 6 轮；10、10、10、10、10、7 |
| Gate | 官方 main-result，hard 不下降即可，平分接受 |
| 评估范围 | 每轮同 batch 比较 baseline 与 candidate |
| Momentum | 启用，保留官方工具调用和记忆实现 |
| 编辑预算 | base=4、minimum=1、beta=0.9、v_max=0.1、metric=hard |
| Patch 尝试 | 原生默认每轮最多 3 次；区别于单次 HTTP 的重试 |
| 轨迹压缩 | 官方 LLM 压缩 |
| 优化器上下文 | 最近 2 个完整优化迭代、context limit=110000，沿用官方估算机制 |
| Actor | 当前 `src.adapters.alfworld.run_task_skill` 子进程入口 |
| Actor 配置 | deepseek-v4.1-flash；medium thinking；temperature=1；16384 输出；300 秒读取超时 |
| Actor 请求 | 每动作最多 6 次，含首次；失败正文及诊断反馈；action-only |
| Actor 任务 | 50 步，最近 2 步观察/动作，8 并发，环境 seed=42 |
| 优化器模型调用 | 同模型、medium、16384 输出、300 秒读取/10 秒连接超时，最多 3 次 HTTP 尝试，SDK 自动重试关闭 |
| Test | 冻结 134 项；本入口不自动运行 Test，需要后续单独授权与评估入口 |

官方运行器每轮执行 training rollout、validation baseline、validation candidate。
尽管 training 与 baseline 使用相同 Skill/任务，仍保留官方的两次独立执行，
不为节省成本合并；正常六轮合计 171 个训练/验证 episode（不含任何 Test）。
如果候选补丁无法应用，官方流程不执行该轮 candidate rollout。

## 接口适配范围

1. 通过现有共享 Actor 启动任务，保留原始轨迹和所有请求响应归档。
2. 将已执行动作转换为 assistant 工具调用，将对应环境观察转换为 tool 消息，
   供官方压缩器读取；动作、反馈、奖励、done 和原始 pre-observation 均保留。
   不生成隐藏思考链，不把未执行的拒绝响应计为环境动作；拒绝响应仍留在原始归档。
3. 将环境返回的任务目标传入官方压缩器的 Query，避免仅显示路径清单的 case ID。
4. 逻辑优化池标为 train；原始 train:/val: ID、gamefile 与 Actor 访问用途不变。
5. 官方 OpenAI 请求格式增加当前代理的 `thinking=enabled`，使用 `max_tokens`。
   原生生成结果解析、补丁、Gate、自适应编辑预算和 Momentum 保留。

优化器每次请求保留不含密钥的请求正文、响应、usage、时间和错误类型；
截断不会作为完整候选输入。未知 usage 保持 unknown，不伪造为零。
`model_calls/` 与 `shared_actor/` 的逐次记录是实际请求和费用审计依据。

## 运行和恢复

以下命令在项目根目录执行。默认检查不读取密钥、不调用模型、不启动环境：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skilladam/bin/python scripts/runs/run_skilladam_aligned.py
```

已授权的小规模验证仅使用 `train:0000` 与 `train:0005`，一轮优化；
正常执行 2 个 training、2 个 baseline、2 个 candidate episode。
数据独立保存在 `artifacts/baselines/skilladam/alfworld_current_actor_20261025_smoke`，
不会用于正式结果、任务筛选或初始 Skill 更新。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skilladam/bin/python scripts/runs/run_skilladam_aligned.py smoke --start --pause-after-gate
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skilladam/bin/python scripts/runs/run_skilladam_aligned.py smoke --start --resume
```

第一次在真实 Gate 已写入原生 checkpoint、Momentum 尚未请求时主动暂停。
第二次恢复原生 pending_post_decision，验证不重复已完成 rollout/patch。
完成后再次 resume 应不产生新请求，最终 Skill 与 checkpoint 保持一致。

恢复边界：已完成 Gate 的 checkpoint 可继续；完整 Actor episode 可核验复用。
未完成的 Actor episode、尚无 Gate checkpoint 的失败，以及存在未完成优化器请求的
情况，会停止并要求明确恢复方案，不会自动重抽任务、重置请求额度或掩盖失败。
完成 checkpoint 与调用缓存的检查不能保证任意断电时刻的 exactly-once 网络请求。

正式训练需要另行明确启动；本次仅授权准备、离线验证与小规模验证。
所有输出拒绝覆盖，锁文件阻止同一运行的并发写入。旧 No Skill、SkillOpt 和当前方法结果不修改。
