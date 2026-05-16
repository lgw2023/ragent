from __future__ import annotations

import pytest

import integrations


def test_rag_insert_batch_defaults_to_all_units_without_hard_timeout(monkeypatch):
    monkeypatch.delenv("RAG_INSERT_BATCH_SIZE", raising=False)

    assert (
        integrations._resolve_rag_insert_batch_size(
            total_units=192,
            llm_model_max_async=8,
            hard_timeout_enabled=False,
        )
        == 192
    )


def test_rag_insert_batch_defaults_to_async_limit_with_hard_timeout(monkeypatch):
    monkeypatch.delenv("RAG_INSERT_BATCH_SIZE", raising=False)

    assert (
        integrations._resolve_rag_insert_batch_size(
            total_units=192,
            llm_model_max_async=8,
            hard_timeout_enabled=True,
        )
        == 8
    )


@pytest.mark.parametrize("raw_value", ["0", "all", "full", "none"])
def test_rag_insert_batch_accepts_all_aliases(monkeypatch, raw_value):
    monkeypatch.setenv("RAG_INSERT_BATCH_SIZE", raw_value)

    assert (
        integrations._resolve_rag_insert_batch_size(
            total_units=192,
            llm_model_max_async=8,
            hard_timeout_enabled=True,
        )
        == 192
    )


def test_rag_insert_batch_caps_explicit_size_to_total_units(monkeypatch):
    monkeypatch.setenv("RAG_INSERT_BATCH_SIZE", "500")

    assert (
        integrations._resolve_rag_insert_batch_size(
            total_units=192,
            llm_model_max_async=8,
            hard_timeout_enabled=False,
        )
        == 192
    )


def test_rag_insert_batch_rejects_invalid_value(monkeypatch):
    monkeypatch.setenv("RAG_INSERT_BATCH_SIZE", "eight")

    with pytest.raises(ValueError, match="Invalid RAG_INSERT_BATCH_SIZE"):
        integrations._resolve_rag_insert_batch_size(
            total_units=192,
            llm_model_max_async=8,
            hard_timeout_enabled=False,
        )
