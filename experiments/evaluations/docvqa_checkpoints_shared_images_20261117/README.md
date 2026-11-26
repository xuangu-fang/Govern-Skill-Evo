# DocVQA 逐轮评测图片归档

将本目录与三个评测目录放在同一父目录。images 中按原始 PNG 的 SHA-256 各存一份，images_by_task.json 记录题号、数据集原始路径和图片哈希。评测 JSON 中的 docvqa-image:sha256: 引用对应同名 PNG。原始得分、回答和其余内容均保留。

在本目录运行以下命令，无需网络或 API 密钥，仅依赖 Python 3 标准库。

```sh
python3 restore.py --verify
python3 restore.py --verify-on-disk
python3 restore.py --output /path/to/new/verification-directory
```

第一条在内存中展开图片并验证原始文件哈希。第二条逐文件还原到临时目录并读回校验，只需容纳一个原始文件。第三条在一个新目录中创建三份完整评测目录，可用于需要原始请求内容的检查。目标目录需要约 35 GiB 可用空间。所有操作均按 manifest.json 核验全部文件的原始 SHA-256。各轮成绩和逐题答案可直接在精简归档中读取。原版评测脚本会校验完整输入，并可能依赖项目布局或引用其他历史评测，应在还原文件后按原有路径关系使用。
