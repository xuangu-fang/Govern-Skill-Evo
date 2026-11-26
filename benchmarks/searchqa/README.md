# SearchQA 基础环境

独立 conda 环境名为 `SearchQA`，Python 3.12.16。此环境用于 v28 的数据准备、HTTP 调用基础依赖和离线验证。Actor Prompt、评分、六次尝试与归档恢复、完整 Gate 身份校验已离线通过；五模块及完整 campaign 仍待接入与验收，未进行真实模型运行。

## 使用

在项目根目录执行：

```sh
conda activate SearchQA
python -m pip check
python scripts/benchmarks/searchqa/check_environment.py
```

检查禁止 socket 网络连接，不读取模型凭据、不调用模型。它核对数据锁中的全部文件哈希、2000 道题的划分和 ID 顺序，检查 Arrow 数据加载，并用五个合成样例验证原生 SearchQA EM/F1 评分。数据集标准答案只用于检查字段是否完整，不产生模型测试成绩。

## 依赖与重建

- `requests`：沿用 v27 的直接 HTTP 调用方式。
- `python-dotenv`、`PyYAML`：供后续显式加载凭据和配置使用。
- `datasets`、`pyarrow`、`huggingface-hub`：本地数据处理和固定 revision 的来源核验。
- `pytest`：后续适配代码的离线测试。

`requirements.in` 记录直接依赖，`requirements.lock.txt` 固定安装后的完整 Python 依赖，`conda-osx-arm64.lock.txt` 固定 conda 包及平台版本。

在项目根目录重建尚不存在的环境：

```sh
conda env create -f benchmarks/searchqa/environment.yml
```

在同为 macOS ARM64 的机器上精确重建 conda 层，再安装 Python 依赖：

```sh
conda create -n SearchQA --file benchmarks/searchqa/conda-osx-arm64.lock.txt
conda run -n SearchQA python -m pip install -r benchmarks/searchqa/requirements.lock.txt
```

## 数据和评分来源

数据读取 `data/searchqa/prepared_v1/`，锁文件为 `data/searchqa/v28_dataset.lock.json`。原始文件保持 SkillOpt 论文的 400 Train / 200 Validation / 1400 Test；已按用户要求通过 `data/searchqa/v28_train600_v1/manifest.json` 合并前两部分为 600 题优化池，独立 Test 为 1400 题。

`reference/evaluator.py` 是未经修改的 SkillOpt SearchQA 评分参考，源 commit、文件哈希和 MIT 许可证保存在同目录。环境检查直接加载这份独立快照，不安装或导入 `external/SkillOpt` 整包。它不代表已完成 v28 的评分接入。

环境安装及离线验证结果保存在 `artifacts/benchmarks/searchqa/environment_20261101/`。

v28 的评分组件直接采用 SkillAdam 原生 EM/F1 实现，未替换上面的 SkillOpt 参考快照。Actor Prompt 与评分组件的独立离线检查命令：

```sh
conda run -n SearchQA python scripts/verification/verify_v28_actor_scoring.py --output artifacts/verification/v28_actor_scoring_20261101
```

实现范围与待接入项目见 `src/skill_evolution/v28/README.md`。检查不启动训练、不请求模型、不生成 Test 成绩。

包含 Actor 重试、恢复和完整 Gate 的扩展离线检查：

```sh
conda run -n SearchQA python scripts/verification/verify_v28_actor_runtime.py --output artifacts/verification/v28_actor_runtime_20261101
```
