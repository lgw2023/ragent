# bge-m3 MEP Model Package

这个目录是给 MEP 使用的独立模型包源码目录，最终打包时应保证压缩包第一层就是 `modelDir/`。

当前结构：

- `modelDir/meta/type.mf`：MEP 模型包必需的元信息占位文件
- `modelDir/model/baai_bge_m3/`：`BAAI/bge-m3` 运行所需的 Hugging Face 模型文件；`model/` 顶层只放 HF 模型目录
- `modelDir/data/config/embedding.properties`：组件侧读取的本地 embedding/vLLM 启动配置
- `modelDir/data/kg/sample_kg/`：示例 KG 快照
- `modelDir/data/deps/`：vLLM 镜像缺少的自定义只读依赖包；当前目标 MEP 镜像无网络时，应把离线 wheelhouse 放在这里
- `modelDir/data/samples/sample.json`：可选的请求样例

本仓库中的组件包默认假设模型包和组件包在 MEP 上会被解压到同一个父目录下，因此 `process.py` 会按平台习惯从相对路径 `../model` 读取模型目录。

本模型包的运行约定：

- 如果 `EMBEDDING_MODEL`、`EMBEDDING_MODEL_URL`、`EMBEDDING_MODEL_KEY` 都已由环境变量提供，则组件继续走外部 embedding API
- 如果没有提供完整的 embedding API 配置，则组件会在 `CustomerModel.load()` 阶段读取 `data/config/embedding.properties`，用 Python 子进程方式拉起本地 vLLM OpenAI-compatible embedding 服务
- 服务成功拉起后，现有知识图谱 inference 链路仍然复用原先的 `openai_embed` 调用，只是目标地址切到本地 vLLM

当前 `embedding.properties` 已按验证通过的 Ascend 910B 镜像配置固定为：

```text
vllm.launch_mode=module
vllm.runner=pooling
vllm.served_model_name=BAAI-bge-m3
vllm.bind_host=0.0.0.0
vllm.host=127.0.0.1
vllm.port=8000
vllm.max_model_len=8192
vllm.extra_args=--dtype auto
vllm.uninstall_packages=vllm,vllm-ascend
vllm.install_requirements=triton-ascend==3.2.0,vllm==0.13.0,vllm-ascend==0.13.0
vllm.install_no_deps=true
vllm.install_force_reinstall=true
vllm.env.ASCEND_RT_VISIBLE_DEVICES=0
vllm.env.VLLM_LOGGING_LEVEL=DEBUG
vllm.env.VLLM_PLUGINS=ascend
```

`vllm.bind_host` 对齐验证脚本中的 vLLM `--host 0.0.0.0`；`vllm.host` 是组件调用 `/v1/embeddings` 时使用的本地回连地址。`vllm.api_key=EMPTY` 只用于满足 ragent 侧调用参数，只有配置为真实 key 时才会传给 vLLM `--api-key`。

组件拉起 vLLM 前会先检查 `triton-ascend==3.2.0`、`vllm==0.13.0`、`vllm-ascend==0.13.0` 是否已经安装；版本不一致时会从模型包 `data/deps/wheelhouse/<platform-tag>/` 离线安装这些 wheel。

组件启动 vLLM 子进程前会自动尝试加载 `/usr/local/Ascend/ascend-toolkit/set_env.sh` 和 `/usr/local/Ascend/nnal/atb/set_env.sh`。如目标镜像路径不同，可通过 `RAGENT_ASCEND_SET_ENV_SH` 或 `RAGENT_ASCEND_ENV_SHS` 覆盖。

目标 MEP Ascend 910B 镜像是 `linux-arm64-py3.10`。离线依赖放置约定：

```text
modelDir/data/deps/wheelhouse/linux-arm64-py3.10/*.whl
modelDir/data/deps/wheelhouse/linux-arm64-py3.10/*.tar.gz
modelDir/data/deps/site-packages/linux-arm64-py3.10/
```

组件启动时会优先加载匹配平台标签的目录，但只直接 zipimport 纯 Python wheel。native vLLM wheel 和 sdist/source archive 不会直接加到 `sys.path`，而是通过上面的离线 `pip install` 修复步骤安装。纯 Python wheel 仅在目标镜像中已经安装且版本完全一致时跳过；需要强制加入模型包内纯 Python wheel 时，可设置 `RAGENT_MEP_FORCE_WHEELHOUSE=1`。

如需按已验证容器环境导出精确 wheelhouse：

```bash
python /Volumes/SSD1/ragent/tools/export_mep_vllm_ascend_wheelhouse.py
```

导出依据是 `MEP_platform_rule/Validated_ragent-mep-test_docker_vllm_requirements.freeze.txt`。导出器会记录 wheel、手工补入的 `.tar.gz` source archive、失败项和本地 `file://` 条目。`@ file://...whl` 形式的条目中，`/tmp/ragent-mep-test` 前缀会默认从索引解析下载；这覆盖启动修复步骤需要的 `triton-ascend==3.2.0`。`/home/mep/...` 和 `/usr/local/Ascend/...` 这类镜像内置路径默认只记录不下载。若这些 wheel 已单独下载到某个目录，可追加 `--local-wheel-dir <dir>` 复制；若确实需要从索引解析全部本地 wheel，可追加 `--resolve-local-file-wheels`。

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

也可以继续使用显式环境变量做局部调试：

```bash
export RAGENT_MEP_MODEL_DIR=/Volumes/SSD1/ragent/mep/model_packages/bge-m3/modelDir/model
export RAGENT_MEP_DATA_DIR=/Volumes/SSD1/ragent/mep/model_packages/bge-m3/modelDir/data
python /Volumes/SSD1/ragent/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/onehop_request.json
```
