# 方法运行产物

[方法总索引](README.md) · [第四步整理记录](../../docs/repository/RUNTIME_LAYOUT.md) · [完整路径映射](runtime-path-map.json)

## 归属

- `experiments/methods/<版本>/<实验编号>/config/`：配置和冻结输入。
- 同一实验下的 `results/`、`reports/`：精选结果和研究报告。
- `artifacts/methods/<版本>/<运行编号>/`：原始运行、日志、轨迹、恢复状态和中间产物，不提交 Git。
- 历史 V17–V19 保留 `pilot/`、`formal/`、`archive/` 阶段层，避免将试运行、正式运行或历史重试混为一谈。旧 `experiments/archive/<版本>` 归入 `archive/legacy/`，不覆盖原有 archive。
- benchmark 构建产物、ST-Web POC 和仓库整理审计不属于这些方法运行，仍在各自目录。

## 启动与恢复

当前运行脚本和配置直接使用新位置。原启动入口仍可使用；`run_method.py` 也提供按版本、运行编号选择输出目录的便利入口。

```sh
# 仅打印命令，不调用模型，不创建运行目录。
python scripts/run_method.py v18-v4 --run-id v18_example_001 --print-command -- --run

# V18 原入口默认为 preflight；传 --run 才运行模型。
python scripts/run_method.py v18-v4 --run-id v18_example_001

# 新 V19 运行；配置模式和参数仍由原运行器校验。
python scripts/run_method.py v19 --run-id v19_example_001 -- run --config experiments/methods/v19/v19_run/config/pilot.json

# 恢复已有正式运行时，必须指定其现有阶段位置；恢复资格仍由原运行器检查。
python scripts/run_method.py v19 --run-id v19_memory_formal_003 --stage formal -- resume
```

入口支持 `v17`、`v18`、`v18-v4`、`v19`、`v20`，分隔符 `--` 后的参数原样传给原脚本。已有其他模块入口继续使用其原有输出参数，显式传入 `artifacts/methods/<版本>/<运行编号>`。V01–V14 动态拼接的默认输出也已改为按方法版本组织。

## 无旧目录链接

主项目已移除全部 190 个兼容软链接。当前源码、配置、测试、导航直接使用规范目录，运行器也不会因旧默认路径重新创建平铺目录。

原始运行记录中的历史路径保留为证据。读取这类记录时，路径工具按[历史身份映射](canonical-paths.json)定位实际文件，不创建旧目录或链接，不改变模型输入输出。历史运行的源码、配置及恢复状态仍由对应运行器检查。

本次修改及验证见[清除兼容链接记录](../../docs/repository/CANONICAL_PATHS.md)。

## 按版本查看

- [v01 方法说明](v01/README.md) · [本机运行材料](../../artifacts/methods/v01)
- [v02 方法说明](v02/README.md) · [本机运行材料](../../artifacts/methods/v02)
- [v03 方法说明](v03/README.md) · [本机运行材料](../../artifacts/methods/v03)
- [v04 方法说明](v04/README.md) · [本机运行材料](../../artifacts/methods/v04)
- [v05 方法说明](v05/README.md) · [本机运行材料](../../artifacts/methods/v05)
- [v06 方法说明](v06/README.md) · [本机运行材料](../../artifacts/methods/v06)
- [v07 方法说明](v07/README.md) · [本机运行材料](../../artifacts/methods/v07)
- [v08 方法说明](v08/README.md) · [本机运行材料](../../artifacts/methods/v08)
- [v09 方法说明](v09/README.md) · [本机运行材料](../../artifacts/methods/v09)
- [v10 方法说明](v10/README.md) · [本机运行材料](../../artifacts/methods/v10)
- [v11 方法说明](v11/README.md) · [本机运行材料](../../artifacts/methods/v11)
- [v12 方法说明](v12/README.md) · [本机运行材料](../../artifacts/methods/v12)
- [v13 方法说明](v13/README.md) · [本机运行材料](../../artifacts/methods/v13)
- [v14 方法说明](v14/README.md) · [本机运行材料](../../artifacts/methods/v14)
- [v15 方法说明](v15/README.md) · [本机运行材料](../../artifacts/methods/v15)
- [v16 方法说明](v16/README.md) · [本机运行材料](../../artifacts/methods/v16)
- [v17 方法说明](v17/README.md) · [本机运行材料](../../artifacts/methods/v17)
- [v18 方法说明](v18/README.md) · [本机运行材料](../../artifacts/methods/v18)
- [v19 方法说明](v19/README.md) · [本机运行材料](../../artifacts/methods/v19)
- [v20 方法说明](v20/README.md) · [本机运行材料](../../artifacts/methods/v20)
- [v21 方法说明](v21/README.md) · [本机运行材料](../../artifacts/methods/v21)
