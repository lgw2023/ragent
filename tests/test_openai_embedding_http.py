from __future__ import annotations

import asyncio

from ragent.llm import openai as openai_module


class _FakeEmbeddingResponse:
    status_code = 200
    headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "data": [{"embedding": [0.1, 0.2, 0.3]}],
            "usage": {"total_tokens": 1},
        }


def _install_fake_async_client(monkeypatch, captured_requests: list[dict]) -> None:
    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, *, headers=None, json=None):
            captured_requests.append(
                {
                    "url": url,
                    "headers": headers,
                    "json": json,
                }
            )
            return _FakeEmbeddingResponse()

    monkeypatch.setattr(openai_module.httpx, "AsyncClient", FakeAsyncClient)


def _set_custom_openai_embedding_env(monkeypatch) -> None:
    for name in (
        "EMBEDDING_MODEL",
        "EMBEDDING_MODEL_KEY",
        "EMBEDDING_MODEL_URL",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_DIMENSIONS",
        "EMBEDDING_DIM",
        "EMBEDDING_SEND_DIMENSIONS",
        "EMBEDDING_REQUEST_DIMENSIONS",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI-bge-m3")
    monkeypatch.setenv("EMBEDDING_MODEL_KEY", "EMPTY")
    monkeypatch.setenv("EMBEDDING_MODEL_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "custom_openai")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "1024")


def test_openai_embed_skips_dimensions_for_custom_openai_bge_m3(monkeypatch):
    captured_requests: list[dict] = []
    _install_fake_async_client(monkeypatch, captured_requests)
    _set_custom_openai_embedding_env(monkeypatch)

    result = asyncio.run(openai_module.openai_embed(["hello"]))

    assert result.shape == (1, 3)
    assert captured_requests[0]["json"]["model"] == "BAAI-bge-m3"
    assert "dimensions" not in captured_requests[0]["json"]


def test_openai_embed_can_force_dimensions_for_custom_openai_bge_m3(monkeypatch):
    captured_requests: list[dict] = []
    _install_fake_async_client(monkeypatch, captured_requests)
    _set_custom_openai_embedding_env(monkeypatch)
    monkeypatch.setenv("EMBEDDING_SEND_DIMENSIONS", "1")

    asyncio.run(openai_module.openai_embed(["hello"]))

    assert captured_requests[0]["json"]["dimensions"] == 1024
