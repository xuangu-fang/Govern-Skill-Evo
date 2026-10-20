# V22 的 57 项五轮实验

这是 v22 内的实验阶段，不是独立方法版本 v23。
实验结论与恢复过程见[正式报告](../../../../docs/methods/v22/ALFWORLD_57_FIVE_ROUND_EXPERIMENT.md)。

## 源码与配置

`revision/` 保留五轮运行、Actor、学习与验证的差异，实现依次引用
22、21、20、17、12 和仓库公共内容。模型路由与 19 完全一致，
通过相对文件链接引用；其余 11 个实现文件与继承版本不同，另有 5 个包入口。

`capacity_amendment/revision/` 保留 5 个容量修订实现和 3 个包入口，
继续引用本目录及前序修订。它只记录原有容量例外，目录整理不改变授权范围。

`config/`、`PROTOCOL.md` 和 `prepare.py` 是计划、来源记录及构造入口；
它们是实验输入，继续保留。历史完整结果位于
`artifacts/methods/v22/23_alfworld57_five_round/`，由根目录忽略规则管理。

## 离线检查

从仓库根目录运行：

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -B experiments/methods/v22/23_alfworld57_five_round/offline_tests.py
/Users/didi/miniforge3/envs/alfworld/bin/python -B -m unittest discover -s experiments/methods/v22/23_alfworld57_five_round -p test_five_round.py -q
```

继承测试包含 420 项行为检查，另有一项仅适用于 20/21 的文件身份检查
明确跳过，因为五轮实现覆盖了 compact learning。三个五轮模拟测试单独运行。
这些命令不调用模型或真实环境。不要重跑 `prepare.py` 或历史恢复脚本来检查目录。
