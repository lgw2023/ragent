from __future__ import annotations

import asyncio
from types import SimpleNamespace

import ragent.runtime_env as runtime_env
from ragent.llm import openai as openai_module


def test_resolve_ssl_verify_disable_with_ragent_env(monkeypatch):
    monkeypatch.setenv("RAGENT_SSL_VERIFY", "0")
    monkeypatch.setenv("SSL_VERIFY", "1")

    assert runtime_env.resolve_ssl_verify() is False


def test_resolve_ssl_verify_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("RAGENT_SSL_VERIFY", raising=False)
    monkeypatch.delenv("SSL_VERIFY", raising=False)

    assert runtime_env.resolve_ssl_verify() is False


def test_resolve_ssl_verify_invalid_value_warns_and_defaults_disabled(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("RAGENT_SSL_VERIFY", "maybe")
    monkeypatch.setenv("SSL_VERIFY", "1")

    assert runtime_env.resolve_ssl_verify() is False
    warning = capsys.readouterr().err
    assert "unsupported RAGENT_SSL_VERIFY='maybe'" in warning
    assert "TLS verification remains disabled" in warning


def test_resolve_ssl_verify_can_enable_with_ragent_env(monkeypatch):
    monkeypatch.setenv("RAGENT_SSL_VERIFY", "1")

    assert runtime_env.resolve_ssl_verify() is True


def test_openai_complete_sets_global_ssl_verify_without_request_kwarg(monkeypatch):
    captured_kwargs: dict = {}

    async def fake_acompletion(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="ok"),
                )
            ],
            usage=None,
        )

    monkeypatch.setenv("RAGENT_SSL_VERIFY", "0")
    monkeypatch.setattr(openai_module.litellm, "ssl_verify", True)
    monkeypatch.setattr(openai_module, "acompletion", fake_acompletion)
    monkeypatch.setattr(
        openai_module,
        "_build_litellm_request",
        lambda **kwargs: (
            kwargs["model"],
            "openai",
            {"api_key": "key", "api_base": "https://example.com/v1"},
        ),
    )
    monkeypatch.setattr(openai_module, "record_model_usage", lambda *args, **kwargs: None)
    monkeypatch.setattr(openai_module, "log_model_call", lambda *args, **kwargs: None)

    result = asyncio.run(
        openai_module.openai_complete_if_cache(
            "test-model",
            "hello",
            api_key="key",
            base_url="https://example.com/v1",
        )
    )

    assert result == "ok"
    assert "ssl_verify" not in captured_kwargs
    assert openai_module.litellm.ssl_verify is False
