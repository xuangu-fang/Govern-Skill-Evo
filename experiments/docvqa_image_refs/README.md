# DocVQA 实验记录还原

实验记录中的 `docvqa-image:sha256:<摘要>` 引用对应本次数据发布的原始 PNG。`manifest.sqlite3` 保存图片的仓库相对路径、每个改写文件的原始和精简 SHA-256、字节数，以及新增引用的字节位置。保留这份目录、精简记录和对应的原图，即可逐字节还原。使用 Python 3 标准库，在仓库根目录运行下列命令。

校验全部原图和记录，完整展开每个文件并核对原始长度及 SHA-256。

```sh
python3 experiments/docvqa_image_refs/restore.py --verify
```

将本次修改的全部记录还原到一个新目录，保留仓库相对路径。输出约需 115 GiB 空间。只读结果或查看评分时可以直接使用精简记录。需要原始请求或原始文件哈希的工具应读取还原后的记录。

```sh
python3 experiments/docvqa_image_refs/restore.py --output /path/to/new-directory
```

要还原单个文件，可指定其仓库相对路径。输出目录同样需要是新目录。

```sh
python3 experiments/docvqa_image_refs/restore.py --output /path/to/new-directory \
  --file experiments/baselines/docvqa_skillopt_deepseek_flash/test/runs/records.json
```

此前三组已精简的评测继续使用其[原有还原工具](../evaluations/docvqa_checkpoints_shared_images_20261117/README.md)。
