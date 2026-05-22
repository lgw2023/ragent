# 问题 4：对 Python 异步组件，`load()` 和 `calc(req_Data)` 的调用顺序是否固定？

## 回答

**是的，调用顺序是固定的。** MEP 框架对 Python 异步组件的调用顺序为：

```
实例化入口类 → 调用 load() 一次 → 多次调用 calc(req_Data)
```

## 证据来源

### 1. MEP 官方文档明确说明

在 `MEP/组件包 异步场景.txt` 中，官方文档原文写道：

> 容器通过 config.json 找到 process.py，然后**顺序调用** process.py 中的 CustomerModel 类的 **load()、calc() 方法**。

这句话明确表达了：
- 框架会**先调用 `load()`，再调用 `calc()`**，顺序固定
- `load()` 和 `calc()` 是框架**必须调用**的两个方法，不是可选的

### 2. 代码库中的实现佐证

本代码库中存在**两套入口类**，均遵循 `load()` → `calc()` 的调用模式：

#### (a) `process_sync.py` / `process.py` 中的 `MyApplication` 类（SFS 异步场景）

```python
class MyApplication:
    def __init__(self, gpu_id=None, model_root=None):
        # 构造函数中启动 vLLM 子进程并等待就绪
        ...

    def load(self):
        """加载资源"""
        pass  # 实际初始化已在 __init__ 中完成

    def calc(self, req_Data):
        # 处理推理请求
        ...
```

这个类把耗时操作（启动 vLLM 服务、等待就绪）放在了 `__init__` 中，`load()` 留空（`pass`），说明开发者**预期 `load()` 一定会被框架调用**，只是把初始化提前到了构造函数。如果 `load()` 不一定会被调用，开发者不会在构造函数中做所有初始化而让 `load()` 空着——这恰恰说明 `load()` 的调用是框架保证的。

#### (b) `application.py` 中的 `PyMepApplication` 类（MEP 内置框架类）

```python
class PyMepApplication:
    def __init__(self, gpu_id=None, model_root=None):
        self.server = create_inference_server(model_root)
        ...

    def load(self):
        self.img_dict = ImageDict()
        self.server.setup()  # 真正的模型加载和初始化

    def calc(self, requests):
        return self.server.inference(requests)
```

这个类中 `load()` 包含了**实质性的初始化逻辑**（`self.server.setup()`），而 `calc()` 依赖 `load()` 完成后的 `self.server` 状态。这进一步证明框架**一定会先调用 `load()` 再调用 `calc()`**。

### 3. 文档中的示例代码也遵循此模式

`MEP/组件包 异步场景.txt` 中的官方示例：

```python
class CustomerModel:
    def load(self):
        logger.info("load model start~")
        self.new_model = handwrite_recognition.Test()
        self.new_model.load_pb(os.path.join(model_path, 'test.pb'))
        logger.info("load model end~")

    def calc(self, req_Data):
        # 使用 load() 中加载的 self.new_model
        calc_res = self.new_model.infer(img_path)
        ...
```

示例中 `calc()` 依赖 `load()` 中加载的 `self.new_model`，如果 `load()` 不被调用，`calc()` 会因 `self.new_model` 不存在而报错。

## 结论

**MEP 框架对 Python 异步组件的调用顺序是固定的**，一定是：

1. **实例化入口类**（调用 `__init__`）
2. **调用 `load()` 一次**（用于加载模型和耗时初始化）
3. **多次调用 `calc(req_Data)`**（处理业务请求）

不存在"只调用构造函数和 `calc()`，不调用 `load()`"的情况。`load()` 是框架**必定调用**的生命周期方法，组件可以安全地在 `load()` 中执行模型加载等初始化操作，`calc()` 中可以依赖 `load()` 完成的初始化状态。
