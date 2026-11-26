# DeepSeek 思考模式与 V26 首批试跑

2026-10-29。使用 `.env` 指定的 DeepSeek 官方地址和 key，模型 `deepseek-flash`；凭据不进入配置、日志或归档。

## 请求与证据隔离

公共 Actor 新增显式 `reasoning_mode=deepseek_thinking`，请求发送 `thinking.type=enabled` 和配置的 reasoning_effort。此前的 omit/top_level/extra_body 行为不变。可选 explicit_none 仍保留，但本次不使用。

在思考工具模式中，每个成功响应的 reasoning_content 原样进入 Actor 持久化消息和后续 API 请求。格式错误的响应仍以普通文本作为临时纠错内容，其 reasoning_content 放在对应 assistant 字段，不重复嵌入文本。技术失败和临时纠错不进入正式轨迹。原始 actor_state 保持实际请求文本；对外执行记录沿用原有路径脱敏。

恢复前根据初始消息、已保存的响应和已提交工具结果重建 API 历史，检查消息、思考内容、计数和临时纠错是否一致。已落盘响应可直接恢复；请求状态未知仍占用一次额度；工具结果未知仍禁止重放。

V26 facts 审计同时重建两条历史：带思考内容的 API 历史用于核对请求归档；不含 reasoning_content 的正式历史用于 Grouping、Diagnosis、Preconditioner、Editor、Replay、Verifier、Repair。七模块学习 Prompt、证据范围、配对邻接、输出规则和 Gate 均未更改。

离线验收：389 项通过，覆盖思考响应/工具恢复、纠错恢复、六次额度、篡改拒绝和七模块思考字段隔离。报告：`artifacts/methods/v26/deepseek_thinking_20261029_001/report.json`。

## 试跑边界

- 74 题优化池，按原顺序每批 10 题，尾批 4 题。
- 只执行第一批一次迭代，入口在恢复时也不得启动 R02；不运行 172 题测试。
- 第一批：UID0002、UID0007、UID0014、UID0017、UID0018、UID0019、UID0026、UID0028、UID0030、UID0031。
- 初始 Skill 使用选定的 SkillOpt initial Skill，不运行 Stage0。
- Actor 和方法模块均启用思考，effort=medium；workers=4，超时 300 秒，六次总尝试，不重置恢复额度。
- 临时输出上限：Actor/Grouping/Editor 16384；Diagnosis/Preconditioner/Replay/Verifier/Repair 32768。输出上限包含思考 tokens，不是正式预算。
- 自然 no_change 或无需 Repair 时不强行补调用；截断和重试按原规则记录，不在冻结运行中改预算。

配置：`experiments/configs/v26_officeqa_pilot10_deepseek_flash.json`。

运行目录：`experiments/methods/v26/pilot10_deepseek_flash_20261029_001`。

```sh
conda run -n OfficeQA python scripts/runs/run_v26_pilot.py \
  experiments/methods/v26/pilot10_deepseek_flash_20261029_001 \
  --config experiments/configs/v26_officeqa_pilot10_deepseek_flash.json
```

显式恢复同一目录时省略 --config，使用 --resume；已经完成 R01 的目录仅校验归档，不重复调用。

## 输入和用量报告

```sh
conda run -n OfficeQA python scripts/runs/report_v26_pilot.py \
  experiments/methods/v26/pilot10_deepseek_flash_20261029_001 \
  --tokenizer-python /Users/didi/miniforge3/bin/python
```

`analysis/INPUTS.md` 链接每次请求，`analysis/input_token_report.json` 包含 API 实际输入、输出、思考 tokens、重试、结束原因、题目评分及模块输入结构。Actor 请求导出由实际 messages 加冻结工具/发送参数重建；没有认证头。模块原始 request.json、messages.json、HTTP 响应保留在模块 attempts 目录；额外生成可阅读的输入 Markdown。

输入视图去重前后长度使用 cl100k_base 参考分词器，仅用于比较 payload；不可与包含系统说明、工具封装、思考历史的 API 实际 prompt_tokens 混用。缺失 usage 标为未知，不记成零。

## 用户授权的 32768 续跑（2026-10-29）

第一次试跑在 UID0007 第 5 轮耗尽六次额度，9 题完成。用户明确要求将 Actor 输出额度提高到 32768，复用已完成的 9 题并继续本批自进化。续跑使用独立目录 `pilot10_deepseek_flash_20261029_002`，不更改原目录的配置、请求或失败记录。

`continue_v26_pilot.py` 导入经完整性、原始任务/文档、评分和 wire 历史校验的 9 条原始 Parent 记录，保留 16384 的实际 Actor 元数据和原 run_id。UID0007 在新目录以 32768 从头重新执行；这是一项新预算试跑，不是重置旧运行的六次额度。所有 Candidate 也使用 32768。

仅本试跑的显式 PilotAdapter 允许清单中指定的预算差异；其它参数、任务、文档、初始消息和 Skill 仍接受原校验。普通 OfficeQA 的参数一致性校验保持严格。七模块共用的执行背景另附预算例外说明，说明哪些 Parent 用了 16384，不把混合预算差异全部归因于 Skill。Actor Prompt、七模块学习规则、Gate、自然 no_change/Repair 分支均保持不变。

Grouping 与 Replay 的记录构造使用当前显式绑定的 adapter；纯离线 Replay 读取未绑定时仍采用严格原规则。混合预算归档恢复须通过该续跑入口绑定原清单。模块格式校验、配对邻接、证据范围及恢复额度不变。

```sh
conda run -n OfficeQA python scripts/runs/continue_v26_pilot.py \
  experiments/methods/v26/pilot10_deepseek_flash_20261029_002 \
  --source experiments/methods/v26/pilot10_deepseek_flash_20261029_001
```

恢复时使用同一目录加 `--resume`，不再传 `--source`。入口仍只运行 R01。报告明确区分 `retained_previous_run` 与 `new_request`，复用记录不算本轮新增 API 消耗；旧 UID0007 的失败消耗仍在 001 原报告中保留。
