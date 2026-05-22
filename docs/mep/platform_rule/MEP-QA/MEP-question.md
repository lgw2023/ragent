请帮忙向 MEP 平台同事确认以下问题：

1. Python 组件包运行时，平台是如何实例化入口类的？

当前组件入口是：

```json
{
  "main_file": "process",
  "main_class": "CustomerModel"
}
```

平台实际是调用：

```python
CustomerModel()
```

还是会传参数，例如：

```python
CustomerModel(gpu_id=..., model_root=...)
```

如果会传 `model_root`，它的值具体是什么路径？

2. 组件包和模型包在容器内的真实解压/挂载路径是什么？

请确认运行时类似下面哪一种：

```text
/component/process.py
/model/...
/data/...
```

还是：

```text
/component/process.py
/model/<MODEL_OBJECT_ID>/model/...
/data/...
```

或者其他路径。最好能提供容器内 `pwd`、`ls /`、`ls /component`、`ls /model`、`ls /data` 的实际结果。

3. 平台是否会注入这些模型路径相关环境变量？

请确认是否有：

```bash
MODEL_SFS
MODEL_OBJECT_ID
path_appendix
MODEL_ABSOLUTE_DIR
```

如果有，请给出实际格式示例。特别是 `MODEL_SFS` 是否类似：

```json
{"sfsBasePath":"/some/sfs/path"}
```

4. 对 Python 异步组件，`load()` 和 `calc(req_Data)` 的调用顺序是否固定？

是否一定是：

```text
实例化 CustomerModel -> 调用 load() 一次 -> 多次调用 calc(req_Data)
```

还是有些模板会只调用构造函数和 `calc()`，不调用 `load()`？

5. vLLM 镜像运行方式是什么？

请确认目标镜像内是否已经安装：

```bash
vllm
vllm-ascend
```

以及平台推荐启动方式是：

```bash
vllm serve ...
```

还是：

```bash
python -m vllm.entrypoints.openai.api_server ...
```

6. 平台是否允许组件代码在 `load()` 或构造函数中自己拉起 vLLM 子进程？

也就是允许组件内执行：

```python
subprocess.Popen([...vllm...])
```

并监听本地端口，例如 `127.0.0.1:xxxx` 吗？

7. SFS 异步请求里的 `basePath` 和 `generatePath` 在组件容器内是否一定可写？

组件会把结果写到：

```text
{generatePath}/gen.json
```

请确认这个路径在 `calc()` 执行时已经存在，还是组件需要自己 `mkdir -p generatePath`。

8. 外部业务方标准调用链是什么？

请确认是否是：

```text
业务方 POST /service action=create
MEP 平台入队并调用组件 calc()
组件写 generatePath/gen.json
业务方 POST /service action=query 轮询状态
业务方读取 gen.json
```

还是业务方直接同步拿 `calc()` 返回体。

9. `action=query` 会不会打到组件的 `calc()`？

文档看起来 `query` 可能由 MEP 框架处理，不一定进入组件。请确认真实行为。

10. 业务方最终解析的是哪个结果？

是解析 `calc()` 返回的：

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

还是读取 SFS 上的：

```text
generatePath/gen.json
```

如果读取 `gen.json`，平台/业务方对 `gen.json` 的字段结构有没有强制要求？