# v27 LiveMathematicianBench

v26 核心机制的独立迁移，LMB 领域实现位于 `benchmarks/lmb/`。运行阶段、输出错误反馈、精确 patch、Plan 编译、Memory 整 entry 替换、Gate 后 Replay 和原子发布沿用现有方法。五个输出 schema 不变；使用 review_01 的五份完整 Prompt，Verifier/Repair 首版明确关闭。

实现记录与验收入口见 [v27 文档](../../../docs/methods/v27/README.md)。本目录不导入旧版本或 OfficeQA adapter，也不修改已安装 SkillOpt。

## 环境与依赖

使用 `/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python`。运行时将仓库根目录和 `external/SkillAdam` 放入 `PYTHONPATH`，复用已冻结的 SkillAdam LMB 消息、选项和评分函数；无需向旧环境安装依赖。真实请求采用与 v26 一致的直接 HTTP 通道、显式六次额度和零隐式重试。已有 `.env` 仅在显式运行 CLI 时读取；离线验收不读取密钥。

## 数据和协议

`training.load_dataset(prepared_root)` 校验冻结内容清单、prepared 文件及 raw 月份文件的字节身份，再按 SkillAdam 固定成员生成独立视图：35 Train＋18 Selection 合并为 53，Test 124；原 source_split 保留。Train、Selection 分别字符串排序后拼接，六批为 10/10/10/10/10/3。初始 Skill 位于 `resources/initial.md`，与 SkillOpt 原文件字节一致。

Actor 只有一轮、无工具，选项 seed=42；Parent/Candidate 使用相同呈现输入。普通 content 完整保留，独立 reasoning_content 仅可存在于请求审计文件。输出事实由白名单构造，Memory、历史引用、反馈和 Editor 均无隐藏字段读取路径。

## 调用边界

- `benchmark.using_benchmark(adapter)` 显式绑定；worker 使用独立 context copy。
- `config.campaign_config(adapter)` 只生成配置，默认沿用 v24.1／v25／v26 的4,000,000字符与6,000,000 UTF-8字节保护上限；可显式覆盖。`context_window_tokens` 为可选参数，默认不设置。不会创建 campaign 或请求模型。
- `evolution.run_campaign(...)` 需要显式 generator 和 Actor transport，才会产生新调用。恢复会验证源码、Prompt、数据、配置、Skill、状态及请求额度。
- `evaluation.run_evaluation(...)` 独立冻结 124 Test 和 Skill，不包含 optimizer/Memory 更新；`final_parent` 拒绝尚未完成的 campaign。
- `cli validate` 只读预检；`cli prepare` 创建独立数据视图；`cli run/evaluate` 是真实执行入口，本次未执行。

方法阶段保留字符/UTF-8 输入硬上限，`capacity.json` 记录实际序列化大小及预留输出。按用户要求，Campaign 不再强制填写 `context_window_tokens`。只有显式提供时才以 UTF-8 加消息框架的保守估计检查输入＋输出；不设置时仍检查字符／字节硬上限并记录输出预留。不从模型名称推断窗口，不裁剪输入。估计不等于 provider 实测 token 数。离线 C01 的 1,048,576 是测试预算，不能作为真实服务窗口声明。

已完成的 Actor 结果在直接恢复、Campaign 缓存复用、最终 Parent 读取及 Test 报告中，都回查原始请求归档；缺失或与结果不一致时停止，不重新作答。完整 HTTP 状态和响应正文可作为只读恢复来源。Skill 按 UTF-8 原始字节读取，保留 CRLF 和混合换行。方法响应的结构异常归为技术重试，仍受六次总额度限制。残缺 `<answer`／`</answer` 标记判格式不合规，原生 EM 提取保持不变。

恢复前同时识别单题 `result.json`、`trajectory.json` 与批次 `records.json` 的完成证据。批次在提交任何 worker 前，先只读校验全部已知完成项；只剩轨迹或批次记录、但结果或响应归档丢失时停止，整个恢复调用不新增 Actor 请求。没有完成证据的请求仍可按原六次总额度恢复：仅有 started 标记时计入 unknown；已有完整 JSON／HTTP 响应时本地解析；已有合法 result 但尚未写入轨迹时补齐轨迹。这些正常恢复不重新作答已完成题目。

## 离线验收

从项目根目录执行：

```bash
/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python scripts/verification/verify_v27_offline.py --output artifacts/verification/v27_offline_recheck
```

入口拒绝其他 Python 环境，封锁 socket 连接和模型子进程，HTTP 用例显式注入 `httpx.MockTransport`。所有执行题均为 `synthetic:*`，真实 177 题仅做本地数据/映射检查。没有导入或运行 SkillAdam Trainer。报告记录每个测试的实际状态；107 项映射中的10项历史人工样例只作为补充，不冒充本轮重新执行的判断。不能据此保证真实模型的自然语言判断质量。

五项审查修复、C01 完整场景的输入规模、超限边界和验收补充见 [修订记录](../../../docs/methods/v27/REVIEW_FIXES_20261030.md)。

当前已保存配置为 [v27_lmb53_epoch1_deepseek_flash.json](../../../experiments/configs/v27_lmb53_epoch1_deepseek_flash.json)。独立环境已补充 python-dotenv 1.2.4，凭据入口通过合成 .env 测试；实际密钥未用于本次验证。详见 [配置对齐记录](../../../docs/methods/v27/RUNTIME_CONFIG_20261030.md)。

## DeepSeek 输出格式适配（2026-10-30）

参照 v23.5 的 action_only_v1，当前采用 lmb_answer_element_words_v1：用文字描述名为
answer 的 XML 元素，正文只含一个选项字母，不要求正文逐步解释，不在固定 Prompt 中展示完整
answer 或 think 标签。v27 与本地 SkillAdam adapter 共用该模板；上游 SkillAdam 源码不改。
选项、题目、答案解析和 EM 评分保持原实现，方法 Prompt 中的 Actor 协议同步更新为 v3。
这是预防性适配，不宣称已证实或根治服务端故障。后续 Skill、Plan 或真实轨迹仍可能包含标签；
这些内容原样保留，不在发送前静默清洗。旧配置、运行档案和历史文档不回写，新协议不能用于
继续旧冻结运行。历史初始 Skill 的来源不变。

## Actor 截断重试修订（2026-10-31）

v27与LMB SkillAdam共用Actor。length响应仅归档，不评分；保持原消息和输出预算重试，与技术错误共用六次总额度，恢复不重置。仅stop结果可进入事实、Gate及Replay。当前执行身份v3、五模块Prompt v5；旧冻结目录不可混用。详见[修订契约与验收](../../../docs/methods/v27/actor_length_retry_20261031/README.md)。SkillAdam原生优化器不变。

请求归档和失败尝试的恢复校验已补齐：所有任务在worker启动前只读检查，失败档案按字节指纹和失败分类核对；真正未完成请求按原额度恢复。见[归档修复说明](../../../docs/methods/v27/ACTOR_ARCHIVE_FIX_20261031.md)。
