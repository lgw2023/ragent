# 问题2：组件包和模型包在容器内的真实解压/挂载路径是什么？

## 结论

根据代码库和MEP文档的综合分析，容器内的真实路径结构**更接近第二种**，即：

```text
/component/process.py
/model/<MODEL_OBJECT_ID>/model/...
/data/...
```

但更完整的目录结构如下：

```text
/
├── component/              # 组件包解压目录（process.py 所在目录）
│   ├── config.json
│   ├── process.py
│   └── ...
├── model/                  # 模型包解压根目录
│   └── <MODEL_OBJECT_ID>/
│       └── model/          # 实际模型文件（权重、config.json 等）
├── data/                   # 模型包 data 目录
├── log/                    # 日志目录
├── service/                # 平台服务目录
└── temp/                   # 临时目录
```

## 证据来源

### 1. 代码中的路径获取方式

MEP官方组件包开发示例（[3.3 代码组件包](MEP/3.3%20代码组件包%20WIKI2021101206391.txt)）中明确给出了路径获取方式：

```python
currentdir = os.path.dirname(__file__)           # → /component/
parentdir = os.path.abspath(os.path.join(currentdir, os.pardir))  # → /
model_path = os.path.join(parentdir, "model")    # → /model/
data_path = os.path.join(parentdir, "data")      # → /data/
```

这表明组件包解压在 `/component/` 下，而 `model/` 和 `data/` 是其同级目录（即容器根目录下）。

### 2. `__init__.py` 中的目录结构定义

[__init__.py](qwen_vllm_async_copilot/__init__.py#L77-L100) 中有明确的注释和代码：

```python
# MEP服务根目录结构
# ├── component
# ├── data
# ├── log
# ├── model
# ├── service
# ├── temp

COMPONENT_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(COMPONENT_DIR)
MODEL_DIR = os.path.join(ROOT_DIR, "model")
DATA_DIR = os.path.join(ROOT_DIR, "data")
```

### 3. 模型路径的拼接方式（关键）

当前项目（vLLM异步组件）**并未使用**上述 `parentdir + "model"` 的方式，而是通过环境变量拼接 SFS 路径。[process.py](qwen_vllm_async_copilot/process.py#L146-L149) 中：

```python
tmp_str = os.environ.get("MODEL_SFS", "{\"sfsBasePath\":\"aaaa\"}")
tmp_json = json.loads(tmp_str)
process_model_base = tmp_json["sfsBasePath"] + "/" + os.environ.get("MODEL_OBJECT_ID", "") + "/model"
model_path = process_model_base + "/" + os.environ.get('path_appendix', "")
```

最终路径公式为：

```text
model_path = {sfsBasePath} / {MODEL_OBJECT_ID} / model / {path_appendix}
```

这说明模型文件**不是**直接放在 `/model/` 下，而是 `/model/<MODEL_OBJECT_ID>/model/` 下，中间多了一层 `MODEL_OBJECT_ID` 目录。

### 4. `application.py` 中的路径解析

[application.py](qwen_vllm_async_copilot/application.py#L180) 中也确认了同样的逻辑：

```python
model_dir = MODEL_ABSOLUTE_DIR if MODEL_ABSOLUTE_DIR else SFS_MODEL_DIR
```

其中 `SFS_MODEL_DIR` 在 `__init__.py` 中定义为：

```python
SFS_MODEL_BASE_DIR = os.path.join(SFS_INFO['sfsBasePath'], os.getenv('MODEL_OBJECT_ID'))
SFS_MODEL_DIR = os.path.join(SFS_MODEL_BASE_DIR, MODEL_RELATIVE_DIR)
```

### 5. MEP文档中模型包的打包结构

[模型包及pipeline部署.txt](MEP/模型包及pipeline部署.txt) 中描述了模型包的打包规范：

```text
xx_xx.zip
└── modelDir/          # 名称固定，不可修改
    ├── meta/
    │   └── type.mf
    ├── model/         # 真正的模型文件
    └── data/          # 可选
```

上传后平台会将 `modelDir` 解压到 `/model/<MODEL_OBJECT_ID>/` 下，因此最终模型文件位于 `/model/<MODEL_OBJECT_ID>/model/`。

## 总结

| 路径 | 说明 |
|------|------|
| `/component/process.py` | 组件包入口文件 |
| `/model/<MODEL_OBJECT_ID>/model/` | 模型包实际文件（权重、config.json等） |
| `/model/<MODEL_OBJECT_ID>/data/` | 模型包中的数据文件（可选） |
| `/data/` | 顶层data目录 |
| `/log/` | 日志目录 |

**注意**：`sfsBasePath` 的具体值取决于平台环境变量 `MODEL_SFS` 的注入。在当前代码中，`sfsBasePath` 可能指向 SFS 共享存储的某个挂载点（如 `/sfs/model`），而非容器根目录下的 `/model`。因此完整的模型路径可能是：

```text
# SFS 模式（当前 process.py 使用的方式）
{sfsBasePath}/{MODEL_OBJECT_ID}/model/{path_appendix}
# 例如：/sfs/model/abc123def456/model/

# 传统模式（MEP官方示例的方式）
/model/{MODEL_OBJECT_ID}/model/
```

两种路径获取方式在代码中并存，具体使用哪种取决于是否设置了 `MODEL_SFS` 环境变量。当前 `config.json` 指定的入口类 `MyApplication` 使用的是 SFS 模式。
