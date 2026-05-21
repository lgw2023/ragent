# Qwen3-Embedding-4B MEP Model Package

MEP 独立模型包，压缩包第一层必须是 `modelDir/`。

## 结构

- `modelDir/meta/type.mf`：MEP 元信息
- `modelDir/model/`：`Qwen/Qwen3-Embedding-4B` Hugging Face 权重（`config.json`、`tokenizer.json`、`model*.safetensors` 等）
- `modelDir/data/config/embedding.properties`：本地 `transformers + torch_npu` embedding 配置
- `modelDir/data/kg/`、`data/deps/`、`data/samples/`：与 bge-m3 包共用（软链），离线 wheelhouse 与示例 KG 快照

## 本地权重

开发环境默认将 `modelDir/model` 软链到本机 Hugging Face 缓存：

```text
~/.cache/huggingface/hub/models--Qwen--Qwen3-Embedding-4B/snapshots/<revision>/
```

交付 MEP 前请用物化拷贝或 `rsync -aL` 把权重放进 `modelDir/model/`，避免上传包仍依赖开发者机器路径。

## embedding.properties

```text
model.name=Qwen/Qwen3-Embedding-4B
embedding.runtime=transformers
embedding.dimensions=2560
embedding.pooling=lasttoken
embedding.device=npu:0
```

Qwen3 使用 **last-token pooling** 与 **left padding**（见官方 README）。支持 MRL：可在 `embedding.dimensions` 中配置更小的输出维度（32–2560）。

**注意**：从 bge-m3（256 维）切换后，既有 KG 向量库需按新维度重新建索引。

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
