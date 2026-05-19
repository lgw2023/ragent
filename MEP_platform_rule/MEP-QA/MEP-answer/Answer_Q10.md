# 问题10：业务方最终解析的是哪个结果？

## 问题原文

业务方最终解析的是 `calc()` 返回的：

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

还是读取 SFS 上的 `generatePath/gen.json`？如果读取 `gen.json`，平台/业务方对 `gen.json` 的字段结构有没有强制要求？

---

## 回答

### 结论：按最新 MSG 异步框架文档，业务方优先解析 `action=query` 返回的 `response_content`。

最新文档说明业务侧只需要调用 MSG。组件 `calc()` 的返回值会被异步框架保存到任务记录的 `response_content`，当业务方通过 `action=query` 查询到任务完成时，框架会把这份内容放到返回体的 `respData` / `recommendResult` 中。因此实际问答 payload 需要放进 `recommendResult.content`，不能只写 SFS 文件。

`generatePath/gen.json` 仍然需要写，作为 SFS 兼容输出和排障文件；如果业务方有 SFS 访问权限，也可以读取这个文件。

---

### 详细分析

#### 1. `calc()` 返回值的作用——状态判断 + query 返回内容来源

根据 MEP 文档（[组件包 异步场景.txt](file:///d:/GitHub/xiaoyi_diet/MEP/组件包%20异步场景.txt)）中的规范，`calc()` 方法的返回值结构如下：

```python
def build_response(self, result_code, result_des):
    res_raw = {"code": str(result_code), "des": result_des, "length": 0, "content": []}
    res = {"recommendResult": res_raw}
    return res
```

旧 SFS 示例里的返回值可以是空 `content`，但最新 MSG 异步框架会保存组件 `calc()` 返回值，并在 `action=query` 完成时返回：

```json
{
    "version": "1.2",
    "meta": { ... },
    "result": {
        "code": "0",
        "des": "success",
        "length": "0",
        "content": []
    }
}
```

其中 `code` 字段的含义：
| 响应码 | 场景 | 描述 |
|--------|------|------|
| 0 | 创建/查询 | 创建任务成功 / 查询任务执行完成并成功 |
| 1 | 创建任务 | 系统忙需要重试 |
| 2 | 查询任务 | 任务正在处理中 |
| 3 | 创建/查询 | 任务创建/查询异常 |
| 4 | 查询任务 | 任务取消状态 |
| 5 | 创建任务 | 所创建任务已存在 |
| 6 | 查询任务 | 没有对应的任务 |

**关键点**：`action=create` 的即时 MSG 响应通常仍是空 `content` 的任务创建回执；组件实际执行完成后的 `calc()` 返回值需要携带 payload，这样 `action=query` 才能从 `response_content` 返回真实结果。

#### 2. 业务方获取推理结果的途径

旧 SFS 文档描述的流程仍然成立：

> 采用异步接口，模型服务与业务服务会通过SFS共享图片存储；业务请求中传入一组图片存储位置信息、相应的处理要求，以及处理后结果文件的存放位置；模型服务接受到请求后放入异步队列后台进行处理；业务服务器定期过来查询任务处理情况，**待任务处理完成后，业务服务读取结果文件内容并进行后续处理**。

组件的 `calc()` 方法中需要将推理结果写入 `generatePath/gen.json`：

```python
generatePath = fileInfo_0.get('generatePath')
# ... 执行推理 ...
result_path = os.path.join(generatePath, "gen.json")
with open(result_path, mode='w', encoding='utf-8') as f:
    json.dump(calc_res, f)
```

按最新 MSG 异步框架，业务方的完整调用链为：
1. POST `/service` action=create → MEP 入队并调用组件 `calc()`
2. 组件 `calc()` 执行推理，将结果写入 `generatePath/gen.json`，并返回 `recommendResult.content=[payload]`
3. 业务方 POST `/service` action=query 轮询状态
4. 当 query 返回 `code=0`（任务完成），业务方从 `respData[0].recommendResult.content[0]` 获取实际结果；必要时再读取 SFS 上的 `generatePath/gen.json`

#### 3. `gen.json` 的字段结构是否有强制要求？

**根据现有 MEP 文档，未发现对 `gen.json` 字段结构的强制要求。** 文档中仅规定了文件名必须为 `gen.json`，存放路径必须为 `generatePath/gen.json`，但对文件内部的 JSON 结构没有定义 schema。

这意味着 `gen.json` 的字段结构由组件开发方与业务方自行约定。实际开发中，建议与业务方协商确定 `gen.json` 的结构规范。

#### 4. 当前代码库中的问题

当前 `qwen_vllm_async_copilot` 代码库中的 `calc()` 实现（[process.py](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process.py) 和 [process_sync.py](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process_sync.py)）存在以下问题：

- **未写入 `gen.json`**：`calc()` 方法直接将推理结果放在返回值中（如 `{"code": 0, "des": "success", "response": "..."}` 或 `{"resultCode": "0000000000", "des": "success", "result": [...]}`），但**没有将结果写入 `generatePath/gen.json`**。
- **返回值格式不符合 MEP 规范**：MEP 异步场景要求 `calc()` 返回 `recommendResult` 契约；按最新 MSG 框架，完成结果应放入 `content`，否则 query 拿到的 `response_content` 为空。
- **未从 `req_Data` 中提取 `generatePath`**：当前 `calc()` 方法没有解析请求中的 `fileInfo` 字段来获取 `generatePath`，因此无法将结果写入 SFS。

如果该组件需要在 MEP 异步场景下正确运行，需要补充以下逻辑：
1. 从 `req_Data['data']['fileInfo'][0]` 中提取 `generatePath`
2. 将推理结果写入 `{generatePath}/gen.json`
3. `calc()` 返回值改为 `{"recommendResult": {"code": "0", "des": "success", "length": 1, "content": [payload]}}` 格式

---

### 总结

| 维度 | `calc()` 返回值 (`recommendResult`) | SFS 上的 `generatePath/gen.json` |
|------|--------------------------------------|----------------------------------|
| 消费者 | MEP 框架；MSG query 完成后返回给业务方 | 业务方或排障人员 |
| 用途 | 判断任务执行状态，并作为 `response_content` 承载实际结果 | 兼容 SFS 文件结果和排障 |
| 结构 | 有强制要求（code/des/length/content） | 无强制要求，由业务方与组件方约定 |
| 是否包含推理结果 | 是，放在 `content[0]` | 是 |

**业务方优先解析 MSG `action=query` 返回的 `respData[0].recommendResult.content[0]`；`generatePath/gen.json` 作为 SFS 兼容输出保留。**
