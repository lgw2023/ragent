from __future__ import annotations
import weakref
import contextvars
import threading

import asyncio
import html
import csv
import json
import logging
import logging.handlers
import os
import re
from contextlib import contextmanager
from pathlib import Path

from ragent.runtime_env import bootstrap_runtime_environment

bootstrap_runtime_environment()

# Before `litellm` is imported (see ragent.llm.openai): default to quiet SDK logs.
# Override with e.g. LITELLM_LOG=DEBUG in the environment when diagnosing calls.
os.environ.setdefault("LITELLM_LOG", "WARNING")
# Keep MEP/offline startup deterministic: LiteLLM otherwise tries to fetch its
# remote model cost map during import and falls back only after a network timeout.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from functools import partial, wraps
from hashlib import md5
from typing import Any, Protocol, Callable, TYPE_CHECKING, List
import numpy as np
from ragent.constants import (
    DEFAULT_LOG_MAX_BYTES,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_FILENAME,
)


def get_env_value(
    env_key: str, default: any, value_type: type = str, special_none: bool = False
) -> any:
    """
    Get value from environment variable with type conversion

    Args:
        env_key (str): Environment variable key
        default (any): Default value if env variable is not set
        value_type (type): Type to convert the value to
        special_none (bool): If True, return None when value is "None"

    Returns:
        any: Converted value from environment or default
    """
    value = os.getenv(env_key)
    if value is None:
        return default

    # Handle special case for "None" string
    if special_none and value == "None":
        return None

    if value_type is bool:
        return value.lower() in ("true", "1", "yes", "t", "on")
    try:
        return value_type(value)
    except (ValueError, TypeError):
        return default


def get_configured_embedding_dimensions() -> str | None:
    return os.getenv("EMBEDDING_DIMENSIONS") or os.getenv("EMBEDDING_DIM")


def get_configured_embedding_dim(default: int = 1024) -> int:
    configured_dimensions = get_configured_embedding_dimensions()
    if configured_dimensions is None:
        return default
    try:
        return int(configured_dimensions)
    except (TypeError, ValueError):
        return default


# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ragent.base import BaseKVStorage

VERBOSE_DEBUG = os.getenv("VERBOSE", "false").lower() == "true"


def _is_model_log_enabled() -> bool:
    """Model-related runtime logs are printed only in debug by default.

    Env override:
    - RAG_TRACE_MODEL_CALLS=1: force enable
    - RAG_TRACE_MODEL_CALLS=0: force disable
    """
    env_value = os.getenv("RAG_TRACE_MODEL_CALLS")
    if env_value is not None:
        return env_value.lower() in ("1", "true", "yes", "on")
    return VERBOSE_DEBUG or logger.isEnabledFor(logging.DEBUG)


def verbose_debug(msg: str, *args, **kwargs):
    """Function for outputting detailed debug information.
    When VERBOSE_DEBUG=True, outputs the complete message.
    When VERBOSE_DEBUG=False, outputs only the first 50 characters.

    Args:
        msg: The message format string
        *args: Arguments to be formatted into the message
        **kwargs: Keyword arguments passed to logger.debug()
    """
    if VERBOSE_DEBUG:
        logger.debug(msg, *args, **kwargs)
    else:
        # Format the message with args first
        if args:
            formatted_msg = msg % args
        else:
            formatted_msg = msg
        # Then truncate the formatted message
        truncated_msg = (
            formatted_msg[:100] + "..." if len(formatted_msg) > 100 else formatted_msg
        )
        logger.debug(truncated_msg, **kwargs)


def set_verbose_debug(enabled: bool):
    """Enable or disable verbose debug output"""
    global VERBOSE_DEBUG
    VERBOSE_DEBUG = enabled


statistic_data = {"llm_call": 0, "llm_cache": 0, "embed_call": 0}
_CURRENT_MODEL_USAGE_COLLECTOR: contextvars.ContextVar["ModelUsageCollector | None"] = (
    contextvars.ContextVar("current_model_usage_collector", default=None)
)
_CURRENT_MODEL_USAGE_STAGE: contextvars.ContextVar[dict[str, str] | None] = (
    contextvars.ContextVar("current_model_usage_stage", default=None)
)

_SENSITIVE_LOG_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "token",
    "access_token",
    "secret",
}

# Initialize logger
logger = logging.getLogger("ragent")
logger.propagate = False  # prevent log message send to root loggger
# Let the main application configure the handlers
logger.setLevel(logging.INFO)
if not logger.handlers:
    _default_stream_handler = logging.StreamHandler()
    _default_stream_handler.setLevel(logging.INFO)
    _default_stream_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s")
    )
    logger.addHandler(_default_stream_handler)

# Set httpx logging level to WARNING
logging.getLogger("httpx").setLevel(logging.WARNING)


def is_verbose_error_logging_enabled() -> bool:
    """Detailed exception logs are opt-in by default.

    Env override:
    - RAG_VERBOSE_ERRORS=1: force enable traceback/context logs
    - RAG_VERBOSE_ERRORS=0: force disable traceback/context logs
    """
    env_value = os.getenv("RAG_VERBOSE_ERRORS")
    if env_value is not None:
        return env_value.lower() in ("1", "true", "yes", "on")
    return VERBOSE_DEBUG or logger.isEnabledFor(logging.DEBUG)


def format_exception_brief(exc: BaseException) -> str:
    """Format exceptions as `module.ExceptionName: message`."""
    exc_type = type(exc)
    module = exc_type.__module__
    qualname = getattr(exc_type, "__qualname__", exc_type.__name__)
    type_name = qualname if module in {"builtins", "__main__"} else f"{module}.{qualname}"
    message = str(exc).strip()
    return f"{type_name}: {message}" if message else type_name


def mark_exception_logged(exc: BaseException) -> None:
    try:
        setattr(exc, "_ragent_logged", True)
    except Exception:
        pass


def is_exception_logged(exc: BaseException) -> bool:
    return bool(getattr(exc, "_ragent_logged", False))


def log_exception(
    message: str | None,
    exc: BaseException,
    *,
    context: Any | None = None,
    level: int = logging.ERROR,
) -> None:
    """Log a short exception by default; include traceback/context in debug mode."""
    brief = format_exception_brief(exc)
    detailed = is_verbose_error_logging_enabled()
    log_kwargs = {}
    if detailed:
        log_kwargs["exc_info"] = (type(exc), exc, exc.__traceback__)

    if context is not None and detailed:
        if message:
            logger.log(level, "%s: %s\nContext: %s", message, brief, context, **log_kwargs)
        else:
            logger.log(level, "%s\nContext: %s", brief, context, **log_kwargs)
    elif message:
        logger.log(level, "%s: %s", message, brief, **log_kwargs)
    else:
        logger.log(level, "%s", brief, **log_kwargs)

    mark_exception_logged(exc)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in _SENSITIVE_LOG_KEYS)


def _sample_text_for_model_log(text: str, sample_len: int = 500) -> str:
    text_len = len(text)
    if text_len <= sample_len:
        return text
    return f"{text[:sample_len]}... (truncated, len={text_len})"


def _sanitize_for_model_log(value: Any):
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if _is_sensitive_key(key):
                sanitized[key] = "***"
            else:
                sanitized[key] = _sanitize_for_model_log(v)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_model_log(v) for v in value]
    if isinstance(value, str):
        return _sample_text_for_model_log(value)
    return value


def _flatten_for_model_log(prefix: str, value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        items: list[tuple[str, Any]] = []
        for k, v in value.items():
            key = str(k)
            new_prefix = f"{prefix}.{key}" if prefix else key
            items.extend(_flatten_for_model_log(new_prefix, v))
        return items

    return [(prefix, value)]


def _format_model_log_value(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, default=str)


def log_model_call(module: str, params: dict[str, Any]) -> None:
    """Log model call params in env-like key=value lines."""
    if not _is_model_log_enabled():
        return
    try:
        sanitized = _sanitize_for_model_log(params)
        flat_items = _flatten_for_model_log("", sanitized)
        payload_lines = [f"{k}={_format_model_log_value(v)}" for k, v in flat_items]
    except Exception:
        payload_lines = [f"params={repr(_sanitize_for_model_log(params))}"]
    message = "\n".join([f"[MODEL-CALL] module={module}", *payload_lines])
    logger.debug(message)


class RagentPathFilter(logging.Filter):
    """Filter for ragent logger to filter out frequent path access logs"""

    def __init__(self):
        super().__init__()
        # Define paths to be filtered
        self.filtered_paths = [
            "/documents",
            "/health",
            "/webui/",
            "/documents/pipeline_status",
        ]
        # self.filtered_paths = ["/health", "/webui/"]

    def filter(self, record):
        try:
            # Check if record has the required attributes for an access log
            if not hasattr(record, "args") or not isinstance(record.args, tuple):
                return True
            if len(record.args) < 5:
                return True

            # Extract method, path and status from the record args
            method = record.args[1]
            path = record.args[2]
            status = record.args[4]

            # Filter out successful GET requests to filtered paths
            if (
                method == "GET"
                and (status == 200 or status == 304)
                and path in self.filtered_paths
            ):
                return False

            return True
        except Exception:
            # In case of any error, let the message through
            return True

class UnlimitedSemaphore:
    """A context manager that allows unlimited access."""

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        pass


@dataclass
class EmbeddingFunc:
    embedding_dim: int
    max_token_size: int
    func: callable
    # concurrent_limit: int = 16

    async def __call__(self, *args, **kwargs) -> np.ndarray:
        return await self.func(*args, **kwargs)


def locate_json_string_body_from_string(content: str) -> str | None:
    """Locate the JSON string body from a string"""
    try:
        maybe_json_str = re.search(r"{.*}", content, re.DOTALL)
        if maybe_json_str is not None:
            maybe_json_str = maybe_json_str.group(0)
            maybe_json_str = maybe_json_str.replace("\\n", "")
            maybe_json_str = maybe_json_str.replace("\n", "")
            maybe_json_str = maybe_json_str.replace("'", '"')
            # json.loads(maybe_json_str) # don't check here, cannot validate schema after all
            return maybe_json_str
    except Exception:
        pass
        return None


def convert_response_to_json(response: str) -> dict[str, Any]:
    json_str = locate_json_string_body_from_string(response)
    assert json_str is not None, f"Unable to parse JSON from response: {response}"
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {json_str}")
        raise e from None


_HASH_UNSERIALIZABLE = object()


def resolve_callable_cache_id(value: Any) -> Any | None:
    """Build a stable identifier for cache-relevant callables.

    Returns a JSON-serializable structure when the callable can be identified
    without relying on memory addresses; otherwise returns None.
    """
    if value is None or not callable(value):
        return None

    if isinstance(value, partial):
        func_id = resolve_callable_cache_id(value.func)
        if func_id is None:
            return None
        normalized_args = _normalize_value_for_hash(list(value.args), strict=True)
        normalized_kwargs = _normalize_value_for_hash(value.keywords or {}, strict=True)
        if (
            normalized_args is _HASH_UNSERIALIZABLE
            or normalized_kwargs is _HASH_UNSERIALIZABLE
        ):
            return None
        return {
            "callable_type": "partial",
            "func": func_id,
            "args": normalized_args,
            "keywords": normalized_kwargs,
        }

    module = getattr(value, "__module__", None)
    qualname = getattr(value, "__qualname__", None)
    if module and qualname:
        identity: dict[str, Any] = {
            "callable_type": "function",
            "module": module,
            "qualname": qualname,
        }
    else:
        cls = getattr(value, "__class__", None)
        cls_module = getattr(cls, "__module__", None) if cls else None
        cls_qualname = getattr(cls, "__qualname__", None) if cls else None
        if not cls_module or not cls_qualname:
            return None
        identity = {
            "callable_type": "callable_instance",
            "module": cls_module,
            "qualname": cls_qualname,
        }

    for attr_name in ("model_name", "name"):
        attr_value = getattr(value, attr_name, None)
        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
            if attr_value not in (None, ""):
                identity[attr_name] = attr_value

    return identity


def _normalize_value_for_hash(value: Any, *, strict: bool) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, float):
        if value != value:
            return "NaN"
        if value == float("inf"):
            return "Infinity"
        if value == float("-inf"):
            return "-Infinity"
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, bytes):
        return {"__type__": "bytes", "hex": value.hex()}

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, np.generic):
        return _normalize_value_for_hash(value.item(), strict=strict)

    if isinstance(value, np.ndarray):
        return _normalize_value_for_hash(value.tolist(), strict=strict)

    if is_dataclass(value) and not isinstance(value, type):
        return _normalize_value_for_hash(asdict(value), strict=strict)

    if isinstance(value, dict):
        normalized_items: dict[str, Any] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            normalized_value = _normalize_value_for_hash(value[key], strict=strict)
            if normalized_value is _HASH_UNSERIALIZABLE:
                return _HASH_UNSERIALIZABLE
            normalized_items[str(key)] = normalized_value
        return normalized_items

    if isinstance(value, (list, tuple)):
        normalized_items = []
        for item in value:
            normalized_item = _normalize_value_for_hash(item, strict=strict)
            if normalized_item is _HASH_UNSERIALIZABLE:
                return _HASH_UNSERIALIZABLE
            normalized_items.append(normalized_item)
        return normalized_items

    if isinstance(value, set):
        normalized_items = []
        for item in value:
            normalized_item = _normalize_value_for_hash(item, strict=strict)
            if normalized_item is _HASH_UNSERIALIZABLE:
                return _HASH_UNSERIALIZABLE
            normalized_items.append(normalized_item)
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True),
        )

    if callable(value):
        callable_id = resolve_callable_cache_id(value)
        if callable_id is not None:
            return callable_id
        if strict:
            return _HASH_UNSERIALIZABLE

    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True)
        return value
    except TypeError:
        if strict:
            return _HASH_UNSERIALIZABLE
        return {
            "__type__": f"{type(value).__module__}.{type(value).__qualname__}",
            "repr": repr(value),
        }


def compute_structured_hash(data: Any, *, strict: bool = False) -> str | None:
    """Compute a stable MD5 hash from JSON-serializable structured data."""
    import hashlib

    normalized = _normalize_value_for_hash(data, strict=strict)
    if normalized is _HASH_UNSERIALIZABLE:
        return None
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def compute_args_hash(*args: Any) -> str:
    """Compute a stable hash for the given arguments.

    Args:
        *args: Arguments to hash
    Returns:
        str: Hash string
    """
    hash_value = compute_structured_hash(list(args))
    if hash_value is None:
        raise ValueError("Arguments cannot be serialized into a stable cache hash")
    return hash_value


def generate_cache_key(mode: str, cache_type: str, hash_value: str) -> str:
    """Generate a flattened cache key in the format {mode}:{cache_type}:{hash}

    Args:
        mode: Cache mode (e.g., 'graph', "hybrid")
        cache_type: Type of cache (e.g., 'extract', 'query', 'keywords')
        hash_value: Hash value from compute_args_hash

    Returns:
        str: Flattened cache key
    """
    return f"{mode}:{cache_type}:{hash_value}"


def parse_cache_key(cache_key: str) -> tuple[str, str, str] | None:
    """Parse a flattened cache key back into its components

    Args:
        cache_key: Flattened cache key in format {mode}:{cache_type}:{hash}

    Returns:
        tuple[str, str, str] | None: (mode, cache_type, hash) or None if invalid format
    """
    parts = cache_key.split(":", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return None


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    """
    Compute a unique ID for a given content string.

    The ID is a combination of the given prefix and the MD5 hash of the content string.
    """
    return prefix + md5(content.encode()).hexdigest()


# Custom exception class
class QueueFullError(Exception):
    """Raised when the queue is full and the wait times out"""

    pass


def priority_limit_async_func_call(
    max_size: int, max_queue_size: int = 1000, label: str | None = None
):
    """
    Enhanced priority-limited asynchronous function call decorator

    Args:
        max_size: Maximum number of concurrent calls
        max_queue_size: Maximum queue capacity to prevent memory overflow
    Returns:
        Decorator function
    """

    def final_decro(func):
        # Ensure func is callable
        if not callable(func):
            raise TypeError(f"Expected a callable object, got {type(func)}")
        log_prefix = f"limit_async[{label}]" if label else "limit_async"
        queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        tasks = set()
        initialization_lock = asyncio.Lock()
        counter = 0
        shutdown_event = asyncio.Event()
        initialized = False  # Global initialization flag
        worker_health_check_task = None

        # Track active future objects for cleanup
        active_futures = weakref.WeakSet()
        reinit_count = 0  # Reinitialization counter to track system health

        # Worker function to process tasks in the queue
        async def worker():
            """Worker that processes tasks in the priority queue"""
            try:
                while not shutdown_event.is_set():
                    try:
                        # Use timeout to get tasks, allowing periodic checking of shutdown signal
                        try:
                            (
                                priority,
                                count,
                                future,
                                args,
                                kwargs,
                                call_context,
                            ) = await asyncio.wait_for(queue.get(), timeout=1.0)
                        except asyncio.TimeoutError:
                            # Timeout is just to check shutdown signal, continue to next iteration
                            continue

                        # If future is cancelled, skip execution
                        if future.cancelled():
                            queue.task_done()
                            continue

                        try:
                            # Execute function
                            coro = call_context.run(func, *args, **kwargs)
                            task = asyncio.create_task(coro, context=call_context)
                            result = await task
                            # If future is not done, set the result
                            if not future.done():
                                future.set_result(result)
                        except asyncio.CancelledError:
                            if not future.done():
                                future.cancel()
                            logger.debug(f"{log_prefix}: Task cancelled during execution")
                        except Exception as e:
                            logger.error(
                                f"{log_prefix}: Error in decorated function: {str(e)}"
                            )
                            if not future.done():
                                future.set_exception(e)
                        finally:
                            queue.task_done()
                    except Exception as e:
                        # Catch all exceptions in worker loop to prevent worker termination
                        logger.error(f"{log_prefix}: Critical error in worker: {str(e)}")
                        await asyncio.sleep(0.1)  # Prevent high CPU usage
            finally:
                logger.debug(f"{log_prefix}: Worker exiting")

        async def health_check():
            """Periodically check worker health status and recover"""
            nonlocal initialized
            try:
                while not shutdown_event.is_set():
                    await asyncio.sleep(5)  # Check every 5 seconds

                    # No longer acquire lock, directly operate on task set
                    # Use a copy of the task set to avoid concurrent modification
                    current_tasks = set(tasks)
                    done_tasks = {t for t in current_tasks if t.done()}
                    tasks.difference_update(done_tasks)

                    # Calculate active tasks count
                    active_tasks_count = len(tasks)
                    workers_needed = max_size - active_tasks_count

                    if workers_needed > 0:
                        logger.info(f"{log_prefix}: Creating {workers_needed} new workers")
                        new_tasks = set()
                        for _ in range(workers_needed):
                            task = asyncio.create_task(worker())
                            new_tasks.add(task)
                            task.add_done_callback(tasks.discard)
                        # Update task set in one operation
                        tasks.update(new_tasks)
            except Exception as e:
                logger.error(f"{log_prefix}: Error in health check: {str(e)}")
            finally:
                logger.debug(f"{log_prefix}: Health check task exiting")
                initialized = False

        async def ensure_workers():
            """Ensure worker threads and health check system are available

            This function checks if the worker system is already initialized.
            If not, it performs a one-time initialization of all worker threads
            and starts the health check system.
            """
            nonlocal initialized, worker_health_check_task, tasks, reinit_count

            if initialized:
                return

            async with initialization_lock:
                if initialized:
                    return

                # Increment reinitialization counter if this is not the first initialization
                if reinit_count > 0:
                    reinit_count += 1
                    logger.warning(
                        f"{log_prefix}: Reinitializing needed (count: {reinit_count})"
                    )
                else:
                    reinit_count = 1  # First initialization

                # Check for completed tasks and remove them from the task set
                current_tasks = set(tasks)
                done_tasks = {t for t in current_tasks if t.done()}
                tasks.difference_update(done_tasks)

                # Log active tasks count during reinitialization
                active_tasks_count = len(tasks)
                if active_tasks_count > 0 and reinit_count > 1:
                    logger.warning(
                        f"{log_prefix}: {active_tasks_count} tasks still running during reinitialization"
                    )

                # Create initial worker tasks, only adding the number needed
                workers_needed = max_size - active_tasks_count
                for _ in range(workers_needed):
                    task = asyncio.create_task(worker())
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)

                # Start health check
                worker_health_check_task = asyncio.create_task(health_check())

                initialized = True
                logger.info(f"{log_prefix}: {workers_needed} new workers initialized")

        async def shutdown():
            """Gracefully shut down all workers and the queue"""
            logger.info(f"{log_prefix}: Shutting down priority queue workers")

            # Set the shutdown event
            shutdown_event.set()

            # Cancel all active futures
            for future in list(active_futures):
                if not future.done():
                    future.cancel()

            # Wait for the queue to empty
            try:
                await asyncio.wait_for(queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(
                    f"{log_prefix}: Timeout waiting for queue to empty during shutdown"
                )

            # Cancel all worker tasks
            for task in list(tasks):
                if not task.done():
                    task.cancel()

            # Wait for all tasks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Cancel the health check task
            if worker_health_check_task and not worker_health_check_task.done():
                worker_health_check_task.cancel()
                try:
                    await worker_health_check_task
                except asyncio.CancelledError:
                    pass

            logger.info(f"{log_prefix}: Priority queue workers shutdown complete")

        @wraps(func)
        async def wait_func(
            *args, _priority=10, _timeout=None, _queue_timeout=None, **kwargs
        ):
            """
            Execute the function with priority-based concurrency control
            Args:
                *args: Positional arguments passed to the function
                _priority: Call priority (lower values have higher priority)
                _timeout: Maximum time to wait for function completion (in seconds)
                _queue_timeout: Maximum time to wait for entering the queue (in seconds)
                **kwargs: Keyword arguments passed to the function
            Returns:
                The result of the function call
            Raises:
                TimeoutError: If the function call times out
                QueueFullError: If the queue is full and waiting times out
                Any exception raised by the decorated function
            """
            # Ensure worker system is initialized
            await ensure_workers()

            # Create a future for the result
            future = asyncio.Future()
            active_futures.add(future)

            nonlocal counter
            async with initialization_lock:
                current_count = counter  # Use local variable to avoid race conditions
                counter += 1

            # Try to put the task into the queue, supporting timeout
            call_context = contextvars.copy_context()
            try:
                if _queue_timeout is not None:
                    # Use timeout to wait for queue space
                    try:
                        await asyncio.wait_for(
                            # current_count is used to ensure FIFO order
                            queue.put(
                                (
                                    _priority,
                                    current_count,
                                    future,
                                    args,
                                    kwargs,
                                    call_context,
                                )
                            ),
                            timeout=_queue_timeout,
                        )
                    except asyncio.TimeoutError:
                        raise QueueFullError(
                            f"Queue full, timeout after {_queue_timeout} seconds"
                        )
                else:
                    # No timeout, may wait indefinitely
                    # current_count is used to ensure FIFO order
                    await queue.put(
                        (
                            _priority,
                            current_count,
                            future,
                            args,
                            kwargs,
                            call_context,
                        )
                    )
            except Exception as e:
                # Clean up the future
                if not future.done():
                    future.set_exception(e)
                active_futures.discard(future)
                raise

            try:
                # Wait for the result, optional timeout
                if _timeout is not None:
                    try:
                        return await asyncio.wait_for(future, _timeout)
                    except asyncio.TimeoutError:
                        # Cancel the future
                        if not future.done():
                            future.cancel()
                        raise TimeoutError(
                            f"{log_prefix}: Task timed out after {_timeout} seconds"
                        )
                else:
                    # Wait for the result without timeout
                    return await future
            finally:
                # Clean up the future reference
                active_futures.discard(future)

        # Add the shutdown method to the decorated function
        wait_func.shutdown = shutdown

        return wait_func

    return final_decro


def wrap_embedding_func_with_attrs(**kwargs):
    """Wrap a function with attributes"""

    def final_decro(func) -> EmbeddingFunc:
        new_func = EmbeddingFunc(**kwargs, func=func)
        return new_func

    return final_decro


def load_json(file_name):
    if not os.path.exists(file_name):
        return None
    with open(file_name, encoding="utf-8") as f:
        return json.load(f)


def write_json(json_obj, file_name):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)


class TokenizerInterface(Protocol):
    """
    Defines the interface for a tokenizer, requiring encode and decode methods.
    """

    def encode(self, content: str) -> List[int]:
        """Encodes a string into a list of tokens."""
        ...

    def decode(self, tokens: List[int]) -> str:
        """Decodes a list of tokens into a string."""
        ...


class Tokenizer:
    """
    A wrapper around a tokenizer to provide a consistent interface for encoding and decoding.
    """

    def __init__(self, model_name: str, tokenizer: TokenizerInterface):
        """
        Initializes the Tokenizer with a tokenizer model name and a tokenizer instance.

        Args:
            model_name: The associated model name for the tokenizer.
            tokenizer: An instance of a class implementing the TokenizerInterface.
        """
        self.model_name: str = model_name
        self.tokenizer: TokenizerInterface = tokenizer

    def encode(self, content: str) -> List[int]:
        """
        Encodes a string into a list of tokens using the underlying tokenizer.

        Args:
            content: The string to encode.

        Returns:
            A list of integer tokens.
        """
        return self.tokenizer.encode(content)

    def decode(self, tokens: List[int]) -> str:
        """
        Decodes a list of tokens into a string using the underlying tokenizer.

        Args:
            tokens: A list of integer tokens to decode.

        Returns:
            The decoded string.
        """
        return self.tokenizer.decode(tokens)


class TiktokenTokenizer(Tokenizer):
    """
    A Tokenizer implementation using the tiktoken library.
    """

    def __init__(self, model_name: str):
        """
        Initializes the TiktokenTokenizer with a specified model name.

        Args:
            model_name: The model name for the tiktoken tokenizer to use.

        Raises:
            ImportError: If tiktoken is not installed.
            ValueError: If the model_name is invalid.
        """
        try:
            import tiktoken
        except ImportError:
            raise ImportError(
                "tiktoken is not installed. Please install it with `pip install tiktoken` or define custom `tokenizer_func`."
            )

        try:
            tokenizer = tiktoken.encoding_for_model(model_name)
            super().__init__(model_name=model_name, tokenizer=tokenizer)
        except KeyError:
            raise ValueError(f"Invalid model_name: {model_name}.")


def pack_user_ass_to_openai_messages(*args: str):
    roles = ["user", "assistant"]
    return [
        {"role": roles[i % 2], "content": content} for i, content in enumerate(args)
    ]


def split_string_by_multi_markers(content: str, markers: list[str]) -> list[str]:
    """Split a string by multiple markers"""
    if not markers:
        return [content]
    content = content if content is not None else ""
    results = re.split("|".join(re.escape(marker) for marker in markers), content)
    return [r.strip() for r in results if r.strip()]


# Refer the utils functions of the official GraphRAG implementation:
def clean_str(input: Any) -> str:
    """Clean an input string by removing HTML escapes, control characters, and other unwanted characters."""
    # If we get non-string input, just give it back
    if not isinstance(input, str):
        return input

    result = html.unescape(input.strip())
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", result)


def is_float_regex(value: str) -> bool:
    return bool(re.match(r"^[-+]?[0-9]*\.?[0-9]+$", value))


def truncate_list_by_token_size(
    list_data: list[Any],
    key: Callable[[Any], str],
    max_token_size: int,
    tokenizer: Tokenizer,
) -> list[int]:
    """Truncate a list of data by token size"""
    if max_token_size <= 0:
        return []
    tokens = 0
    for i, data in enumerate(list_data):
        tokens += len(tokenizer.encode(key(data)))
        if tokens > max_token_size:
            return list_data[:i]
    return list_data


def process_combine_contexts(*context_lists):
    """
    Combine multiple context lists and remove duplicate content

    Args:
        *context_lists: Any number of context lists

    Returns:
        Combined context list with duplicates removed
    """
    seen_content = {}
    combined_data = []

    # Iterate through all input context lists
    for context_list in context_lists:
        if not context_list:  # Skip empty lists
            continue
        for item in context_list:
            content_dict = {
                k: v for k, v in item.items() if k != "id" and k != "created_at"
            }
            content_key = tuple(sorted(content_dict.items()))
            if content_key not in seen_content:
                seen_content[content_key] = item
                combined_data.append(item)

    # Reassign IDs
    for i, item in enumerate(combined_data):
        item["id"] = str(i + 1)

    return combined_data


def cosine_similarity(v1, v2):
    """Calculate cosine similarity between two vectors"""
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    return dot_product / (norm1 * norm2)


def quantize_embedding(embedding: np.ndarray | list[float], bits: int = 8) -> tuple:
    """Quantize embedding to specified bits"""
    # Convert list to numpy array if needed
    if isinstance(embedding, list):
        embedding = np.array(embedding)

    # Calculate min/max values for reconstruction
    min_val = embedding.min()
    max_val = embedding.max()

    if min_val == max_val:
        # handle constant vector
        quantized = np.zeros_like(embedding, dtype=np.uint8)
        return quantized, min_val, max_val

    # Quantize to 0-255 range
    scale = (2**bits - 1) / (max_val - min_val)
    quantized = np.round((embedding - min_val) * scale).astype(np.uint8)

    return quantized, min_val, max_val


def dequantize_embedding(
    quantized: np.ndarray, min_val: float, max_val: float, bits=8
) -> np.ndarray:
    """Restore quantized embedding"""
    if min_val == max_val:
        # handle constant vector
        return np.full_like(quantized, min_val, dtype=np.float32)

    scale = (max_val - min_val) / (2**bits - 1)
    return (quantized * scale + min_val).astype(np.float32)


async def handle_cache(
    hashing_kv,
    args_hash,
    prompt,
    mode="default",
    cache_type=None,
):
    """Generic cache handling function with flattened cache keys"""
    if hashing_kv is None:
        return None, None, None, None

    if mode != "default":  # handle cache for all type of query
        if not hashing_kv.global_config.get("enable_llm_cache"):
            return None, None, None, None
    else:  # handle cache for entity extraction
        if not hashing_kv.global_config.get("enable_llm_cache_for_entity_extract"):
            return None, None, None, None

    # Use flattened cache key format: {mode}:{cache_type}:{hash}
    flattened_key = generate_cache_key(mode, cache_type, args_hash)
    cache_entry = await hashing_kv.get_by_id(flattened_key)
    if cache_entry:
        logger.debug(f"Flattened cache hit(key:{flattened_key})")
        return cache_entry["return"], None, None, None

    logger.debug(f"Cache missed(mode:{mode} type:{cache_type})")
    return None, None, None, None


@dataclass
class CacheData:
    args_hash: str
    content: str
    prompt: str
    quantized: np.ndarray | None = None
    min_val: float | None = None
    max_val: float | None = None
    mode: str = "default"
    cache_type: str = "query"
    chunk_id: str | None = None


async def save_to_cache(hashing_kv, cache_data: CacheData):
    """Save data to cache using flattened key structure.

    Args:
        hashing_kv: The key-value storage for caching
        cache_data: The cache data to save
    """
    # Skip if storage is None or content is a streaming response
    if hashing_kv is None or not cache_data.content:
        return

    # If content is a streaming response, don't cache it
    if hasattr(cache_data.content, "__aiter__"):
        logger.debug("Streaming response detected, skipping cache")
        return

    # Use flattened cache key format: {mode}:{cache_type}:{hash}
    flattened_key = generate_cache_key(
        cache_data.mode, cache_data.cache_type, cache_data.args_hash
    )

    # Check if we already have identical content cached
    existing_cache = await hashing_kv.get_by_id(flattened_key)
    if existing_cache:
        existing_content = existing_cache.get("return")
        if existing_content == cache_data.content:
            logger.info(f"Cache content unchanged for {flattened_key}, skipping update")
            return

    # Create cache entry with flattened structure
    cache_entry = {
        "return": cache_data.content,
        "cache_type": cache_data.cache_type,
        "chunk_id": cache_data.chunk_id if cache_data.chunk_id is not None else None,
        "embedding": cache_data.quantized.tobytes().hex()
        if cache_data.quantized is not None
        else None,
        "embedding_shape": cache_data.quantized.shape
        if cache_data.quantized is not None
        else None,
        "embedding_min": cache_data.min_val,
        "embedding_max": cache_data.max_val,
        "original_prompt": cache_data.prompt,
    }

    logger.info(f" == LLM cache == saving: {flattened_key}")

    # Save using flattened key
    await hashing_kv.upsert({flattened_key: cache_entry})


def safe_unicode_decode(content):
    # Regular expression to find all Unicode escape sequences of the form \uXXXX
    unicode_escape_pattern = re.compile(r"\\u([0-9a-fA-F]{4})")

    # Function to replace the Unicode escape with the actual character
    def replace_unicode_escape(match):
        # Convert the matched hexadecimal value into the actual Unicode character
        return chr(int(match.group(1), 16))

    # Perform the substitution
    decoded_content = unicode_escape_pattern.sub(
        replace_unicode_escape, content.decode("utf-8")
    )

    return decoded_content


def exists_func(obj, func_name: str) -> bool:
    """Check if a function exists in an object or not.
    :param obj:
    :param func_name:
    :return: True / False
    """
    if callable(getattr(obj, func_name, None)):
        return True
    else:
        return False


def get_conversation_turns(
    conversation_history: list[dict[str, Any]], num_turns: int
) -> str:
    """
    Process conversation history to get the specified number of complete turns.

    Args:
        conversation_history: List of conversation messages in chronological order
        num_turns: Number of complete turns to include

    Returns:
        Formatted string of the conversation history
    """
    # Check if num_turns is valid
    if num_turns <= 0:
        return ""

    # Group messages into turns
    turns: list[list[dict[str, Any]]] = []
    messages: list[dict[str, Any]] = []

    # First, filter out keyword extraction messages
    for msg in conversation_history:
        if msg["role"] == "assistant" and (
            msg["content"].startswith('{ "high_level_keywords"')
            or msg["content"].startswith("{'high_level_keywords'")
        ):
            continue
        messages.append(msg)

    # Then process messages in chronological order
    i = 0
    while i < len(messages) - 1:
        msg1 = messages[i]
        msg2 = messages[i + 1]

        # Check if we have a user-assistant or assistant-user pair
        if (msg1["role"] == "user" and msg2["role"] == "assistant") or (
            msg1["role"] == "assistant" and msg2["role"] == "user"
        ):
            # Always put user message first in the turn
            if msg1["role"] == "assistant":
                turn = [msg2, msg1]  # user, assistant
            else:
                turn = [msg1, msg2]  # user, assistant
            turns.append(turn)
        i += 2

    # Keep only the most recent num_turns
    if len(turns) > num_turns:
        turns = turns[-num_turns:]

    # Format the turns into a string
    formatted_turns: list[str] = []
    for turn in turns:
        formatted_turns.extend(
            [f"user: {turn[0]['content']}", f"assistant: {turn[1]['content']}"]
        )

    return "\n".join(formatted_turns)


def always_get_an_event_loop() -> asyncio.AbstractEventLoop:
    """
    Ensure that there is always an event loop available.

    This function tries to get the current event loop. If the current event loop is closed or does not exist,
    it creates a new event loop and sets it as the current event loop.

    Returns:
        asyncio.AbstractEventLoop: The current or newly created event loop.
    """
    try:
        # Try to get the current event loop
        current_loop = asyncio.get_event_loop()
        if current_loop.is_closed():
            raise RuntimeError("Event loop is closed.")
        return current_loop

    except RuntimeError:
        # If no event loop exists or it is closed, create a new one
        logger.info("Creating a new event loop in main thread.")
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        return new_loop

def lazy_external_import(module_name: str, class_name: str) -> Callable[..., Any]:
    """Lazily import a class from an external module based on the package of the caller."""
    # Get the caller's module and package
    import inspect

    caller_frame = inspect.currentframe().f_back
    module = inspect.getmodule(caller_frame)
    package = module.__package__ if module else None

    def import_class(*args: Any, **kwargs: Any):
        import importlib

        module = importlib.import_module(module_name, package=package)
        cls = getattr(module, class_name)
        return cls(*args, **kwargs)

    return import_class


async def update_chunk_cache_list(
    chunk_id: str,
    text_chunks_storage: "BaseKVStorage",
    cache_keys: list[str],
    cache_scenario: str = "batch_update",
) -> None:
    """Update chunk's llm_cache_list with the given cache keys

    Args:
        chunk_id: Chunk identifier
        text_chunks_storage: Text chunks storage instance
        cache_keys: List of cache keys to add to the list
        cache_scenario: Description of the cache scenario for logging
    """
    if not cache_keys:
        return

    try:
        chunk_data = await text_chunks_storage.get_by_id(chunk_id)
        if chunk_data:
            # Ensure llm_cache_list exists
            if "llm_cache_list" not in chunk_data:
                chunk_data["llm_cache_list"] = []

            # Add cache keys to the list if not already present
            existing_keys = set(chunk_data["llm_cache_list"])
            new_keys = [key for key in cache_keys if key not in existing_keys]

            if new_keys:
                chunk_data["llm_cache_list"].extend(new_keys)

                # Update the chunk in storage
                await text_chunks_storage.upsert({chunk_id: chunk_data})
                logger.debug(
                    f"Updated chunk {chunk_id} with {len(new_keys)} cache keys ({cache_scenario})"
                )
    except Exception as e:
        logger.warning(
            f"Failed to update chunk {chunk_id} with cache references on {cache_scenario}: {e}"
        )


def remove_think_tags(text: str) -> str:
    """Remove <think> tags from the text"""
    return re.sub(r"^(<think>.*?</think>|<think>)", "", text, flags=re.DOTALL).strip()


async def use_llm_func_with_cache(
    input_text: str,
    use_llm_func: callable,
    llm_response_cache: "BaseKVStorage | None" = None,
    max_tokens: int = None,
    history_messages: list[dict[str, str]] = None,
    cache_type: str = "extract",
    chunk_id: str | None = None,
    cache_keys_collector: list = None,
) -> str:
    """Call LLM function with cache support

    If cache is available and enabled (determined by handle_cache based on mode),
    retrieve result from cache; otherwise call LLM function and save result to cache.

    Args:
        input_text: Input text to send to LLM
        use_llm_func: LLM function with higher priority
        llm_response_cache: Cache storage instance
        max_tokens: Maximum tokens for generation
        history_messages: History messages list
        cache_type: Type of cache
        chunk_id: Chunk identifier to store in cache
        text_chunks_storage: Text chunks storage to update llm_cache_list
        cache_keys_collector: Optional list to collect cache keys for batch processing

    Returns:
        LLM response text
    """
    if llm_response_cache:
        if history_messages:
            history = json.dumps(history_messages, ensure_ascii=False)
            _prompt = history + "\n" + input_text
        else:
            _prompt = input_text

        arg_hash = compute_args_hash(_prompt)
        # Generate cache key for this LLM call
        cache_key = generate_cache_key("default", cache_type, arg_hash)

        cached_return, _1, _2, _3 = await handle_cache(
            llm_response_cache,
            arg_hash,
            _prompt,
            "default",
            cache_type=cache_type,
        )
        if cached_return:
            logger.debug(f"Found cache for {arg_hash}")
            statistic_data["llm_cache"] += 1

            # Add cache key to collector if provided
            if cache_keys_collector is not None:
                cache_keys_collector.append(cache_key)

            return cached_return
        statistic_data["llm_call"] += 1

        # Call LLM
        kwargs = {}
        if history_messages:
            kwargs["history_messages"] = history_messages
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        res: str = await use_llm_func(input_text, **kwargs)
        res = remove_think_tags(res)

        if llm_response_cache.global_config.get("enable_llm_cache_for_entity_extract"):
            await save_to_cache(
                llm_response_cache,
                CacheData(
                    args_hash=arg_hash,
                    content=res,
                    prompt=_prompt,
                    cache_type=cache_type,
                    chunk_id=chunk_id,
                ),
            )

            # Add cache key to collector if provided
            if cache_keys_collector is not None:
                cache_keys_collector.append(cache_key)

        return res

    # When cache is disabled, directly call LLM
    kwargs = {}
    if history_messages:
        kwargs["history_messages"] = history_messages
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    logger.info(f"Call LLM function with query text length: {len(input_text)}")
    res = await use_llm_func(input_text, **kwargs)
    return remove_think_tags(res)


def get_content_summary(content: str, max_length: int = 250) -> str:
    """Get summary of document content

    Args:
        content: Original document content
        max_length: Maximum length of summary

    Returns:
        Truncated content with ellipsis if needed
    """
    content = content.strip()
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."


def normalize_extracted_info(name: str, is_entity=False) -> str:
    """Normalize entity/relation names and description with the following rules:
    1. Remove spaces between Chinese characters
    2. Remove spaces between Chinese characters and English letters/numbers
    3. Preserve spaces within English text and numbers
    4. Replace Chinese parentheses with English parentheses
    5. Replace Chinese dash with English dash
    6. Remove English quotation marks from the beginning and end of the text
    7. Remove English quotation marks in and around chinese
    8. Remove Chinese quotation marks

    Args:
        name: Entity name to normalize

    Returns:
        Normalized entity name
    """
    # Replace Chinese parentheses with English parentheses
    name = name.replace("（", "(").replace("）", ")")

    # Replace Chinese dash with English dash
    name = name.replace("—", "-").replace("－", "-")

    # Use regex to remove spaces between Chinese characters
    # Regex explanation:
    # (?<=[\u4e00-\u9fa5]): Positive lookbehind for Chinese character
    # \s+: One or more whitespace characters
    # (?=[\u4e00-\u9fa5]): Positive lookahead for Chinese character
    name = re.sub(r"(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])", "", name)

    # Remove spaces between Chinese and English/numbers/symbols
    name = re.sub(
        r"(?<=[\u4e00-\u9fa5])\s+(?=[a-zA-Z0-9\(\)\[\]@#$%!&\*\-=+_])", "", name
    )
    name = re.sub(
        r"(?<=[a-zA-Z0-9\(\)\[\]@#$%!&\*\-=+_])\s+(?=[\u4e00-\u9fa5])", "", name
    )

    # Remove English quotation marks from the beginning and end
    if len(name) >= 2 and name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    if len(name) >= 2 and name.startswith("'") and name.endswith("'"):
        name = name[1:-1]

    if is_entity:
        # remove Chinese quotes
        name = name.replace("“", "").replace("”", "").replace("‘", "").replace("’", "")
        # remove English queotes in and around chinese
        name = re.sub(r"['\"]+(?=[\u4e00-\u9fa5])", "", name)
        name = re.sub(r"(?<=[\u4e00-\u9fa5])['\"]+", "", name)

    return name


def clean_text(text: str) -> str:
    """Clean text by removing null bytes (0x00) and whitespace

    Args:
        text: Input text to clean

    Returns:
        Cleaned text
    """
    return text.strip().replace("\x00", "")


def check_storage_env_vars(storage_name: str) -> None:
    """Check if all required environment variables for storage implementation exist

    Args:
        storage_name: Storage implementation name

    Raises:
        ValueError: If required environment variables are missing
    """
    from ragent.kg import STORAGE_ENV_REQUIREMENTS

    required_vars = STORAGE_ENV_REQUIREMENTS.get(storage_name, [])
    missing_vars = [var for var in required_vars if var not in os.environ]

    if missing_vars:
        raise ValueError(
            f"Storage implementation '{storage_name}' requires the following "
            f"environment variables: {', '.join(missing_vars)}"
        )


class TokenTracker:
    """Track token usage for LLM calls."""

    def __init__(self):
        self.reset()

    def __enter__(self):
        self.reset()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(self)

    def reset(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0

    def add_usage(self, token_counts):
        """Add token usage from one LLM call.

        Args:
            token_counts: A dictionary containing prompt_tokens, completion_tokens, total_tokens
        """
        self.prompt_tokens += token_counts.get("prompt_tokens", 0)
        self.completion_tokens += token_counts.get("completion_tokens", 0)

        # If total_tokens is provided, use it directly; otherwise calculate the sum
        if "total_tokens" in token_counts:
            self.total_tokens += token_counts["total_tokens"]
        else:
            self.total_tokens += token_counts.get(
                "prompt_tokens", 0
            ) + token_counts.get("completion_tokens", 0)

        self.call_count += 1

    def get_usage(self):
        """Get current usage statistics."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
        }

    def __str__(self):
        usage = self.get_usage()
        return (
            f"LLM call count: {usage['call_count']}, "
            f"Prompt tokens: {usage['prompt_tokens']}, "
            f"Completion tokens: {usage['completion_tokens']}, "
            f"Total tokens: {usage['total_tokens']}"
        )


def _coerce_usage_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _object_to_usage_dict(raw_usage: Any) -> dict[str, Any] | None:
    if raw_usage is None:
        return None
    if isinstance(raw_usage, dict):
        return raw_usage
    usage_dict: dict[str, Any] = {}
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "input_token_count",
        "output_token_count",
    ):
        if hasattr(raw_usage, key):
            usage_dict[key] = getattr(raw_usage, key)
    return usage_dict or None


def _locate_usage_payload(raw_usage: Any) -> dict[str, Any] | None:
    usage_dict = _object_to_usage_dict(raw_usage)
    if usage_dict is not None:
        return usage_dict
    if not isinstance(raw_usage, dict):
        return None

    interesting_keys = {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "input_token_count",
        "output_token_count",
    }
    if any(key in raw_usage for key in interesting_keys):
        return raw_usage

    for key in ("usage", "token_usage", "meta", "output", "result", "data", "billed_units"):
        value = raw_usage.get(key)
        nested = _locate_usage_payload(value)
        if nested is not None:
            return nested

    for value in raw_usage.values():
        nested = _locate_usage_payload(value)
        if nested is not None:
            return nested
    return None


def normalize_token_usage(raw_usage: Any) -> dict[str, int] | None:
    usage_payload = _locate_usage_payload(raw_usage)
    if usage_payload is None:
        return None

    input_tokens = _coerce_usage_value(
        usage_payload.get("prompt_tokens", usage_payload.get("input_tokens"))
    )
    if input_tokens is None:
        input_tokens = _coerce_usage_value(usage_payload.get("input_token_count"))

    output_tokens = _coerce_usage_value(
        usage_payload.get("completion_tokens", usage_payload.get("output_tokens"))
    )
    if output_tokens is None:
        output_tokens = _coerce_usage_value(usage_payload.get("output_token_count"))

    total_tokens = _coerce_usage_value(usage_payload.get("total_tokens"))
    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)

    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    return {
        "input_tokens": input_tokens or 0,
        "output_tokens": output_tokens or 0,
        "total_tokens": total_tokens or 0,
    }


class ModelUsageCollector:
    """Collect task-scoped model token usage across chat/embed/rerank/image calls."""

    def __init__(self, label: str):
        self.label = label
        self.started_at = datetime.now()
        self._events: list[dict[str, Any]] = []
        self._aggregate: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._token = None

    def __enter__(self):
        self._token = _CURRENT_MODEL_USAGE_COLLECTOR.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token is not None:
            _CURRENT_MODEL_USAGE_COLLECTOR.reset(self._token)
            self._token = None

    def record(
        self,
        model_type: str,
        model_name: str | None,
        usage: dict[str, int] | None,
        *,
        source: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            bucket = self._aggregate.setdefault(
                model_type,
                {
                    "call_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "missing_usage_count": 0,
                    "models": {},
                },
            )
            bucket["call_count"] += 1

            model_key = model_name or "unknown_model"
            model_bucket = bucket["models"].setdefault(
                model_key,
                {
                    "call_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "missing_usage_count": 0,
                },
            )
            model_bucket["call_count"] += 1

            if usage is None:
                bucket["missing_usage_count"] += 1
                model_bucket["missing_usage_count"] += 1
            else:
                bucket["input_tokens"] += usage["input_tokens"]
                bucket["output_tokens"] += usage["output_tokens"]
                bucket["total_tokens"] += usage["total_tokens"]
                model_bucket["input_tokens"] += usage["input_tokens"]
                model_bucket["output_tokens"] += usage["output_tokens"]
                model_bucket["total_tokens"] += usage["total_tokens"]

            self._events.append(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "model_type": model_type,
                    "model_name": model_key,
                    "source": source,
                    "usage": usage,
                    "extra": extra or {},
                }
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "label": self.label,
                "started_at": self.started_at.isoformat(timespec="seconds"),
                "ended_at": datetime.now().isoformat(timespec="seconds"),
                "aggregate": json.loads(json.dumps(self._aggregate)),
                "events": json.loads(json.dumps(self._events, default=str)),
            }


def get_current_model_usage_collector() -> ModelUsageCollector | None:
    return _CURRENT_MODEL_USAGE_COLLECTOR.get()


@contextmanager
def model_usage_stage(stage: str, label: str):
    token = _CURRENT_MODEL_USAGE_STAGE.set({"stage": stage, "label": label})
    try:
        yield
    finally:
        _CURRENT_MODEL_USAGE_STAGE.reset(token)


def record_model_usage(
    model_type: str,
    model_name: str | None,
    raw_usage: Any,
    *,
    source: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    collector = get_current_model_usage_collector()
    if collector is None:
        return
    enriched_extra = dict(extra or {})
    current_stage = _CURRENT_MODEL_USAGE_STAGE.get()
    if current_stage:
        enriched_extra.setdefault("stage", current_stage["stage"])
        enriched_extra.setdefault("stage_label", current_stage["label"])
    collector.record(
        model_type,
        model_name,
        normalize_token_usage(raw_usage),
        source=source,
        extra=enriched_extra,
    )


def write_model_usage_report(
    collector: ModelUsageCollector,
    report_dir: str,
    *,
    task_name: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    os.makedirs(report_dir, exist_ok=True)
    snapshot = collector.snapshot()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(report_dir, f"model_usage_{task_name}_{timestamp}.md")

    lines = [
        f"# Model Usage Report: {task_name}",
        "",
        f"- Task label: `{snapshot['label']}`",
        f"- Started at: `{snapshot['started_at']}`",
        f"- Ended at: `{snapshot['ended_at']}`",
    ]
    if metadata:
        lines.append("- Metadata:")
        for key, value in metadata.items():
            lines.append(f"  - `{key}`: `{value}`")
    lines.append("")
    lines.append("## Summary By Model Type")
    lines.append("")
    lines.append("| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")

    aggregate = snapshot["aggregate"]
    grand_input = grand_output = grand_total = grand_calls = grand_missing = 0
    for model_type in ("chat", "embedding", "rerank", "image"):
        bucket = aggregate.get(model_type, {})
        grand_calls += int(bucket.get("call_count", 0))
        grand_input += int(bucket.get("input_tokens", 0))
        grand_output += int(bucket.get("output_tokens", 0))
        grand_total += int(bucket.get("total_tokens", 0))
        grand_missing += int(bucket.get("missing_usage_count", 0))
        lines.append(
            "| {model_type} | {call_count} | {input_tokens} | {output_tokens} | {total_tokens} | {missing_usage_count} |".format(
                model_type=model_type,
                call_count=bucket.get("call_count", 0),
                input_tokens=bucket.get("input_tokens", 0),
                output_tokens=bucket.get("output_tokens", 0),
                total_tokens=bucket.get("total_tokens", 0),
                missing_usage_count=bucket.get("missing_usage_count", 0),
            )
        )

    lines.extend(
        [
            f"| total | {grand_calls} | {grand_input} | {grand_output} | {grand_total} | {grand_missing} |",
            "",
            "## Summary By Model",
            "",
        ]
    )

    for model_type in ("chat", "embedding", "rerank", "image"):
        bucket = aggregate.get(model_type)
        if not bucket:
            continue
        lines.append(f"### {model_type}")
        lines.append("")
        lines.append("| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for model_name, model_bucket in sorted(bucket.get("models", {}).items()):
            lines.append(
                "| {model_name} | {call_count} | {input_tokens} | {output_tokens} | {total_tokens} | {missing_usage_count} |".format(
                    model_name=model_name,
                    call_count=model_bucket.get("call_count", 0),
                    input_tokens=model_bucket.get("input_tokens", 0),
                    output_tokens=model_bucket.get("output_tokens", 0),
                    total_tokens=model_bucket.get("total_tokens", 0),
                    missing_usage_count=model_bucket.get("missing_usage_count", 0),
                )
            )
        lines.append("")

    lines.extend(["## Call Events", ""])
    for index, event in enumerate(snapshot["events"], start=1):
        usage = event.get("usage") or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        lines.append(
            f"{index}. `{event['timestamp']}` `{event['model_type']}` / `{event['model_name']}`"
            f" input={usage.get('input_tokens', 0)} output={usage.get('output_tokens', 0)} total={usage.get('total_tokens', 0)}"
            + (f" source=`{event['source']}`" if event.get("source") else "")
        )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return report_path
