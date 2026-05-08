from __future__ import annotations

import asyncio
import contextvars

from ragent.utils import priority_limit_async_func_call


class _LazyEmbeddingFunc:
    __name__ = "lazy_embedding"
    max_token_size = 8192

    @property
    def embedding_dim(self):
        return 256

    async def __call__(self):
        return []


def test_priority_limit_async_func_call_preserves_callable_object_attrs():
    wrapped = priority_limit_async_func_call(1, label="embedding")(_LazyEmbeddingFunc())

    assert wrapped.embedding_dim == 256
    assert wrapped.max_token_size == 8192


def test_priority_limit_async_func_call_supports_python310_create_task(monkeypatch):
    marker = contextvars.ContextVar("marker")
    original_create_task = asyncio.create_task

    def python310_create_task(coro, *, name=None):
        return original_create_task(coro, name=name)

    monkeypatch.setattr(asyncio, "create_task", python310_create_task)

    @priority_limit_async_func_call(1, label="test")
    async def read_marker():
        return marker.get()

    async def run():
        token = marker.set("propagated")
        try:
            assert await read_marker() == "propagated"
        finally:
            marker.reset(token)
            await read_marker.shutdown()

    asyncio.run(run())
