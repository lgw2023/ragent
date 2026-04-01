# Ragent：一个专业领域知识图谱增强的RAG框架

Ragent是一个先进的、多模态（multimodal）的检索增强生成（Retrieval-Augmented Generation, RAG）框架，专为专业领域构建高级问答系统而设计。它在向量库的基础上，又利用知识图谱（Knowledge Graph）来强化检索过程，从而提供更准确、上下文感知度更高且可追溯的答案。

## 功能特性

- **多模态文档处理**：能够处理像PDF这样的复杂文档，不仅能提取文本，还能通过集成的**MinerU**工具提取图像、表格和布局信息。
- **自动化知识图谱构建**：能自动从文本块中提取实体和关系，并支持主流格式构建结构化的知识图谱。
- **图像到文本的知识提取**：利用多模态大语言模型（如GPT-4o）生成对图像的丰富描述，这些描述随后会与周围的文本上下文融合，并嵌入到知识库中。
- **混合检索 (Hybrid Retrieval)**：结合了语义向量搜索（semantic vector search）和基于图的遍历（graph-based traversal），以检索最相关的信息，确保了语义相关性和事实准确性。
- **多跳问题解答 (Multi-Hop Question Answering)**：实现了一个问题拆解引擎（question dismantling engine），该引擎能将复杂查询分解为更简单、有序的子问题，并使用一个带记忆功能的迭代过程来推导出全面的答案。
- **完全可追溯的答案 (Fully Traceable Answers)**：所有生成的答案都会返回完整的源信息，包括指向原始文本块、文档所使用的特定图像的存储路径。
- **可插拔与可扩展 (Pluggable and Extensible)**：核心组件（如LLM模型和存储后端）被设计为可以轻松替换。

## 架构概览

Ragent的流程遵循一个清晰的多阶段过程：

1.  **数据提取与解析**：文档（如PDF）被送入`MinerU`，后者将其解析为干净的`Markdown`文本并提取出关联的图像。
2.  **分块与知识提取**：文本被分割成可管理的块。对于每个块，LLM会提取实体和关系来构建知识图谱。对于图像，多模态LLM会生成描述，然后将其与上下文结合，作为一个新的、可搜索的、链接到图像文件的文本块来处理。
3.  **存储**：文本块及其向量嵌入存储在`nano_vector_db`向量数据库中，用于语义搜索。提取的实体和关系存储在`NetworkX`图数据库中，用于结构化查询。所有数据都本地存储在指定的工作目录中。无论是向量库还是图数据库都支持其他主流格式的替换。
4.  **检索与推理**：当收到查询时，系统执行混合检索。对于复杂查询，多跳引擎会分解问题并迭代检索推理。
5.  **答案生成**：检索到的上下文（包括文本和图像引用）被送入LLM，以生成最终的、人类可读的答案，并附带所有来源引用。

## 安装与设置

### 前置要求

- Python `>=3.10`（仓库当前 `.python-version` 为 `3.13`）
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip
- 如需处理 DOCX，还需要 LibreOffice

### 1. 获取代码

```bash
unzip ragent_master.zip
cd ragent_master
```

### 2. 安装依赖

`README` 中下面的命令按当前代码入口整理过：

- 当前 `integrations.py` / `singlefile.py` 会在导入阶段直接加载 `MinerU pipeline` 相关模块，所以即使只跑 `onehop` / `multihop` / `chat`，环境里也必须具备 `MinerU` 的 `pipeline` 依赖（如 `torch`、`torchvision`、`transformers`、`doclayout_yolo`）。
- 仓库的 `pyproject.toml` 已将根依赖切换为 `mineru[pipeline]`，因此 `uv sync` 会一并安装这组依赖。
- 如果你要直接运行 `integrations.py` / `singlefile.py` 的主流程，建议至少安装 `openai` 和 `api` 两组 extra。
  这里的 `openai` extra 现在实际包含 `litellm`，用于统一适配 OpenAI-compatible / 多提供商模型调用。
- `api` 这个名字虽然偏服务端，但当前文档解析主流程里实际用到了其中的 `aiofiles` 依赖。
**使用 uv（推荐）：**

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 推荐：可直接跑当前 README 中的 parse / onehop / multihop / chat 全流程
# 其中会自动带上本地 MinerU 的 pipeline 依赖
uv sync --extra openai --extra api

# 其他可选依赖
uv sync --extra hf        # HuggingFace 本地模型
uv sync --extra ollama    # Ollama 本地模型
uv sync --extra neo4j     # Neo4j 图后端
uv sync --extra milvus    # Milvus 向量库后端
uv sync --extra faiss     # FAISS 向量库后端

# 或一次性安装全部
uv sync --all-extras
```

**使用 pip：**

```bash
python -m venv env
source env/bin/activate   # Windows: env\Scripts\activate

# 先安装随仓库附带的 MinerU 源码及 pipeline 依赖
pip install -e "./MinerU-master[pipeline]"

# 再安装当前项目及推荐 extra
pip install -e ".[openai,api]"
```


### 3. 安装 MinerU 模型

当前仓库中用于解析 PDF 的是 `MinerU`。推荐使用 `MinerU` 自带的 CLI 下载模型，而不是根目录下的 `models_download.py`。

```bash
# 推荐：下载 pipeline 模型
uv run mineru-models-download --source modelscope --model_type pipeline

# 如果你用的是 pip 虚拟环境，也可以这样执行
python -m mineru.cli.models_download --source modelscope --model_type pipeline
```

执行完成后，`MinerU` 会在用户目录下生成或更新 `~/mineru.json` 配置文件。

### 4. 安装 LibreOffice（处理 DOCX 时需要）

```bash
sudo apt update && sudo apt install libreoffice libreoffice-writer
```

### 5. 配置环境变量

在项目根目录创建 `.env` 文件。下面这些变量是当前代码路径里实际会读取到的关键配置：

```.env
# ========== LLM（必需）==========
LLM_MODEL_KEY=""
LLM_MODEL_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL="qwen3-max"
# 可选：显式指定 LiteLLM provider；不填时会自动推断
# 例如 openai / custom_openai / anthropic / openrouter / ollama
# LLM_API_PROVIDER="custom_openai"
LLM_API_TIMEOUT_SECONDS="180"
LLM_API_CLIENT_MAX_RETRIES="0"

# ========== Embedding（必需）==========
# 当前实现不会复用 LLM_API_*，而是单独读取这组变量
EMBEDDING_MODEL_KEY=""
EMBEDDING_MODEL_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBEDDING_MODEL="text-embedding-v3"
# 可选：显式指定 LiteLLM provider；不填时会自动推断
# EMBEDDING_PROVIDER="custom_openai"
EMBEDDING_DIMENSIONS="256"

# ========== Rerank（默认推荐）==========
# 当前启动检查会验证 rerank；如果不配置 rerank，请看下面的“关闭开关”
RERANK_MODEL_KEY=""
RERANK_MODEL_URL="https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
RERANK_MODEL="qwen3-rerank"

# ========== 图像模型（可选）==========
# 不配置时，图片描述会被跳过
IMAGE_MODEL_KEY=""
IMAGE_MODEL_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
IMAGE_MODEL="qwen3-vl-flash"
IMAGE_MODEL_TIMEOUT="300"

# ========== 可选开关 / 调优 ==========
MODEL_STARTUP_CHECK_ENABLED="1"
# 可选：不设置时，启动健康检查超时会自动跟随 LLM_API_TIMEOUT_SECONDS
# 若配置了图片模型，则也会参考 IMAGE_MODEL_TIMEOUT；需要更大值时可显式覆盖
# MODEL_STARTUP_CHECK_TIMEOUT_SECONDS="180"
ENABLE_RERANK="true"
num_chars_of_front="512"
num_chars_of_behind="512"
chunk_size="1024"
overlap_size="128"
RAG_INSERT_TIMEOUT_SECONDS="30"
RAG_INSERT_TIMEOUT_MAX_SECONDS="60"
RAG_INDEX_TIMEOUT_SECONDS="1800"
RAG_PROGRESS_BAR="1"
```

如果你暂时不打算接 rerank 服务，至少同时设置：

```.env
MODEL_STARTUP_CHECK_ENABLED="0"
ENABLE_RERANK="false"
```

否则当前实现会在启动检查或混合检索阶段直接因为缺少 `RERANK_*` 配置而失败。

## 核心模块指南

- **`ragent.ragent.Ragent`**：底层编排类。直接使用时，至少要提供 `embedding_func`、`llm_model_func` 和 `llm_model_name`。
- **`integrations.py`**：当前仓库的主入口封装，建议优先从这里开始：
  - `build_enhanced_md`：第一阶段，只做 PDF 解析和图片描述回写，产出最终 Markdown。
  - `index_md_to_rag`：第二阶段，只基于已生成的 Markdown 构建 RAG / KG 索引。
  - `pdf_insert`：串联执行上面两个阶段。
  - `docx_insert`：先将 DOCX 转 PDF，再走同样流程。
  - `inference_one_hop_problem`：单跳问答。
  - `inference_multi_hop_problem`：多跳问答。
- **`singlefile.py`**：当前最方便的命令行入口，支持 `parse`、`onehop`、`multihop`、`chat`。
- **`ragent/kg/`**：存储实现目录。默认使用本地 `nano_vector_db` 和 `NetworkX`。

## 快速开始

仓库已经附带一个可直接复现的样例 PDF：`example/成人高血压食养指南.pdf`。

### 1. 只生成增强 Markdown

```bash
uv run python singlefile.py parse \
  example/成人高血压食养指南.pdf \
  demo_md
```

这一步会调用 `build_enhanced_md`，在 `demo_md/txt/` 下生成：

- 最终 Markdown
- `content_list.json`
- `images/` 目录
- 每张图对应的描述 `.txt`

### 2. 继续构建知识库

```bash
uv run python singlefile.py parse \
  example/成人高血压食养指南.pdf \
  demo_md \
  demo_kg
```

如果对应 Markdown 已存在，上面的命令会自动只执行 `rag` 阶段；如果不存在，则会自动走完整 `all` 流程。

### 3. 提问

```bash
uv run python singlefile.py onehop \
  demo_kg \
  "文档推荐的限盐原则是什么？"

uv run python singlefile.py multihop \
  demo_kg \
  "比较文档中不同血压分级对应的食养建议，有哪些关键区别？"
```

当前 CLI 默认会打印较完整的检索/推理 trace，而不只是最终答案。

### 4. 连续追问（多轮 chat）

```bash
uv run python singlefile.py chat \
  demo_kg \
  demo_kg/conversation_history.json \
  "文档推荐的限盐原则是什么？"

uv run python singlefile.py chat \
  demo_kg \
  demo_kg/conversation_history.json \
  "那老人群体还有什么补充建议？" \
  graph \
  3
```

`chat` 会从本地 JSON 读取已有 `conversation_history`，把当前轮问答追加回同一个文件，并在检索时透传给底层 `QueryParam`。历史文件格式兼容 `QueryParam.conversation_history`，即：

```json
[
  {"role": "user", "content": "上一轮问题"},
  {"role": "assistant", "content": "上一轮回答"}
]
```

## Python 用法示例

### 一体化流程

```python
import asyncio
from integrations import pdf_insert, inference_one_hop_problem, inference_multi_hop_problem

PDF_FILE_PATH = "path/to/your/document.pdf"
MINERU_OUTPUT_DIR = "mineru_out"
PROJECT_DIR = "my_ragent_project"

async def main():
    await pdf_insert(PDF_FILE_PATH, MINERU_OUTPUT_DIR, PROJECT_DIR)

    answer1 = await inference_one_hop_problem(
        PROJECT_DIR,
        "文档的主要主题是什么？",
        mode="hybrid",
    )
    print(answer1)

    answer2 = await inference_multi_hop_problem(
        PROJECT_DIR,
        "比较第2节和第3节中描述的方法，它们的主要区别是什么？",
    )
    print(answer2)

if __name__ == "__main__":
    asyncio.run(main())
```

### 两阶段流程

```python
import asyncio
from integrations import build_enhanced_md, index_md_to_rag

PDF_FILE_PATH = "path/to/your/document.pdf"
MINERU_OUTPUT_DIR = "mineru_out"
PROJECT_DIR = "my_ragent_project"

async def main():
    artifacts = await build_enhanced_md(PDF_FILE_PATH, MINERU_OUTPUT_DIR)
    await index_md_to_rag(
        PDF_FILE_PATH,
        PROJECT_DIR,
        artifacts["md_path"],
        content_list_path=artifacts["content_list_path"],
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## 命令行用法（singlefile.py）

### `parse`

`singlefile.py parse` 支持自动推断处理阶段，无需手动区分 `all` / `md` / `rag`。

**自动推断规则：**

- 只传 `<mineru_output_dir>`（不传 `<project_dir>`）：执行 `md`
- 传了 `<project_dir>` 且已存在对应 md 结果：执行 `rag`
- 传了 `<project_dir>` 但不存在对应 md 结果：执行 `all`

```bash
# 单文件：仅生成 md
python singlefile.py parse SCAPTURE.pdf SCAPTURE_md

# 单文件：自动在 all / rag 之间选择
python singlefile.py parse SCAPTURE.pdf SCAPTURE_md SCAPTURE_kg

# 目录：递归处理目录下所有 PDF
python singlefile.py parse ./pdfs SCAPTURE_md
python singlefile.py parse ./pdfs SCAPTURE_md SCAPTURE_kg
```

如需手动覆盖自动推断：

```bash
python singlefile.py parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]
# stage: auto | all | md | rag

# 即使传了 <project_dir>，也可以强制只做 md
python singlefile.py parse SCAPTURE.pdf SCAPTURE_md SCAPTURE_kg md
```

### `onehop`

```bash
python singlefile.py onehop <project_dir> "<query>" [mode]
# mode: hybrid | graph
```

### `multihop`

```bash
python singlefile.py multihop <project_dir> "<query>"
```

### `chat`

```bash
python singlefile.py chat <project_dir> <history_json> "<query>" [mode] [history_turns]
# mode: hybrid | graph
```

`history_json` 不存在时会自动创建；存在时应为 `conversation_history` 原生格式（JSON 列表），或者形如 `{"conversation_history": [...]}` 的对象。

## 定制化

- **LLM 和 Embedding 模型**：可替换 `Ragent` 构造参数中的 `llm_model_func`、`embedding_func`。参考 `ragent/llm/`。
- **存储后端**：可基于 `ragent/base.py` 中的抽象基类扩展自己的向量库 / 图数据库实现。
- **提示词**：抽取、问答、拆解等提示词定义在 `ragent/prompt.py`。
