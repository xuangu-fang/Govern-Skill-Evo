# V23.5 ALFWorld action-only 配置

## 2026-10-27 当前材料状态

仅有配置与准备材料；截至本次检查，未发现对应 artifacts 运行目录，不生成轮次结果或最终 Skill。

正式 config/、任务 data/ 原样保留；以下结果来自已有文件，本次没有运行实验或测试。

仍保留 config/campaign.json、budget、provenance、initial_baseline_reference、全部 data/ 和准备验证报告。没有执行记录，因此不借用其他配置的结果来补齐本目录。

当前通用脚本 [run_v23_5_alfworld.sh](../../../../scripts/runs/run_v23_5_alfworld.sh) 默认指向 alfworld_action_feedback_001；下方旧入口说明保留历史阶段含义，通用脚本不会自动恢复旧目录。本次未执行任何入口。

未来运行的既定输出仍为 `artifacts/methods/v23_5/alfworld_action_only_001/`；本次不创建空归档冒充已运行。

## 历史说明（保留原阶段记录）

本目录是从头开始的新实验配置。已离线准备，尚未执行训练或 Test。
原 `alfworld_initial_skill_001` 的配置、初始 Skill、u3 和所有执行记录保留原样。

修改限定为初始 Skill 的 Output format，以及 Actor 无历史/有历史模板的输出要求。
两处统一使用不含完整标签示例的措辞：输出一个名为 `action` 的 XML 元素，其正文为当前
合法动作列表中的一条命令，不输出元素外文字或嵌套元素。模型 thinking 保持开启。
适配器按 `actor_output_format=action_only_v1` 生成模板，将其保存到执行记录，进化模块
从记录获得同一份实际执行背景；观察、历史、动作解析及进化流程未改变。

配置继续沿用原实验的 57 个优化任务、6 批任务顺序、同批 Gate、独立 134 个 Test 任务。
每次调用最多 6 次总尝试；Actor / Editor 等输出上限 16,384，Preconditioner / Replay 为
32,768。有限反馈、引用权限、精确唯一匹配、原子应用与恢复额度规则保持不变。

初始 Skill 来源及派生哈希保存在 `config/campaign.json` 和 `config/provenance.json`。
`config/initial_baseline_reference.json` 中的 SkillOpt 分数仅为旧协议下的历史参考；
不能据此计算本次 Prompt 修改的效果，也未把它冒充新初始 Skill 的 Test 成绩。

离线准备：

```bash
bash scripts/runs/run_v23_5_alfworld.sh check
```

下列命令会发起实际模型请求和环境执行；本次修改没有执行它们：

```bash
bash scripts/runs/run_v23_5_alfworld.sh run
bash scripts/runs/run_v23_5_alfworld.sh resume
```

运行目录为 `artifacts/methods/v23_5/alfworld_action_only_001/S1`。
最终 Test 入口也指向新目录，只有 Campaign 正式完成后才能运行。

验证与限制：前置 [16 次真实请求对照](../action_format_probe_001/RESULTS.md) 支持减少触发源；
它不证明零失败概率。保留旧 u3 的压力案例仍失败，后续 Plan 再引入完整 think 标签仍存在风险。
本次落地只做离线回归和历史完整性核对，没有额外真实请求或环境执行。

## Actor 动作错误重试

当前未启动配置已启用 `actor_retry_invalid_actions=true`：缺少完整 action 标签或
提取动作不在本步展示列表时，原样重发请求，与技术重试共用每步六次总额度。
校验只在本地执行；无效响应不推进环境，耗尽额度停止并保留记录。原有 Prompt、
模型参数、token 上限、任务批次和 Gate 不变。旧实验不启用此规则。

