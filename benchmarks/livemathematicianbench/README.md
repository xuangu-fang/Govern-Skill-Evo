# LiveMathematicianBench 数据准备

使用已下载的最新题目内容，按 SkillOpt 固定 ID 清单及原顺序提取
35 Train / 17 Selection / 125 Test。Selection 对应目录名 `val`。
数据准备脚本不重新随机划分、不安装环境、不调用模型。

原始下载位于 `data/livemathematicianbench/raw/`；本次内容版本为
`6f53c5ff7227633ea954b2847cd590314d582047`。
固定 ID 清单位于 `external/SkillOpt/data/livemathematicianbench_id_split/`。
这些路径均相对于项目根目录。

完整运行数据输出到：

```text
data/livemathematicianbench/prepared_v1/
├── train/items.json       # 35
├── val/items.json         # 17
├── test/items.json        # 125
└── split_manifest.json   # 来源版本、源文件/ID清单/输出文件 SHA-256
```

每条记录保留最新版原始字段（含 `mcq`、定理、证明草图和元数据），
另加 SkillOpt `split_dir` loader 所需的顶层 `id/question/choices/correct_choice`，
以及来源路径 `source_file`。顶层 `choices` 含完整五个选项，按原标签排序；
准备阶段不打乱选项。内容不从旧版本回填。
准备文件包含答案；运行时应通过 Actor 输入构造器选择可见字段，不直接将整条记录发送给模型。

从项目根目录执行（仅依赖 Python 标准库及 Git）：

```bash
python scripts/benchmarks/livemathematicianbench/prepare.py
python scripts/benchmarks/livemathematicianbench/prepare.py --check
```

检查覆盖数量、ID 唯一性和跨组不相交、来源身份、五选项结构、固定顺序、
原始内容与全部输出字节一致性。既有输出内容不同则报错，不覆盖。
原始仓库及生成数据按本地数据管理；准备脚本和本说明可纳入主仓库。

2026-10-29 已完成准备及离线验证：177 个 ID 唯一、原顺序及全部原始字段保留；
现有 SkillOpt 原生 loader 可直接加载三组数据，177 题的确定性选项打乱、
正确答案映射及正反例评分检查通过。模型调用为 0。
详见[验证记录](../../artifacts/benchmarks/livemathematicianbench/preparation_20261029/validation.json)。

## 独立运行环境

2026-10-29 已新建 Conda 环境 `LiveMathematicianBench`，位置为
`/Users/didi/miniforge3/envs/LiveMathematicianBench`，Python 3.12.16。
SkillOpt 0.2.0 从提交 `7da46ae693ee0329b80225c0128a37d65db10e9e`
的干净源码快照构建 wheel 后普通安装，不使用 editable 安装，不包含共享工作区的本地补丁。
原有 10 个环境的 Conda 包记录及 Python 包元数据前后比较无变化。

依赖按 SkillOpt 基础声明安装，另安装其 JSON 容错解析所用的 `json-repair`。
全部安装版本保存在 [requirements.lock.txt](requirements.lock.txt)，
环境定义为 [environment.yml](environment.yml)，来源和 wheel 校验信息见
[runtime_manifest.json](runtime_manifest.json)。这里配置的是文本/API 接入环境，
没有安装本地模型推理服务或其他 benchmark 的可选运行环境。

使用现有环境（从项目根目录运行）：

```bash
conda activate LiveMathematicianBench
python scripts/benchmarks/livemathematicianbench/prepare.py --check
python scripts/benchmarks/livemathematicianbench/verify_environment.py
```

不激活也可以直接使用独立解释器：

```bash
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/benchmarks/livemathematicianbench/verify_environment.py
```

环境锁定文件引用 `artifacts/benchmarks/livemathematicianbench/environment_20261029/wheels/`
中的本地 SkillOpt wheel；重建时须同时保留该归档，从项目根目录运行
`conda env create -f benchmarks/livemathematicianbench/environment.yml`。
已有同名环境无需重复创建。源码快照、逐文件哈希、Conda 平台包清单也保存在同一归档目录。

离线验收已通过：

- `pip check` 无依赖冲突，安装包中 138 个 SkillOpt Python/Prompt 文件与源码快照一致。
- 原生 Adapter、Trainer 及训练/评估 CLI 的帮助入口可导入；没有执行 Trainer。
- 35/17/125 数据加载、固定 ID 顺序、177 题选项打乱及答案映射检查通过。
- 默认 Actor 输入只含题干和选项；使用合成哨兵字段核验定理、草图、答案元数据不会被附加。
- 三个人工构造案例通过原生 Adapter、模型路由、SDK 及内存 HTTP transport，覆盖正确、错误和无效答案。
- 完成记录再次恢复不增加模拟请求。

验证进程禁止网络连接和模型子进程，允许 SDK 调用系统只读工具查询操作系统信息。
共 3 次内存模拟 HTTP 请求，真实模型请求、真实 benchmark rollout、训练实验均为 0。
详见[环境验收报告](../../artifacts/benchmarks/livemathematicianbench/environment_20261029/validation.json)
和[已有环境隔离检查](../../artifacts/benchmarks/livemathematicianbench/environment_20261029/environment_isolation.json)。

上述 2026-10-29 环境验收没有选择真实模型或配置凭据。

## 实际模型接口（2026-10-30）

接口配置保存在 [model_access.json](model_access.json)：

- Base URL：`https://api.deepseek.com`；模型：`deepseek-flash`。
- Target 和 Optimizer 均使用 SkillOpt `openai_compatible` 后端。
- 与 V24/V25/V26 当前官方 DeepSeek 路由保持一致：temperature=1.0，
  reasoning_effort=medium，thinking.type=enabled，非流式请求。
- 从项目根目录现有 `.env` 读取 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，
  不复制密钥，不修改 `.env`；地址不匹配即报错。
- 保留 LiveMathematicianBench 原生单次输出上限 16384 和 300 秒超时；
  连接超时 10 秒。未设定 V27 的角色预算、训练轮数或并发。

从项目根目录执行离线配置检查：

```bash
conda activate LiveMathematicianBench
python scripts/benchmarks/livemathematicianbench/model_access.py
```

追加 `--check-access` 会使用真实凭据请求 `GET /models`，验证模型可见性，
不会发起生成或运行 benchmark。该检查已通过。

后续在同一 Python 进程接入 SkillOpt 时，先执行：

```python
from scripts.benchmarks.livemathematicianbench.model_access import configure
configure()
# 此后可使用 skillopt.model 的 target / optimizer API。
```

配置在当前进程生效，单纯激活 Conda 环境不会自动加载密钥。
不要直接使用 SkillOpt 默认训练配置：它仍指向 Azure/OpenAI，且 CLI 可以覆盖路由。
本次没有创建或运行训练入口。

上游后端忽略 reasoning_effort 且不支持 thinking 配置；本项目接入函数在
SDK 客户端构造处绑定这两个参数，只作用于调用该函数的进程，未修改安装包。
SDK 内部使用 httpx2，离线验收显式注入 MockTransport，检查两个角色发出的
真实序列化请求参数及认证头，并阻止 socket 连接。密钥不写入报告。

首次调试时 HTTP 拦截未生效，发出了 4 次仅要求返回 OK 的真实短请求；
随后修正并通过 2 次内存模拟请求及真实 GET /models 鉴权检查。
未发送 benchmark 题目、启动实验或设计 V27。
见[本次检查报告](../../artifacts/benchmarks/livemathematicianbench/model_access_20261030/validation.json)
和[配置过程记录](../../artifacts/benchmarks/livemathematicianbench/model_access_20261030/setup_record.json)。

## 单题真实链路试跑（2026-10-30）

已使用独立环境，对 Train 固定顺序第 1 题 `202602:22` 完成一次真实作答。
通过原生 Adapter / Loader / rollout / evaluator，使用安装包原生初始 skill；
选项按原生规则以 seed=42 打乱，单并发、单轮、最多一次 HTTP 请求。
Target 输入只有初始 skill、题干与选项，没有参考定理、证明草图或答案。

结果：HTTP 200，正常结束（finish_reason=stop），预测 A、正确 A（打乱后标签），
EM=1；耗时 95.805 秒，输入 1,725 tokens，输出 14,574 tokens，共 16,299 tokens。
此结果只用于确认单题链路可用，不代表整体 benchmark 成绩。
没有更新 skill，没有运行 Selection/Test，没有启动自进化或设计 V27。

[结果摘要](../../artifacts/benchmarks/livemathematicianbench/smoke_train1_20261030_120621/summary.json)
所在目录保存了题目快照、初始 skill、无认证头的请求/响应、原生对话和评分。
保存后的回答重新评分一致，并检查了输出文件不含 API 密钥。

入口为 `scripts/benchmarks/livemathematicianbench/smoke_one.py`。
再次执行会新建记录目录并产生一次真实模型调用，不是离线检查。

## v27 独立接入（2026-10-30）

v27 实现位于 `src/skill_evolution/v27/`，使用上述独立环境与模型参数。
它按 SkillAdam 固定成员构造35 Train＋18 Selection的53题优化池与124题Test，
独立视图保存于 `data/livemathematicianbench/v27_skilladam53_v1/`，
不会修改上文为 SkillOpt 准备的35/17/125 `prepared_v1`。

[实现与离线验收报告](../../docs/methods/v27/README.md)包含模块迁移、数据/证据边界和逐项验收结果。
此次验收仅使用合成模型响应和受封锁的网络环境，没有启动v27实验。

后续五项审查修复见 [修订记录与 C01 边界](../../docs/methods/v27/REVIEW_FIXES_20261030.md)。
v27 Campaign 沿用旧版本4,000,000字符／6,000,000字节保护上限；`context_window_tokens` 为可选检查，正式配置未设置。
离线 C01 单独提供窗口预算，不代表已核实的真实模型服务容量。
独立环境已补装 `python-dotenv==1.2.4` 并更新依赖锁定，详见 [配置对齐记录](../../docs/methods/v27/RUNTIME_CONFIG_20261030.md)。

## SkillAdam 对照配置（2026-10-30）

已补齐独立配置 `experiments/configs/lmb_skilladam53_epoch1_deepseek_flash.json`，
优化器沿用 SkillAdam 开源 LMB 配置及原生实现，Actor、模型、数据内容和环境与 v27 对齐。
初始 Skill 继续使用 SkillOpt 原生 `initial.md`，不运行 Stage0。
入口默认只做离线 preflight；未启动实验或 Test。
参数来源、传输重试差异和离线验证见 [SkillAdam LMB 配置说明](../../docs/methods/skilladam/LMB_CONFIG_20261030.md)。
本地接入层已补齐轮内恢复和整体 Actor 归档预检；证据压缩、优化器 Prompt 和优化参数
继续保持 SkillAdam 原生行为。详见 [恢复修复与离线回归](../../docs/methods/skilladam/LMB_RECOVERY_FIX_20261030.md)。
复审补充的“结果落盘但完成回执未写入”和“先接受后保留的两轮恢复一致性”已固化为回归测试，
独立 LMB 环境29项离线测试通过，网络连接尝试及真实模型请求均为0；未启动实验。

## 当前 Actor 重试规则（2026-10-31）

v27和SkillAdam共用Actor现在对length响应自动重试；首次、技术错误及截断共用最多六次总请求。正常stop才评分，额度耗尽停止，恢复不重置。SkillAdam原生优化器不变。详见[修订说明](../../docs/methods/v27/actor_length_retry_20261031/README.md)。历史实验与旧规则结果保留，本次未重跑。
