# V23.2 历史 Memory 决策分析

状态：2026-10-19 完成；纯历史证据分析，不进入优化实现。

- [分析报告](reports/REPORT.md)：逐条 Memory 核查、7 项 Original Update 对照、6 个案例、跨轮归因边界与三个后续研究方向。
- [正式来源索引](reports/SOURCES.md)：各轮实际输入、Plan、Diff、Replay、Gate 和 57 个配对任务的原始轨迹链接。
- [时序及核验索引](reports/index.json)：当轮可见 Memory、修订关系、114 条原始执行与 246 个历史 source 核验。
- [文件保护结果](reports/PROTECTION.json)。

唯一原始证据来源为 `artifacts/methods/v23/v23_alfworld_formal_001/S1/`。未使用最终 Test、V23.2 实验或外部方法结果判断正式更新。重读入口仅提取与核验既有档案，不运行模型或环境：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. /tmp/gse-v23-py313/bin/python \
  experiments/methods/v23_2/v23_2_memory_analysis_001/extract.py
```

脚本只写本目录的来源索引，不生成 Candidate、Patch 或 Memory；语义判断由报告逐项说明，不使用自动自然语言评分或分类。V23/V23.2 当前 Prompt 和方法基线不变。
