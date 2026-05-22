# 问题9：`action=query` 会不会打到组件的 `calc()`？

## 问题原文

> `action=query` 会不会打到组件的 `calc()`？文档看起来 `query` 可能由 MEP 框架处理，不一定进入组件。请确认真实行为。

## 结论

**`action=query` 大概率不会打到组件的 `calc()` 方法，而是由 MEP 异步框架（SFS 异步框架 / MSG 消息网关）自行处理。** 但需注意：现有文档中**没有显式声明**这一行为，属于文档缺失点。

## 证据与分析

### 1. 代码库中无任何 action 分派逻辑

在整个 `qwen_vllm_async_copilot` 代码库中，**没有任何 `.py` 文件包含对 `action` 字段的读取、判断或分派逻辑**。所有 `calc()` 实现均不检查 `action`：

- [process.py:285-347](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process.py#L285-L347)：直接从 `data` 中取 `messages`，不检查 `action`
- [process_sync.py:323-395](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process_sync.py#L323-L395)：使用 `self.build_messages(data)` 构建消息，同样不检查 `action`
- [application.py:270-273](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/application.py#L270-L273)：直接委托给 `InferenceServer.inference()`，无 action 判断

如果 `action=query` 会进入 `calc()`，那么代码中应该有类似 `if action == "query": ...` 的分支逻辑，但完全没有。

### 2. MEP 文档中 query 的响应码是框架级状态码

MEP 异步场景接口说明文档中，`action=query` 的响应码定义为：

| 响应码 | 场景 | 描述 |
|--------|------|------|
| 0 | 查询任务 | 任务执行完成并成功 |
| 2 | 查询任务 | 任务正在处理中 |
| 3 | 查询任务 | 任务查询结束，异常 |
| 4 | 查询任务 | 没有对应的任务 |

这些状态码描述的是**异步任务队列的生命周期状态**（处理中/完成/异常/不存在），由框架的任务队列管理，而非组件业务逻辑产生。组件的 `calc()` 返回的是业务推理结果，不可能返回"任务正在处理中"这种状态。

### 3. MEP 示例代码只处理 create 场景

MEP 组件包开发指南中的 `calc()` 示例代码只展示了处理 `fileInfo`、执行推理、存储结果的流程，没有任何基于 `action` 字段的分支判断：

```python
def calc(self, req_Data):
    data = req_Data.get('data')
    fileInfo = data.get('fileInfo')
    fileInfo_0 = fileInfo[0]
    sourceImage = fileInfo_0.get('sourceImage')
    # ... 执行推理 ...
    calc_res = self.new_model.infer(img_path)
    # ... 结果存储到sfs ...
```

### 4. 架构层面：请求经过 MSG 消息网关

文档指出接口样例是"业务 --> MSG（消息网关）"的参数说明。MSG 作为网关层，有能力在将请求转发到容器之前，对 `action=query` 的请求进行拦截并直接查询任务队列状态返回，无需转发到组件的 `calc()` 方法。

### 5. 异步场景的设计意图

MEP 异步场景的流程描述为：

> "模型服务接受到请求后放入**异步队列**后台进行处理；业务服务器定期过来**查询任务处理情况**，待任务处理完成后，业务服务读取结果文件内容并进行后续处理。"

查询是针对异步队列中任务状态的查询，属于框架层面的任务管理，而非业务推理逻辑。

## 不确定性说明

虽然从多方面证据推断 `action=query` 不会打到 `calc()`，但以下因素导致无法 100% 确认：

1. **文档未显式声明**：现有 MEP 文档没有明确说明 query 请求的处理路径
2. **未查阅框架源码**：MEP Python 异步框架（`python-async-framework`）的源码可能包含明确的拦截逻辑，但本次未获取到
3. **建议查阅**：MEP 文档中提到的子文档"MEP Python异步框架容器接口文档"可能包含框架对 query 请求的拦截逻辑说明

## 对组件开发的影响

基于当前分析，组件开发者**无需在 `calc()` 中处理 `action=query`**。`calc()` 只需关注 `action=create` 的业务推理请求即可。如果未来确认 query 确实会进入 `calc()`，则需要添加 action 判断逻辑。
