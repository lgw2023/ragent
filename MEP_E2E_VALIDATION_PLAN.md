# MEP 端到端验证计划与当前结论

更新时间：2026-04-24

## 1. 背景与最初目标

本次讨论最初的目标是：检查当前代码仓库在最近几次 MEP 相关修改之后，原本项目功能是否仍然正常。

随后目标扩展为：明确如何做真实端到端推理调用，以及 MEP 平台到底如何加载组件包、模型包、vLLM 镜像和外部业务请求。为此，我们检查了当前仓库代码、测试结果、`/Volumes/SSD1/ragent/MEP_platform_rule/` 下的平台规则文档，以及新增的样例目录 `/Volumes/SSD1/ragent/MEP_platform_rule/qwen_vllm_async_copilot/`。

当前阶段的目标不是立即修改所有代码，而是先把：

- 已经验证的代码健康状态
- MEP 平台运行模型
- 当前 ragent 组件实现方式
- 参照样例后修正过的目录理解
- 已知信息
- 仍需确认的信息
- 下一步验证计划

整理成一份后续改代码可直接执行的工程文档。

## 2. 当前代码健康状态

已执行的本地验证结果如下。

### 2.1 全量测试

```bash
python -m pytest
```

结果：

```text
116 passed
```

覆盖范围包括：

- MEP adapter
- MEP component bundle
- MEP embedding runtime
- runtime env
- backend config
- SQLite kv storage
- SQLite query cache
- query cache semantics
- revision semantics
- diversified graph retrieval

### 2.2 MEP 相关测试

```bash
python -m pytest \
  tests/test_mep_adapter.py \
  tests/test_mep_component_bundle.py \
  tests/test_mep_embedding_runtime.py \
  tests/test_run_mep_local.py \
  tests/test_runtime_env.py
```

结果：

```text
61 passed
```

### 2.3 编译检查

```bash
python -m compileall -q ragent process.py run_mep_local.py
```

结果：通过。

### 2.4 轻量 smoke check

已验证：

- `process.py` 可导入
- `process.py` 中存在 `CustomerModel`
- 核心模块可导入：
  - `ragent`
  - `ragent.runtime_env`
  - `ragent.inference_runtime`
  - `ragent.kg.backend_config`
  - `ragent.kg.sqlite_kv_impl`
  - `ragent.kg.sqlite_query_cache_impl`
  - `ragent.kg.networkx_impl`
- 示例 MEP 请求可被规范化：
  - `example/mep_requests/chat_request.json`
  - `example/mep_requests/onehop_request.json`
  - `example/mep_requests/multihop_request.json`
  - `example/mep_requests/sfs_create_request.json`
- MEP runtime bootstrap 会跳过 `.env`，符合 MEP runtime 隔离预期

### 2.5 当前健康结论

在不依赖真实外部模型服务和 MEP 平台的前提下，当前仓库功能正常，没有发现最近 MEP 修改导致的测试回归。

尚未完成的是“真实端到端推理调用”，即：

```text
MEP/runtime -> process.CustomerModel.load()
            -> embedding 服务
            -> 已有 KG 快照
            -> 外部 LLM / rerank
            -> calc(req_Data)
            -> generatePath/gen.json
            -> 业务方读取结果
```

## 3. 当前 ragent MEP 组件实现摘要

### 3.1 当前源码入口

当前仓库源码根目录直接包含：

- `init.py`
- `process.py`
- `config.json`
- `package.json`
- `ragent/`
- `MEP_COMPONENT.md`

`config.json` 当前内容：

```json
{
  "main_file": "process",
  "main_class": "CustomerModel"
}
```

`process.py` 当前导出：

```python
class CustomerModel:
    def __init__(self, gpu_id=None, model_root=None):
        ...

    def load(self):
        ...

    def calc(self, req_Data):
        ...

    def event(self, req_Data):
        return self.calc(req_Data)

    def health(self):
        ...
```

`init.py` 当前作为对齐样例的轻量平台初始化文件，暴露运行时目录常量、SFS 环境变量解析结果和 `build_runtime_probe()`。它不启动 vLLM、不加载 KG runtime，也不改变 `.env` 策略。

### 3.2 当前组件职责

当前 MEP 入口只做 inference：

- 不执行文档解析
- 不执行 MinerU
- 不执行建图
- 只在已有 KG 快照上做 `onehop` / `multihop` / `chat` 查询

### 3.3 当前代码的目录解析行为

当前代码通过 `resolve_component_bundle_paths()` 解析 `model` 和 `data`，优先级如下：

1. `process.py` 位于 `<runtime_root>/component` 时，优先使用父目录同级 `model/`、`data/`、`meta/`
   只有匹配到包含 `config.json` 的 `component/` 组件包目录祖先时才使用这条规则；源码仓库根目录本地运行不会把仓库父目录当成 runtime root
2. 平台注入的 SFS env：`MODEL_SFS`、`MODEL_OBJECT_ID`、`MODEL_RELATIVE_DIR`、`MODEL_ABSOLUTE_DIR`
3. 兼容 `CustomerModel(model_root=...)`，同时接受 `model_root=<runtime_root>` 和 `model_root=<model_dir>`
4. 本地调试 env fallback：`RAGENT_MEP_MODEL_DIR`、`RAGENT_MEP_DATA_DIR`
5. 源码目录同级 `model/`、`data/` 作为最后兜底

其中 `path_appendix` 不改变 bundle 级 `model_dir` 解析，而是用于 embedding runtime 选择 `model/` 下的实际权重子目录。当前仓库推荐通过 `tools/build_mep_layout.py` 生成 `.mep_build/<model-package>/runtime`，用平台形态验证这条路径解析，而不是把模型包直接当成组件源码的一部分。

### 3.4 参照样例后修正的目标理解

样例 `/Volumes/SSD1/ragent/MEP_platform_rule/qwen_vllm_async_copilot/init.py` 明确把运行时目录建模为：

```python
COMPONENT_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(COMPONENT_DIR)
MODEL_DIR = os.path.join(ROOT_DIR, "model")
DATA_DIR = os.path.join(ROOT_DIR, "data")
```

这意味着平台运行时更应该理解为：

```text
<runtime_root>/
  component/
    config.json
    <main_file>.py
    ...
  model/
    <huggingface-model-dir>/
  data/
    config/
    kg/
    deps/
    samples/
  meta/
    ...
```

也就是：

- 组件包最终位于 `<runtime_root>/component`
- 模型包解压/挂载后向组件暴露的是平级 `model/`、`data/`、`meta/`
- `component/` 通过父目录访问 `model/` 和 `data/`
- `model/` 顶层只放 Hugging Face 模型目录；`data/` 放组件侧只读配置、KG、依赖包、样例等自定义数据

因此此前把 `model_root` 默认理解为“模型包根目录 `modelDir`”并不稳妥。

### 3.5 样例暴露出的另一条路径契约

样例 `process.py` / `process_sync.py` 虽然也有 `__init__(gpu_id=None, model_root=None)`，但实际模型路径主要不是从 `model_root` 推出来，而是从环境变量推出来：

```python
tmp_json = json.loads(os.environ.get("MODEL_SFS", "{\"sfsBasePath\":\"aaaa\"}"))
process_model_base = tmp_json["sfsBasePath"] + "/" + os.environ.get("MODEL_OBJECT_ID", "") + "/model"
model_path = process_model_base + "/" + os.environ.get("path_appendix", "")
```

样例 `init.py` 同时还定义了：

```python
MODEL_ABSOLUTE_DIR
MODEL_RELATIVE_DIR
SFS_MODEL_DIR
```

因此，参照样例后的合理结论是：

- `model_root` 不是平台唯一或主要契约
- 平台可能更依赖运行时平级目录和 SFS 环境变量
- 当前代码已把“平级目录 + SFS env”放到 `model_root` 之前

### 3.6 当前 embedding 运行方式

embedding 仍有两种模式。

第一种：外部 embedding API。

如果环境变量完整提供：

```text
EMBEDDING_MODEL
EMBEDDING_MODEL_URL
EMBEDDING_MODEL_KEY
```

则组件直接调用外部 embedding API，不拉起本地 vLLM。

第二种：本地 vLLM embedding 服务。

如果没有完整外部 embedding 配置，`CustomerModel.load()` 会优先读取 `data/config/embedding.properties`，并通过 `ragent.mep_embedding_runtime.bootstrap_local_embedding_runtime()` 拉起本地 OpenAI-compatible embedding 服务。旧的 `model/sysconfig.properties` 只作为兼容兜底，新模型包不再把组件配置文件放入 `model/`。

当前代码支持两种 vLLM 启动候选：

```bash
vllm serve <model_path> ...
```

或：

```bash
python -m vllm.entrypoints.openai.api_server --model <model_path> ...
```

### 3.7 当前 calc 行为

`calc(req_Data)` 的行为：

- 如果 `action=query`，当前代码有防御性兼容，会尝试返回查询状态
- 如果 `action=create`，会执行 KG 查询，写 `{generatePath}/gen.json`，再返回 `recommendResult`
- 如果没有 `action`，视为直接调试请求，返回内容会放进 `recommendResult.content`

`action=create` 成功返回：

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

`gen.json` 当前由组件写出，包含：

```text
code
des
taskId
query
query_type
mode
answer
referenced_file_paths
image_list
conversation_history_used_count
history_turns
enable_rerank
response_type
trace
runtime
result_file_path
```

## 4. MEP 平台规则中已经明确的信息

以下信息综合来自 `MEP_platform_rule/`、`MEP_platform_rule/MEP-QA/`，以及新增样例目录 `qwen_vllm_async_copilot/`。

### 4.1 组件包入口

MEP 组件包需要包含：

- `config.json`
- `config.json.main_file` 指向的入口模块文件
- `config.json.main_class` 指向的入口类

`main_file` 不一定是 `process`。

当前仓库是：

```json
{
  "main_file": "process",
  "main_class": "CustomerModel"
}
```

样例是：

```json
{
  "main_file": "process_sync",
  "main_class": "MyApplication"
}
```

### 4.2 生命周期调用顺序

平台会按顺序调用：

```text
实例化入口类 -> load() -> calc(req_Data)
```

`load()` 用于模型加载和耗时初始化，`calc()` 用于处理业务请求。

### 4.3 组件包、模型包、数据目录关系

参照样例，平台运行时目录应理解为：

```text
<runtime_root>/
  component/
    config.json
    <main_file>.py
    ...
  model/
    ...
  data/
    ...
  meta/
    ...
```

源码仓库可以不是这个样子，但平台容器里更可能是这个样子。

这说明后续代码和文档都应基于以下事实：

- `component/`、`model/`、`data/`、`meta/` 是平级关系
- 组件入口通过父目录看到同级 `model/` 和 `data/`
- `data/` 不是默认挂在 `model/` 下面
- `meta/` 是模型包标准结构的一部分，即使当前组件未直接读取

### 4.4 SFS 异步调用链

标准链路：

```text
业务方 POST /service action=create
MEP 平台入队并调用组件 calc()
组件执行推理
组件写 generatePath/gen.json
组件返回 recommendResult 状态
业务方 POST /service action=query 轮询状态
query 返回完成后，业务方读取 SFS 上的 gen.json
```

### 4.5 `action=create` / `action=query`

`action=create`：

- 创建任务
- 携带 `taskId`、`basePath`、`fileInfo`、`generatePath` 等
- 会触发组件推理
- 组件需要写 `{generatePath}/gen.json`

`action=query`：

- 用于查询异步任务状态
- 大概率由 MEP 异步框架或 MSG 网关处理，不一定进入组件 `calc()`
- 当前 ragent 仍保留 `action=query` 的防御性兼容

### 4.6 `calc()` 返回值和 `gen.json` 的消费者不同

`calc()` 返回值：

- 消费者是 MEP 框架
- 用于判断任务执行状态
- 结构必须符合 `recommendResult` 约定
- 异步 create 成功时，`content` 通常为空

`generatePath/gen.json`：

- 消费者是业务方
- 承载实际推理结果
- 平台主要强制文件名和位置，不强制 JSON 内部 schema
- schema 需要组件方和业务方对齐

### 4.7 vLLM 子进程方案

样例工程明确采用组件内 `subprocess.Popen()` 拉起 vLLM 子进程的方式。

这说明平台机制上允许组件代码启动本地服务进程，并监听 `127.0.0.1:<port>` 给组件内部调用。

但是进程生命周期、初始化超时、端口限制和资源隔离策略仍需平台侧确认。

## 5. 当前不确定或待确认的信息

### 5.1 `model_root` 传参语义

参照样例后，`model_root` 的不确定性比之前想得更大。

当前结论不是“平台大概率会传 `<runtime_root>` 或 `<runtime_root>/model`”，而是：

- 样例构造函数里虽然有 `model_root` 参数，但实际业务路径没有依赖它
- 平台很可能更依赖平级目录或 SFS 环境变量
- `model_root` 最多应视为兼容输入，而不是唯一契约

当前代码已兼容至少三种情况：

```text
1. 原生运行时：<runtime_root>/component 的父目录下有 model/、data/、meta/
2. SFS env 注入：MODEL_SFS + MODEL_OBJECT_ID (+ MODEL_RELATIVE_DIR / MODEL_ABSOLUTE_DIR / path_appendix)
3. 兼容传参：model_root=<runtime_root> 或 model_root=<runtime_root>/model
```

### 5.2 是否必须支持 `MODEL_SFS` / `MODEL_OBJECT_ID`

参照样例，这已经不再只是“可能需要”的问题，而是高优先级兼容项。

样例直接使用：

```text
MODEL_SFS
MODEL_OBJECT_ID
path_appendix
```

并在初始化常量里同时考虑：

```text
MODEL_ABSOLUTE_DIR
MODEL_RELATIVE_DIR
```

当前 ragent 已读取这些变量，并按 bundle 层和 embedding 层分工处理：

```text
bundle 层：MODEL_SFS / MODEL_OBJECT_ID / MODEL_RELATIVE_DIR / MODEL_ABSOLUTE_DIR
embedding 层：path_appendix
```

仍需平台实测确认这些变量在真实容器里的最终落盘形态，尤其是 `MODEL_ABSOLUTE_DIR`、`MODEL_RELATIVE_DIR` 和 `path_appendix` 分别指向模型包根、`model/` 目录还是具体权重子目录。

### 5.3 `data/` 目录到底如何暴露给组件

当前 ragent 需要 `data/` 下有且只有一个 Ragent KG 快照，或者 `data/` 本身就是 KG 快照。

有效快照至少包含以下 marker 中的两个：

```text
graph_chunk_entity_relation.graphml
kv_store_text_chunks.json
vdb_chunks.json
```

仍需确认：

- 平台是否会把模型包的 `data/` 直接暴露为 `<runtime_root>/data`
- `data/` 下是否只包含一个 KG 快照
- 如果有多个目录，平台侧是否会给出目标快照约定

### 5.4 目标 vLLM 镜像是否支持 embedding / pooling runner

已知目标 vLLM Ascend 镜像中存在：

```text
vllm
vllm-ascend
```

但当前 ragent 拉起的是 embedding 服务，不是样例那种 chat/completions 主模型服务。

仍需确认：

- 目标 vLLM 版本是否支持 `BAAI/bge-m3`
- 目标 vLLM Ascend 环境是否支持 embedding / pooling runner
- `python -m vllm.entrypoints.openai.api_server --task embed` 是否可用
- `vllm serve ... --runner pooling` 是否可用
- `/v1/models` 和 `/v1/embeddings` 是否能正常响应

### 5.5 vLLM 子进程运行限制

样例工程证明可以 `Popen`，但以下限制仍需平台确认或实测：

- `load()` 最长允许阻塞多久
- vLLM 启动时间超过平台初始化超时会发生什么
- 子进程是否会随组件进程一起被清理
- 同一容器内是否可能启动多个组件实例
- 本地端口监听是否有限制
- GPU/NPU 资源是否会被多个进程竞争
- 平台健康检查是否只检查主进程，还是也能感知子进程状态

### 5.6 `generatePath` 是否预创建且可写

当前 ragent 写结果时会执行：

```python
generate_path.mkdir(parents=True, exist_ok=True)
```

因此目录不存在不是问题，但仍需确认：

- `{generatePath}` 是否一定在组件容器内可写
- 如果目录不存在，组件自行创建是否被允许
- 写出的 `gen.json` 是否业务方可见

### 5.7 `gen.json` schema 需要业务方确认

MEP 不强制 `gen.json` 内部 schema。

当前 ragent schema 偏向 KG QA 场景：

```json
{
  "code": "0",
  "des": "success",
  "taskId": "100002455",
  "query": "...",
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
  "result_file_path": "..."
}
```

待业务方确认：

- 是否读取 `answer` 字段
- 是否希望字段名是 `response`、`result`、`content` 或其他
- 是否需要保留引用文件路径
- 是否需要错误时也写 `gen.json`
- 是否允许携带 `runtime` 调试信息

### 5.8 外部 LLM / rerank 配置注入方式

当前 KG QA 除 embedding 外，还依赖外部 LLM。

至少需要：

```text
LLM_MODEL
LLM_MODEL_URL
LLM_MODEL_KEY
```

如果启用 rerank，还需要 rerank 相关环境变量。

仍需确认：

- MEP 平台如何注入这些外部 API 环境变量
- 是否允许组件访问外部 OpenAI-compatible LLM 服务
- 网络出口和 DNS 是否可达
- API key 是否通过环境变量、密钥管理或配置文件注入

### 5.9 平台实测确认清单

后续进入真实 MEP 平台联调前，至少需要把以下事项逐项记录到联调日志或更新回本文档。

| 待确认项 | 需要记录的事实 | 影响范围 |
| --- | --- | --- |
| 运行时目录布局 | `cwd`、入口 `__file__`、`component/` 是否包含 `config.json`、`component/` 父目录下是否存在 `model/`、`data/`、`meta/` | 决定 `runtime_sibling_*` 路径是否是主路径 |
| `model_root` 传参 | 平台实例化入口类时是否传入 `model_root`；传入值是 `<runtime_root>`、`<runtime_root>/model`、模型包根目录，还是为空 | 决定兼容输入是否命中，避免误把它当主契约 |
| SFS 环境变量 | `MODEL_SFS`、`MODEL_OBJECT_ID`、`MODEL_ABSOLUTE_DIR`、`MODEL_RELATIVE_DIR`、`path_appendix` 的原始值和最终落盘目标 | 决定模型目录、数据目录和具体 embedding 权重子目录解析 |
| 模型包 `data/` 暴露形态 | 推荐 `data/kg/<snapshot_name>/`；如平台或业务包使用其他位置，需要通过 `RAGENT_MEP_KG_DIR` 指定 | 决定 `resolve_single_snapshot_from_data_dir()` 的目标选择规则 |
| vLLM embedding 能力 | `vllm serve ... --runner pooling`、`python -m vllm.entrypoints.openai.api_server --task embed`、`/v1/models`、`/v1/embeddings` 是否可用 | 决定本地 embedding runtime 是否能在目标镜像上工作 |
| 子进程生命周期限制 | `load()` 超时上限、端口监听限制、同容器多实例行为、组件退出时子进程是否被平台清理 | 决定 vLLM 启动超时、端口和 cleanup 策略 |
| 资源隔离 | GPU/NPU 是否会被多个组件实例竞争，平台是否限制子进程资源 | 决定是否需要单实例保护或资源配置约束 |
| `generatePath` 写入 | 目录是否预创建、组件是否允许 `mkdir`、`gen.json` 写出后业务方是否可见 | 决定异步 create/query 的结果落盘可靠性 |
| 外部 LLM/rerank 注入 | `LLM_MODEL`、`LLM_MODEL_URL`、`LLM_MODEL_KEY` 及 rerank 变量如何注入，网络出口和 DNS 是否可用 | 决定 KG QA 主链路是否能完成推理 |
| `gen.json` 业务 schema | 业务方读取 `answer` 还是其他字段；错误时是否要求写 `gen.json`；是否允许携带 `runtime` 调试字段 | 决定输出契约是否需要新增 schema 兼容层 |

## 6. 当前计划

### 阶段 1：本地端到端验证

目标：在不依赖 MEP 平台的情况下，先证明当前组件可以完整跑通真实推理链路。

前置条件：

- 准备一个真实 KG 快照
- 准备完整 embedding 模型包，或配置外部 embedding API
- 配置外部 LLM API

推荐优先使用接近平台的本地装配目录：

```bash
cd /Volumes/SSD1/ragent

python tools/build_mep_layout.py --model-package bge-m3

set -a
source .env
set +a

python .mep_build/bge-m3/runtime/component/run_mep_local.py \
  --request example/mep_requests/sfs_create_request.json
```

如需检查物化后的本地交付内容，可使用：

```bash
python tools/build_mep_layout.py --model-package bge-m3 --materialize --archive-format zip
```

如需指定 `--archive-output`，输出路径必须位于 `.mep_build/<model-package>/runtime/` 之外，避免归档过程把自身也写进交付包。

物化模式会解引用 `model/`、`data/`、`meta/` 源目录内部的软链，以便本地归档内容自包含。`--archive-output` 必须是文件路径而不是已有目录；装配脚本也会拒绝 `model/` 顶层非目录项，避免把旧式组件配置重新打进模型目录。

如需准备真正上传到 MEP 的组件包和模型包目录，使用上传包构建脚本，而不是本地 runtime layout：

```bash
python tools/build_mep_upload_packages.py --model-package bge-m3
```

输出位于 `.mep_upload/bge-m3/`：

- `component_package/`：组件包根目录，默认不包含 `run_mep_local.py`
- `model_package/modelDir/`：模型包根目录，压缩后第一层必须是 `modelDir/`

可选追加 `--archive-format zip` 生成两个独立归档；组件归档根目录直接是组件文件，模型归档根目录直接是 `modelDir/`，不会额外套 `component_package/` 或 `model_package/`。

上传归档默认写在 `.mep_upload/<model-package>/` 下；如需指定其他归档目录，可追加 `--archive-output-dir <dir>`，该参数必须和 `--archive-format` 一起使用。构建脚本会拒绝把归档写进 `component_package/` 或 `model_package/` 内部；自定义归档目录也不能覆盖仓库根、组件源码或源模型包。

构建脚本会拒绝会覆盖仓库根、组件源码或源模型包的输出目录，并要求 `modelDir/meta/type.mf` 存在且非空。

验证点：

- `CustomerModel.load()` 成功
- embedding 服务可用
- 外部 LLM 可用
- `calc()` 返回 `recommendResult.code="0"`
- `{generatePath}/gen.json` 被写出
- `gen.json.answer` 有合理回答

### 阶段 2：容器仿真验证

目标：按样例运行时布局验证路径解析，而不是只验证本地 override。

构造目录：

```text
<runtime_root>/
  component/
    process.py
    config.json
    package.json
    ragent/
  model/
    baai_bge_m3/
  data/
    config/
      embedding.properties
    kg/
      <kg snapshot>/
    deps/
  meta/
    ...
```

至少做两类验证。

第一类：原生平级目录验证。

在 `<runtime_root>/component` 内直接模拟平台：

```python
import json
import process

model = process.CustomerModel()
model.load()

with open("request.json", "r", encoding="utf-8") as f:
    req = json.load(f)

print(model.calc(req))
```

第二类：兼容参数/环境变量验证。

需要分别测试：

```python
process.CustomerModel()
process.CustomerModel(model_root="<runtime_root>")
process.CustomerModel(model_root="<runtime_root>/model")
```

并补一组 SFS 环境变量模拟：

```text
MODEL_SFS
MODEL_OBJECT_ID
MODEL_RELATIVE_DIR
MODEL_ABSOLUTE_DIR
path_appendix
```

目标不是强迫平台按某一种方式工作，而是让组件兼容样例暴露出来的多种路径契约。

### 阶段 3：MEP 平台最小探针

目标：在真实 MEP 容器中打印运行时事实，消除路径猜测。

建议临时加入或通过日志输出以下信息：

```python
import os
from pathlib import Path

print("cwd=", os.getcwd())
print("__file__=", __file__)
print("env MODEL_SFS=", os.getenv("MODEL_SFS"))
print("env MODEL_OBJECT_ID=", os.getenv("MODEL_OBJECT_ID"))
print("env MODEL_RELATIVE_DIR=", os.getenv("MODEL_RELATIVE_DIR"))
print("env MODEL_ABSOLUTE_DIR=", os.getenv("MODEL_ABSOLUTE_DIR"))
print("env path_appendix=", os.getenv("path_appendix"))
print("env RAGENT_MEP_MODEL_DIR=", os.getenv("RAGENT_MEP_MODEL_DIR"))
print("env RAGENT_MEP_DATA_DIR=", os.getenv("RAGENT_MEP_DATA_DIR"))
print("component_dir=", Path(__file__).resolve().parent)
print("runtime_root=", Path(__file__).resolve().parent.parent)
print("sibling model exists=", (Path(__file__).resolve().parent.parent / "model").exists())
print("sibling data exists=", (Path(__file__).resolve().parent.parent / "data").exists())
print("sibling meta exists=", (Path(__file__).resolve().parent.parent / "meta").exists())
```

如果平台允许执行 shell，也建议采集：

```bash
pwd
env | sort
ls -la /
ls -la /component || true
ls -la /model || true
ls -la /data || true
ls -la /meta || true
find /model -maxdepth 3 -type f | head -50
find /data -maxdepth 3 -type f | head -50
```

### 阶段 4：真实 MEP create/query 验证

目标：验证业务链路。

请求样例：

```json
{
  "version": "1.2",
  "meta": {
    "bId": "businessId",
    "flowId": "kg_qa",
    "uuId": "xxx"
  },
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

验证点：

- `action=create` 返回任务创建成功
- MEP 平台日志中看到组件 `load()` 和 `calc()`
- 组件写出 `generatePath/gen.json`
- `action=query` 返回完成
- 业务方能读取并解析 `gen.json.answer`

## 7. 建议的代码增强

以下增强中，7.1-7.3 已在当前代码中实现；7.4 仍需后续和业务方确认。

### 7.1 已实现的目录解析优先级

当前 `resolve_component_bundle_paths()` / `CustomerModel._load_async()` 已按以下顺序解析：

1. 原生运行时平级目录：`component` 父目录下的 `model/`、`data/`、`meta/`
2. SFS 环境变量 fallback：`MODEL_SFS`、`MODEL_OBJECT_ID`、`MODEL_RELATIVE_DIR`、`MODEL_ABSOLUTE_DIR`、`path_appendix`
3. `model_root` 兼容模式：
   - `model_root=model_root_of_runtime`
   - `model_root=model_dir`
4. 本地显式 env fallback：`RAGENT_MEP_MODEL_DIR`、`RAGENT_MEP_DATA_DIR`
5. 源码目录同级 `model/`、`data/` 作为最后兜底

重点不是继续强化 `model_root/model` 这一条，而是先对齐样例暴露出的原生平台路径契约。当前推荐用 `.mep_build/<model-package>/runtime` 做本地仿真，避免把仓库里的模型包源码位置误认为平台运行时位置。

### 7.2 已补充 `MODEL_SFS` 系列 fallback

当前实现已支持以下模型定位方式：

```text
MODEL_ABSOLUTE_DIR
MODEL_SFS + MODEL_OBJECT_ID + MODEL_RELATIVE_DIR
MODEL_SFS + MODEL_OBJECT_ID + "/model"
```

但要注意：ragent 需要同时定位 `data/`，不能只定位 embedding 模型目录；`path_appendix` 当前只用于 embedding runtime 在 `model/` 下选择具体权重子目录。

### 7.3 已增加启动诊断日志

当前 `CustomerModel.load()` 会记录：

- `__file__`
- `cwd`
- `model_root`
- `MODEL_SFS`
- `MODEL_OBJECT_ID`
- `MODEL_RELATIVE_DIR`
- `MODEL_ABSOLUTE_DIR`
- resolved `model_dir`
- resolved `data_dir`
- resolved KG snapshot dir
- 是否使用外部 embedding
- vLLM command
- vLLM log path
- runtime copied path

这样平台联调失败时能快速判断是路径、权限、模型、网络还是 API 配置问题。

### 7.4 输出 schema 与业务方对齐

当前 `gen.json` schema 仍需业务方确认。建议在确认后固化到 `MEP_COMPONENT.md`，并补一组 schema 测试。

## 8. 当前结论

当前仓库的本地测试和非真实模型依赖验证均通过，说明最近 MEP 相关修改没有破坏已有测试覆盖下的功能。

参照新增样例后，真实端到端验证的主要风险已经从“平台完全未知”进一步收敛为以下几类：

1. 平台原生运行时是否就是 `component/`、`model/`、`data/`、`meta/` 平级布局
2. 平台是否主要通过 `MODEL_SFS` / `MODEL_OBJECT_ID` / `MODEL_RELATIVE_DIR` / `MODEL_ABSOLUTE_DIR` / `path_appendix` 暴露模型路径
3. 当前代码是否需要把“平级目录 + SFS env”提升到 `model_root` 之前
4. 目标 vLLM Ascend 镜像是否支持当前 embedding / pooling 服务
5. 外部 LLM / rerank 环境变量如何注入
6. `generatePath` 写权限和业务方 `gen.json` schema 是否一致

优先级最高的下一步不再是泛泛地“猜平台目录”，而是：

1. 先按样例目录改造路径解析代码
2. 做一次本地容器式目录仿真
3. 在真实平台打印最小路径探针
4. 再做 create/query 联调
