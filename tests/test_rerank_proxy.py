from __future__ import annotations

import asyncio

from ragent import rerank


def test_rerank_api_uses_environment_proxy_settings(monkeypatch):
    captured_kwargs = {}

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def json(self):
            return {"results": [{"index": 0, "relevance_score": 0.9}]}

        async def text(self):
            return ""

    class FakeSession:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(rerank.aiohttp, "ClientSession", FakeSession)
    monkeypatch.setattr(rerank, "record_model_usage", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerank, "log_model_call", lambda *args, **kwargs: None)

    result = asyncio.run(
        rerank.rerank_api(
            query="query",
            documents=["doc"],
            model="rerank-model",
            base_url="https://example.com/v1",
            api_key="key",
        )
    )

    assert captured_kwargs["trust_env"] is True
    assert result == [{"index": 0, "relevance_score": 0.9}]
