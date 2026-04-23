# bge-m3 MEP Model Package

这个目录是给 MEP 使用的独立模型包源码目录，最终打包时应保证压缩包第一层就是 `modelDir/`。

当前结构：

- `modelDir/meta/type.mf`：MEP 模型包必需的元信息占位文件
- `modelDir/model/sysconfig.properties`：组件侧读取的模型包配置
- `modelDir/model/baai_bge_m3/`：`BAAI/bge-m3` 运行所需的 Hugging Face 模型文件
- `modelDir/data/sample.json`：可选的请求样例

本仓库中的组件包默认假设模型包和组件包在 MEP 上会被解压到同一个父目录下，因此 `process.py` 会按平台习惯从相对路径 `../model` 读取模型目录。

本模型包的运行约定：

- 如果 `EMBEDDING_MODEL`、`EMBEDDING_MODEL_URL`、`EMBEDDING_MODEL_KEY` 都已由环境变量提供，则组件继续走外部 embedding API
- 如果没有提供完整的 embedding API 配置，则组件会在 `CustomerModel.load()` 阶段读取 `sysconfig.properties`，用 Python 子进程方式拉起本地 vLLM OpenAI-compatible embedding 服务
- 服务成功拉起后，现有知识图谱 inference 链路仍然复用原先的 `openai_embed` 调用，只是目标地址切到本地 vLLM

本地模拟 MEP 组件时，可以这样指定模型包目录：

```bash
export RAGENT_MEP_MODEL_DIR=/Volumes/SSD1/ragent/model_packages/bge-m3/modelDir/model
export RAGENT_MEP_DATA_DIR=/Volumes/SSD1/ragent/example/demo_diet_kg
python /Volumes/SSD1/ragent/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/onehop_request.json
```
