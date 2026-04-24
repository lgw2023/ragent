# 问题5：vLLM 镜像运行方式是什么？

## 问题原文

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

---

## 基于代码库的分析回答

### 1. 镜像内是否已安装 `vllm` 和 `vllm-ascend`

从代码库可以确认，**镜像内必然已安装 `vllm`**，依据如下：

- [vllm_backend.py](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/backends/vllm_backend.py) 中大量直接 `from vllm import ...`，包括 `AsyncEngineArgs`、`SamplingParams`、`MQLLMEngineClient` 等核心模块。
- [process_sync.py](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process_sync.py) 和 [process.py](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process.py) 中通过 `subprocess.Popen` 调用 `python -m vllm.entrypoints.openai.api_server`，说明镜像中 vllm 作为 Python 包已安装。

关于 **`vllm-ascend`**：

- 代码中存在明显的昇腾（Ascend）NPU 适配痕迹：
  - `init.sh` 中设置了 `LCCL_DETERMINISTIC=true` 和 `HCCL_DETERMINISTIC=true`（HCCL 是昇腾集合通信库）
  - [vllm_backend.py:278](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/backends/vllm_backend.py#L278) 中使用了 `ASCEND_RT_VISIBLE_DEVICES` 环境变量
  - [vllm_backend.py:289-295](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/backends/vllm_backend.py#L289-L295) 中设置了 `HCCL_HOST_SOCKET_PORT_RANGE`、`HCCL_NPU_SOCKET_PORT_RANGE` 等 HCCL 相关端口配置
  - [launcher.py:17](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/launcher.py#L17) 中通过 `glob.glob("/dev/davinci[0-9]*")` 检测 NPU 设备数量
  - `process_sync.py` 中设置了 `os.environ["HCCL_OP_EXPANSION_MODE"] = "AIV"`
- 这些都表明运行环境是昇腾 NPU，因此 **`vllm-ascend`（昇腾适配包）极大概率也已安装在镜像中**，否则 vllm 无法在 NPU 上运行。

### 2. 平台实际使用的 vLLM 启动方式

代码库中存在 **多种 vLLM 启动方式**，对应不同的引擎类型：

#### 方式一：`python -m vllm.entrypoints.openai.api_server`（当前组件包入口使用）

这是 [process_sync.py:154-155](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process_sync.py#L154-L155) 和 [process.py:154-155](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/process.py#L154-L155) 中 `MyApplication.__init__()` 实际使用的启动命令：

```python
commands = [
    'python', '-m', 'vllm.entrypoints.openai.api_server', '--model',
    model_path,
    '--tokenizer', model_path,
    '--host', '127.0.0.1', '--port', '1040',
    '--tensor-parallel-size', tp,
    '--max-num-seqs', max_num_seqs,
    '--max-num-batched-tokens', max_num_batched_tokens,
    '--trust-remote-code',
    '--dtype', 'float16',
    '--gpu-memory-utilization', gpu_memory_utilization,
    '--max-model-len', max_model_len,
    '--served-model-name', model_name,
    '--swap-space', '4',
]
```

这是 **OpenAI 兼容的 API Server** 模式，启动后通过 `http://127.0.0.1:1040/v1/chat/completions` 提供服务，组件代码中使用 `OpenAI` 客户端库进行调用。

#### 方式二：`python -m vllm.entrypoints.dist_api_server`（ disaggregate 引擎使用）

这是 [vllm_backend.py:187](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/backends/vllm_backend.py#L187) 中 `DisaggregateVllmEngineExecutor` 使用的启动命令：

```python
commands = [
    'python', '-m', 'vllm.entrypoints.dist_api_server',
    '--host', self.HTTP_HOST, '--port', env["VLLM_HTTP_PORT"],
    '--model', str(self._engine_args.model),
    '--trust-remote-code',
    ...
]
```

以及 [launcher.py:134-135](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/launcher.py#L134-L135) 中同样使用：

```python
command = [
    "python",
    "-m", "vllm.entrypoints.dist_api_server",
    ...
]
```

这是 **PD 分离（Prefill-Decode Disaggregate）模式** 的专用入口，支持 prefill 和 decode 分离部署。

#### 方式三：`python -m vllm.entrypoints.api_server_vision`（ViT 视觉模型使用）

这是 [vllm_backend.py:481](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/backends/vllm_backend.py#L481) 中 `VitVllmEngineExecutor` 使用的启动命令：

```python
commands = [
    'python', '-m', 'vllm.entrypoints.api_server_vision',
    '--host', self.HTTP_HOST, '--port', env["VLLM_HTTP_PORT"],
    '--tokenizer', ...,
    '--trust-remote-code',
    ...
]
```

#### 方式四：`python -m vllm.entrypoints.api_server`（ViT 备用路径）

[vllm_backend.py:522](file:///d:/GitHub/xiaoyi_diet/qwen_vllm_async_copilot/backends/vllm_backend.py#L522) 中 `VitVllmEngineExecutor._build_server_processes()` 还有一段使用标准 api_server 的代码：

```python
commands = [
    'python', '-m', 'vllm.entrypoints.api_server',
    '--model', ...,
    '--tokenizer', ...,
    '--host', self.HTTP_HOST, '--port', env["VLLM_HTTP_PORT"]
]
```

### 3. 关于 `vllm serve` 命令

代码库中 **没有使用** `vllm serve ...` 这种启动方式。所有启动都是通过 `python -m vllm.entrypoints.xxx` 的形式。`vllm serve` 是 vLLM 较新版本（v0.6+）引入的 CLI 命令，本质上是 `python -m vllm.entrypoints.openai.api_server` 的封装。当前代码库使用的镜像版本可能尚未支持该命令，或者团队习惯使用 `python -m` 方式。

---

## 总结

| 问题 | 回答 |
|------|------|
| 镜像内是否安装 `vllm`？ | **是**，代码中大量直接 import vllm 模块 |
| 镜像内是否安装 `vllm-ascend`？ | **极大概率是**，运行环境为昇腾 NPU，vllm 需要 vllm-ascend 适配包才能在 NPU 上运行 |
| 平台推荐启动方式？ | **`python -m vllm.entrypoints.openai.api_server ...`**（当前组件包入口 process_sync.py 实际使用的方式） |
| 是否使用 `vllm serve`？ | **否**，代码库中未使用此方式 |

### 注意

以上结论完全基于代码库中的实际代码推断。关于 **MEP 平台官方推荐的 vLLM 镜像运行方式**，MEP 目录下的文档中并未找到明确说明。建议向 MEP 平台同事确认：
1. 平台提供的 vLLM 基础镜像中 `vllm` 和 `vllm-ascend` 的具体版本号
2. 平台是否对 `vllm serve` 或 `python -m vllm.entrypoints.openai.api_server` 有偏好或限制
3. 是否有平台定制的 vLLM 入口模块（如代码中出现的 `dist_api_server`、`api_server_vision` 等非标准入口）
