# Q1: Python 组件包运行时，平台是如何实例化入口类的？

## 问题回顾

当前组件入口配置为：

```json
{
  "main_file": "process",
  "main_class": "CustomerModel"
}
```

平台实际调用的是 `CustomerModel()` 无参构造，还是 `CustomerModel(gpu_id=..., model_root=...)` 带参构造？如果会传 `model_root`，它的值具体是什么路径？

---

## 回答

### 结论：平台会传参数，调用方式为带参构造

根据代码库中的证据，**平台实例化入口类时会传入 `gpu_id` 和 `model_root` 两个参数**，即：

```python
MyApplication(gpu_id=..., model_root=...)
```

而非无参调用 `MyApplication()`。

---

### 证据链

#### 1. 本项目入口类的构造函数签名

本项目中有三个入口类，它们的 `__init__` 均声明了 `gpu_id` 和 `model_root` 参数：

- [process_sync.py:140](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process_sync.py#L140)（当前 config.json 指定的入口）：

```python
class MyApplication:
    def __init__(self, gpu_id=None, model_root=None):
```

- [process.py](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process.py) 中签名一致。

- [application.py:228](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/application.py#L228)（框架层类）：

```python
class PyMepApplication:
    def __init__(self, gpu_id=None, model_root=None):
        LOGGER.info("Unused param: gpu_id=%s", gpu_id)
        self.server = create_inference_server(model_root)
```

三个类都声明了相同的参数签名，且设置了默认值 `None`，说明设计意图是**平台会传入这两个参数**，默认值仅为兼容不传参的情况。

#### 2. `model_root` 的实际使用方式

框架层 `PyMepApplication` **实际使用了 `model_root`**，将其传入 `create_inference_server(model_root)` 创建推理服务器。在 [application.py:152-158](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/application.py#L152-L158) 中：

```python
def create_models_from_repository(model_root) -> Dict[str, ModelType]:
    repo_folder = model_root if model_root else MODEL_DIR
    model_dirs = [os.path.join(repo_folder, d) for d in os.listdir(repo_folder)]
```

当 `model_root` 非空时使用它，否则回退到 `MODEL_DIR`（即 `{ROOT_DIR}/model`）。

#### 3. 本项目 `MyApplication` 对 `model_root` 的态度

本项目的 `MyApplication`（process_sync.py）**忽略了 `model_root` 参数**，而是通过环境变量自行构建模型路径：

```python
tmp_str = os.environ.get("MODEL_SFS", "{\"sfsBasePath\":\"aaaa\"}")
tmp_json = json.loads(tmp_str)
process_model_base = tmp_json["sfsBasePath"] + "/" + os.environ.get("MODEL_OBJECT_ID", "") + "/model"
model_path = process_model_base + "/" + os.environ.get('path_appendix', "")
```

这说明在 SFS 场景下，`model_root` 可能不可靠或为空，组件需要通过环境变量自行定位模型。

---

### `gpu_id` 和 `model_root` 的含义

| 参数 | 含义 | 本项目是否使用 |
|------|------|----------------|
| `gpu_id` | 平台传入的 GPU 卡号标识 | ❌ 未使用（框架层标注为 "Unused param"） |
| `model_root` | 平台传入的容器内模型包路径 | ❌ 本项目忽略，通过环境变量自行构建 |

### `model_root` 的值

根据代码推断，`model_root` 的值取决于部署场景：

- **非 SFS 场景**：`model_root` 应为 `{ROOT_DIR}/model`，即组件包同级目录下的 `model/` 子目录。容器内目录结构为：
  ```
  /component/process.py
  /model/...
  /data/...
  ```
- **SFS 场景**：`model_root` 可能为空或不准确，组件需要通过环境变量 `MODEL_SFS` + `MODEL_OBJECT_ID` + `path_appendix` 自行构建路径，格式为：
  ```
  {sfsBasePath}/{MODEL_OBJECT_ID}/model/{path_appendix}
  ```

---

### 与 MEP 官方文档的差异

| 对比项 | MEP 官方文档示例 | 本项目实际实现 |
|--------|------------------|----------------|
| 入口类名 | `CustomerModel` | `MyApplication` |
| `__init__` 参数 | 无参数 | `gpu_id=None, model_root=None` |
| 模型路径获取 | `os.path.dirname(__file__)` 的父目录下 `model/` | 环境变量 `MODEL_SFS` + `MODEL_OBJECT_ID` + `path_appendix` |

**MEP 官方文档中的示例代码 `CustomerModel` 的 `__init__` 没有接收任何参数**，模型路径通过 `os.path` 相对路径计算。但本项目代码和框架层代码都明确声明了 `gpu_id` 和 `model_root` 参数，说明平台实际运行时会传入这两个参数。

---

### 不确定之处

尽管从代码可以推断平台会传参，但**MEP 官方文档中没有明确说明平台实例化入口类时是否传参以及传什么参数**。文档只说了"容器通过 config.json 找到 process.py，然后顺序调用 CustomerModel 类的 load()、calc() 方法"，对构造函数的调用方式未做描述。

因此，**建议向 MEP 平台同事确认以下问题**：

1. 平台实例化入口类时，具体传入的 `gpu_id` 和 `model_root` 的值是什么？
2. 在 SFS 场景下，`model_root` 是否为空？是否需要依赖环境变量来定位模型？
3. `gpu_id` 的格式是什么？是整数索引还是字符串标识？
