# MEP 离线全链路验证说明

更新时间：2026-05-23

本文用于指导后续在修改 ragent 代码、MEP 组件包、模型包或 Ascend/vLLM 镜像后，重复验证本项目在 MEP 离线运行环境中的可交付性。目标不是只让某个样例请求通过，而是确认同一套组件包和模型包上传到 MEP 平台后，能够在离线镜像中完成依赖构建、embedding 服务拉起、知识图谱检索和服务接口调用。

## 1. 任务目的

本任务验证的是“MEP 交付形态是否可用”，不是单次本地调试。

核心目标：

- 将本机项目代码和离线资产迁移到 Ascend/NPU 服务器后，用目标 MEP 镜像验证完整离线链路。
- 明确组件包 `component` 和模型包 `qwen3-embedding-4b` 的目录结构、依赖归属、启动脚本、运行时路径解析和接口行为。
- 确认离线环境下可以安装组件运行依赖，而不依赖外网 pip、Hugging Face 或临时下载。
- 确认组件能在同一容器内自动拉起 vLLM embedding 服务，并通过 OpenAI-compatible embedding API 调用 Qwen3-Embedding-4B。
- 确认 ragent 的 KG runtime 能完整加载图谱、向量库、关键词 fallback、query cache、retrieval-only 输出和 `gen.json` 落盘。
- 最终形成固定的模型包压缩包和组件包压缩包，供 MEP 平台同步或异步接口调用。

## 2. 验证范围

必须覆盖：

- MEP runtime layout：`component/`、`model/`、`data/`、`meta/` 平级结构。
- 组件入口：`config.json` 指向的入口模块和入口类，当前为 `process.CustomerModel`。
- `CustomerModel.load()`：离线依赖 bootstrap、Ascend 环境、embedding runtime、GLiNER fallback、KG runtime 初始化。
- `CustomerModel.calc(req_Data)`：读取请求、执行 onehop retrieval-only、写出 `generatePath/gen.json`。
- 离线 pip install：从 `component/deps/wheelhouse/<platform-tag>/` 和 `component/deps/keyword_wheelhouse/<platform-tag>/` 安装缺失依赖。
- component-owned dependencies：`litellm`、`openai`、`fastuuid`、`tenacity`、`nano-vectordb`、GLiNER 相关 wheel、GLiNER 模型快照。
- embedding 服务：组件内 autostart vLLM，而不是外部手工服务。
- strict offline：`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、`PIP_NO_INDEX=1` 等离线约束。

不要求在每次 full-chain smoke test 中证明检索排序最优。链路验收和检索质量评估要分开记录。

## 3. 基本规范

### 3.1 包边界

组件包负责应用运行时：

```text
component/
  config.json
  package.json
  init.py
  process.py
  run_mep_local.py              # 本地/容器内验证工具，可随测试包携带
  mep_dependency_bootstrap.py
  ragent/
  deps/
    site-packages/linux-arm64-py3.10/
    site-packages/linux-arm64-py3.11/
    requirements-linux-arm64-py3.10.txt
    requirements-linux-arm64-py3.11.txt
    wheelhouse/linux-arm64-py3.10/
    wheelhouse/linux-arm64-py3.11/
    keyword-requirements-linux-arm64-py3.10.txt
    keyword-requirements-linux-arm64-py3.11.txt
    keyword_wheelhouse/linux-arm64-py3.10/
    keyword_wheelhouse/linux-arm64-py3.11/
    models/keyword_extraction/knowledgator-gliner-x-small/
```

模型包负责模型权重和只读数据：

```text
modelDir/
  meta/
    type.mf
  model/
    config.json
    tokenizer.json
    model*.safetensors
    ...
  data/
    kg/
      sample_kg/
    deps/
      README.md                 # Qwen3 包不再放 component runtime 依赖
    samples/
```

运行时视图必须是：

```text
<runtime_root>/
  component/
  model/
  data/
  meta/
```

### 3.2 依赖归属

- `litellm`、`openai`、`tenacity`、`fastuuid`、`nano-vectordb` 属于 component runtime，不属于某个 embedding 模型。
- GLiNER Python wheels 和 `knowledgator-gliner-x-small` 模型快照属于 component-owned keyword fallback，也不应放进单个 embedding 模型包。
- Qwen3 模型包的 `modelDir/data/deps/` 只保留模型数据相关说明或极少数模型特定数据依赖，不承载通用 Python runtime。
- 镜像已经提供的 Ascend/vLLM 栈不应打进组件包，包括 `torch`、`torch_npu`、`vllm`、`vllm_ascend`、CANN/Ascend runtime。

### 3.3 离线约束

- 默认启用 `RAGENT_MEP_OFFLINE_PIP_INSTALL=1`。
- pip 安装必须使用本地 wheelhouse 和 `PIP_NO_INDEX=1`。
- 缺包时先补 `mep/component_deps/requirements-*.txt` 和对应 wheelhouse，不允许通过外网 pip 修复。
- strict offline 下 GLiNER 模型必须解析到本地目录，不能从 Hugging Face 下载。
- retrieval-only 也必须完整 import `ragent.llm.openai`、`litellm` 等链路，不允许为了绕过缺包问题改成直接 HTTP 调 embedding 或替换 embedding callable。

### 3.4 embedding 运行规范

- Qwen3-Embedding-4B 在 MEP 镜像内由组件自动拉起 vLLM：

```text
vllm serve <runtime_root>/model --task embed --runner pooling ...
```

- Ascend/ATB 默认路径：

```bash
MEP_ATB_HOME_PATH=/usr/local/Ascend/nnal/atb/latest/atb
ATB_CXX_ABI=cxx_abi_0
```

- MEP 镜像 + vLLM 引擎下，embedding 请求默认不发送 `dimensions` 参数。不要把该行为改成依赖某个样例请求的临时开关。

### 3.5 关键词 fallback 规范

- MEP retrieval-only 默认可以没有 `high_level_keywords` / `low_level_keywords`。
- 无完整 LLM 配置且请求未提供关键词时，必须启用 GLiNER fallback。
- 请求显式提供关键词时使用 request keywords。
- 如果配置了完整 LLM 模型，则可走 LLM keyword extraction。
- 不允许为了固定 smoke query 做硬编码关键词优化。关键词质量优化必须是通用规则、可解释，并配套多 query 评估。

### 3.6 路径规范

- 输出给 MEP 的 `referenced_file_paths`、`image_list`、`source_ref`、retrieval trace 中的路径应是可移植路径，例如 `example/中国居民膳食指南_2022.pdf`。
- 不应向接口输出 `/Volumes/SSD1/ragent/...` 或 `/data/disk2/ragent/...` 这类开发机/服务器绝对路径。
- KG 内部 metadata 可保留构建时原始路径，但对外响应和可复用 cache payload 应做 portable path normalization。

### 3.7 代码修改规范

- 不绕过依赖链路，不把 import 问题改成运行路径绕开。
- 不针对单个固定 query 做硬编码优化。
- 不提交无关运行缓存，尤其是 `example/qwen4b_diet_kg/kv_store_llm_response_cache.sqlite` 这类二进制 cache；如因历史原因存在变更，应在 PR/review 中明确说明。
- 组件依赖新增后，必须同时更新 py3.10 和 py3.11 的 requirements/wheelhouse，除非明确不支持对应 Python 版本。
- 修改模型包结构、组件 deps 或启动脚本后，必须跑一次服务器 full-chain。

## 4. 本地准备

在本机仓库根目录：

```bash
cd /Volumes/SSD1/ragent
git status --porcelain
```

建议先运行相关单测：

```bash
python3 -m pytest \
  tests/test_mep_adapter.py \
  tests/test_mep_component_bundle.py \
  tests/test_mep_embedding_runtime.py \
  tests/test_run_mep_local.py \
  tests/test_runtime_env.py \
  tests/test_mep_keyword_fallback_assets.py \
  tests/test_validate_mep_wheelhouse.py \
  -q
```

构建 upload 包：

```bash
python3 tools/build_mep_upload_packages.py --model-package qwen3-embedding-4b
```

如果只需要构建本地 runtime layout：

```bash
python3 tools/build_mep_layout.py --model-package qwen3-embedding-4b
```

如果需要拷贝到服务器，可使用项目已有同步脚本或 `rsync`。同步时要包含：

- `process.py`、`run_mep_local.py`、`mep_dependency_bootstrap.py`
- `ragent/`
- `docs/mep/platform_rule/Validated_ragent-mep-test_docker_full_chain.sh`
- `example/mep_requests/`
- `mep/component_deps/`
- `mep/model_packages/qwen3-embedding-4b/modelDir/`
- `tools/validate_mep_full_chain_result.py`
- `tools/mep_package_utils.py` 等 package/preflight 工具

## 5. 服务器验证方法

以下命令以服务器仓库路径 `/data/disk2/ragent` 为例；如实际路径不同，替换为对应目录。

### 5.1 同步代码

```bash
cd /data/disk2/ragent
git pull --ff-only
git log -3 --oneline
```

确认最新提交包含本次待验证代码。

### 5.2 检查关键离线资产

Python 3.11 镜像示例：

```bash
test -f mep/component_deps/requirements-linux-arm64-py3.11.txt && echo req-ok
test -d mep/component_deps/site-packages/linux-arm64-py3.11/litellm && echo litellm-ok
test -d mep/component_deps/site-packages/linux-arm64-py3.11/openai && echo openai-ok
test -f mep/component_deps/wheelhouse/linux-arm64-py3.11/fastuuid-0.14.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl && echo fastuuid-ok
test -f mep/component_deps/wheelhouse/linux-arm64-py3.11/nano_vectordb-0.0.4.3-py3-none-any.whl && echo nano-vectordb-ok
test -d mep/component_deps/keyword_wheelhouse/linux-arm64-py3.11 && echo keyword-wheelhouse-ok
test -d mep/component_deps/models/keyword_extraction/knowledgator-gliner-x-small && echo gliner-model-ok
test -d mep/model_packages/qwen3-embedding-4b/modelDir/model && echo qwen3-model-ok
test -d mep/model_packages/qwen3-embedding-4b/modelDir/data/kg/sample_kg && echo kg-ok
```

如果镜像使用 Python 3.10，同步检查 `linux-arm64-py3.10`。

### 5.3 运行 full-chain

```bash
cd /data/disk2/ragent
docker rm -f qwen3_embedding_4b_mep_full_chain || true

NPU_HOST_ID=4 \
NPU_CONTAINER_ID=0 \
ASCEND_VISIBLE_DEVICES=0 \
ASCEND_RT_VISIBLE_DEVICES=0 \
MEP_ATB_HOME_PATH=/usr/local/Ascend/nnal/atb/latest/atb \
ATB_CXX_ABI=cxx_abi_0 \
RAGENT_MEP_OFFLINE_PIP_INSTALL=1 \
SKIP_VLLM_VALIDATION=1 \
MEP_REUSE_EXISTING_VLLM=0 \
MEP_REQUEST_NAME=retrieval_only_request.json \
MEP_ENABLE_RERANK=false \
bash docs/mep/platform_rule/Validated_ragent-mep-test_docker_full_chain.sh
```

目标镜像默认值当前为：

```text
swr.cn-southwest-2.myhuaweicloud.com/huaweiccs-hivoice-product-ga/vllm-ascend-0.10.2-910b-cann8.2.rc1-torch2.7.1rc1:1.2.9.300
```

如果要验证新镜像，显式加：

```bash
IMAGE=<new-image> bash docs/mep/platform_rule/Validated_ragent-mep-test_docker_full_chain.sh
```

### 5.4 预期关键日志

应看到：

```text
strict offline mode: enabled
installed offline requirements from: /tmp/ragent-mep-runtime/component/deps/requirements-linux-arm64-py3.11.txt
installed keyword fallback offline requirements from: ...
Bootstrapping local embedding service via vLLM
Local embedding service is ready
preloading resident GLiNER keyword fallback model
Load (...) data
MEP full-chain validation passed
```

不应出现：

```text
ModuleNotFoundError
pip tries to access external index
HF/Transformers tries to download from network
vLLM BadRequest caused by embedding dimensions
CustomerModel.load failed
CustomerModel.calc failed
```

## 6. 通过标准

full-chain 通过需同时满足：

- 脚本 exit code 为 0。
- Docker 容器可成功启动，并正确映射 NPU。
- runtime layout 成功构建到 `/tmp/ragent-mep-runtime`。
- strict offline 生效。
- component offline requirements 安装成功。
- keyword fallback wheelhouse 安装成功。
- vLLM embedding 服务在组件内启动并 ready。
- GLiNER fallback 模型可预热。
- KG 图和三个向量库可加载，维度与 embedding 模型一致。
- `CustomerModel.load()` 成功。
- `CustomerModel.calc()` 成功。
- 输出 `generatePath/gen.json`，且 `code=0`。
- retrieval-only 请求返回非空 context。
- `retrieval_result.keyword_source` 符合请求场景：
  - 无关键词且无完整 LLM 配置：`gliner_fallback`
  - 请求带关键词：`request`
  - 完整 LLM 配置：`llm`
- 输出路径为 portable path，不泄露本机或服务器绝对路径。

通过不等于检索效果最优。质量评估应另行记录：

- top-k source_ref 是否命中核心证据。
- fallback keywords 是否覆盖关键概念。
- graph/vector/rerank 各分支是否引入明显噪声。
- rerank 开关对排序影响。

## 7. 失败排查顺序

### 7.1 缺 Python 包

典型错误：

```text
ModuleNotFoundError: No module named 'fastuuid'
ModuleNotFoundError: No module named 'tenacity'
ModuleNotFoundError: No module named 'gliner'
RuntimeError: nano-vectordb is required ...
```

排查：

```bash
docker exec -it qwen3_embedding_4b_mep_full_chain bash
find /tmp/ragent-mep-runtime/component/deps -maxdepth 4 -type f | sort | grep -E 'requirements|fastuuid|tenacity|nano|gliner|litellm|openai'
python3 -m pip show fastuuid tenacity nano-vectordb gliner || true
python3 - <<'PY'
import fastuuid
import tenacity
import nano_vectordb
import litellm
from gliner import GLiNER
print("imports-ok")
PY
```

修复原则：补 component deps 的 requirements 和 wheelhouse，不绕过 import。

### 7.2 vLLM embedding 请求 400

典型错误：

```text
does not support matryoshka representation, changing output dimensions will lead to poor results
```

修复原则：MEP 镜像 + vLLM embedding 服务默认不发送 embedding `dimensions` 参数。不要在请求样例里临时规避。

### 7.3 GLiNER fallback 不可用

检查：

```bash
test -d /tmp/ragent-mep-runtime/component/deps/models/keyword_extraction/knowledgator-gliner-x-small
python3 - <<'PY'
from gliner import GLiNER
m = GLiNER.from_pretrained("/tmp/ragent-mep-runtime/component/deps/models/keyword_extraction/knowledgator-gliner-x-small")
print(type(m))
PY
```

修复原则：GLiNER 模型快照和 wheels 属于 component，不复制到单个 embedding 模型包。

### 7.4 KG 或向量库加载失败

检查：

```bash
find /tmp/ragent-mep-runtime/data/kg/sample_kg -maxdepth 2 -type f | sort
```

Qwen3-Embedding-4B 使用 2560 维 KG。切换 embedding 模型或维度后，必须重建 KG/VDB。

### 7.5 输出路径不可移植

如果输出仍包含：

```text
/Volumes/SSD1/ragent/...
/data/disk2/ragent/...
```

优先检查 `ragent/portable_paths.py` 是否在 trace、query cache payload、retrieval_result 构造出口生效。不要只改单个样例请求的字符串。

## 8. 变更后的重复验证清单

修改代码后：

- 跑 MEP 相关单测。
- 构建 runtime layout 或 upload package。
- 服务器 full-chain 一次。
- 检查 `retrieval_result.keyword_source`、`keyword_strategy`、`referenced_file_paths`、`final_context_document_chunks`。

修改 component deps 后：

- py3.10 和 py3.11 requirements 同步更新。
- wheelhouse 中 wheel 文件存在且平台 tag 正确。
- full-chain 日志确认离线安装成功。

修改 GLiNER 或 keyword fallback 后：

- 无关键词 retrieval-only 请求必须真实走 `gliner_fallback`。
- 不允许对固定 query 做硬编码优化。
- 如需评估质量，应准备多 query 集合，报告关键词覆盖率、top-k 命中和噪声 chunk。

修改 embedding 模型后：

- 模型包 `modelDir/model/` 保持标准 Hugging Face 目录。
- KG/VDB 按新 embedding 维度重建。
- vLLM 启动参数重新验证。
- 不发送 unsupported dimensions 参数。

修改镜像后：

- 重新确认 Python 版本，选择 `linux-arm64-py3.10` 或 `linux-arm64-py3.11`。
- 重新确认 image-owned 包：`torch`、`torch_npu`、`vllm`、`vllm_ascend`、`transformers`。
- 只把镜像缺失且属于应用层的依赖补进 component deps。
- 重跑 full-chain，记录镜像 tag、NPU 映射、启动耗时和缺包情况。

## 9. 交付产物

最终交付给 MEP 平台时，应至少准备：

- 组件包压缩包：第一层为组件包内容，含 `config.json`、`process.py`、`ragent/`、`deps/`。
- 模型包压缩包：第一层必须为 `modelDir/`，含 `meta/`、`model/`、`data/`。
- 镜像 tag：与服务器 full-chain 验证一致。
- 样例请求：至少包含 retrieval-only 无关键词请求。
- 验证报告：记录 commit、镜像、NPU、命令、exit code、关键日志、输出路径、`gen.json` 位置。

建议保存服务器验证日志：

```bash
bash docs/mep/platform_rule/Validated_ragent-mep-test_docker_full_chain.sh 2>&1 | tee /tmp/mep_full_chain_run.log
```

容器内常见输出：

```text
/tmp/ragent-mep-output/<request-name>/generatePath/gen.json
/tmp/ragent-mep-full-chain/<request-name>.stdout.json
/tmp/ragent-mep-full-chain/<request-name>.stderr.log
```

## 10. 验收结论模板

每次验证后按以下格式记录：

```text
日期：
服务器路径：
分支/commit：
镜像：
NPU 映射：
请求文件：
Rerank：
exit code：
总耗时：
vLLM 启动耗时：
GLiNER 预热耗时：
是否 strict offline：
是否离线安装 component requirements：
是否离线安装 keyword requirements：
keyword_source / keyword_strategy：
KG/VDB 加载数量：
final_context_document_chunks 数量：
referenced_file_paths 是否 portable：
gen.json 路径：
主要 WARNING：
阻塞错误：
结论：通过 / 不通过 / 链路通过但质量需复查
```

验收结论应明确区分：

- 链路可用：MEP 离线依赖、vLLM embedding、KG runtime、接口调用均成功。
- 检索质量：关键词质量、排序、rerank、弱相关 chunk 是否满足业务要求。
