# MEP KG Inference Component

当前仓库定义为一个 **MEP SFS 异步模板下的知识图谱问答 inference 组件**。参照 `/Volumes/SSD1/ragent/MEP_platform_rule/qwen_vllm_async_copilot/` 样例后，本文明确区分两个概念：

- 源码目录：当前仓库如何组织代码
- 平台运行时目录：组件包和模型包在 MEP 容器里如何落盘

之前文档里把“仓库根目录”“组件包目录”“模型包根目录”“`model_root` 参数”混在一起描述，容易导致后续代码按错目录规则实现。本文先把目标目录约定写清楚，后续代码再据此调整。

## 1. 两个视角

### 1.1 当前源码目录

当前仓库源码根目录里直接维护：

- `init.py`
- `process.py`
- `config.json`
- `package.json`
- `ragent/`
- `example/`
- `mep/model_packages/`
- `tools/build_mep_layout.py`

这只是源码组织方式，不等于 MEP 运行时最终目录。

### 1.2 平台运行时目录

参照样例 `init.py` 的路径定义：

```python
COMPONENT_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(COMPONENT_DIR)
MODEL_DIR = os.path.join(ROOT_DIR, "model")
DATA_DIR = os.path.join(ROOT_DIR, "data")
```

更合理的运行时视图应理解为：

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

也就是：

- 组件包最终位于 `<runtime_root>/component`
- 模型包解压/挂载后的 `model/`、`data/`、`meta/` 与 `component/` 平级
- 组件入口代码通过 `component/` 的父目录看到同级 `model/` 和 `data/`

`meta/` 在当前 ragent 代码里还没有直接使用，但样例说明它是模型包标准结构的一部分，所以文档里要保留这个概念。

## 2. 包边界

### 2.1 组件包

组件包至少需要：

- `config.json`
- `config.json.main_file` 指向的入口模块
- `config.json.main_class` 指向的入口类
- `init.py`：对齐样例的轻量平台初始化文件，集中暴露运行时目录、SFS 环境变量和探针信息

注意：入口文件 **不一定** 叫 `process.py`。

当前仓库配置：

```json
{
  "main_file": "process",
  "main_class": "CustomerModel"
}
```

样例组件配置：

```json
{
  "main_file": "process_sync",
  "main_class": "MyApplication"
}
```

因此，文档后续统一使用“`config.json` 指向的入口模块/入口类”这一说法，不再把 `process.py` 写成平台唯一入口文件名。

### 2.2 模型包

参照样例，模型包构建目录应理解为：

```text
modelDir/
  meta/
    ...
  model/
    config.json
    tokenizer.json
    pytorch_model.bin
    1_Pooling/
  data/
    config/
    kg/
    deps/
    samples/
```

但组件在运行时真正看到的重点不是 `modelDir` 这个名字，而是服务根目录下的平级目录：

- `<runtime_root>/model`
- `<runtime_root>/data`
- `<runtime_root>/meta`

`model/` 本身就是 Hugging Face 模型目录；组件可读取的只读自定义数据放在 `data/`，例如配置、KG 快照、依赖包、样例请求等。因此不要再把“模型包根目录”和“组件收到的 `model_root` 参数”默认视为同一个概念。

当前仓库内的模型包源码放在：

```text
mep/model_packages/bge-m3/modelDir/
  meta/
    type.mf
  model/
    config.json
    tokenizer.json
    pytorch_model.bin
    1_Pooling/
  data/
    config/
      embedding.properties
    kg/
      sample_kg/
    deps/
      README.md
    samples/
      sample.json
```

## 3. 目录映射约定

参照样例后，本文采用以下优先级理解 MEP 平台目录约定：

1. 原生运行时平级目录：`<runtime_root>/component`、`<runtime_root>/model`、`<runtime_root>/data`、`<runtime_root>/meta`
2. 平台注入的 SFS 相关环境变量：`MODEL_SFS`、`MODEL_OBJECT_ID`、`MODEL_RELATIVE_DIR`、`MODEL_ABSOLUTE_DIR`、`path_appendix`
3. 兼容性输入 `model_root`
4. 本地调试兜底输入：`RAGENT_MEP_MODEL_DIR`、`RAGENT_MEP_DATA_DIR`

样例 `process.py` / `process_sync.py` 虽然保留了 `__init__(gpu_id=None, model_root=None)` 这个签名，但实际模型路径主要由环境变量拼出：

```python
tmp_json = json.loads(os.environ.get("MODEL_SFS", "{\"sfsBasePath\":\"aaaa\"}"))
process_model_base = tmp_json["sfsBasePath"] + "/" + os.environ.get("MODEL_OBJECT_ID", "") + "/model"
model_path = process_model_base + "/" + os.environ.get("path_appendix", "")
```

这说明：

- `model_root` 不是样例里的主路径契约
- 平台更可能通过运行时目录和平级目录，或通过 SFS 环境变量告诉组件模型位置
- 后续 ragent 代码不应再把 `model_root=<modelDir>` 视为唯一或首要假设

当前仓库代码现已按上述优先级实现路径解析，并保留旧的“源码目录同级 `model/`、`data/`”作为最后一层本地 fallback。

## 4. 当前组件职责

当前 MEP 入口只做 inference：

- 不执行文档解析
- 不执行 MinerU
- 不执行默认建图流程
- 只在已有 KG 快照上做 `onehop` / `multihop` / `chat` 查询

建图相关代码仍保留在仓库中，但当前 MEP 入口不会把它们作为默认在线链路的一部分。

## 5. 运行时约定

### 5.1 生命周期

平台侧按以下顺序使用组件：

```text
实例化入口类 -> load() -> calc(req_Data)
```

`load()` 负责耗时初始化，`calc(req_Data)` 负责处理业务请求。

### 5.2 `init.py` 职责

当前组件包根目录提供 `init.py`，用于和样例组件保持一致的初始化入口层。

它只负责：

- 暴露 `COMPONENT_DIR`、`ROOT_DIR`、`MODEL_DIR`、`DATA_DIR`、`META_DIR`
- 解析 `MODEL_SFS`、`MODEL_OBJECT_ID`、`MODEL_ABSOLUTE_DIR`、`MODEL_RELATIVE_DIR`、`path_appendix`
- 提供 `build_runtime_probe()` 方便平台联调时打印目录和环境事实

它不负责：

- 启动 vLLM 子进程
- 加载 KG runtime
- 修改 `.env` 加载策略

这些职责仍分别属于 `process.py`、`ragent/mep_embedding_runtime.py` 和 `ragent/runtime_env.py`。

### 5.3 路径解析目标

参照样例后，ragent 的目标目录解析约定应为：

1. 优先按 `<runtime_root>/component` 的父目录查找同级 `model/` 和 `data/`
   仅当入口模块实际位于包含 `config.json` 的 `component/` 组件包目录内时，才启用这条规则；源码仓库根目录本地运行时，不会把仓库父目录误判为 `<runtime_root>`
2. 如平台只暴露 SFS 信息，则从 `MODEL_SFS` / `MODEL_OBJECT_ID` / `MODEL_RELATIVE_DIR` / `MODEL_ABSOLUTE_DIR` / `path_appendix` 推导模型路径，并补齐 `data` 定位
3. `model_root` 仅作为兼容输入，允许兼容 `runtime_root` 或 `model/` 两种含义
4. 本地调试再使用 `RAGENT_MEP_MODEL_DIR` / `RAGENT_MEP_DATA_DIR`
5. 若以上均未命中，则回退到源码目录同级 `model/` / `data/`

这与此前“默认认为 `model_root=modelDir`，再拼出 `model_root/model` 和 `model_root/data`”的写法不同。

### 5.4 embedding 运行方式

当前 ragent 保留两种 embedding 模式。

第一种：外部 embedding API。

如果环境变量完整提供：

```text
EMBEDDING_MODEL
EMBEDDING_MODEL_URL
EMBEDDING_MODEL_KEY
```

则组件直接调用外部 embedding API。

第二种：本地 transformers embedding 推理。

如果没有完整外部 embedding 配置，`CustomerModel.load()` 会优先读取 `data/config/embedding.properties`，再通过 `ragent.mep_embedding_runtime.bootstrap_local_embedding_runtime()` 注入本地 embedding 函数。旧的 `model/sysconfig.properties` 仍作为兼容兜底，但新模型包不再把组件配置文件放入 `model/`。

权威测试结果显示，新目标镜像没有可用的 vLLM OpenAI embedding server 入口，但 `transformers + torch_npu` 能在 `npu:0` 上跑通 BGE-M3。因此 bge-m3 模型包默认放弃 vLLM，直接加载本地 Hugging Face 模型目录：

对应配置位于 `mep/model_packages/bge-m3/modelDir/data/config/embedding.properties`：

```text
embedding.runtime=transformers
embedding.dimensions=256
embedding.max_token_size=8192
embedding.device=npu:0
embedding.pooling=cls
embedding.normalize=true
embedding.batch_size=8
```

本地 embedding 实现按模型包中的 `1_Pooling/config.json` 使用 CLS pooling，并在截断到 `embedding.dimensions=256` 后做 normalize，保持现有 KG 向量维度一致。

`ragent.mep_embedding_runtime` 仍保留 vLLM 启动逻辑用于兼容旧包，但模型包默认走 transformers。加载模型前会自动尝试加载：

```text
/usr/local/Ascend/ascend-toolkit/set_env.sh
/usr/local/Ascend/nnal/atb/set_env.sh
```

如目标镜像路径不同，可用 `RAGENT_ASCEND_SET_ENV_SH` 指定单个脚本，或用 `RAGENT_ASCEND_ENV_SHS` 指定多个脚本。

### 5.5 本地推理能力

当前方向不再依赖组件内 vLLM 子进程。本地 BGE-M3 embedding 在组件进程内完成，减少端口占用、子进程清理和 OpenAI-compatible server 兼容性风险。

### 5.6 `data/` 自定义依赖

MEP 平台默认从组件包的 `process.py` 启动组件，所以 `process.py` 是生产入口。入口文件最开始会默认启用 strict offline 环境，设置 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、`HF_DATASETS_OFFLINE=1`、`PIP_NO_INDEX=1`，然后再执行离线依赖安装、依赖路径注入和后续 `ragent` 导入。确需排查镜像基础环境时，可显式设置 `MEP_STRICT_OFFLINE=0` 或 `RAGENT_MEP_STRICT_OFFLINE=0`。

`data/` 被视为模型包随附的只读自定义数据目录。当前组件在导入 ragent 之前会尝试把以下路径加入 Python import path：

```text
data/deps/pythonpath/
data/deps/pythonpath/<platform-tag>/
data/deps/site-packages/
data/deps/site-packages/<platform-tag>/
data/deps/python/
data/deps/python/<platform-tag>/
data/deps/wheelhouse/<platform-tag>/*.whl
data/deps/wheelhouse/*.whl
```

这用于承载目标镜像中没有的轻量 Python 依赖。`<platform-tag>` 形如 `linux-arm64-py3.9`；目标 Ascend 910B MEP 镜像当前是 `linux-arm64-py3.9`。运行时会先查找 `requirements-<platform-tag>.txt` 和 `constraints-<platform-tag>.txt`，并用匹配的 `wheelhouse/<platform-tag>/` 执行一次 `pip install --no-index`。已安装且版本一致的镜像包会被跳过；缺失的应用依赖和 native wheel 会从本地 wheelhouse 安装。

当前 transformers embedding wheelhouse 由以下脚本解析生成：

```bash
python tools/export_mep_transformers_embedding_wheelhouse.py --clean
```

它会生成 `constraints-linux-arm64-py3.9.txt`、`manifest.json` 和 `downloaded-wheels.txt`。`image-baseline-constraints-linux-arm64-py3.9.txt` 固定镜像内已验证的 `torch`、`torch_npu`、`transformers`、`tokenizers`、`numpy` 等版本，防止离线解析替换 Ascend 栈。

这段 bootstrap 逻辑位于组件包顶层的 `mep_dependency_bootstrap.py`，`process.py` 在导入 `ragent` 之前调用它。这样入口文件保持轻量，同时仍能让 `data/deps` 中的依赖影响后续导入。

如果本轮没有找到任何可加入的依赖路径，bootstrap 会清理 `RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH`，避免平台诊断读到上一轮进程留下的过期路径。

## 6. 接口契约

当前 ragent 顶层返回约定仍保持：

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

这里仍然不使用样例里的 `code/response` 或 `resultCode/result` 风格，而是维持当前 KG QA 组件既有的 `recommendResult` 契约。

### 6.1 `action=create`

组件同步执行 KG 问答，将结果写入 `{generatePath}/gen.json`，然后返回 `recommendResult.code="0"`。

异步 create 成功时，`content` 默认保持空数组，避免和平台异步查询语义冲突。

`generatePath` 优先级：

1. `data.generatePath`
2. `data.fileInfo[0].generatePath`

默认结果文件名为 `gen.json`。

### 6.2 `action=query`

理论上由 MEP 框架处理；当前 ragent 仍保留防御性兼容：

- 找到 `gen.json`：返回 `code="0"`
- 目录存在但结果文件还不存在：返回 `code="2"`
- 缺少路径或任务路径不存在：返回 `code="4"`

### 6.3 直接调试请求

没有 `action` 的直接请求继续同步返回结果：

```text
recommendResult.content=[payload]
```

只有请求中提供 `generatePath` 时才写文件；默认文件名也是 `gen.json`。

错误统一返回 `recommendResult.code="3"`，`des` 为错误信息，`content=[]`。

## 7. KG 参数解析

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

## 8. `gen.json` schema

成功结果文件格式如下：

```json
{
  "code": "0",
  "des": "success",
  "taskId": "100002455",
  "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
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

## 9. 请求示例

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
    "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
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

更多样例位于 `/Volumes/SSD1/ragent/example/mep_requests/`。

## 10. 本地模拟

### 10.1 当前代码可直接工作的本地调试方式

推荐先用装配脚本生成接近 MEP 平台的本地运行时目录：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_layout.py --model-package bge-m3

set -a
source /Volumes/SSD1/ragent/.env
set +a

python /Volumes/SSD1/ragent/.mep_build/bge-m3/runtime/component/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/sfs_create_request.json
```

装配脚本默认对 `model/`、`data/`、`meta/` 使用软链，避免复制大模型；如果需要物化目录用于离线包检查，可加 `--materialize`。物化模式会解引用源目录内部的软链，生成自包含的本地运行时目录。

如果需要生成本地交付归档，可以在物化模式下追加 archive 参数：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_layout.py \
  --model-package bge-m3 \
  --materialize \
  --archive-format zip
```

支持的归档格式为 `zip`、`tar`、`tar.gz`/`tgz`。归档内容的第一层就是 `component/`、`model/`、`data/`、`meta/`，不会额外套一层 `runtime/`。

如果显式指定 `--archive-output`，输出路径必须位于 runtime 根目录之外，并且必须是文件路径而不是已有目录；装配脚本会拒绝把归档写到 runtime 内部，避免归档过程中把自身也打入包中。装配脚本会校验 `model/` 本身是 Hugging Face 模型目录，防止误把模型文件继续套进额外子目录。

兼容调试时仍可使用显式 env override 或直接传 `model_root`：

```bash
export RAGENT_MEP_MODEL_DIR=/Volumes/SSD1/ragent/mep/model_packages/bge-m3/modelDir/model
export RAGENT_MEP_DATA_DIR=/Volumes/SSD1/ragent/mep/model_packages/bge-m3/modelDir/data
python /Volumes/SSD1/ragent/run_mep_local.py \
  --request /Volumes/SSD1/ragent/example/mep_requests/sfs_create_request.json
```

### 10.2 MEP 上传包构建

`tools/build_mep_layout.py` 用于本地 MEP 运行时仿真；真正准备平台上传目录时，使用独立的上传包构建脚本：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_upload_packages.py --model-package bge-m3
```

默认输出：

```text
/Volumes/SSD1/ragent/.mep_upload/bge-m3/
  component_package/
    config.json
    package.json
    process.py
    init.py
    mep_dependency_bootstrap.py
    pyproject.toml
    setup.py
    ragent/
  model_package/
    modelDir/
      model/
      data/
      meta/
```

组件上传包默认不包含 `run_mep_local.py`，避免把本地调试入口带到平台；确需随包检查时可加：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_upload_packages.py \
  --model-package bge-m3 \
  --include-local-runner
```

如果需要直接生成可上传归档：

```bash
python /Volumes/SSD1/ragent/tools/build_mep_upload_packages.py \
  --model-package bge-m3 \
  --archive-format zip
```

归档会分别写在 `.mep_upload/bge-m3/` 下：组件归档根目录直接是 `config.json`、`process.py`、`ragent/` 等文件；模型归档根目录直接是 `modelDir/`。手工压缩时也应保持同样结构，尤其模型包 zip 的第一层必须是 `modelDir/`，不能额外套一层 `model_package/`。

如需把两个上传归档写到其他目录，可在 `--archive-format` 基础上追加 `--archive-output-dir <dir>`。脚本会拒绝把归档写进正在打包的 `component_package/` 或 `model_package/` 内部，避免归档过程把自身也打入包中；自定义归档目录同样不能覆盖仓库根、组件源码或源模型包。

上传包构建脚本会复制真实文件而不是生成软链，并过滤 `__pycache__/`、`.pytest_cache/`、`.DS_Store`、`*.pyc`、`*.pyo`。组件包还会排除 `tests/`、`example/`、`benchmark/`、`vendor/`、`presentation/`、`MEP_platform_rule/`、`.venv/`、`.git/`。脚本会拒绝会覆盖仓库根、组件源码或源模型包的危险输出目录，并强校验 `modelDir/meta/type.mf` 非空以及 `modelDir/model` 本身直接包含 Hugging Face 模型文件。

### 10.3 参照样例的目标容器布局

后续代码对齐后，优先验证如下布局：

```text
<runtime_root>/
  component/
    config.json
    process.py
    ragent/
    ...
  model/
    config.json
    tokenizer.json
    pytorch_model.bin
    1_Pooling/
  data/
    config/
      embedding.properties
    kg/
      <kg snapshot>/
    deps/
  meta/
    ...
```

重点不是传 `model_root=<modelDir>`，而是让组件在 `component/` 下运行时，能通过父目录看到同级 `model/` 和 `data/`，并在需要时兼容平台注入的 SFS 环境变量。

## 11. 平台待确认事项

真实 MEP 平台联调时需要显式记录以下事实，完整 checklist 见 `/Volumes/SSD1/ragent/MEP_E2E_VALIDATION_PLAN.md`。

- 入口 `__file__`、`cwd`、`component/`、`model/`、`data/`、`meta/` 的实际落盘位置
- 平台是否传入 `model_root`，以及传入值的真实含义
- `MODEL_SFS`、`MODEL_OBJECT_ID`、`MODEL_ABSOLUTE_DIR`、`MODEL_RELATIVE_DIR`、`path_appendix` 的原始值和指向关系
- 模型包 `data/` 是否按 `data/kg/<snapshot_name>/` 提供 KG snapshot；如不是，需设置 `RAGENT_MEP_KG_DIR`
- 目标 vLLM Ascend 镜像是否支持 embedding / pooling runner 和 OpenAI-compatible `/v1/embeddings`
- 组件内 vLLM 子进程的启动超时、端口、资源隔离和清理限制
- `{generatePath}` 是否可写，组件自行创建目录是否被允许，写出的 `gen.json` 是否业务方可见
- 外部 LLM / rerank 环境变量、网络出口和密钥注入方式
- 业务方最终读取的 `gen.json` schema，尤其是成功字段、错误字段和是否保留 `runtime` 调试字段

## 12. 测试

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
  tests/test_mep_layout_builder.py \
  tests/test_model_package_bundle.py
```
