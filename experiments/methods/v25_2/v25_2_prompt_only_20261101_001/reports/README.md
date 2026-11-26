# V25.2 prompt-only 独立实验配置

已接入 2026-11-01 复审通过的 Diagnosis / Preconditioner 草稿，并完成离线检查。
**没有启动正式训练、测试集评测或真实模型请求。** 离线夹具产生的合成 campaign
仅位于 `offline_checks/fixtures/`，不是实验训练结果。

## 基线与变更范围

基线为已完成实验
`../v25_v25_1_common_actor_no_review_20261030_001/v25_1/` 的冻结工作区和实际配置，
不依赖当前仓库主线的实现。独立快照位于 `frozen_workspace/`，内部仍使用
`src.skill_evolution.v25` 命名空间。这样保留算法版本，仅切换 prompt 版本。

`config.json` 和 `evaluation/config.json` 相对各自 V25.1 文件，均仅有三个字段不同：

| 字段 | V25.2 |
| --- | --- |
| `candidate` | `v25_2_selective_updates_prompt_only` |
| `method.diagnosis_version` | `v25_2_diagnosis_selective_updates_v1` |
| `method.preconditioner_prompt` | `v25_2_current_update_concise_refinement_v1` |

Diagnosis 在 prompt 中每轮最多提出两个有独立价值的 Updates，允许一个或 no_change；
不为凑数增加要求，也不将多个无关修复打包成一条。现有 validator 没有增加数量硬限制。
Preconditioner 只替换一个指导段落，约束无意义的新增行为和重复表述；保留 D/S/C、
历史 Knowledge、探索、KEEP / modify / withdraw、必要条件与观察性 Checks 的原有作用。
Editor 与 V25.1 完全一致。

运行源码共四处变更：Diagnosis 模板、新增 Preconditioner 模板，以及两处模块的版本／路径常量。
`source_changes.patch` 是全部源码差异；`approved_prompts/` 保存完整已批准草稿、原有 diff、方案说明和复审记录。
没有改动接受机制、Memory、Replay、输出结构或重试逻辑。

## 与 V25.1 保持一致的设置

- 同一 Verified-400 数据：Train + Val 共 120 个优化任务，顺序不变，8 批 × 15，1 epoch；Test 280 个。
- 同一初始 Skill，从空 Memory 开始，不继承 V25.1 最终 Skill、Memory、checkpoint 或历史人工重试授权。
- Actor 与优化模块均为 `deepseek-flash`；模型参数、预算、超时、重试和 Actor 并发 4 全部不变。
- 保留严格分数提升才 ACCEPT 的 gate，以及 `knowledge_review=disabled_v1`。
- Actor 的 `execution_only_v1`、30 次程序执行上限、6 次请求预算、Docker 配置及其他参数全部不变。
- 测试配置继承已完成 V25.1 测试的元数据修正和 `evaluation/scoring.py`，评分口径一致。

## 离线检查

34 项 pytest 全部通过：继承基线的 27 项测试，新增 7 项 V25.2 检查。测试使用合成小表格、
预设生成响应和替代执行器，审计钩子阻止网络连接和子进程，未执行真实数据任务。
新增检查覆盖两个模板到实际系统消息／归档的完整链路、版本标识、恢复不重复调用、
KEEP / modify / withdraw / no_change、只改变观察性 Checks，以及不存在新增 Updates 数量硬校验。

`offline_checks/report.json` 记录配置、原始文件与新快照的哈希校验、800 个数据文件的只读校验、
冻结导入路径、完整运行契约、Actor 消息一致性、测试结果以及正式输出目录不存在的检查。
这仅证明接线和已有契约正常；效果、Skill 长度及模型是否遵循新指令仍需后续实验验证。
本轮没有检查真实 API 或 Docker 运行就绪性。

从仓库根目录重做只读审计：

```sh
python -B experiments/comparisons/v25_2_prompt_only_20261101_001/verify_bundle.py
```

需要重跑合成测试时，先确保报告父目录存在，再执行以下命令；这些命令不会启动正式训练：

```sh
mkdir -p experiments/comparisons/v25_2_prompt_only_20261101_001/offline_checks
COMPARISON_ARM="$PWD/experiments/comparisons/v25_2_prompt_only_20261101_001" \
PRECONDITIONER_VERSION=v25_2_current_update_concise_refinement_v1 \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
/tmp/govern-skill-skilladam-native-venv/bin/python -B -m pytest \
  experiments/comparisons/v25_2_prompt_only_20261101_001/offline_suite \
  -q -p no:cacheprovider \
  --basetemp=experiments/comparisons/v25_2_prompt_only_20261101_001/offline_checks/fixtures \
  --junitxml=experiments/comparisons/v25_2_prompt_only_20261101_001/offline_checks/pytest.xml
```

上述 Python 环境是本次已验证的本机环境；不在实验配置内改变依赖。

## 后续运行约定（本轮未执行）

以后得到训练指令后，必须让本目录 `frozen_workspace` 优先于主仓库参与导入，并显式读取本目录
`config.json`，将全新训练输出写入本目录 `campaign/`。不要使用主仓库默认配置或续跑 V25.1。
最终 Skill 的测试使用本目录 `evaluation/config.json` 和 `evaluation/scoring.py`，输出到本目录 `test/`。
`frozen_contract.json` 保存实际导入得到的运行契约；`frozen_manifest.json` 固定配置、源码、草稿和检查工具。
`verify_bundle.py` 是启动前检查，正式运行产生输出后，其“未启动”断言预期不再通过。

准备脚本为仓库根目录下 `scripts/runs/prepare_v25_2_comparison.py`：拒绝覆盖已有目录，
仅复制和准备基础配置；本目录额外保存了本次完成的离线测试、审计脚本与报告。
