# MEP Component Packaging

当前仓库根目录就是 MEP 组件包根目录，但上传前仍需把
[package.json](/Volumes/SSD1/ragent/package.json) 中的 `scope` 占位值替换成
WiseDevOps 要求的真实组织/命名空间。

## 入口文件

仓库顶层已经提供：

- [process.py](/Volumes/SSD1/ragent/process.py)
- [config.json](/Volumes/SSD1/ragent/config.json)
- [package.json](/Volumes/SSD1/ragent/package.json)

因此不需要再额外构造 `mep_component/` 子目录；但在实际上传前，必须先把
`package.json` 中当前的 `scope: "replace-me"` 改成可用值，否则会卡在
WiseDevOps 的组件包前置校验。

## 运行时规则

- `process.py` 只负责 inference，不触碰 `parse/build/MinerU` 链路。
- `chat` 历史上下文统一从 `req_Data["data"]["conversation_history"]` 读取。
- 组件启动时会显式设置 `RAGENT_RUNTIME_ENV=mep`，因此不会读取仓库根目录 `.env`。
- 模型包资源默认按 MEP 习惯从 `process.py` 的相对父目录读取 `../data` 和 `../model`。
- 若快照目录不可写，会自动复制到临时目录，再把副本作为 `working_dir` 初始化 `Ragent`。

## 模型包 data/ 放置方式

当前只支持一个内置知识库快照。现有 `project_dir` 可按下面任一方式放入模型包：

1. 直接把快照文件平铺到 `data/`
2. 放到 `data/<snapshot_name>/`

快照至少应包含类似：

- `graph_chunk_entity_relation.graphml`
- `kv_store_text_chunks.json`
- `vdb_chunks.json`

## 本地模拟

本地调试时，可以把 MEP 数据目录显式指向已有快照，例如：

```bash
export RAGENT_MEP_DATA_DIR=/Volumes/SSD1/ragent/example/demo_diet_kg
python /Volumes/SSD1/ragent/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/onehop_request.json
```

## 平台请求字段

`calc(req_Data)` 支持：

- `query_type`: `onehop | multihop | chat`
- `query`
- `mode`: `graph | hybrid`
- `conversation_history`
- `history_turns`
- `enable_rerank`
- `response_type`
- `include_trace`
- `generatePath`
- `result_filename`
