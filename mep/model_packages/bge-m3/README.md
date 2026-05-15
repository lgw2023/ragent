# bge-m3 MEP Model Package

这个目录是给 MEP 使用的独立模型包源码目录，最终打包时应保证压缩包第一层就是 `modelDir/`。

当前结构：

- `modelDir/meta/type.mf`：MEP 模型包必需的元信息占位文件
- `modelDir/model/`：`BAAI/bge-m3` 运行所需的 Hugging Face 模型目录，`config.json`、`tokenizer.json`、`pytorch_model.bin` 和 `1_Pooling/` 直接放在这里
- `modelDir/data/config/embedding.properties`：组件侧读取的本地 embedding 启动配置
- `modelDir/data/kg/sample_kg/`：示例 KG 快照
- `modelDir/data/deps/`：目标镜像缺少的自定义只读依赖包；当前目标 MEP 镜像无网络时，应把离线 wheelhouse 放在这里
- `modelDir/data/samples/sample.json`：可选的请求样例

本仓库中的组件包默认假设模型包和组件包在 MEP 上会被解压到同一个父目录下，因此 `process.py` 会按平台习惯从相对路径 `../model` 读取模型目录。

本模型包的运行约定：

- 如果 `EMBEDDING_MODEL`、`EMBEDDING_MODEL_URL`、`EMBEDDING_MODEL_KEY` 都已由环境变量提供，则组件继续走外部 embedding API
- 如果没有提供完整的 embedding API 配置，则组件会在 `CustomerModel.load()` 阶段读取 `data/config/embedding.properties`，用本地 `transformers + torch_npu` 直接加载 BGE-M3
- 本地 embedding 函数会注入到现有 `openai_embed` 调用链路，知识图谱 inference 代码不需要再感知 vLLM 或 OpenAI-compatible embedding server

当前 `embedding.properties` 已按验证通过的 Ascend 910B Python 3.9 镜像配置固定为：

```text
model.relative_path=.
embedding.runtime=transformers
embedding.dimensions=256
embedding.max_token_size=8192
embedding.device=npu:0
embedding.pooling=cls
embedding.normalize=true
embedding.batch_size=8
```

组件加载本地 transformers 模型前会自动尝试加载 `/usr/local/Ascend/ascend-toolkit/set_env.sh` 和 `/usr/local/Ascend/nnal/atb/set_env.sh`。当前权威测试显示，仅 `/usr/local/Ascend/ascend-toolkit/set_env.sh` 就能让 `torch.npu.is_available()` 为 true。如目标镜像路径不同，可通过 `RAGENT_ASCEND_SET_ENV_SH` 或 `RAGENT_ASCEND_ENV_SHS` 覆盖。

目标 MEP Ascend 910B 镜像是 `linux-arm64-py3.9`。离线依赖放置约定：

```text
modelDir/data/deps/requirements-linux-arm64-py3.9.txt
modelDir/data/deps/constraints-linux-arm64-py3.9.txt
modelDir/data/deps/wheelhouse/linux-arm64-py3.9/*.whl
```

组件启动时会优先用 `requirements/constraints/wheelhouse` 执行一次 `pip install --no-index`，已安装且版本一致的镜像包会被跳过，缺失的应用层依赖和 native wheel 会从本地 wheelhouse 安装。之后才加载匹配平台标签的 `site-packages`、`pythonpath` 和可 zipimport 的纯 Python wheel。

组件入口 `process.py` 和 Ascend full-chain 验证脚本都默认启用 `MEP_STRICT_OFFLINE=1`，会设置 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、`HF_DATASETS_OFFLINE=1`、`PIP_NO_INDEX=1` 和 `PIP_CONFIG_FILE=/dev/null`。这会把运行约束在模型包自带模型文件、KG 快照和离线 wheelhouse 上，避免 Hugging Face、Transformers 或 pip 走外部网络兜底，并屏蔽镜像全局 pip 配置中的外部 index 提示。只有在排查镜像基础环境时，才建议临时设置 `MEP_STRICT_OFFLINE=0`。

如需按 Python 3.9/aarch64 重新解析并导出 wheelhouse：

```bash
python /Volumes/SSD1/ragent/tools/export_mep_transformers_embedding_wheelhouse.py --clean
```

本地模拟 MEP 组件时，推荐先生成平台形态运行时目录：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_layout.py --model-package bge-m3
python /Volumes/SSD1/ragent/.mep_build/bge-m3/runtime/component/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/onehop_request.json
```

如需生成本地归档用于检查或交付，可使用物化模式：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_layout.py \
  --model-package bge-m3 \
  --materialize \
  --archive-format zip
```

`--archive-output` 可用于指定归档位置，但路径必须位于生成的 runtime 根目录之外，并且必须是文件路径而不是已有目录，避免归档文件被再次打入归档。物化模式会解引用源目录内部软链，使本地归档内容自包含。

准备 MEP 上传包时，使用独立的上传包构建脚本：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_upload_packages.py --model-package bge-m3
```

输出为：

```text
/Volumes/SSD1/ragent/.mep_upload/bge-m3/
  component_package/
  model_package/
    modelDir/
```

如果需要直接生成上传归档，可追加：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_upload_packages.py \
  --model-package bge-m3 \
  --archive-format zip
```

上传归档默认写在 `.mep_upload/bge-m3/` 下；如需写到其他目录，可追加 `--archive-output-dir <dir>`，该参数必须和 `--archive-format` 一起使用，且不能指向正在打包的 `component_package/`、`model_package/`、组件源码或源模型包内部。

模型包归档的第一层必须是 `modelDir/`，不能额外套一层 `model_package/`。`modelDir/meta/type.mf` 必须存在且非空。组件包默认不携带 `run_mep_local.py`；确需包含本地调试入口时使用 `--include-local-runner`。

上传前可运行 preflight 校验组件包、模型包、KG/vdb 维度和目标平台 wheelhouse：

```bash
python /Volumes/SSD1/ragent/tools/preflight_mep_upload_packages.py \
  --upload-root /Volumes/SSD1/ragent/.mep_upload/bge-m3 \
  --platform-tag linux-arm64-py3.9
```

也可以继续使用显式环境变量做局部调试：

```bash
export RAGENT_MEP_MODEL_DIR=/Volumes/SSD1/ragent/mep/model_packages/bge-m3/modelDir/model
export RAGENT_MEP_DATA_DIR=/Volumes/SSD1/ragent/mep/model_packages/bge-m3/modelDir/data
python /Volumes/SSD1/ragent/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/onehop_request.json
```
