# Q8: 外部业务方标准调用链是什么？

## 结论

**是异步调用链，业务方不是直接同步拿 `calc()` 返回体。** 标准调用链如下：

```
1. 业务方 POST /service action=create
2. MEP 平台入队并调用组件 calc()
3. 组件写 generatePath/gen.json
4. 业务方 POST /service action=query 轮询状态
5. 业务方读取 SFS 上的 gen.json
```

## 依据

### 1. MEP 官方文档明确描述了异步流程

MEP 异步场景组件包接口说明文档（3.1 接口描述）原文：

> 采用异步接口，模型服务与业务服务会通过 SFS 共享图片存储；业务请求中传入一组图片存储位置信息、相应的处理要求，以及处理后结果文件的存放位置；**模型服务接受到请求后放入异步队列后台进行处理；业务服务器定期过来查询任务处理情况，待任务处理完成后，业务服务读取结果文件内容并进行后续处理。**

### 2. 接口设计印证了异步模式

MEP 定义了两种 action：

| action | 用途 | 说明 |
|--------|------|------|
| `create` | 创建任务 | 业务方提交任务，携带 `fileInfo`（含 sourcePath、generatePath 等） |
| `query` | 查询任务 | 业务方轮询任务状态，只需 `taskId` 和 `basePath`，不需要 `fileInfo` |

响应码也区分了两种场景的含义：
- **code=0**：create 时表示任务创建成功；query 时表示任务执行完成并成功
- **code=2**：query 时表示任务正在处理中（业务方需继续轮询）
- **code=3**：create/query 时均表示异常

### 3. 代码库 process.py 的实现印证了这一点

`calc()` 方法返回的是状态码，而非业务数据：

```python
# process.py calc() 返回格式
return {
    'code': 0,
    'des': 'success',
    'response': response.choices[0].message.content
}
```

而 MEP 框架会将 `calc()` 返回值封装为 `recommendResult` 格式返回给业务方：

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

业务数据本身则由组件写入 SFS 的 `{generatePath}/gen.json` 文件中，业务方通过 query 确认任务完成后，自行从 SFS 读取该文件。

### 4. 完整调用时序

```
业务方                    MEP平台                   组件(CustomerModel)
  |                         |                         |
  |-- POST /service ------->|                         |
  |   action=create         |                         |
  |   taskId, basePath,     |                         |
  |   fileInfo(含           |                         |
  |   sourcePath,           |                         |
  |   generatePath)         |                         |
  |                         |                         |
  |<-- {code:0,des:success}-|  (任务创建成功)          |
  |                         |                         |
  |                         |-- calc(req_Data) ------->|
  |                         |                         |-- 执行推理
  |                         |                         |-- 写 generatePath/gen.json
  |                         |<-- {code:0,...} ---------|
  |                         |                         |
  |-- POST /service ------->|                         |
  |   action=query          |                         |
  |   taskId                |                         |
  |                         |                         |
  |<-- {code:2,des:处理中}--|  (任务仍在处理)          |
  |                         |                         |
  |-- POST /service ------->|                         |
  |   action=query          |                         |
  |                         |                         |
  |<-- {code:0,des:success}-|  (任务完成)             |
  |                         |                         |
  |-- 读取 SFS 上的 -------->|                         |
  |   generatePath/gen.json |                         |
  |                         |                         |
```

### 5. 补充说明

- `calc()` 的返回值是给 MEP 框架的状态反馈，不是直接给业务方的业务数据。
- 业务方最终解析的是 SFS 上的 `gen.json` 文件内容，而非 `calc()` 返回体中的 `recommendResult`。
- `action=query` 由 MEP 框架处理（根据任务状态返回响应码），不会打到组件的 `calc()` 方法。
