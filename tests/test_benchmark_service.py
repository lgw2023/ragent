from __future__ import annotations

import asyncio
from types import SimpleNamespace

from ragent.api import benchmark_service


def test_preload_configured_projects_creates_sessions(monkeypatch, tmp_path):
    project_a = tmp_path / "project_a"
    project_b = tmp_path / "project_b"
    project_a.mkdir()
    project_b.mkdir()
    calls: list[tuple[str, bool]] = []

    async def fake_initialize_rag(
        project_dir,
        stage_timings=None,
        *,
        require_llm=True,
        enable_rerank=None,
    ):
        calls.append((project_dir, require_llm))
        return SimpleNamespace(
            llm_response_cache=None,
            vector_sidecar_info={
                "profile": "default_hnsw_v1",
                "sidecar_dir": f"{project_dir}/vector_sidecars/default",
                "manifest_digest": f"digest-{len(calls)}",
            },
            keyword_fallback_preload_info={
                "keyword_model": "/models/gliner",
                "keyword_model_device": "cpu",
            },
        )

    monkeypatch.setattr(benchmark_service, "initialize_rag", fake_initialize_rag)
    monkeypatch.setenv(
        "RAG_PRELOAD_PROJECT_DIRS",
        f"{project_a},{project_b}",
    )

    state = benchmark_service.BenchmarkServiceState()
    asyncio.run(state.preload_configured_projects())

    assert calls == [(str(project_a.resolve()), True), (str(project_b.resolve()), True)]
    assert sorted(state._sessions) == [
        str(project_a.resolve()),
        str(project_b.resolve()),
    ]
    assert (
        state._sessions[str(project_a.resolve())].vector_sidecar_info["sidecar_dir"]
        == f"{project_a.resolve()}/vector_sidecars/default"
    )
    assert (
        state._sessions[str(project_b.resolve())].vector_sidecar_info["sidecar_dir"]
        == f"{project_b.resolve()}/vector_sidecars/default"
    )
    assert (
        state._sessions[str(project_a.resolve())].keyword_fallback_preload_info[
            "keyword_model"
        ]
        == "/models/gliner"
    )
