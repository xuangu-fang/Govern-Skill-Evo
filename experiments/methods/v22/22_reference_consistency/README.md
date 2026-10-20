# V22 类型化引用修订

本目录保留引用规则及其必要的算法差异；公共内容按
22 → 21 → 20 → 17 → 12 → 仓库的顺序查找。

`revision/src/skill_evolution/v22/` 中 10 个实现文件均与继承版本有差异：
`reference_rules`、`compact_learning`、`compact_update`、`train_response_update`、
`effective_memory`、`grouped_representation`、`grouped_update`、`continual_runner`、
`continual_runtime`、`continual_verify`。其余 3 个源码文件是包入口。
`revision/tests` 引用 21 的测试包，`revision/benchmarks` 引用公共任务定义；
两个目录链接均为相对路径。

`validation/` 保存历史验证脚本和离线检查，原始产物仍在
`artifacts/methods/v22/22_reference_consistency/`。从仓库根目录运行：

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/22_reference_consistency/validation -q
```

这只运行离线检查，不重启历史验证请求。
见[方法报告](../../../../docs/methods/v22/UNIFIED_DSC_REFERENCE_CONSISTENCY.md)
和[总导航](../README.md)。
