# SearchQA 的 SkillOpt 训练与测试

在仓库根目录使用现有的 SearchQA Python 环境。入口默认执行离线验证，使用本地 SkillOpt 源码、SearchQA 数据锁和已归档的 v28.16 / SkillAdam 配置。

```sh
conda run -n SearchQA python scripts/runs/skillopt/searchqa/run.py verify
```

[配置](../../../../experiments/configs/searchqa_skillopt_deepseek_flash.yaml) 继承上游 SearchQA 的训练与优化器参数。每个 epoch 在原 Train 400 题上洗牌，每批 40 题。独立 Val 200 题按 EM 严格提升采纳候选，包括跨 epoch 的 slow update。训练、验证及测试共用 v28 SearchQA 的 Actor、提示词、答案抽取和 EM/F1 评分。Actor 与 teacher 都使用 deepseek-flash、thinking、medium、温度 1，初始输出上限分别为 32,768 和 16,384 tokens。Actor 训练及验证并发 60，测试并发 15，反思并发 16。

正式运行使用两个独立子命令，并从进程环境读取 `OPENAI_API_KEY`。

```sh
conda run -n SearchQA python scripts/runs/skillopt/searchqa/run.py train
conda run -n SearchQA python scripts/runs/skillopt/searchqa/run.py test
```

新正式训练的默认运行目录是 `experiments/baselines/searchqa_skillopt_deepseek_flash_shared_retry/`。两条命令也可以通过 `--output` 指向同一个专用目录。`train` 写入运行配置、原生 Trainer 检查点、逐题 Actor 日志及优化器调用记录，训练结束后保存 `best_skill.md` 与 `selection.json`。`test` 校验所选 Skill 的哈希并在全部 1,400 个 Test ID 上评估，`test/report.json` 记录精确答对数、EM 和 token F1。重复执行测试会校验和复用已完成的逐题结果。

离线验证逐批核对正式日程的 40 个更新步，端到端部分仅在临时目录使用合成数据与模拟模型，覆盖四个 epoch、普通与慢更新的门控、Actor 重试、冻结 Skill 测试及恢复。可用 `verify --report <路径>` 保存 JSON 报告。

## 正式训练的优化器重试与恢复

正式入口复用 OfficeQA 的优化器实现。analyst、merge、ranking、slow_update、meta_skill 中每个逻辑调用各有六次 HTTP 请求预算，含首次请求。截断、格式纠正、HTTP 错误和发送后未收到可确认响应的请求共用同一预算。累计第三次 `finish_reason="length"` 后，下一次请求的上限从 16,384 提至 32,768。正常结束但正文为空、JSON 解析失败或不符合该阶段结构时，会附上前次回复和校验错误请求纠正。六次耗尽时，训练器写入 `campaign/optimizer_paused.json` 并退出。重启会读取原有记录。请求与处理决定按调用保存在 `campaign/model_calls/`。

`train` 默认从初始 Skill 开始。需要复现历史 Step 5 的截断时，可在新目录使用 `train --from-step5 --output <目录>`。它导入前四步历史与拒绝编辑记录，以及 Step 5 的 40 条已有 rollout、五份同批补丁和第一次截断响应。该响应计入六次预算，后续从 analyst 的第二次请求开始。再次运行时只需使用相同目录。原版归档位于 `experiments/baselines/searchqa_skillopt_deepseek_flash/`。

离线验证同时检查五个阶段的混合错误、重启后的预算、归档 JSON 纠正及 Step 5 后续进入 Step 6 的路径。验证中的 Selection 分数为模拟值。
