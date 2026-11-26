# OfficeQA 三方法执行环境对齐验收

协议 `officeqa_skilladam_aligned_v2`，2026-10-28。范围是任务准备、共同 Actor、本地工具及方法接入边界，不是训练或模型效果实验。

## 实现

- 数据解析以 SkillAdam 为基础，额外统一独立 URL 拆分；UID0057、UID0077、UID0124、UID0215 使用已核对的来源映射。生成数据与旧 source_aligned 的题目、答案、来源链接和文件关联逐项一致。
- 三条方法入口直接调用同一个 Runtime。SkillAdam 的工具函数、消息模板、页面渲染、答案解析和 EM/F1 直接导入使用。
- 共同循环保留 24 轮，移除每轮 8 次和每题 96 次工具数量拦截。同轮工具串行执行，所有观察进入下一轮。
- ChatTransport 要求显式指定各方法 max_completion_tokens；未设统一默认值。没有 Stage0，没有默认初始 Skill，也没有改动优化器或训练参数。
- 公共批调度采用线程池，每题一个任务，默认 workers=4，按完成顺序返回和写入 results.jsonl。每轮生成共六次总尝试，直接 HTTP、连接 10 秒/读取 300 秒、无 SDK/HTTP 内层重试；失败分类、临时格式反馈和持久化额度由公共 Actor 统一管理。按题目 ID 恢复，并核对批次身份；各迭代/阶段/重复评估必须使用独立目录。
- 原始下载 1403 项重新核验；两个 external 仓库没有因本次对齐而修改。SkillOpt 既有修改仍在，已记录实际安装模块哈希。

## 离线验证

| 检查 | 结果 |
|---|---|
| 环境依赖 | Python 3.12.16，OpenAI 2.54.0，两个项目同时安装，pip check 通过 |
| 回归测试 | 81 项通过，包含工具调用类型错误反馈及合法空值的 7 项新增回归检查，无真实模型调用 |
| 数据覆盖 | Train 50 / Val 24 / Test 172，三条 loader 边界一致 |
| 来源页面 | 493 个引用有非空内容；修正仅涉及四题 |
| 输入布局 | 全部任务符合 SkillAdam 页面追加布局；未自动注入 Skill |
| 本地工具 | 全部任务的 glob 范围、read 截断和 grep 语义通过，拒绝任务 CSV |
| 调用次数限制 | 三条入口均通过每轮 10 次、累计 100 次工具调用的合成轨迹 |
| 输出预算 | 三条入口分别传入 1111/2222/3333，实际请求保留各自参数；这些仅是测试值 |
| 差分测试 | 旧限制内，除新增的请求级 timeout=300 之外，逐轮模型请求与 SkillAdam 原生执行器一致，评分一致 |
| 调度与恢复 | 三条批入口均验证最多四题同时运行、完成顺序落盘、重启零重复请求、配置不符拒绝；请求耗尽不补额、答错题跳过、截断日志尾行修复通过 |
| 重试与反馈 | 六次混合额度、最新临时反馈、六次耗尽恢复不重置、已保存第六次响应复用、整轮工具预校验、工具进度恢复和未知结果禁止重放通过 |
| 直接 HTTP | 模拟 HTTP 会话验证超时、内层重试为 0、禁止重定向、错误分类、额外参数展开；没有真实网络请求 |
| 终止与错误 | 24 轮耗尽无额外调用、末行答案回退、无效参数恢复、非法响应拒绝通过 |
| 隔离 | 参考答案不影响 Actor 输入；空名单、缺文件、越界符号链接被拒绝 |

合成工具调用是固定脚本响应驱动的单元测试，不是模型 rollout。真实 246 题仅构造输入和检查本地文件，没有生成答案或计算 benchmark 成绩。

复核命令：

```sh
conda run -n OfficeQA python -m pip check
conda run -n OfficeQA python -m scripts.benchmarks.officeqa.align --check
conda run -n OfficeQA python -m pytest tests/adapters/officeqa -q
```

机器报告位于 `artifacts/benchmarks/officeqa/offline_v2/report.json`，测试记录位于同目录 `pytest.xml`。验收进程禁用网络并禁止创建 OpenAI 客户端；真实模型调用、真实任务 rollout、Stage0、优化运行均为 0。依赖安装与离线验收是独立步骤。

## 不能据此声称已完成的工作

尚未配置或验证真实模型路由；每轮输出上限仍须显式指定。V26 的 facts/evidence、七模块、Campaign 及独立测试现已接通；SkillOpt / SkillAdam 也已增加显式绑定公共 Actor 的[正式训练 launcher](NATIVE_LAUNCHERS.md)。旧上游 CLI 不会自动改写，原有 SpreadsheetBench 和 ALFWorld 实验保持原样。

公共 OfficeQA Actor 调度在新 launcher 中固定为四线程；SkillAdam 现已按迭代及训练/父验证/候选验证阶段绑定独立目录。原生 EvaluationRunner 可在评分聚合时按 ID 重排结果，公共日志仍保留完成顺序。请求重试规则已固定，但尚未验证真实模型路由和服务端响应。检查点和请求审计保存原始模型输出及消息，仅正式响应进入 Actor 历史；它们不是训练或模型效果实验。

训练数据权限、优化预算、初始 Skill 来源及最终选择规则没有在本次环境任务中重新决定。特别是不能把 SkillAdam 原始 Train+Val 优化池直接当作三方已统一的训练协议。

UID0057 保留原始 October 链接及 80000 字符截断；UID0077 的历年/财政年度疑点保留。评分保留原生 EM/F1（包括删除 million/billion 单位词的既有行为），未调整标准答案。共同环境比上游原版多了来源映射修正、URL 拆分和工具次数限制调整，后续结果需注明这些差异。
