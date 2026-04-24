# process_sync.py

> 本文件为脱敏参考版本，仅保留运行时环境配置、参数配置、目录配置等工程代码，业务逻辑已脱敏。

```python
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

# v0.0.3  46-49行类型转换

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
model_name = os.getenv('model_name', 'qwen25-vl')
wait_time = int(os.getenv('wait_time', '120'))

# ==================== 全局并发控制 ====================
MAX_CONCURRENT = int(max_num_seqs)
_GLOBAL_SEMAPHORE = Semaphore(MAX_CONCURRENT)  # 匹配 vLLM --max-num-seqs
_GLOBAL_STATS_LOCK = threading.Lock()
_GLOBAL_STATS = {
    'total_requests': 0,
    'active_requests': 0,
    'success_count': 0,
    'fail_count': 0
}


# ==================== 业务函数（已脱敏） ====================

def encode_image(image_path: str) -> str:
    """[已脱敏] 文件转base64，异常返回空字符串"""
    # ... 业务逻辑已脱敏 ...
    pass


def create_mm_request_body(image_paths: List[str], prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
    """[已脱敏] 构建多模态请求体"""
    # ... 业务逻辑已脱敏 ...
    pass


def get_mm_response(url, body: Dict[str, Any]) -> str:
    """[已脱敏] 发送请求并获取响应"""
    # ... 业务逻辑已脱敏 ...
    pass


# ==================== 主应用类 ====================

class MyApplication:

    def __init__(self, gpu_id=None, model_root=None):

        # ---------- 服务地址 & 日志路径 ----------
        self.url = "http://127.0.0.1:1040/v1/chat/completions"
        self.log_path = "/opt/huawei/log/run/vllm_server.log"

        # ---------- 模型路径配置（从环境变量读取） ----------
        tmp_str = os.environ.get("MODEL_SFS", "{\"sfsBasePath\":\"aaaa\"}")
        tmp_json = json.loads(tmp_str)
        process_model_base = tmp_json["sfsBasePath"] + "/" + os.environ.get("MODEL_OBJECT_ID", "") + "/model"
        model_path = process_model_base + "/" + os.environ.get('path_appendix', "")

        logger.info(f"Model path: {model_path}")

        # ---------- 启动 vLLM 服务 ----------
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

        # 方式1：Popen 后台启动，stdout/stderr 重定向，不阻塞主线程
        self.vllm_process = subprocess.Popen(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # 启动守护线程打印子进程日志
        def log_subprocess_output(pipe):
            for line in iter(pipe.readline, ''):
                if line:
                    logger.info(f"[vLLM] {line.strip()}")

        threading.Thread(target=log_subprocess_output, args=(self.vllm_process.stdout,), daemon=True).start()

        # 方式2：同时写入日志文件
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

        # ---------- 健康检查：轮询等待服务就绪 ----------
        start_time = time.time()
        # [已脱敏] 测试用的 prompt 和图片路径
        test_prompt = "<image>\n[已脱敏-测试prompt]"
        test_image_path = [os.path.join(currentdir, "[已脱敏-测试图片路径]")]
        test_body = create_mm_request_body(test_image_path, test_prompt, 512)
        self.prompt = "[已脱敏-测试prompt]"

        while not self.daemon_started:
            try:
                logger.info(f"测试prompt: {self.prompt}")
                request_start = time.time()
                res = get_mm_response(self.url, test_body)
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

        # ---------- httpx 连接池配置 ----------
        http_client = httpx.Client(
            limits=httpx.Limits(
                max_connections=MAX_CONCURRENT + 8,  # 略大于并发数，留缓冲
                max_keepalive_connections=MAX_CONCURRENT  # 保持长连接复用
            ),
            timeout=httpx.Timeout(
                connect=10.0,   # 连接建立超时
                read=wait_time, # 推理超时
                write=10.0,
                pool=10.0       # 从连接池获取连接的超时
            )
        )

        # ---------- OpenAI 客户端配置 ----------
        self.client = OpenAI(
            base_url="http://127.0.0.1:1040/v1",
            api_key="sk-1234",  # vLLM服务器默认不验证API Key，但需要提供
            http_client=http_client
        )

        # ---------- 重试配置 ----------
        self.max_retries = 3
        self.retry_delay = 1.0

    def _count_images(self, messages: list) -> int:
        """[已脱敏] 统计图片数量"""
        # ... 业务逻辑已脱敏 ...
        pass

    def _get_permits_needed(self, messages: list) -> int:
        """[已脱敏] 计算需要的并发槽位"""
        # ... 业务逻辑已脱敏 ...
        pass

    def load(self):
        """加载资源"""
        pass

    @staticmethod
    def build_messages(data: dict) -> list:
        """[已脱敏] 构建请求消息体"""
        # ... 业务逻辑已脱敏 ...
        pass

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

        # [已脱敏] 业务消息构建
        messages = self.build_messages(data)

        # 计算需要的槽位
        permits_needed = self._get_permits_needed(messages)
        image_count = self._count_images(messages)

        logger.info(f"图片数: {image_count}, 申请槽位: {permits_needed}/{MAX_CONCURRENT}")

        # 获取多个信号量（并发控制）
        acquired = 0
        try:
            for i in range(permits_needed):
                if not _GLOBAL_SEMAPHORE.acquire(timeout=wait_time):
                    # 释放已获取的
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

            # [已脱敏] 构建请求参数
            request_params = {
                "model": model_name,
                "messages": messages,
                "stream": False,
                "temperature": data.get("temperature", 0.7),
                "max_tokens": data.get("max_tokens", 512),
                "timeout": 120
            }

            # 执行请求（带重试）
            result = self._call_with_retry(request_params)
            logger.info(f"请求结果: {result}")

            with _GLOBAL_STATS_LOCK:
                if result['resultCode'] == "0000000000":
                    _GLOBAL_STATS['success_count'] += 1
                else:
                    _GLOBAL_STATS['fail_count'] += 1

            return result

        finally:
            # 必须释放所有槽位
            for _ in range(acquired):
                _GLOBAL_SEMAPHORE.release()
            with _GLOBAL_STATS_LOCK:
                _GLOBAL_STATS['active_requests'] -= 1

    def _call_with_retry(self, request_params: dict) -> dict:
        """带重试的调用"""
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=request_params["model"],
                    messages=request_params["messages"],
                    stream=request_params["stream"],
                    temperature=request_params["temperature"],
                    max_tokens=request_params["max_tokens"],
                    timeout=request_params["timeout"]
                )

                result = [response.choices[0].message.content]

                return {
                    'resultCode': "0000000000",
                    'des': 'success',
                    'result': result
                }

            except (httpx.ConnectError, httpx.PoolTimeout) as e:
                logger.warning(f"连接错误(尝试{attempt + 1}/{self.max_retries + 1}): {str(e)[:100]}")

                # 检查是否是vLLM崩溃
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

| 模块 | 保留内容 | 脱敏内容 |
|------|---------|---------|
| **日志配置** | `logging.basicConfig`、第三方库日志级别抑制 | — |
| **环境变量** | `HCCL_OP_EXPANSION_MODE`、`tp`、`max_num_seqs`、`max_num_batched_tokens`、`max_model_len`、`gpu_memory_utilization`、`model_name`、`wait_time` | — |
| **全局并发控制** | `Semaphore`、`_GLOBAL_STATS`、`_GLOBAL_STATS_LOCK` | — |
| **`encode_image`** | 函数签名、docstring | 文件读取 & base64 编码的具体实现 |
| **`create_mm_request_body`** | 函数签名、docstring | 请求体构建的具体逻辑（prompt拼接、图片URL组装） |
| **`get_mm_response`** | 函数签名、docstring | HTTP 请求发送 & 响应解析的具体逻辑 |
| **`MyApplication.__init__`** | 服务地址、日志路径、模型路径配置、vLLM 启动命令、`subprocess.Popen` 启动方式、健康检查轮询框架、httpx 连接池配置、OpenAI 客户端配置、重试配置 | 测试 prompt 内容、测试图片路径 |
| **`_count_images`** | 函数签名 | 图片计数逻辑 |
| **`_get_permits_needed`** | 函数签名 | 槽位计算逻辑 |
| **`build_messages`** | 函数签名 | 消息体构建逻辑 |
| **`calc`** | 请求校验、信号量并发控制、统计更新、finally 释放 | 业务消息构建细节 |
| **`_call_with_retry`** | 完整重试框架、异常分类处理（ConnectError/Timeout/通用异常）、指数退避 | — |
| **`event` / `health`** | 完整保留 | — |
