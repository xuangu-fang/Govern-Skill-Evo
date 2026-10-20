# V23.2：历史响应支持范围与 Update 变换对齐

日期：2026-10-19。固定 R04、R05、R06 原始 Plan，各一次 Preconditioner，完成后停止。结果与候选判断见[报告](reports/REPORT.md)。

## 唯一方法变量

使用正式 V23 `S1/contract.json` 冻结的 Preconditioner 模板作为基准。原句同时表达 Parent 适当性和可执行性；仅替换前者为历史具体编辑／条件／效果／限制的支持范围要求，并原样保留“决策时可用信息与动作”的要求。追加的第二句属于这同一位置的替换，强调方向支持不自动支持不同策略、范围或强度。

- [精确 Prompt Diff](config/prompt.diff)与[实验模板](config/preconditioner_prompt.md)。
- [冻结材料、当轮 Memory、模型与容量配置](config/plan.json)。
- [调用器和实现快照](config/implementation.json)。
- [离线测试](reports/offline_tests.txt)：165 passed；网络禁用。
- [真实输出对照](reports/OUTPUTS.md)与[原始档案](../../../../artifacts/methods/v23_2/v23_2_response_alignment_001/)。

不修改原 V23 文件或 V23.2 当前默认路径；本实验显式传入 `prompt_path`，没有 Execution Context 覆盖。Diagnosis、共享 Actor 背景、输入接口、Memory、Adjustments 和确定性编译均复用原实现。不叠加此前可执行性实验规则。

## 固定比较与核查

正式 V23 旧结果只读复用，不额外重跑。当前证据和原 Plan 完全固定。R04 输入 M1–M6；R05 输入 M1/M2/M3/M6/M7/M8/M9；R06 输入 M1/M2/M6/M7/M9/M10/M11。R04 使用当时已生效的容量恢复配置；三组均为 4,000,000 字符／6,000,000 UTF-8 字节，输出上限 16,384 tokens。R05/R06 沿用优化池 Selection 身份，不读取最终 Test 轨迹。

人工核查最终 Effective Update：R04 是否保留 M4 支持的直接持物温度动作及条件；R05 是否允许由当前证据支持的不同搜索尝试；R06 是否准确处理跨类别覆盖与类内穷尽的策略差异。Keep 可以合理，Adjustment 可以不合理；不以引用 Memory、理由自述、关键词或调整数量代替语义判断。

## 调用边界

最多 3 次逻辑调用、每组首次加两次技术重试，最多 9 次实际请求。使用原技术错误判定、输出契约与请求配置，不进行语义重采样。发生容量问题时停止，不压缩证据、删减 Memory 或扩大预算。保存每次实际请求、原始响应、失败与用量，合法输出由原编译器生成 Effective Plan。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_response_alignment_001/run.py prepare
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_response_alignment_001/run.py run
```

产物目录存在时拒绝重新分配预算；不要再次执行已有实验。重读使用既有 `local_validation.load_attempt(..., prompt_path=本实验模板)`。不运行 Editor、Candidate、Replay、Actor、ALFWorld 或正式六轮实验，不写 Memory。局部文本比较不证明行为成功率提升，也不能凭单次模型输出建立严格因果关系。
