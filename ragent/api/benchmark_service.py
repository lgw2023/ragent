from __future__ import annotations

import argparse
import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from integrations import (
    _close_rag,
    _run_one_hop_with_rag,
    ensure_startup_model_check_once,
    initialize_rag,
)
from ragent.benchmarking import (
    QUERY_CACHE_TYPES,
    clear_query_cache_entries,
    collect_cache_hit_stages,
    extract_stage_seconds,
    normalize_project_dir,
)


class BenchmarkQueryRequest(BaseModel):
    project_dir: str
    query: str
    mode: Literal["graph", "hybrid"] = "hybrid"
    enable_rerank: bool = True
    include_trace: bool = False
    response_type: str = "Multiple Paragraphs"
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    history_turns: int | None = None


class CacheClearRequest(BaseModel):
    project_dir: str
    modes: list[str] = Field(default_factory=list)
    cache_types: list[Literal["answer", "retrieval", "render", "prompt"]] = Field(
        default_factory=list
    )


class ProjectResetRequest(BaseModel):
    project_dir: str
    clear_cache: bool = False
    modes: list[str] = Field(default_factory=list)
    cache_types: list[Literal["answer", "retrieval", "render", "prompt"]] = Field(
        default_factory=list
    )


@dataclass
class ProjectSession:
    project_dir: str
    rag: Any
    query_count: int = 0
    query_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def clear_cache(
        self,
        *,
        modes: list[str] | None = None,
        cache_types: list[str] | None = None,
    ) -> bool:
        storage = getattr(self.rag, "llm_response_cache", None)
        if storage is None:
            return False

        dropped = await storage.drop_cache_entries(
            modes=modes or None,
            cache_types=cache_types or None,
        )
        if dropped:
            await storage.index_done_callback()
        return dropped

    async def close(self) -> None:
        await _close_rag(self.rag)


class BenchmarkServiceState:
    def __init__(self):
        self.started_at = time.time()
        self.startup_ready_seconds: float | None = None
        self._sessions: dict[str, ProjectSession] = {}
        self._project_locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def startup(self) -> None:
        started_at = time.perf_counter()
        await ensure_startup_model_check_once()
        self.startup_ready_seconds = round(time.perf_counter() - started_at, 6)

    async def shutdown(self) -> None:
        async with self._registry_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._project_locks.clear()
        for session in sessions:
            await session.close()

    async def get_or_create_session(
        self,
        project_dir: str,
    ) -> tuple[ProjectSession, bool, list[dict[str, Any]]]:
        existing = self._sessions.get(project_dir)
        if existing is not None:
            return existing, True, []

        async with self._registry_lock:
            project_lock = self._project_locks.setdefault(project_dir, asyncio.Lock())

        async with project_lock:
            existing = self._sessions.get(project_dir)
            if existing is not None:
                return existing, True, []

            init_stage_timings: list[dict[str, Any]] = []
            rag = await initialize_rag(project_dir, stage_timings=init_stage_timings)
            session = ProjectSession(project_dir=project_dir, rag=rag)
            async with self._registry_lock:
                self._sessions[project_dir] = session
            return session, False, list(init_stage_timings)

    async def clear_cache(
        self,
        project_dir: str,
        *,
        modes: list[str] | None = None,
        cache_types: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self._sessions.get(project_dir)
        if session is not None:
            async with session.query_lock:
                dropped = await session.clear_cache(
                    modes=modes,
                    cache_types=cache_types,
                )
            return {
                "project_loaded": True,
                "cache_files": [],
                "deleted_entry_count": None,
                "cache_cleared": dropped,
                "modes": list(modes or []),
                "cache_types": list(cache_types or []),
            }

        result = clear_query_cache_entries(
            project_dir,
            modes=modes,
            cache_types=cache_types,
        )
        return {
            "project_loaded": False,
            "cache_cleared": True,
            **result,
        }

    async def reset_project(
        self,
        project_dir: str,
        *,
        clear_cache: bool = False,
        modes: list[str] | None = None,
        cache_types: list[str] | None = None,
    ) -> dict[str, Any]:
        async with self._registry_lock:
            session = self._sessions.pop(project_dir, None)

        if session is not None:
            async with session.query_lock:
                await session.close()

        cache_result: dict[str, Any] | None = None
        if clear_cache or modes or cache_types:
            cache_result = await self.clear_cache(
                project_dir,
                modes=modes,
                cache_types=cache_types,
            )

        return {
            "project_unloaded": session is not None,
            "cache": cache_result,
        }


def _normalize_and_validate_project_dir(project_dir: str) -> str:
    resolved = normalize_project_dir(project_dir)
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Project dir not found: {resolved}")
    return str(resolved)


def _response_payload(
    *,
    request: BenchmarkQueryRequest,
    result: dict[str, Any],
    stage_timings: list[dict[str, Any]],
    request_processing_seconds: float,
    project_dir: str,
    project_initialized_before_request: bool,
    project_first_request: bool,
) -> dict[str, Any]:
    cache_hit_stages = collect_cache_hit_stages(stage_timings)
    trace = result.get("trace") or {}
    referenced_file_paths = list(result.get("referenced_file_paths") or [])

    return {
        "project_dir": project_dir,
        "query": request.query,
        "mode": request.mode,
        "enable_rerank": request.enable_rerank,
        "include_trace": request.include_trace,
        "answer": result.get("answer", ""),
        "referenced_file_paths": referenced_file_paths,
        "stage_timings": stage_timings,
        "cache_hit_stages": cache_hit_stages,
        "cache_hit_count": len(cache_hit_stages),
        "project_initialized_before_request": project_initialized_before_request,
        "project_first_request": project_first_request,
        "request_processing_seconds": round(request_processing_seconds, 6),
        "project_initialization_seconds": extract_stage_seconds(
            stage_timings, "rag_initialization_total"
        ),
        "startup_model_check_seconds": extract_stage_seconds(
            stage_timings, "startup_model_check"
        ),
        "query_seconds": extract_stage_seconds(stage_timings, "onehop_total"),
        "trace": trace if request.include_trace else None,
        "trace_stage_count": len(stage_timings),
        "reference_chunk_count": len(trace.get("final_context_document_chunks") or []),
    }


def create_app() -> FastAPI:
    state = BenchmarkServiceState()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await state.startup()
        app.state.benchmark_service = state
        yield
        await state.shutdown()

    app = FastAPI(title="Ragent Benchmark Service", version="1.0.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "started_at": state.started_at,
            "startup_ready_seconds": state.startup_ready_seconds,
            "loaded_projects": sorted(state._sessions.keys()),
            "supported_cache_types": list(QUERY_CACHE_TYPES),
        }

    @app.post("/v1/benchmark/query")
    async def benchmark_query(request: BenchmarkQueryRequest) -> dict[str, Any]:
        project_dir = _normalize_and_validate_project_dir(request.project_dir)
        session, initialized_before_request, init_stage_timings = await state.get_or_create_session(
            project_dir
        )
        project_first_request = session.query_count == 0
        started_at = time.perf_counter()

        async with session.query_lock:
            result = await _run_one_hop_with_rag(
                session.rag,
                request.query,
                request.mode,
                conversation_history=request.conversation_history or None,
                history_turns=request.history_turns,
                include_trace=True,
                prefill_stage_timings=init_stage_timings if not initialized_before_request else None,
                enable_rerank=request.enable_rerank,
                response_type=request.response_type,
            )
            session.query_count += 1

        trace = result.get("trace") or {}
        stage_timings = list(trace.get("stage_timings") or [])
        return _response_payload(
            request=request,
            result=result,
            stage_timings=stage_timings,
            request_processing_seconds=time.perf_counter() - started_at,
            project_dir=project_dir,
            project_initialized_before_request=initialized_before_request,
            project_first_request=project_first_request,
        )

    @app.post("/v1/benchmark/cache/clear")
    async def clear_cache(request: CacheClearRequest) -> dict[str, Any]:
        project_dir = _normalize_and_validate_project_dir(request.project_dir)
        return await state.clear_cache(
            project_dir,
            modes=request.modes or None,
            cache_types=request.cache_types or None,
        )

    @app.post("/v1/benchmark/project/reset")
    async def reset_project(request: ProjectResetRequest) -> dict[str, Any]:
        project_dir = _normalize_and_validate_project_dir(request.project_dir)
        return await state.reset_project(
            project_dir,
            clear_cache=request.clear_cache,
            modes=request.modes or None,
            cache_types=request.cache_types or None,
        )

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Ragent benchmark HTTP service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
