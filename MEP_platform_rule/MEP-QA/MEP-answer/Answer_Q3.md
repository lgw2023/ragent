# 问题3：平台是否会注入模型路径相关环境变量？

## 结论

**是的，平台会注入这些模型路径相关环境变量。** 代码库中多处读取并依赖这些环境变量，可以确认它们由 MEP 平台在容器启动时注入。

---

## 四个环境变量的详细说明

### 1. `MODEL_SFS`

- **格式**：JSON 字符串，至少包含 `sfsBasePath` 字段
- **示例值**：`{"sfsBasePath":"/sfs/model"}`
- **代码中的使用**：

```python
# process.py / process_sync.py (第146-147行)
tmp_str = os.environ.get("MODEL_SFS", "{\"sfsBasePath\":\"aaaa\"}")
tmp_json = json.loads(tmp_str)
# 然后通过 tmp_json["sfsBasePath"] 获取共享存储根路径
```

```python
# __init__.py (第95-100行)
if os.getenv('MODEL_SFS') and os.getenv('MODEL_OBJECT_ID'):
    SFS_INFO = json.loads(os.getenv('MODEL_SFS'))
    SFS_MODEL_BASE_DIR = os.path.join(
        SFS_INFO['sfsBasePath'],
        os.getenv('MODEL_OBJECT_ID')
    )
```

### 2. `MODEL_OBJECT_ID`

- **格式**：字符串，模型对象 ID（目录名）
- **示例值**：`abc123def456`
- **代码中的使用**：与 `MODEL_SFS` 的 `sfsBasePath` 拼接，构成模型基础路径

```python
# process.py / process_sync.py (第148行)
process_model_base = tmp_json["sfsBasePath"] + "/" + os.environ.get("MODEL_OBJECT_ID", "") + "/model"
```

### 3. `path_appendix`

- **格式**：字符串，模型子目录后缀（可为空）
- **示例值**：空字符串 `""` 或 `"qwen3_vl"`
- **代码中的使用**：拼在模型路径末尾，用于定位模型权重在更深子目录的情况

```python
# process.py / process_sync.py (第149行)
model_path = process_model_base + "/" + os.environ.get('path_appendix', "")
```

### 4. `MODEL_ABSOLUTE_DIR`

- **格式**：字符串，模型绝对路径
- **示例值**：`/data/model`
- **代码中的使用**：优先级高于 SFS 拼接路径，如果设置了此变量则直接使用

```python
# __init__.py (第120行)
MODEL_ABSOLUTE_DIR = getenv_or_default('MODEL_ABSOLUTE_DIR', '')

# application.py (第180行)
model_dir = MODEL_ABSOLUTE_DIR if MODEL_ABSOLUTE_DIR else SFS_MODEL_DIR
```

---

## 路径拼接公式

代码中存在两种路径拼接方式，对应两种运行模式：

### 方式一：子进程模式（process.py / process_sync.py）

```
model_path = {sfsBasePath} / {MODEL_OBJECT_ID} / model / {path_appendix}
```

例如：`/sfs/model/abc123def456/model/qwen3_vl`

### 方式二：内嵌引擎模式（__init__.py + application.py）

```
SFS_MODEL_BASE_DIR = {sfsBasePath} / {MODEL_OBJECT_ID}
SFS_MODEL_DIR = SFS_MODEL_BASE_DIR / {MODEL_RELATIVE_DIR}
model_dir = MODEL_ABSOLUTE_DIR（优先） 或 SFS_MODEL_DIR
```

如果 `MODEL_ABSOLUTE_DIR` 有值，则直接使用它，不再走 SFS 拼接逻辑。

---

## 不确定的部分

- **`MODEL_SFS` 的 JSON 中是否还有除 `sfsBasePath` 之外的其他字段**：代码中只读取了 `sfsBasePath`，无法确认平台是否注入了其他字段。
- **这些环境变量的实际值**：代码中的默认值（如 `{"sfsBasePath":"aaaa"}`）明显是占位符，实际值取决于平台运行时注入。MEP 目录下的官方文档中未找到对这些环境变量的明确说明，无法给出平台侧的真实示例值。

---

## 信息来源

以上结论均来自代码库中的实际代码逻辑，主要文件：
- `process.py` / `process_sync.py`：子进程模式的路径拼接
- `__init__.py`：全局环境变量定义
- `application.py`：内嵌引擎模式的路径解析
- `utils/nsp/get_multimodel_data.py`：NSP 工具中的路径解析
- `README.md`：项目文档中的环境变量汇总表
