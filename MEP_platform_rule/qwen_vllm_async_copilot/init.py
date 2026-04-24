# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

import json
import os
import re
from typing import TypeVar

import betterproto


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    if isinstance(val, bool):
        return val

    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError(f"invalid truth value {val}")


def getenv_or_default(key: str, default=None) -> str:
    """Returns default value if environment variable is None or empty."""
    value = os.getenv(key, None)
    if value is None:
        return default
    value = value.strip()
    if not value or value.lower() in ('null', 'none'):
        return default
    return value


def getint_or_default(key: str, default=None) -> int:
    """Returns int value if environment variable is None or empty."""
    value = getenv_or_default(key, default)
    if value is not None:
        return int(value)
    return default


def getfloat_or_default(key: str, default=None) -> float:
    """Returns float value if environment variable is None or empty."""
    value = getenv_or_default(key, default)
    if value is not None:
        return float(value)
    return default


def getbool_or_default(key: str, default=None) -> bool:
    """Returns bool value if environment variable is None or empty."""
    value = getenv_or_default(key, default)
    if value is not None:
        return strtobool(value)
    return default


def setenv_if_exists(key: str, value=None):
    """Set environment value if value is not None."""
    if value is None:
        return
    os.environ[key] = value


def is_uppercase_underscore(name: str) -> bool:
    """Check if it is named with uppercase and underscore."""
    pattern = r'^[A-Z][A-Z0-9_]*$'
    return re.fullmatch(pattern, name) is not None


# MEP服务根目录结构
# ├── component
# ├── data
# ├── log
# ├── model
# ├── service
# ├── temp

# 组件包目录
COMPONENT_DIR = os.path.abspath(os.path.dirname(__file__))
# 服务主目录（容器目录）
ROOT_DIR = os.path.dirname(COMPONENT_DIR)
# 模型文件中model目录
MODEL_DIR = os.path.join(ROOT_DIR, "model")
# 模型文件中data目录
DATA_DIR = os.path.join(ROOT_DIR, "data")
# SFS模型文件目录
SFS_MODEL_BASE_DIR = ''
if os.getenv('MODEL_SFS') and os.getenv('MODEL_OBJECT_ID'):
    SFS_INFO = json.loads(os.getenv('MODEL_SFS'))
    SFS_MODEL_BASE_DIR = os.path.join(
        SFS_INFO['sfsBasePath'],
        os.getenv('MODEL_OBJECT_ID')
    )

# 服务环境变量
# MEP大模型服务
MEP_POD_NAME = getenv_or_default('podName', None)
MEP_GROUP_NAME, MEP_POD_ROLE, MEP_INSTANCE_ID, MEP_POD_ID = None, None, None, None
if MEP_POD_NAME is not None:
    # 格式：groupName-podRole-instanceId-podId
    MEP_GROUP_NAME, MEP_POD_ROLE, MEP_INSTANCE_ID, MEP_POD_ID = MEP_POD_NAME.rsplit('-', maxsplit=3)

# 框架参数
FAST_API = getbool_or_default('FAST_API', False)
SSE_RETURN = getbool_or_default('SSE_RETURN', False)
SSE_ACCELERATE_GPU = getbool_or_default('SSE_ACCELERATE_GPU', False)
MEP_FRAMEWORK_RUN_LOG_LEVEL = getenv_or_default('MEP_FRAMEWORK_RUN_LOG_LEVEL', 'INFO')

# 模型类型
MODEL_NAME = getenv_or_default('MODEL_NAME', '')
MODEL_BACKEND = getenv_or_default('MODEL_BACKEND', '')
# 模型文件
MODEL_ABSOLUTE_DIR = getenv_or_default('MODEL_ABSOLUTE_DIR', '')
MODEL_RELATIVE_DIR = getenv_or_default('MODEL_RELATIVE_DIR', '')
SFS_MODEL_DIR = os.path.join(SFS_MODEL_BASE_DIR, MODEL_RELATIVE_DIR)
# Tokenizer
USE_PROMPT_TOKEN_IDS = getbool_or_default('USE_PROMPT_TOKEN_IDS', False)
USE_AUTO_TOKENIZER = getbool_or_default('USE_AUTO_TOKENIZER', False)
TOKENIZER_DIR = getenv_or_default('TOKENIZER_DIR', os.path.join(COMPONENT_DIR, 'configs/vocab/llama_v1'))

# 服务参数
PYTHON_ENABLE_PROFILING = getbool_or_default('PYTHON_ENABLE_PROFILING', False)
BATCH_MAX_WAIT_LATENCY = getfloat_or_default('BATCH_MAX_WAIT_LATENCY', 0.1)
BATCH_MAX_SIZE = getint_or_default('BATCH_MAX_SIZE', 1)
PRINT_METRICS = getbool_or_default('PRINT_METRICS', False)
FIRST_TOKEN_TIMEOUT = getint_or_default('FIRST_TOKEN_TIMEOUT', 30)
GENERATION_TIMEOUT = getint_or_default('GENERATION_TIMEOUT', 600)
MAX_NEW_TOKENS_NUM = getint_or_default('MAX_NEW_TOKENS_NUM', 2048)
MIN_NEW_TOKENS_NUM = getint_or_default('MIN_NEW_TOKENS_NUM', 0)
TENSOR_PARALLEL_SIZE = getint_or_default('TENSOR_PARALLEL_SIZE', 1)
PIPELINE_PARALLEL_SIZE = getint_or_default('PIPELINE_PARALLEL_SIZE', 1)
DATA_PARALLEL_SIZE = getint_or_default('DATA_PARALLEL_SIZE', 1)
DECODE_TENSOR_PARALLEL_SIZE = getint_or_default('DECODE_TENSOR_PARALLEL_SIZE', 1)
DECODE_PIPELINE_PARALLEL_SIZE = getint_or_default('DECODE_PIPELINE_PARALLEL_SIZE', 1)
DECODE_DATA_PARALLEL_SIZE = getint_or_default('DECODE_DATA_PARALLEL_SIZE', 1)
GPU_MEMORY_UTILIZATION = getfloat_or_default('GPU_MEMORY_UTILIZATION', 0.9)
DEFAULT_SAMPLING_TOPK = getenv_or_default('DEFAULT_SAMPLING_TOPK', None)
DEFAULT_SAMPLING_TOPP = getenv_or_default('DEFAULT_SAMPLING_TOPP', None)
DEFAULT_SAMPLING_TEMPERATURE = getenv_or_default('DEFAULT_SAMPLING_TEMPERATURE', None)
ASCEND_RT_VISIBLE_DEVICES = getenv_or_default('ASCEND_RT_VISIBLE_DEVICES', '0,1,2,3,4,5,6,7')
IMAGE_PLACEHOLDER_BEGIN = getenv_or_default('IMAGE_PLACEHOLDER_BEGIN', None)
IMAGE_PLACEHOLDER_END = getenv_or_default('IMAGE_PLACEHOLDER_END', None)
IMAGES_DOWNLOAD_TIMEOUT = getint_or_default('IMAGES_DOWNLOAD_TIMEOUT', 2)
MEP_APPID = getenv_or_default('mep_appid', 'hivoice')
MEP_SECRET = getenv_or_default('MEP_SECRET', None)
MEP_ELB_IP = getenv_or_default('MEP_ELB_IP', '10.41.1.17')
MIN_PIXELS = getint_or_default('MIN_PIXELS', 4 * 28 * 28)
MAX_PIXELS = getint_or_default('MAX_PIXELS', 1280 * 28 * 28)
VIT_ROUTE = getenv_or_default('VIT_ROUTE', 'default_vit')
VIT_DISAGGREGATE = getbool_or_default('VIT_DISAGGREGATE', False)

# vLLM
VLLM_ENGINE_TYPE = getenv_or_default('VLLM_ENGINE_TYPE', 'default')
VLLM_LOG_LEVEL = getenv_or_default('LOG_LEVEL', 'INFO')
VLLM_NUM_INSTANCES = getint_or_default('VLLM_NUM_INSTANCES', 1)
VLLM_CORE_NUM = getint_or_default('CORE_NUM', 20)
VLLM_SCHEDULER_BUDGET_LEN = getint_or_default('VLLM_SCHEDULER_BUDGET_LEN', 512)
VLLM_MAX_NUM_SEQS = getint_or_default('VLLM_MAX_NUM_SEQS', 32)
VLLM_SWAP_SPACE = getint_or_default('VLLM_SWAP_SPACE', 48)
VLLM_TOKENIZER_MODE = getenv_or_default('VLLM_TOKENIZER_MODE', "slow")
VLLM_BLOCK_SIZE = getint_or_default('VLLM_BLOCK_SIZE', 128)
VLLM_GPU_BLOCKS = getenv_or_default('VLLM_GPU_BLOCKS', None)
VLLM_CPU_BLOCKS = getenv_or_default('VLLM_CPU_BLOCKS', None)
VLLM_OPS_DEV_MODE = getenv_or_default('VLLM_OPS_DEV_MODE', None)
VLLM_MAX_MODEL_LEN = getint_or_default('VLLM_MAX_MODEL_LEN', None)
VLLM_MAX_PROMPT_LEN = getenv_or_default('VLLM_MAX_PROMPT_LEN', None)
VLLM_ARCHITECTURES = getenv_or_default('VLLM_ARCHITECTURES', None)
VLLM_DISABLE_LOG_REQUESTS = getbool_or_default('VLLM_DISABLE_LOG_REQUESTS', True)
VLLM_RAY_ENGINE_TYPE = getenv_or_default('VLLM_RAY_ENGINE_TYPE', 'RayAsyncLLMEngine')
VLLM_RAY_CLUSTER_NAMESPACE = getenv_or_default(
    'VLLM_RAY_CLUSTER_NAMESPACE', MEP_GROUP_NAME if MEP_GROUP_NAME else 'ray_cluster')
VLLM_PP_GROUP_SPECIFICATIONS = getenv_or_default('VLLM_PP_GROUP_SPECIFICATIONS', '1:1:P|1:1:D').replace("|", ";")
VLLM_REDIRECT_LOG_DIR = getenv_or_default('VLLM_REDIRECT_LOG_DIR', '/opt/huawei/log/engine')
VLLM_ORIG_LOG_DIR = getenv_or_default('VLLM_ORIG_LOG_DIR', '/opt/huawei/log/engine/ray/session_latest/logs')
VLLM_RAY_LOG_DIR = getenv_or_default('VLLM_RAY_LOG_DIR', '/opt/huawei/log/engine/ray')
VLLM_RUNTIME_DIRECT_CONNECTION_ENABLED = getenv_or_default('VLLM_RUNTIME_DIRECT_CONNECTION_ENABLED', 'true')
VLLM_ENABLE_FUSE_PREFILL_AND_DECODE = getbool_or_default('VLLM_ENABLE_FUSE_PREFILL_AND_DECODE', True)
VLLM_ENABLE_CHUNKED_PREFILL = getbool_or_default('VLLM_ENABLE_CHUNKED_PREFILL', True)
VLLM_ENABLE_BATCHING_PREFILL = getbool_or_default('VLLM_ENABLE_BATCHING_PREFILL', True)
VLLM_DEEPSEEK_V3_USE_EP = getbool_or_default('VLLM_DEEPSEEK_V3_USE_EP', True)
VLLM_CHUNK_SIZE = getint_or_default('VLLM_CHUNK_SIZE', 2) * 1024 * 1024
setenv_if_exists('RAY_EXPERIMENTAL_NOSET_ASCEND_RT_VISIBLE_DEVICES', '1')
setenv_if_exists('RAY_ENGINE_TYPE', VLLM_RAY_ENGINE_TYPE)
setenv_if_exists('CLUSTER_NAMESPACE_KEY', VLLM_RAY_CLUSTER_NAMESPACE)
setenv_if_exists('GPU_BLOCKS', VLLM_GPU_BLOCKS)
setenv_if_exists('CPU_BLOCKS', VLLM_CPU_BLOCKS)
setenv_if_exists('REDIRECT_LOG_DIR', VLLM_REDIRECT_LOG_DIR)
setenv_if_exists('ORIG_LOG_DIR', VLLM_ORIG_LOG_DIR)
setenv_if_exists('RAY_LOG_PATH', VLLM_RAY_LOG_DIR)
setenv_if_exists('RUNTIME_DIRECT_CONNECTION_ENABLE', VLLM_RUNTIME_DIRECT_CONNECTION_ENABLED)
# vLLM - 卡内PD分离
VLLM_DISAGGREGATE_ENABLED = getbool_or_default('VLLM_DISAGGREGATE_ENABLED', False)
VLLM_DISAGGREGATE_PD_CORE_NUM = getenv_or_default('VLLM_DISAGGREGATE_PD_CORE_NUM', '14,6')
os.environ['DIS_PD_CORE_NUM'] = VLLM_DISAGGREGATE_PD_CORE_NUM
# vLLM - 卡间PD分离
VLLM_USE_YR = getenv_or_default('VLLM_USE_YR', 'False')
VLLM_DISAGGREGATE_REDIS_IP = getenv_or_default('VLLM_DISAGGREGATE_REDIS_IP', '')
VLLM_DISAGGREGATE_REDIS_PORT = getenv_or_default('VLLM_DISAGGREGATE_REDIS_PORT', '2881')
VLLM_DISAGGREGATE_REDIS_AUTH = getenv_or_default('VLLM_DISAGGREGATE_REDIS_AUTH', '')
VLLM_DISAGGREGATE_REDIS_USER = getenv_or_default('VLLM_DISAGGREGATE_REDIS_USER', 'default')
VLLM_DISAGGREGATE_P_RATIO = getenv_or_default('VLLM_DISAGGREGATE_P_RATIO', '0.75')
VLLM_DISAGGREGATE_D_RATIO = getenv_or_default('VLLM_DISAGGREGATE_D_RATIO', '0.25')
VLLM_DISAGGREGATE_M_RATIO = getenv_or_default('VLLM_DISAGGREGATE_M_RATIO', '0.0')
VLLM_DIST_DEPLOY_MODE = getenv_or_default('VLLM_DIST_DEPLOY_MODE', 'redis_one_group')
VLLM_ENGINE_ROLE = getenv_or_default('VLLM_ENGINE_ROLE', 'M')
VLLM_PREFILL_GROUP_NUM = getint_or_default('VLLM_PREFILL_GROUP_NUM')
VLLM_DECODE_GROUP_NUM = getint_or_default('VLLM_DECODE_GROUP_NUM')
VLLM_ENABLE_EXPERT_PARALLEL = getbool_or_default('VLLM_ENABLE_EXPERT_PARALLEL', False)
VLLM_DECODE_ENABLE_EXPERT_PARALLEL = getbool_or_default('VLLM_DECODE_ENABLE_EXPERT_PARALLEL', False)
VLLM_ENABLE_LOOKAHEAD_SCHEDULING = getbool_or_default('VLLM_ENABLE_LOOKAHEAD_SCHEDULING', False)
VLLM_PP_LAYER_PARTITION = getenv_or_default('VLLM_PP_LAYER_PARTITION', None)
VLLM_DECODE_PP_LAYER_PARTITION = getenv_or_default('VLLM_DECODE_PP_LAYER_PARTITION', '')
VLLM_ENABLE_BYPASS_BALANCER = getbool_or_default('VLLM_ENABLE_BYPASS_BALANCER', False)
VLLM_HCCL_PORT_START = getint_or_default('VLLM_HCCL_PORT_START', 9000)
VLLM_HCCL_PORT_INTERVAL = getint_or_default('VLLM_HCCL_PORT_INTERVAL', 100)
VLLM_START_LCAL_IF_PORT = getint_or_default('VLLM_START_LCAL_IF_PORT', 6400)
VLLM_START_HTTP_SERVER_PORT = getint_or_default('VLLM_START_HTTP_SERVER_PORT', 29000)
VLLM_DEV_USE_ZMQ_STREAMING = str(getbool_or_default('VLLM_DEV_USE_ZMQ_STREAMING', 'False'))
VLLM_DEV_ENABLE_DIFF_APPLY = str(getbool_or_default('VLLM_DEV_ENABLE_DIFF_APPLY', 'False'))
VLLM_SCHEDULE_POLICY = getenv_or_default('VLLM_SCHEDULE_POLICY')
setenv_if_exists('USE_YR', VLLM_USE_YR)
setenv_if_exists('REDIS_IP', VLLM_DISAGGREGATE_REDIS_IP)
setenv_if_exists('REDIS_PORT', VLLM_DISAGGREGATE_REDIS_PORT)
setenv_if_exists('REDIS_AUTH', VLLM_DISAGGREGATE_REDIS_AUTH)
setenv_if_exists('REDIS_USER', VLLM_DISAGGREGATE_REDIS_USER)
setenv_if_exists('P_RATIO', VLLM_DISAGGREGATE_P_RATIO)
setenv_if_exists('D_RATIO', VLLM_DISAGGREGATE_D_RATIO)
setenv_if_exists('M_RATIO', VLLM_DISAGGREGATE_M_RATIO)
setenv_if_exists('VLLM_PP_LAYER_PARTITION', VLLM_PP_LAYER_PARTITION)
setenv_if_exists('VLLM_DEV_USE_ZMQ_STREAMING', "false")
setenv_if_exists('VLLM_DEV_ENABLE_DIFF_APPLY', "false")
# Parse from MEP environments
MEP_RTC_ROLE = getenv_or_default('MEP_RTC_ROLE', None)
if MEP_RTC_ROLE:
    if MEP_RTC_ROLE == 'prompt':
        value_ = 'P'
    elif MEP_RTC_ROLE == "Vision":
        value_ = MEP_RTC_ROLE
    else:
        value_ = 'D'
    setenv_if_exists('VLLM_ENGINE_ROLE', value_)
    VLLM_ENGINE_ROLE = value_
# Set VLLM_DEEPSEEK_V3_USE_EP by engine role
if VLLM_ENGINE_ROLE == 'P':
    setenv_if_exists('VLLM_DEEPSEEK_V3_USE_EP', str(VLLM_ENABLE_EXPERT_PARALLEL))
elif VLLM_ENGINE_ROLE == 'D':
    setenv_if_exists('VLLM_DEEPSEEK_V3_USE_EP', str(VLLM_DECODE_ENABLE_EXPERT_PARALLEL))
    setenv_if_exists('VLLM_PP_LAYER_PARTITION', str(VLLM_DECODE_PP_LAYER_PARTITION))
    setenv_if_exists('PREFILL_VLLM_PP_LAYER_PARTITION', str(VLLM_PP_LAYER_PARTITION))

# vLLM - 量化
VLLM_QUANTIZATION = getenv_or_default('VLLM_QUANTIZATION', None)
# vLLM - Auto Prefix Sharing
VLLM_PREFIX_SHARING_TYPE = getenv_or_default('VLLM_PREFIX_SHARING_TYPE')
# vLLM - Auto Prefix Sharing - 前缀KV缓存最多可占用总共NPU KV pool的比例
VLLM_PREFIX_SHARING_GPU_USAGE_THRESHOLD = getfloat_or_default('VLLM_PREFIX_SHARING_GPU_USAGE_THRESHOLD', 0.7)
# vLLM - Auto Prefix Sharing - 当前缀KV缓存比例的超阈值后，一次老化的前缀KV缓存的大小（总共NPU KV pool的比例）
VLLM_PREFIX_SHARING_EVICT_GPU_USAGE = getfloat_or_default('VLLM_PREFIX_SHARING_EVICT_GPU_USAGE', 0.2)
# vLLM - 投机
VLLM_SPECULATE_TYPE = getenv_or_default('VLLM_SPECULATE_TYPE', '')
VLLM_SPECULATE_PIA_ADAPTIVE_ENABLED = getbool_or_default('VLLM_SPECULATE_PIA_ADAPTIVE_ENABLED', False)
VLLM_SPECULATE_VNL_USE_DATASTORE = getbool_or_default('VLLM_SPECULATE_VNL_USE_DATASTORE', False)
VLLM_SPECULATE_VNL_DECODING_LENGTH = getint_or_default('VLLM_SPECULATE_VNL_DECODING_LENGTH', 12)
VLLM_SPECULATE_VNL_ASYNC_UPDATE_DATASTORE = getbool_or_default('VLLM_SPECULATE_VNL_ASYNC_UPDATE_DATASTORE', True)
# vLLM - 长序列
VLLM_LONG_CONTEXT_ENABLED = getbool_or_default('VLLM_LONG_CONTEXT_ENABLED', False)
setenv_if_exists('LONG_CONTEXT', str(VLLM_LONG_CONTEXT_ENABLED))
# vLLM - EMS加速
VLLM_EMS_ACCELERATE_ID = os.getenv('ACCELERATE_ID', '')
VLLM_EMS_ACCELERATE_KEY = os.getenv('ACCELERATE_KEY', '')
setenv_if_exists('VLLM_EMS_ACCELERATE_ID', VLLM_EMS_ACCELERATE_ID)
setenv_if_exists('VLLM_EMS_ACCELERATE_KEY', VLLM_EMS_ACCELERATE_KEY)
setenv_if_exists('VLLM_WORKER_MULTIPROC_METHOD', 'spawn')

VLLM_MAX_LOG_LEN = getint_or_default('VLLM_MAX_LOG_LEN', 10)
# Print all environments
print("Environments:")
for name_, value_ in list(os.environ.items()):
    if is_uppercase_underscore(name_):
        print(f"{name_}={value_}")

# Type of message.
RequestType = TypeVar("RequestType", bound=betterproto.Message)
ResponseType = TypeVar("ResponseType", bound=betterproto.Message)


# qwen series vit image process config
MIN_PIXELS = getint_or_default("MIN_PIXELS", 4 * 32 * 32)
MAX_PIXELS = getint_or_default("MAX_PIXELS", 8192 * 32 * 32)
FACTOR = getint_or_default("FACTOR", 32)
setenv_if_exists('MIN_PIXELS', str(MIN_PIXELS))
setenv_if_exists('MAX_PIXELS', str(MAX_PIXELS))