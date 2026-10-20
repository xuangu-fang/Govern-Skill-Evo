# V23.2：最终 Update 可执行性的最后一次局部验证

状态：**两次验证已完成，均首次返回 ready；仍存在最终 Update 信息依赖，按边界停止。**

日期：2026-10-19。只验证固定 R03、R06 的 Preconditioner，各一次逻辑调用，最多首次请求加两次技术重试。合法语义结果不重采样，完成后停止。

## 最小修改

在原有可执行性要求的位置，使用用户给定的三句要求，检查所有最终保留的 Updates（包含未调整项），并避免在修订时引入不受支持的限制。没有新增模型编译步骤或输出字段；正式 Effective Plan 仍由 V23 的确定性函数编译。

- [唯一 Prompt 差异](config/prompt.diff)
- [本次完整模板](config/preconditioner_prompt.md)
- [调用适配差异](config/adapter.diff)：仅增加可选显式模板参数，旧默认保持不变。
- [冻结材料及参数](config/plan.json)
- [新增实现快照](config/implementation.json)
- [离线测试](reports/offline_tests.txt)：597 passed、19 subtests passed，禁用网络和环境执行。
- [完整验证报告](reports/REPORT.md)
- [真实文本全文对照](reports/OUTPUTS.md)
- [实际运行日志](reports/live.log)
- [原始产物](../../../../artifacts/methods/v23_2/v23_2_executability_002/)

本次模板放在独立配置目录，由既有 `local_validation.run_stage(..., prompt_path=...)` 显式读取。没有覆盖上一版源码目录中的模板，旧档案继续使用旧模板读取。Diagnosis Prompt、V23 源码和模型接口均不改变。实验入口复用上一实验的材料读取／核验与已有 V23.2 调用器，不创建新演化框架。

## 固定比较

三侧共用 V23 原始 Parent、Grouping、Original Plan、当前执行事实、当轮 Active Memory 和 Actor 背景。比较 V23 已保存输出、V23.2 第一轮有效输出和本次新输出；不重跑旧侧。R03 使用 M1/M2/M3，R06 使用 M1/M2/M6/M7/M9/M10/M11。R06 是正式优化池中的 Selection 任务，沿用原身份，不混入 Test。

R03 保持 1,000,000 字符／1,500,000 字节容量；R06 保持 4,000,000／6,000,000。模型参数与重试判定直接复用上一版。输入超限时保留停点，不压缩 Memory 或增加预算。

## 运行与复现

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_executability_002/run.py prepare
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_executability_002/run.py run
```

已有产物后拒绝重新分配调用预算。读取本次输出须显式传入本配置模板；不得放宽旧档案的 Prompt 比较。技术失败、无效输出和有效输出全部归档。不执行 Editor、Candidate、Replay 或 ALFWorld，不更新 Memory，不开展第二项改进或正式六轮实验。
