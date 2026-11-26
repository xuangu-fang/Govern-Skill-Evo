# V26 OfficeQA 正式训练

2026-10-29 冻结本次训练范围：74 题优化池（原 Train 50 + Validation 24），按现有顺序分为 7 批 10 题和末批 4 题，1 epoch，共 8 次迭代。合法 no_change 继续下一批；技术失败或既定语义停止仍按 Campaign 协议保存现场，不自动扩额。

正式配置：`experiments/configs/v26_officeqa_train74_epoch1_deepseek_flash.json`。配置数值继承已确认的 pilot 配置，但通过完整 Campaign CLI 执行，不使用仅运行第一轮的 pilot 入口。

- 数据：`data/officeqa/prepared_v2`；语料：`data/officeqa/corrected_v2/treasury_bulletins_parsed`。
- 初始 Skill：SkillOpt OfficeQA initial.md 的原样快照，无 Stage0。
- Actor 与七模块：deepseek-flash，保留思考模式；思考内容不进入七模块证据。
- 输出预算：Actor 32768；Grouping / Editor 各 16384；其余五模块各 32768。
- 公共 Actor：workers=4，300 秒请求超时，直接 HTTP，六次总尝试，临时格式反馈；恢复不重置额度。
- 方法层：最多六次总尝试，重试退避基数 2 秒，保持各模块既定语义。
- Gate：EM=1 为成功，Candidate 成功数严格增加才 ACCEPT。
- 不在训练入口启动 Test；最终 172 题评估需另行执行 evaluate。

本次运行目录：
`experiments/campaigns/v26_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_001`

```sh
conda activate OfficeQA
python scripts/runs/run_v26_campaign.py \
  experiments/campaigns/v26_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_001 \
  --config experiments/configs/v26_officeqa_train74_epoch1_deepseek_flash.json
```

启动包装仅安全读取 .env、检查 API 路由并调用 `src.skill_evolution.v26.cli run`；不执行 shell 中的 .env 文本，不将凭据放入命令行或配置归档。中断后使用相同命令加 `--resume`。无凭据归档恢复仍使用原 CLI 的 `--resume --archive-only`。

训练使用全新目录，从 R01 开始，旧 pilot 不作为本次已完成批次。Campaign 自动冻结配置、源码、Prompt、数据指纹和初始 Skill。运行期间保持这些文件不变；发生截断或长输入停止时先分析，不自动修改预算绕过恢复校验。

准备与启动记录、进程号和日志：`artifacts/methods/v26/formal_training_20261029_001/`。此前 OfficeQA/V26 离线测试 402 项通过；本次另做真实 74 题配置与源文件身份预检，以及启动包装的无网络分发、恢复、路由与凭据检查。

## 2026-10-29 UID0007 单题预算续训

原运行在 18:36:55 因 UID0007 第 8 轮连续六次输出截断而技术停止。原目录及停止记录保留，不能用普通 `--resume` 重置额度。

用户授权 UID0007 从头运行，将其 Actor 输出预算从 32768 调为 65536，Parent 与 Candidate 一致。其余题目、七模块预算、思考模式和重试规则不变。专属入口为 `scripts/runs/continue_v26_uid0007.py`；默认 Actor 配置仍为 32768，单题例外冻结在新 Campaign 的 `budget_policy.json`、`runtime.json` 和入口源码快照中。

单题验证归档：`artifacts/methods/v26/uid0007_65536_20261029/`。只有完整产出答案且 EM=1 才继续训练；未通过则保留现场。验证通过后，复用该 Parent 记录及原有九题已完成记录，并重新核对源码数据、输入和原生评分；Candidate 使用同一任务预算。不会导入 UID0007 的旧失败状态或修改历史请求。

新续训目录：`experiments/campaigns/v26_officeqa_train74_epoch1_uid0007_65536_20261029_002`。

```sh
python scripts/runs/continue_v26_uid0007.py \
  experiments/campaigns/v26_officeqa_train74_epoch1_uid0007_65536_20261029_002 \
  --source experiments/campaigns/v26_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_001 \
  --validation artifacts/methods/v26/uid0007_65536_20261029
```

后续恢复必须使用相同专属入口和目录，加 `--resume`，不再传 `--source` / `--validation`。此入口不启动独立 Test。
