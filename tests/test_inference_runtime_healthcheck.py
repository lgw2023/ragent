from __future__ import annotations

import asyncio

import numpy as np

from ragent import inference_runtime
from ragent import operate
from ragent.base import QueryParam


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


def test_retrieval_only_startup_model_check_skips_llm_and_incomplete_rerank(monkeypatch):
    calls = {"llm": 0, "embed": 0, "rerank": 0}
    _patch_startup_model_calls(monkeypatch, calls)
    for key in (
        "LLM_MODEL",
        "LLM_MODEL_KEY",
        "LLM_MODEL_URL",
        "RERANK_MODEL_KEY",
        "RERANK_MODEL_URL",
        "RERANK_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    asyncio.run(
        inference_runtime.verify_env_models_before_startup(
            require_llm=False,
            enable_rerank=True,
        )
    )

    assert calls == {"llm": 0, "embed": 1, "rerank": 0}


def _patch_initialize_rag_runtime(monkeypatch, calls: dict[str, object]) -> None:
    async def fake_ensure_startup_model_check_once(*, require_llm, enable_rerank):
        calls["startup_require_llm"] = require_llm
        calls["startup_enable_rerank"] = enable_rerank

    class FakeRagent:
        def __init__(self, **kwargs):
            calls["rag_kwargs"] = kwargs

        async def initialize_storages(self):
            calls["storage_initialized"] = True

    async def fake_initialize_pipeline_status():
        calls["pipeline_status_initialized"] = True

    monkeypatch.setattr(
        inference_runtime,
        "ensure_startup_model_check_once",
        fake_ensure_startup_model_check_once,
    )
    monkeypatch.setattr(inference_runtime, "Ragent", FakeRagent)
    monkeypatch.setattr(
        inference_runtime,
        "initialize_pipeline_status",
        fake_initialize_pipeline_status,
    )


def test_initialize_rag_preloads_gliner_in_mep_without_llm(monkeypatch, tmp_path):
    calls: dict[str, object] = {"preload_calls": 0}
    _patch_initialize_rag_runtime(monkeypatch, calls)
    inference_runtime._KEYWORD_FALLBACK_PRELOAD_DONE.clear()
    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "mep")
    for name in ("LLM_MODEL", "LLM_MODEL_KEY", "LLM_MODEL_URL"):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(
        inference_runtime.keyword_extraction,
        "get_gliner_keyword_model_name",
        lambda: "/models/gliner",
    )
    monkeypatch.setattr(
        inference_runtime.keyword_extraction,
        "get_gliner_keyword_device",
        lambda: "cpu",
    )

    async def fake_ensure_gliner_keyword_model_ready():
        calls["preload_calls"] = int(calls["preload_calls"]) + 1
        return {
            "keyword_model": "/models/gliner",
            "keyword_model_device": "cpu",
            "warmup_entity_count": 2,
        }

    monkeypatch.setattr(
        inference_runtime.keyword_extraction,
        "ensure_gliner_keyword_model_ready",
        fake_ensure_gliner_keyword_model_ready,
    )

    stage_timings: list[dict] = []
    asyncio.run(
        inference_runtime.initialize_rag(
            str(tmp_path),
            stage_timings=stage_timings,
            require_llm=False,
        )
    )

    assert calls["startup_require_llm"] is False
    assert calls["preload_calls"] == 1
    assert calls["storage_initialized"] is True
    assert calls["pipeline_status_initialized"] is True
    assert calls["rag_kwargs"]["llm_model_name"] == "retrieval-only-no-llm"
    assert any(item["stage"] == "keyword_fallback_preload" for item in stage_timings)
    inference_runtime._KEYWORD_FALLBACK_PRELOAD_DONE.clear()


def test_initialize_rag_skips_gliner_preload_when_llm_config_is_complete(
    monkeypatch,
    tmp_path,
):
    calls: dict[str, object] = {}
    _patch_initialize_rag_runtime(monkeypatch, calls)
    inference_runtime._KEYWORD_FALLBACK_PRELOAD_DONE.clear()
    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "mep")
    monkeypatch.setenv("LLM_MODEL", "qwen")
    monkeypatch.setenv("LLM_MODEL_KEY", "key")
    monkeypatch.setenv("LLM_MODEL_URL", "http://127.0.0.1:8000/v1")

    async def fail_preload():
        raise AssertionError("GLiNER preload should be skipped with complete LLM config")

    monkeypatch.setattr(
        inference_runtime.keyword_extraction,
        "ensure_gliner_keyword_model_ready",
        fail_preload,
    )

    stage_timings: list[dict] = []
    asyncio.run(
        inference_runtime.initialize_rag(
            str(tmp_path),
            stage_timings=stage_timings,
            require_llm=False,
        )
    )

    assert calls["rag_kwargs"]["llm_model_name"] == "qwen"
    assert not any(item["stage"] == "keyword_fallback_preload" for item in stage_timings)


def test_execute_retrieval_only_skips_llm_check_and_returns_retrieval_payload(
    monkeypatch,
):
    calls: dict[str, object] = {}

    async def fake_ensure_startup_model_check_once(*, require_llm, enable_rerank):
        calls["require_llm"] = require_llm
        calls["enable_rerank"] = enable_rerank

    async def fake_run_one_hop_with_rag(
        _rag,
        query,
        mode,
        **kwargs,
    ):
        calls["query"] = query
        calls["mode"] = mode
        calls["retrieval_only"] = kwargs["retrieval_only"]
        calls["only_need_context"] = kwargs["only_need_context"]
        calls["high_level_keywords"] = kwargs["high_level_keywords"]
        return {
            "answer": "上下文",
            "referenced_file_paths": ["doc.md"],
            "image_list": ["doc.md"],
            "retrieval_result": {"final_context_text": "上下文"},
            "trace": {"final_context_text": "上下文"},
        }

    monkeypatch.setattr(
        inference_runtime,
        "ensure_startup_model_check_once",
        fake_ensure_startup_model_check_once,
    )
    monkeypatch.setattr(
        inference_runtime,
        "_run_one_hop_with_rag",
        fake_run_one_hop_with_rag,
    )

    request = inference_runtime.InferenceRequest(
        query_type="onehop",
        query="我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
        retrieval_only=True,
        enable_rerank=True,
        high_level_keywords=["指南"],
    )

    result = asyncio.run(
        inference_runtime.execute_inference_request(object(), request)
    )

    assert calls["require_llm"] is False
    assert calls["enable_rerank"] is True
    assert calls["retrieval_only"] is True
    assert calls["only_need_context"] is True
    assert calls["high_level_keywords"] == ["指南"]
    assert result["answer"] == "上下文"
    assert result["retrieval_only"] is True
    assert result["only_need_context"] is True
    assert result["retrieval_result"]["final_context_text"] == "上下文"


def test_hybrid_retrieval_debug_skips_missing_rerank_config(monkeypatch):
    for key in ("RERANK_MODEL_KEY", "RERANK_MODEL_URL", "RERANK_MODEL"):
        monkeypatch.delenv(key, raising=False)

    async def fake_vector_context(_query, _chunks_vdb, _query_param):
        return (
            {"c1": 1.0},
            {"c1": "含糖饮料 330ml 150kcal"},
            {"c1": "doc.md"},
            {"c1": {"file_path": "doc.md", "source_ref": "doc.md | p.1"}},
        )

    async def fake_keywords(*_args, **_kwargs):
        return ["指南"], ["饮食"]

    async def fake_node_data(*_args, **_kwargs):
        return [], [], [], []

    async def fake_edge_data(*_args, **_kwargs):
        return [], [], [], []

    async def fail_rerank(*_args, **_kwargs):
        raise AssertionError("rerank should not be called without full config")

    monkeypatch.setattr(operate, "_get_vector_context_new", fake_vector_context)
    monkeypatch.setattr(operate, "get_keywords_from_query", fake_keywords)
    monkeypatch.setattr(operate, "_get_node_data", fake_node_data)
    monkeypatch.setattr(operate, "_get_edge_data", fake_edge_data)
    monkeypatch.setattr(operate, "rerank_from_env", fail_rerank)

    class FakeTokenizer:
        def encode(self, text):
            return list(str(text))

    query_param = QueryParam(mode="hybrid")
    query_param.enable_rerank = True

    result = asyncio.run(
        operate._build_hybrid_retrieval_debug_data(
            query="我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
            chunks_vdb=object(),
            knowledge_graph_inst=object(),
            relationships_vdb=object(),
            entities_vdb=object(),
            text_chunks_db=object(),
            query_param=query_param,
            global_config={
                "tokenizer": FakeTokenizer(),
                "addon_params": {},
                "llm_model_name": "unit-test-llm",
                "llm_model_func": object(),
                "answer_prompt_mode": "single_prompt",
                "rerank_model_func": None,
                "corpus_revision": 0,
                "index_digest": None,
            },
        )
    )

    assert result["rerank_used"] is False
    assert "RERANK_MODEL_KEY" in result["rerank_skip_reason"]
    assert result["rerank_results"] == [{"index": 0}]
