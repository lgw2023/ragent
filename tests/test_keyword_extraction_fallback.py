from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from ragent import inference_runtime
from ragent import keyword_extraction
from ragent import operate
from ragent.base import QueryParam


class _FakeTokenizer:
    def encode(self, text):
        return list(str(text))


class _FailingLLM:
    def __init__(self):
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        raise AssertionError("LLM keyword extraction should not be called")


class _JsonLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def __call__(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        return self.response


def _global_config(model):
    return {
        "llm_model_func": model,
        "llm_model_name": "unit-test-llm",
        "tokenizer": _FakeTokenizer(),
        "addon_params": {"language": "Chinese", "example_number": 1},
        "answer_prompt_mode": "single_prompt",
        "rerank_model_func": None,
        "corpus_revision": 0,
        "index_digest": None,
    }


def test_only_need_context_uses_gliner_fallback_without_llm(monkeypatch):
    llm = _FailingLLM()

    async def fake_gliner(text, global_config, *, fallback_reason=None):
        assert text == "糖尿病患者如何控制餐后血糖？"
        return keyword_extraction.KeywordResolution(
            high_level_keywords=["餐后血糖控制"],
            low_level_keywords=["糖尿病患者"],
            keyword_source=keyword_extraction.KEYWORD_SOURCE_GLINER_FALLBACK,
            keyword_strategy=keyword_extraction.KEYWORD_STRATEGY_TOKEN_CLASSIFICATION,
            keyword_fallback_reason=fallback_reason,
            keyword_model="knowledgator/gliner-x-small",
            keyword_model_device="cpu",
        )

    monkeypatch.setattr(
        keyword_extraction,
        "extract_keywords_with_gliner",
        fake_gliner,
    )

    param = QueryParam(mode="hybrid", only_need_context=True)
    hl_keywords, ll_keywords = asyncio.run(
        operate.get_keywords_from_query(
            "糖尿病患者如何控制餐后血糖？",
            param,
            _global_config(llm),
        )
    )

    assert hl_keywords == ["餐后血糖控制"]
    assert ll_keywords == ["糖尿病患者"]
    assert llm.calls == []
    assert param.keyword_source == "gliner_fallback"
    assert param.keyword_strategy == "token_classification_fallback"
    assert param.keyword_model == "knowledgator/gliner-x-small"
    assert "LLM keyword extraction disabled" in param.keyword_fallback_reason


def test_gliner_unavailable_does_not_fall_back_to_llm(monkeypatch):
    llm = _FailingLLM()

    async def fake_gliner(_text, _global_config, *, fallback_reason=None):
        return keyword_extraction.build_gliner_unavailable_resolution(
            reason=f"{fallback_reason}; GLiNER fallback unavailable: missing package",
            model_name="knowledgator/gliner-x-small",
            device="cpu",
            error="missing package",
        )

    monkeypatch.setattr(
        keyword_extraction,
        "extract_keywords_with_gliner",
        fake_gliner,
    )

    param = QueryParam(mode="graph", only_need_context=True)
    hl_keywords, ll_keywords = asyncio.run(
        operate.get_keywords_from_query("总结主要主题", param, _global_config(llm))
    )

    assert hl_keywords == []
    assert ll_keywords == []
    assert llm.calls == []
    assert param.keyword_source == "gliner_fallback"
    assert "GLiNER fallback unavailable" in param.keyword_fallback_reason
    assert param.keyword_model_error == "missing package"


def test_retrieval_only_uses_real_gliner_loader_without_llm(monkeypatch, tmp_path: Path):
    captured = {}
    model_dir = tmp_path / "data" / "models" / "keyword_extraction" / "gliner"
    model_dir.mkdir(parents=True)

    class FakeModel:
        def to(self, device):
            captured["device"] = device
            return self

        def eval(self):
            captured["eval"] = True

        def predict_entities(self, text, labels, threshold):
            captured["text"] = text
            captured["labels"] = labels
            captured["threshold"] = threshold
            return [
                {"text": "餐后血糖控制", "label": "topic", "start": 0, "score": 0.91},
                {"text": "糖尿病患者", "label": "person", "start": 2, "score": 0.84},
            ]

    class FakeGLiNER:
        @classmethod
        def from_pretrained(cls, model_name):
            captured["model_name"] = model_name
            return FakeModel()

    monkeypatch.setitem(sys.modules, "gliner", SimpleNamespace(GLiNER=FakeGLiNER))
    monkeypatch.setenv("RAG_KEYWORD_FALLBACK_MODEL", str(model_dir))
    monkeypatch.setenv("RAG_KEYWORD_FALLBACK_DEVICE", "cpu")
    keyword_extraction._MODEL_CACHE.clear()

    llm = _FailingLLM()
    param = QueryParam(mode="hybrid", only_need_context=True)
    hl_keywords, ll_keywords = asyncio.run(
        operate.get_keywords_from_query(
            "糖尿病患者如何控制餐后血糖？",
            param,
            _global_config(llm),
        )
    )

    assert hl_keywords == ["餐后血糖控制"]
    assert ll_keywords == ["糖尿病患者"]
    assert llm.calls == []
    assert captured["model_name"] == str(model_dir)
    assert captured["device"] == "cpu"
    assert captured["eval"] is True
    assert captured["text"] == "糖尿病患者如何控制餐后血糖？"
    assert "topic" in captured["labels"]
    assert param.keyword_source == "gliner_fallback"
    assert param.keyword_strategy == "token_classification_fallback"
    assert param.keyword_model == str(model_dir)
    assert param.keyword_model_device == "cpu"
    assert param.keyword_model_error is None
    keyword_extraction._MODEL_CACHE.clear()


def test_explicit_keywords_take_priority_over_gliner_and_llm(monkeypatch):
    llm = _FailingLLM()

    async def fail_gliner(*_args, **_kwargs):
        raise AssertionError("GLiNER fallback should not be called")

    monkeypatch.setattr(
        keyword_extraction,
        "extract_keywords_with_gliner",
        fail_gliner,
    )

    param = QueryParam(
        mode="hybrid",
        only_need_context=True,
        hl_keywords=["指南"],
        ll_keywords=["饮食"],
    )
    hl_keywords, ll_keywords = asyncio.run(
        operate.get_keywords_from_query("文档主题", param, _global_config(llm))
    )

    assert hl_keywords == ["指南"]
    assert ll_keywords == ["饮食"]
    assert llm.calls == []
    assert param.keyword_source == "request"
    assert param.keyword_strategy == "request"


def test_normal_query_still_uses_llm_keyword_extraction(monkeypatch):
    async def fail_gliner(*_args, **_kwargs):
        raise AssertionError("GLiNER fallback should not be used when LLM is allowed")

    monkeypatch.setattr(
        keyword_extraction,
        "extract_keywords_with_gliner",
        fail_gliner,
    )
    llm = _JsonLLM(
        '{"high_level_keywords": ["营养建议"], "low_level_keywords": ["低糖饮食"]}'
    )
    param = QueryParam(mode="hybrid")

    hl_keywords, ll_keywords = asyncio.run(
        operate.get_keywords_from_query("如何制定低糖饮食？", param, _global_config(llm))
    )

    assert hl_keywords == ["营养建议"]
    assert ll_keywords == ["低糖饮食"]
    assert len(llm.calls) == 1
    assert llm.calls[0]["kwargs"]["keyword_extraction"] is True
    assert param.keyword_source == "llm"
    assert param.keyword_strategy == "llm_keyword_extraction"


def test_hybrid_retrieval_debug_includes_keyword_metadata(monkeypatch):
    async def fake_gliner(_text, _global_config, *, fallback_reason=None):
        return keyword_extraction.KeywordResolution(
            high_level_keywords=["营养建议"],
            low_level_keywords=["低糖饮食"],
            keyword_source=keyword_extraction.KEYWORD_SOURCE_GLINER_FALLBACK,
            keyword_strategy=keyword_extraction.KEYWORD_STRATEGY_TOKEN_CLASSIFICATION,
            keyword_fallback_reason=fallback_reason,
            keyword_model="knowledgator/gliner-x-small",
            keyword_model_device="cpu",
        )

    async def fake_vector_context(*_args, **_kwargs):
        return {}, {}, {}, {}

    async def fake_node_data(*_args, **_kwargs):
        return [], [], [], []

    async def fake_edge_data(*_args, **_kwargs):
        return [], [], [], []

    monkeypatch.setattr(
        keyword_extraction,
        "extract_keywords_with_gliner",
        fake_gliner,
    )
    monkeypatch.setattr(operate, "_get_vector_context_new", fake_vector_context)
    monkeypatch.setattr(operate, "_get_node_data", fake_node_data)
    monkeypatch.setattr(operate, "_get_edge_data", fake_edge_data)

    param = QueryParam(mode="hybrid", only_need_context=True, enable_rerank=False)
    result = asyncio.run(
        operate._build_hybrid_retrieval_debug_data(
            query="如何制定低糖饮食？",
            chunks_vdb=object(),
            knowledge_graph_inst=object(),
            relationships_vdb=object(),
            entities_vdb=object(),
            text_chunks_db=object(),
            query_param=param,
            global_config=_global_config(_FailingLLM()),
        )
    )

    assert result["high_level_keywords"] == ["营养建议"]
    assert result["low_level_keywords"] == ["低糖饮食"]
    assert result["keyword_source"] == "gliner_fallback"
    assert result["keyword_strategy"] == "token_classification_fallback"
    assert result["keyword_model"] == "knowledgator/gliner-x-small"


def test_trace_and_retrieval_result_expose_keyword_metadata():
    debug_payload = {
        "high_level_keywords": ["营养建议"],
        "low_level_keywords": ["低糖饮食"],
        "keyword_source": "gliner_fallback",
        "keyword_strategy": "token_classification_fallback",
        "keyword_fallback_reason": "explicit keywords missing",
        "keyword_model": "knowledgator/gliner-x-small",
        "keyword_model_device": "cpu",
        "keyword_model_error": None,
        "graph_entities": [],
        "graph_relations": [],
        "vector_weights": {},
        "vector_texts": {},
        "vector_file_paths": {},
        "graph_weights": {},
        "graph_texts": {},
        "graph_file_paths": {},
        "merged_candidates": [],
        "rerank_results": [],
        "results_text": [],
        "results_file_paths": [],
        "results_chunk_ids": [],
        "results_source_labels": [],
        "selected_candidate_indexes": [],
        "final_context_document_chunks": [],
        "final_context_text": "",
        "stage_timings": [],
    }

    trace = inference_runtime._build_one_hop_trace(
        "如何制定低糖饮食？",
        "hybrid",
        "",
        [],
        debug_payload,
    )
    retrieval_result = inference_runtime._build_retrieval_result_from_trace(trace)

    assert trace["keyword_source"] == "gliner_fallback"
    assert trace["keyword_strategy"] == "token_classification_fallback"
    assert retrieval_result["keyword_model"] == "knowledgator/gliner-x-small"
    assert retrieval_result["keyword_model_device"] == "cpu"


def test_retrieval_cache_fingerprint_changes_with_keyword_source():
    config = _global_config(_JsonLLM("{}"))
    request_param = QueryParam(mode="hybrid", hl_keywords=["营养建议"])
    keyword_extraction.apply_keyword_resolution(
        request_param,
        keyword_extraction.build_request_keyword_resolution(["营养建议"], []),
    )
    gliner_param = QueryParam(mode="hybrid", hl_keywords=["营养建议"])
    keyword_extraction.apply_keyword_resolution(
        gliner_param,
        keyword_extraction.KeywordResolution(
            high_level_keywords=["营养建议"],
            low_level_keywords=[],
            keyword_source=keyword_extraction.KEYWORD_SOURCE_GLINER_FALLBACK,
            keyword_strategy=keyword_extraction.KEYWORD_STRATEGY_TOKEN_CLASSIFICATION,
            keyword_fallback_reason="fallback",
            keyword_model="knowledgator/gliner-x-small",
            keyword_model_device="cpu",
        ),
    )

    request_key = operate._build_query_request_fingerprint(
        scope=operate._QUERY_CACHE_TYPE_RETRIEVAL,
        query="q",
        query_param=request_param,
        global_config=config,
        answer_prompt_mode="single_prompt",
    )
    gliner_key = operate._build_query_request_fingerprint(
        scope=operate._QUERY_CACHE_TYPE_RETRIEVAL,
        query="q",
        query_param=gliner_param,
        global_config=config,
        answer_prompt_mode="single_prompt",
    )

    assert request_key != gliner_key


def test_run_one_hop_no_longer_prefills_raw_query(monkeypatch):
    captured = {}

    class FakeRag:
        chunks_vdb = object()
        chunk_entity_relation_graph = object()
        relationships_vdb = object()
        entities_vdb = object()
        text_chunks = object()
        llm_response_cache = None

        async def _build_runtime_global_config(self):
            return _global_config(_FailingLLM())

        async def _query_done(self):
            return None

    async def fake_hybrid_query(
        _query,
        _chunks_vdb,
        _knowledge_graph_inst,
        _relationships_vdb,
        _entities_vdb,
        _text_chunks_db,
        query_param,
        *_args,
        **_kwargs,
    ):
        captured["hl_keywords"] = list(query_param.hl_keywords)
        captured["ll_keywords"] = list(query_param.ll_keywords)
        captured["allow_llm_keyword_extraction"] = (
            query_param.allow_llm_keyword_extraction
        )
        return "", [], {
            "high_level_keywords": [],
            "low_level_keywords": [],
            "keyword_source": "gliner_fallback",
            "keyword_strategy": "token_classification_fallback",
            "keyword_fallback_reason": "fallback",
            "keyword_model": "knowledgator/gliner-x-small",
            "keyword_model_device": "cpu",
            "graph_entities": [],
            "graph_relations": [],
            "vector_weights": {},
            "vector_texts": {},
            "vector_file_paths": {},
            "graph_weights": {},
            "graph_texts": {},
            "graph_file_paths": {},
            "merged_candidates": [],
            "rerank_results": [],
            "results_text": [],
            "results_file_paths": [],
            "results_chunk_ids": [],
            "results_source_labels": [],
            "selected_candidate_indexes": [],
            "final_context_document_chunks": [],
            "final_context_text": "",
            "stage_timings": [],
        }

    monkeypatch.setattr(inference_runtime, "hybrid_query", fake_hybrid_query)

    result = asyncio.run(
        inference_runtime._run_one_hop_with_rag(
            FakeRag(),
            "文档的主要主题是什么？",
            "hybrid",
            retrieval_only=True,
            only_need_context=True,
        )
    )

    assert captured["hl_keywords"] == []
    assert captured["ll_keywords"] == []
    assert captured["allow_llm_keyword_extraction"] is False
    assert result["retrieval_result"]["keyword_source"] == "gliner_fallback"
