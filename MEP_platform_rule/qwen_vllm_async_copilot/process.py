# process.py

> 本文件为脱敏版本，仅保留运行时环境配置、参数配置、目录配置等工程代码，业务逻辑已用占位符替换。

```python
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

import logging
import os

import time
import json
import requests

import threading
from typing import List, Dict, Any, Union
import base64
from tqdm import tqdm
import traceback

from threading import Lock, Semaphore
from openai import OpenAI
import httpx

currentdir = os.path.dirname(__file__)
parentdir = os.path.abspath(os.path.join(currentdir, os.pardir))

from utils import LOGGER as logger
import subprocess

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# ==================== 环境变量 & 参数配置 ====================
os.environ["HCCL_OP_EXPANSION_MODE"] = "AIV"
tp = os.getenv('tp', '1')
max_num_seqs = os.getenv('max_num_seqs', '32')
max_num_batched_tokens = os.getenv('max_num_batched_tokens', '8192')
max_model_len = os.getenv('max_model_len', '40960')
gpu_memory_utilization = os.getenv('gpu_memory_utilization', '0.8')
model_name = os.getenv('model_name', '<YOUR_MODEL_NAME>')
wait_time = int(os.getenv('wait_time', '120'))

# ==================== 并发控制 ====================
MAX_CONCURRENT = int(max_num_seqs)
_GLOBAL_SEMAPHORE = Semaphore(MAX_CONCURRENT)  # 匹配 vLLM --max-num-seqs
_GLOBAL_STATS_LOCK = threading.Lock()
_GLOBAL_STATS = {
    'total_requests': 0,
    'active_requests': 0,
    'success_count': 0,
    'fail_count': 0
}


# ==================== 业务工具函数（脱敏） ====================

def encode_input(input_path: str) -> str:
    """输入文件转base64，异常返回空字符串"""
    try:
        with open(input_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        logging.error(f"文件不存在 {input_path}")
        return ""
    except PermissionError:
        logging.error(f"无读取权限 {input_path}")
        return ""
    except IsADirectoryError:
        logging.error(f"路径是文件夹 {input_path}")
        return ""
    except Exception as e:
        logging.error(f"编码失败：{input_path}，异常: {str(e)}")
        return ""


def create_request_body(input_paths: List[str], prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
    """构建请求体，编码失败返回空字典"""
    base64_items = []
    for path in input_paths:
        base64_item = encode_input(path)
        if not base64_item:
            logging.error(f"编码失败: {path}")
            return {}
        base64_items.append(base64_item)

    # --- 以下为业务特定的消息构造逻辑，已脱敏 ---
    messages = []
    for base64_item in base64_items:
        messages.append({
            "type": "<YOUR_INPUT_TYPE>",
            "<YOUR_INPUT_KEY>": {
                "<YOUR_URL_KEY>": f"data:<YOUR_MIME_TYPE>;base64,{base64_item}"
            }
        })

    messages.append({
        "type": "text",
        "text": prompt
    })

    return {
        "model": "<YOUR_MODEL_NAME>",
        "messages": [{"role": "user", "content": messages}],
        "max_tokens": max_tokens,
        "temperature": 0.01,
        "top_p": 0.001
    }


def get_response(url, body: Dict[str, Any]) -> str:
    """独立请求函数"""
    try:
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(url, json=body, headers=headers, timeout=300)

        if resp.status_code != 200:
            logger.error(f"请求失败，状态码: {resp.status_code}, 响应: {resp.text}")
            return "error"

        response_data = resp.json()

        if 'choices' in response_data and len(response_data['choices']) > 0:
            result_text = response_data['choices'][0]['message']['content'].strip()
            # --- 业务特定的响应清洗逻辑，已脱敏 ---
            # <YOUR_RESPONSE_PARSING_LOGIC_HERE>
            return result_text
        else:
            logger.error(f"响应格式异常: {response_data}")
            return "error"

    except Exception as e:
        logger.error(f"推理请求异常: {e}")
        traceback.print_exc()
        return "error"


# ==================== 主应用类 ====================

class MyApplication:

    def __init__(self, gpu_id=None, model_root=None):

        # --- 服务地址配置 ---
        self.url = "http://127.0.0.1:1040/v1/chat/completions"
        self.log_path = "/opt/huawei/log/run/vllm_server.log"

        # --- 模型路径配置（从环境变量读取） ---
        tmp_str = os.environ.get("MODEL_SFS", "{\"sfsBasePath\":\"aaaa\"}")
        tmp_json = json.loads(tmp_str)
        process_model_base = tmp_json["sfsBasePath"] + "/" + os.environ.get("MODEL_OBJECT_ID", "") + "/model"
        model_path = process_model_base + "/" + os.environ.get('path_appendix', "")

        logger.info(f"Model path: {model_path}")

        # --- vLLM 服务启动命令 ---
        commands = [
            'python', '-m', 'vllm.entrypoints.openai.api_server', '--model',
            model_path,
            '--tokenizer',
            model_path,
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
            '{"cudagraph_mode": "FULL_DECODE_ONLY", "cudagraph_capture_sizes": [1,2,3,4,6,8,16,24,32]}'
        ]

        logger.info(f"Starting vLLM with command: {' '.join(commands)}")

        # --- 子进程启动 vLLM（前台日志线程） ---
        self.vllm_process = subprocess.Popen(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        def log_subprocess_output(pipe):
            for line in iter(pipe.readline, ''):
                if line:
                    logger.info(f"[vLLM] {line.strip()}")

        threading.Thread(target=log_subprocess_output, args=(self.vllm_process.stdout,), daemon=True).start()

        # --- 子进程启动 vLLM（后台日志写文件） ---
        with open(self.log_path, 'a', encoding='utf-8') as f:
            process = subprocess.Popen(
                commands,
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            print(f"vLLM 已后台启动 (PID: {process.pid})")
            print(f"日志文件: {self.log_path}")

        self.daemon_started = False

        # --- 服务启动健康检查 ---
        start_time = time.time()
        # <YOUR_TEST_PROMPT_AND_INPUT_HERE>
        test_prompt = "<YOUR_TEST_PROMPT>"
        test_input_path = ["<YOUR_TEST_INPUT_PATH>"]
        test_body = create_request_body(test_input_path, test_prompt, 512)
        self.prompt = "<YOUR_DEFAULT_PROMPT>"

        while not self.daemon_started:
            try:
                logger.info(f"测试prompt: {self.prompt}")
                request_start = time.time()
                res = get_response(self.url, test_body)
                request_duration = time.time() - request_start
                if res and res != "error":
                    total_wait = time.time() - start_time
                    logger.info(f"测试响应: {res}")
                    logger.info("服务已启动成功。")
                    logger.info(f"服务启动成功！总等待时间: {total_wait:.2f} 秒，单次请求耗时: {request_duration:.2f} 秒")
                    self.daemon_started = True
                else:
                    logger.info("等待服务启动...")
                    time.sleep(15)
            except Exception as e:
                logger.info(f"服务启动中: {e}")
                time.sleep(15)

        # --- HTTP 客户端配置 ---
        http_client = httpx.Client(
            limits=httpx.Limits(
                max_connections=MAX_CONCURRENT + 8,
                max_keepalive_connections=MAX_CONCURRENT
            ),
            timeout=httpx.Timeout(
                connect=10.0,
                read=wait_time,
                write=10.0,
                pool=10.0
            )
        )

        self.client = OpenAI(
            base_url="http://127.0.0.1:1040/v1",
            api_key="sk-1234",  # vLLM服务器默认不验证API Key，但需要提供
            http_client=http_client
        )

        self.max_retries = 3
        self.retry_delay = 1.0

    # ==================== 并发槽位计算（脱敏） ====================

    def _count_inputs(self, messages: list) -> int:
        """统计输入项数量"""
        count = 0
        for msg in messages:
            content = msg.get('content', [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        # <YOUR_INPUT_COUNTING_LOGIC_HERE>
                        if item.get('type') == '<YOUR_INPUT_TYPE>' or '<YOUR_KEYWORD>' in str(item):
                            count += 1
            elif isinstance(content, str):
                if '<YOUR_PATTERN>' in content or content.startswith('http'):
                    count += 1
        return max(count, 1)

    def _get_permits_needed(self, messages: list) -> int:
        """计算需要的并发槽位"""
        input_count = self._count_inputs(messages)
        permits = input_count * 2  # 保守策略：每项占2个槽位
        max_permits = MAX_CONCURRENT // 2  # 不超过最大并发的一半
        return min(permits, max_permits)

    def load(self):
        """加载资源"""
        pass

    # ==================== 核心请求处理 ====================

    def calc(self, req_Data):
        """
        单条请求处理（外部框架多并发调用此方法）
        内部用全局信号量控制总并发 ≤ MAX_CONCURRENT
        """
        logger.info("~~~~~~~~~~~~开始处理请求 ~~~~~~~~~~~")

        if req_Data is None:
            return {"code": 3, "des": "fail, request data is missing.", "response": "request data is missing."}

        data = req_Data.get('data')
        if data is None:
            return {"code": 3, "des": "fail, data is missing.", "response": "data is missing."}

        logger.info(f"请求字段: {', '.join(data.keys())}")
        messages = data.get('messages', [])
        permits_needed = self._get_permits_needed(messages)
        input_count = self._count_inputs(messages)

        logger.info(f"输入项数: {input_count}, 申请槽位: {permits_needed}/{MAX_CONCURRENT}")

        # --- 获取多个信号量 ---
        acquired = 0
        try:
            for i in range(permits_needed):
                if not _GLOBAL_SEMAPHORE.acquire(timeout=wait_time):
                    for _ in range(acquired):
                        _GLOBAL_SEMAPHORE.release()
                    return {
                        "code": 2,
                        "des": "fail, server busy",
                        "response": f"需要{permits_needed}槽位，当前资源不足，请稍后重试"
                    }
                acquired += 1

            with _GLOBAL_STATS_LOCK:
                _GLOBAL_STATS['total_requests'] += 1
                _GLOBAL_STATS['active_requests'] += 1
                active = _GLOBAL_STATS['active_requests']
                logger.info(f"当前并发: {active}/{MAX_CONCURRENT}, 总请求: {_GLOBAL_STATS['total_requests']}")

            # 执行请求（带重试）
            result = self._call_with_retry(data)

            with _GLOBAL_STATS_LOCK:
                if result['code'] == 0:
                    _GLOBAL_STATS['success_count'] += 1
                else:
                    _GLOBAL_STATS['fail_count'] += 1

            return result

        finally:
            for _ in range(acquired):
                _GLOBAL_SEMAPHORE.release()
            with _GLOBAL_STATS_LOCK:
                _GLOBAL_STATS['active_requests'] -= 1

    def _call_with_retry(self, data: dict) -> dict:
        """带重试的调用"""
        for attempt in range(self.max_retries + 1):
            try:
                # 检查vLLM是否还活着
                if self.vllm_process.poll() is not None:
                    logger.error("vLLM进程已退出...")

                response = self.client.chat.completions.create(
                    model="<YOUR_MODEL_NAME>",
                    messages=data.get('messages', []),
                    stream=False,
                    temperature=data.get('temperature', 0.7),
                    max_tokens=data.get('max_tokens', 512),
                    timeout=120
                )

                return {
                    'code': 0,
                    'des': 'success',
                    'response': response.choices[0].message.content
                }

            except (httpx.ConnectError, httpx.PoolTimeout) as e:
                logger.warning(f"连接错误(尝试{attempt + 1}/{self.max_retries + 1}): {str(e)[:100]}")

                if "Connection refused" in str(e):
                    logger.error("检测到vLLM崩溃，等待重启...")
                    time.sleep(5)
                    try:
                        self._wait_for_vllm_ready(timeout=60)
                        continue
                    except:
                        pass

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return {'code': 2, 'des': 'connection_error', 'response': str(e)[:200]}

            except httpx.TimeoutException as e:
                logger.warning(f"超时(尝试{attempt + 1}): {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return {'code': 2, 'des': 'timeout', 'response': '请求超时'}

            except Exception as e:
                logger.error(f"API错误: {str(e)[:200]}")
                return {'code': 1, 'des': 'error', 'response': str(e)[:500]}

        return {'code': 1, 'des': 'error', 'response': 'Max retries exceeded'}

    def event(self, req_Data: Dict[str, Any]) -> Dict[str, Any]:
        """事件接口（与calc相同）"""
        return self.calc(req_Data)

    def health(self):
        return True
```

---

## 脱敏说明

| 原始内容 | 脱敏后占位符 | 说明 |
|---|---|---|
| `qwen25-vl` | `<YOUR_MODEL_NAME>` | 模型名称 |
| `image_url` / `image` | `<YOUR_INPUT_TYPE>` / `<YOUR_INPUT_KEY>` | 输入类型标识 |
| `data:image/jpeg;base64,` | `data:<YOUR_MIME_TYPE>;base64,` | MIME 类型 |
| 图片计数逻辑 (`_count_images`) | `_count_inputs` + `<YOUR_INPUT_COUNTING_LOGIC_HERE>` | 输入项统计 |
| 测试 prompt `请详细描述图片` | `<YOUR_TEST_PROMPT>` | 测试提示词 |
| 测试图片路径 | `<YOUR_TEST_INPUT_PATH>` | 测试输入路径 |
| 响应清洗逻辑 (````json````剥离) | `<YOUR_RESPONSE_PARSING_LOGIC_HERE>` | 响应后处理 |
| `encode_image` | `encode_input` | 函数名泛化 |
| `create_mm_request_body` | `create_request_body` | 函数名泛化 |
| `get_mm_response` | `get_response` | 函数名泛化 |

## 保留的工程代码

- ✅ 环境变量读取 (`os.getenv`)
- ✅ HCCL 环境变量配置
- ✅ 日志级别与格式配置
- ✅ 全局信号量并发控制 (`Semaphore`)
- ✅ 全局统计锁与计数器 (`Lock`, `_GLOBAL_STATS`)
- ✅ vLLM 子进程启动 (前台日志线程 + 后台日志写文件)
- ✅ 服务健康检查循环
- ✅ httpx 连接池配置
- ✅ OpenAI 客户端初始化
- ✅ 重试机制 (指数退避)
- ✅ 异常分类处理 (ConnectError / TimeoutException / 通用异常)
- ✅ 并发槽位申请与释放 (finally 保证释放)
- ✅ 模型路径从环境变量动态拼接
