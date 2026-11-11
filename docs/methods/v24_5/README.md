# ALFWorld v24.5

v24.5 使用自己的[四份 Prompt](../../../src/skill_evolution/v24_5/prompts/)，训练及评测复用 v24.4。六轮训练结束后，最终 Skill 在 134 道 Test 题上成功 109 题。[训练、首测与 R05 分析](../../../experiments/methods/v24_5/README.md)

[运行入口](../../../scripts/runs/v24_5/run_v24_5.py)接收配置、训练目录和评测目录。下面的命令只读核对已有正式训练和题单。

```sh
run=v24_5_alfworld_20261107_220520
python scripts/runs/v24_5/run_v24_5.py --validate-only \
  --config "experiments/methods/v24_5/$run/config/config.json" \
  --campaign "artifacts/methods/v24_5/$run" \
  --evaluation "artifacts/methods/v24_5/${run}_test134"
```

对上述已完成的归档，去掉 `--validate-only` 会逐题读回首测。指定新的训练和评测目录时，该入口会启动训练并执行 Test。运行当时的脚本、Prompt 快照和日志保存在[原始启动目录](../../../artifacts/methods/v24_5/v24_5_alfworld_20261107_220520/launch/)。
