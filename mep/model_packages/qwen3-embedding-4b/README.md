# Qwen3-Embedding-4B MEP Model Package

MEP 独立模型包，压缩包第一层必须是 `modelDir/`。

## 结构

- `modelDir/meta/type.mf`：MEP 元信息
- `modelDir/model/`：`Qwen/Qwen3-Embedding-4B` 标准 Hugging Face 权重目录（`config.json`、`tokenizer.json`、`model*.safetensors` 等）
- `modelDir/data/`：组件可读取的只读 KG、依赖和样例数据；vLLM 启动和镜像 runtime 适配由组件包负责
- `modelDir/data/kg/sample_kg/`：Qwen3-Embedding-4B 以 2560 维构建的示例 KG 快照
- `modelDir/data/deps/`：仅保留说明文件；Qwen3 不再复用 bge-m3 离线 wheelhouse
- `modelDir/data/samples/`：样例请求资产，可按构建器布局复用历史包资产

## 本地权重

开发环境默认将 `modelDir/model` 软链到本机 Hugging Face 缓存：

```text
~/.cache/huggingface/hub/models--Qwen--Qwen3-Embedding-4B/snapshots/<revision>/
```

交付 MEP 前请用物化拷贝或 `rsync -aL` 把权重放进 `modelDir/model/`，避免上传包仍依赖开发者机器路径。

## embedding runtime

Qwen3 在 MEP 上默认由组件同容器启动 vLLM OpenAI-compatible embedding 服务。镜像 runtime 适配、vLLM 命令参数、Ascend/ATB 环境处理和 transformers fallback 都属于组件包职责；模型包中的 `model/` 保持标准 Hugging Face 目录。当前默认使用完整 2560 维，不做 MRL 截断。

**注意**：从 bge-m3（256 维）切换后，既有 KG 向量库需按 2560 维重新建索引。当前内置 `data/kg/sample_kg/` 来自 `example/qwen4b_diet_kg`，三个 VDB 文件的 `embedding_dim` 均为 2560。

## 构建与本地验证

```bash
python tools/build_mep_layout.py --model-package qwen3-embedding-4b
python .mep_build/qwen3-embedding-4b/runtime/component/run_mep_local.py \
  --request example/mep_requests/onehop_request.json
```

```bash
python tools/build_mep_upload_packages.py --model-package qwen3-embedding-4b
```

本地调试环境变量：

```bash
export RAGENT_MEP_MODEL_DIR=/path/to/ragent/mep/model_packages/qwen3-embedding-4b/modelDir/model
export RAGENT_MEP_DATA_DIR=/path/to/ragent/mep/model_packages/qwen3-embedding-4b/modelDir/data
```
