from __future__ import annotations

import asyncio

import numpy as np

from ragent import inference_runtime


def _patch_startup_model_calls(monkeypatch, calls: dict[str, int]) -> None:
    async def fake_llm_complete(**_kwargs):
        calls["llm"] += 1
        return "LLM_OK"

    async def fake_openai_embed(_texts):
        calls["embed"] += 1
        return np.array([[0.1, 0.2, 0.3]], dtype=float)

    async def fake_rerank_from_env(**_kwargs):
        calls["rerank"] += 1
        return [{"index": 0, "relevance_score": 1.0}]

    monkeypatch.setattr(inference_runtime, "env_openai_complete", fake_llm_complete)
    monkeypatch.setattr(inference_runtime, "openai_embed", fake_openai_embed)
    monkeypatch.setattr(inference_runtime, "rerank_from_env", fake_rerank_from_env)
    for key in ("IMAGE_MODEL_KEY", "IMAGE_MODEL", "IMAGE_MODEL_URL"):
        monkeypatch.delenv(key, raising=False)


def test_startup_model_check_skips_rerank_when_config_is_incomplete(monkeypatch):
    calls = {"llm": 0, "embed": 0, "rerank": 0}
    _patch_startup_model_calls(monkeypatch, calls)
    monkeypatch.delenv("ENABLE_RERANK", raising=False)
    for key in ("RERANK_MODEL_KEY", "RERANK_MODEL_URL", "RERANK_MODEL"):
        monkeypatch.delenv(key, raising=False)

    asyncio.run(inference_runtime.verify_env_models_before_startup())

    assert calls == {"llm": 1, "embed": 1, "rerank": 0}


def test_startup_model_check_skips_rerank_when_disabled(monkeypatch):
    calls = {"llm": 0, "embed": 0, "rerank": 0}
    _patch_startup_model_calls(monkeypatch, calls)
    monkeypatch.setenv("ENABLE_RERANK", "false")
    monkeypatch.setenv("RERANK_MODEL_KEY", "key")
    monkeypatch.setenv("RERANK_MODEL_URL", "http://127.0.0.1:8000/v1/reranks")
    monkeypatch.setenv("RERANK_MODEL", "rerank-model")

    asyncio.run(inference_runtime.verify_env_models_before_startup())

    assert calls == {"llm": 1, "embed": 1, "rerank": 0}


def test_startup_model_check_runs_rerank_when_enabled_and_configured(monkeypatch):
    calls = {"llm": 0, "embed": 0, "rerank": 0}
    _patch_startup_model_calls(monkeypatch, calls)
    monkeypatch.setenv("ENABLE_RERANK", "true")
    monkeypatch.setenv("RERANK_MODEL_KEY", "key")
    monkeypatch.setenv("RERANK_MODEL_URL", "http://127.0.0.1:8000/v1/reranks")
    monkeypatch.setenv("RERANK_MODEL", "rerank-model")

    asyncio.run(inference_runtime.verify_env_models_before_startup())

    assert calls == {"llm": 1, "embed": 1, "rerank": 1}
