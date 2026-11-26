# 实验记录还原

OfficeQA、SearchQA、SpreadsheetBench、ALFWorld和 LMB 各自保留一份共享内容和校验清单。请将本目录与精简实验记录按仓库中的相对位置一起保存。下列命令在仓库根目录运行，使用 Python 3 标准库。

## 校验

```sh
python3 experiments/benchmark_record_refs/restore.py officeqa --verify
python3 experiments/benchmark_record_refs/restore.py searchqa --verify
python3 experiments/benchmark_record_refs/restore.py spreadsheetbench --verify
python3 experiments/benchmark_record_refs/restore.py alfworld --verify
python3 experiments/benchmark_record_refs/restore.py lmb --verify
```

工具逐个校验共享字段，再从磁盘读取每个改写文件，展开整文件引用和字段引用，并核对替换前的字节数及 SHA-256。实验附件的相对链接、原始长度与 SHA-256 也会逐个核对。

对 SpreadsheetBench 和 ALFWorld 再做去重时，先从候选路径中排除仓库根目录下 `git ls-files -z` 列出的路径。在 Git 工作区运行上述校验时，工具也会检查这两个清单中已被 Git 跟踪的路径是否保留普通文件和原始字节。输出中的 `already_original_records` 和 `regular_assets` 分别统计已恢复原文的记录和附件。

ALFWorld 的 v24.10、v24.11 `--read-archive` 和 SkillAdam 逐步轨迹反馈归档命令可以直接读取精简目录。它们按原路径查清单，在内存中还原记录并核验，再用原来的逐题校验器读取轨迹与 HTTP 回执。

LMB 主对照的训练与评测精简目录已归档到 `artifacts/methods/`。工具通过[历史路径映射](../methods/canonical-paths.json)查找文件。SQLite 索引与 `assets.json` 保留历史路径。LMB 的 `--file` 接受历史或规范的仓库相对路径，还原输出使用清单中的原路径。[主对照读回命令](../methods/lmb/README.md)

在新的工作区运行 LMB 离线验证前，从同一份本地归档补齐 `experiments/benchmark_record_refs/lmb/` 中的共享数据、索引和附件，并按原相对路径放置精简记录。`payloads.pack` 与对应 `manifest.sqlite3` 配套使用。

## 还原

```sh
python3 experiments/benchmark_record_refs/restore.py officeqa --output /path/to/new-officeqa-directory
python3 experiments/benchmark_record_refs/restore.py searchqa --output /path/to/new-searchqa-directory
python3 experiments/benchmark_record_refs/restore.py spreadsheetbench --output /path/to/new-spreadsheetbench-directory
python3 experiments/benchmark_record_refs/restore.py alfworld --output /path/to/new-alfworld-directory
python3 experiments/benchmark_record_refs/restore.py lmb --output /path/to/new-lmb-directory
```

每条命令需要一个新的输出目录。工具在其中按仓库相对路径创建本次改写文件的原始副本。只还原一个文件时，附加 `--file` 和仓库相对路径。需要原请求、完整 JSON 字段或历史文件哈希的评测程序，应在一份完整的实验目录副本中使用还原后的文件。

## 数据格式

`manifest.sqlite3` 保存原始文件哈希、精简模板哈希、插入引用的确切位置和共享内容在 `payloads.pack` 中的位置。相同的整份文本记录以 `$qa_file_ref` 指向一份模板。原始 JSON 长字符串以 `qa-field:sha256:` 加摘要指向原始转义字节，因此引号、空白和换行格式均可恢复。完全相同的实验附件以相对符号链接指向 `assets/` 中的副本，`assets.json` 保存附件原路径和校验信息。

`verification.json` 记录 OfficeQA 和 SearchQA 的全量验证结果、落盘回读样本、实际分配空间和两项已结束作业的补充归档记录。

SpreadsheetBench 的重复工作簿在原路径以相对符号链接指向保留扩展名的只读共享副本。需要编辑工作簿时，可用上面的还原命令输出独立文件。SpreadsheetBench 和 ALFWorld 的逐文件落盘回读结果及净节省见 [归档校验报告](verification_spreadsheetbench_alfworld.json)。
