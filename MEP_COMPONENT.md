# MEP KG Inference Component

当前仓库定义为 **MEP SFS 异步模板下的知识图谱问答 inference 组件包**。组件只负责在已有知识图谱快照上做查询，不在默认入口中执行 parse、build 或 MinerU 建图流程。建图相关代码仍保留在仓库中，但 MEP 入口 `process.py` 不会默认 import 或执行这些依赖。

## 包边界

组件包根目录包含 MEP 必需入口文件：

- `process.py`: MEP 入口，导出 `CustomerModel`
- `config.json`: 指向 `process.CustomerModel`
- `package.json`: 组件元信息，当前 `scope` 为 `semtp`，若目标 WiseDevOps 命名空间不同，上传前需替换为目标值

模型包使用固定目录：

```text
modelDir/
  model/
    sysconfig.properties
    <embedding-model-files>/
  data/
    <one-kg-snapshot>/
      graph_chunk_entity_relation.graphml
      kv_store_text_chunks.json
      vdb_chunks.json
      ...
```

`modelDir/model/` 放 embedding 模型和 `sysconfig.properties`。`modelDir/data/` 放一个 Ragent 知识图谱快照；快照可以直接平铺在 `data/`，也可以放在 `data/<snapshot_name>/`。如果 `data/` 下发现多个快照，组件会报错，避免默认查询目标不确定。

注意：GitHub LFS 单文件上限为 2 GiB，完整 embedding 权重文件不应依赖普通仓库提交分发。正式部署时需要在模型包构建/上传阶段补齐完整 `modelDir/model/<embedding-model-files>/` 权重。

## 运行时

- LLM 和 rerank 继续走外部 OpenAI-compatible API，由环境变量配置。
- embedding 若已配置外部 `EMBEDDING_MODEL`、`EMBEDDING_MODEL_URL`、`EMBEDDING_MODEL_KEY`，组件直接使用外部 API。
- embedding 若未配置外部 API，`CustomerModel.load()` 会从 `modelDir/model/sysconfig.properties` 读取配置，并本地拉起 vLLM OpenAI-compatible embedding 服务。
- MEP 若以 `CustomerModel(model_root=<modelDir>)` 实例化，组件直接使用 `<modelDir>/model` 和 `<modelDir>/data`；否则默认先找入口同级 `model/`、`data/`，再回退到父目录同名目录。
- 组件启动时设置 `RAGENT_RUNTIME_ENV=mep`，不会读取仓库根目录 `.env`。
- 快照目录不可写时，组件会复制到临时 runtime 目录，再用副本初始化查询 runtime。

## 接口契约

`calc(req_Data)` 顶层统一返回：

```json
{
  "recommendResult": {
    "code": "0",
    "des": "success",
    "length": 0,
    "content": []
  }
}
```

不使用 qwen 样例中的 `resultCode/result` 或 `code/response`。

### `action=create`

组件同步执行 KG 问答，将结果写入 `{generatePath}/gen.json`，然后返回 `recommendResult.code="0"`。异步 create 返回的 `content` 默认为空，避免和平台异步查询逻辑冲突。

`generatePath` 优先级：

1. `data.generatePath`
2. `data.fileInfo[0].generatePath`

`action=create` 下结果文件名固定为 `gen.json`，忽略请求里的自定义文件名。

### `action=query`

理论上由 MEP 框架处理。组件中保留防御性兼容：

- 找到 `gen.json`: 返回 `code="0"`
- 目录存在但结果文件还不存在: 返回 `code="2"`
- 缺少路径或任务路径不存在: 返回 `code="4"`

查询路径会检查 `generatePath/gen.json`、`fileInfo[0].generatePath/gen.json`、`basePath/gen.json` 和 `basePath/generatePath/gen.json`。

### 直接调试请求

没有 `action` 的直接请求继续同步返回结果：`recommendResult.content=[payload]`。只有请求中提供 `generatePath` 时才写文件；默认文件名也是 `gen.json`，直接调试模式仍允许用 `result_filename` 覆盖。

错误统一返回 `recommendResult.code="3"`，`des` 为错误信息，`content=[]`。

## KG 参数解析

KG 查询参数按三层兜底解析，前层优先：

1. `req_Data["data"]` 直接字段
2. `fileInfo[0].processSpec`
3. 若 `fileInfo[0].sourcePath + sourceImage` 指向 `.json` 文件，则读取该 JSON

支持字段：

- `query_type`: `onehop | multihop | chat`
- `query`
- `mode`: `graph | hybrid`
- `conversation_history`
- `history_turns`
- `enable_rerank`
- `response_type`
- `include_trace`

## `gen.json` schema

成功结果文件是有效 JSON，格式如下：

```json
{
  "code": "0",
  "des": "success",
  "taskId": "100002455",
  "query": "文档的主要主题是什么？",
  "query_type": "onehop",
  "mode": "hybrid",
  "answer": "...",
  "referenced_file_paths": [],
  "image_list": [],
  "conversation_history_used_count": 0,
  "history_turns": null,
  "enable_rerank": null,
  "response_type": null,
  "trace": null,
  "runtime": {
    "runtime_project_dir": "...",
    "snapshot_source_dir": "...",
    "copied_to_runtime_dir": false
  },
  "result_file_path": "/opt/business/100002455/generatePath/gen.json"
}
```

`include_trace=true` 时，`trace` 会包含查询调试信息；multi-hop trace 还可能包含 `steps`。

## 请求示例

SFS 异步 create：

```json
{
  "version": "1.2",
  "meta": {"bId": "businessId", "flowId": "kg_qa", "uuId": "xxx"},
  "data": {
    "taskId": "100002455",
    "action": "create",
    "basePath": "/opt/business/100002455",
    "query_type": "onehop",
    "query": "文档的主要主题是什么？",
    "mode": "hybrid",
    "fileInfo": [
      {
        "generatePath": "/opt/business/100002455/generatePath",
        "processSpec": []
      }
    ]
  }
}
```

更多样例在 `example/mep_requests/`：

- `sfs_create_request.json`
- `onehop_request.json`
- `multihop_request.json`
- `chat_request.json`

## 本地模拟

本地调试时，用环境变量指向已有快照和模型包。`process.py` 会按 MEP runtime 启动，默认不会自动加载 `.env`；如果要使用本地 `.env` 里的外部 LLM / embedding 配置，需要先在 shell 中显式导出：

```bash
set -a
source /Volumes/SSD1/ragent/.env
set +a
export RAGENT_MEP_DATA_DIR=/Volumes/SSD1/ragent/example/demo_diet_kg
export RAGENT_MEP_MODEL_DIR=/Volumes/SSD1/ragent/model_packages/bge-m3/modelDir/model
python /Volumes/SSD1/ragent/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/sfs_create_request.json
```

如果不导出 `EMBEDDING_MODEL`、`EMBEDDING_MODEL_URL`、`EMBEDDING_MODEL_KEY`，组件会在 `load()` 阶段按模型包的 `sysconfig.properties` 尝试拉起本地 vLLM embedding 服务。

脚本会打印 `calc()` 返回值，并在 stderr 打印目标 `gen.json` 路径。

## 测试

优先运行不依赖真实模型服务的接口测试：

```bash
pytest tests/test_mep_adapter.py tests/test_mep_component_bundle.py
```

完整目标测试集：

```bash
pytest \
  tests/test_mep_adapter.py \
  tests/test_mep_component_bundle.py \
  tests/test_mep_embedding_runtime.py \
  tests/test_model_package_bundle.py
```
