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

- Python 3.13
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 1. 获取代码

```bash
unzip ragent_master.zip
cd ragent_master
```

### 2. 安装依赖

**使用 uv（推荐）：**

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装核心依赖
uv sync

# 按需安装可选依赖（可组合）
uv sync --extra openai    # OpenAI / 兼容接口 LLM
uv sync --extra hf        # HuggingFace 本地模型（torch + transformers）
uv sync --extra ollama    # Ollama 本地模型
uv sync --extra api       # FastAPI 服务端
uv sync --extra neo4j     # Neo4j 知识图谱后端
uv sync --extra milvus    # Milvus 向量数据库后端
uv sync --extra faiss     # FAISS 向量数据库后端

# 或一次性安装全部
uv sync --all-extras
```

**使用 pip：**

```bash
python -m venv env
source env/bin/activate   # Windows: env\Scripts\activate

pip install -e .
pip install -e ".[openai,api]"   # 安装所需可选依赖
```

### 3. 安装 MinerU 模型

集成的`MinerU`工具需要本地模型来进行文档解析，运行以下脚本下载：

```bash
python models_download.py
```

这将下载必要的模型，并在主目录中创建`mineru.json`配置文件。

### 4. 安装 LibreOffice（处理 DOCX 时需要）

```bash
sudo apt update && sudo apt install libreoffice libreoffice-writer
```

### 5. 配置环境变量

在项目根目录创建`.env`文件：

```.env
# LLM API 密钥
LLM_API_KEY="sk-..."

# 多模态模型（图像分析）配置
IMAGE_MODEL_KEY="your-vlm-api-key"
IMAGE_MODEL_URL="https://api.example.com/v1/chat/completions"
IMAGE_MODEL="gpt-4o"

# 图像描述的上下文窗口大小
num_chars_of_front=500
num_chars_of_behind=500
```

## 核心模块指南

-   **`ragent.ragent.Ragent`**：主要的编排类。它通过LLM/嵌入函数和工作目录进行初始化。其`ainsert`和`aquery`方法是与框架交互的主要入口点。
-   **`integrations.py`**：主要的应用程序逻辑文件，包含使用`Ragent`框架的实际示例：
    -   `process_image_file`：单张图片的提取流程，使用多模态模型生成描述后将文本数据插入Ragent。
    -   `pdf_insert`：完整的PDF处理流程，使用`MinerU`解析并将文本和图像数据插入Ragent。
    -   `docx_insert`：完整的DOCX处理流程，先用`libreoffice`转换为PDF，再通过`MinerU`解析插入Ragent。
    -   `inference_one_hop_problem`：处理简单、直接问题的函数。
    -   `inference_multi_hop_problem`：通过将复杂问题拆解为子问题来解决多跳推理的函数。
-   **`ragent.operate.Operate`**：负责知识提取，使用LLM提示识别和结构化文本中的实体和关系。
-   **`ragent/kg/`**：数据存储的实现目录。默认使用`nano_vector_db_impl.py`处理向量、`networkx_impl.py`处理图，所有数据本地存储。

## 用法示例

以下示例演示了一个完整的工作流程：处理一个PDF，询问一个简单问题，以及询问一个复杂的多跳问题。

```python
import asyncio
from integrations import pdf_insert, inference_one_hop_problem, inference_multi_hop_problem

PDF_FILE_PATH = "path/to/your/document.pdf"
MINERU_OUTPUT_DIR = "mineru_out"   # 存储解析结果的目录
PROJECT_DIR = "my_ragent_project"  # 存储知识库的目录

async def main():
    # 1. 将PDF文档提取到知识库中
    print("开始提取PDF...")
    await pdf_insert(PDF_FILE_PATH, MINERU_OUTPUT_DIR, PROJECT_DIR)
    print("PDF提取完成。")

    # 2. 问一个简单的单跳问题
    print("\n--- 询问一个简单问题 ---")
    simple_query = "文档的主要主题是什么？"
    simple_answer = await inference_one_hop_problem(PROJECT_DIR, simple_query, mode="hybrid")
    print(f"查询: {simple_query}")
    print(f"答案: {simple_answer}")

    # 3. 问一个复杂的多跳问题
    print("\n--- 询问一个多跳问题 ---")
    complex_query = "比较第2节和第3节中描述的方法，它们的主要区别是什么？"
    complex_answer = await inference_multi_hop_problem(PROJECT_DIR, complex_query)
    print(f"查询: {complex_query}")
    print(f"答案: {complex_answer}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 命令行用法（singlefile.py）

`singlefile.py parse` 支持自动推断处理阶段，无需手动区分 `all/md/rag`。

**自动推断规则：**
- 只传 `<mineru_output_dir>`（不传 `<project_dir>`）：执行 `md`
- 传了 `<project_dir>` 且已存在对应 md 结果：执行 `rag`
- 传了 `<project_dir>` 但不存在对应 md 结果：执行 `all`

```bash
# 单文件：仅生成 md
python singlefile.py parse SCAPTURE.pdf SCAPTURE_md

# 单文件：自动在 all/rag 之间选择
python singlefile.py parse SCAPTURE.pdf SCAPTURE_md SCAPTURE_kg

# 目录：递归处理目录下所有 PDF
python singlefile.py parse ./pdfs SCAPTURE_md
python singlefile.py parse ./pdfs SCAPTURE_md SCAPTURE_kg
```

如需手动覆盖自动推断：

```bash
python singlefile.py parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]
# stage: auto | all | md | rag
```

## 定制化

-   **LLM和嵌入模型**：LLM和嵌入模型作为函数传递给`Ragent`的构造函数，可以通过提供符合所需签名的自定义函数来替换。参见`ragent/llm/`（如`ollama.py`、`hf.py`）。
-   **存储后端**：存储层基于`ragent/base.py`中定义的抽象基类，可通过子类化相应基类并更新`Ragent`类来部署自己的存储后端（如Milvus、Neo4j等）。
-   **提示**：所有用于提取、问答和推理的提示都在`ragent/prompt.py`中定义，可修改以适应特定领域或任务。
