from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


_CODE_ROOT = Path(__file__).resolve().parent
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

from ragent.runtime_env import bootstrap_runtime_environment  # noqa: E402


bootstrap_runtime_environment(explicit_runtime_env="mep", repo_root=_CODE_ROOT)

from ragent.mep_adapter import (  # noqa: E402
    AsyncLoopThread,
    InferenceRuntimeSession,
    build_action_query_response,
    build_recommend_error,
    build_recommend_success,
    build_result_payload,
    cleanup_runtime_project_layout,
    get_mep_action,
    maybe_write_result_payload,
    normalize_mep_request,
    prepare_runtime_project_layout,
    resolve_component_bundle_paths,
)
from ragent.mep_embedding_runtime import (  # noqa: E402
    LocalEmbeddingRuntime,
    bootstrap_local_embedding_runtime,
)


logger = logging.getLogger("ragent.mep_process")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(os.getenv("RAGENT_LOG_LEVEL", "INFO").upper())


class CustomerModel:
    def __init__(self, gpu_id=None, model_root=None):
        self._gpu_id = gpu_id
        self._model_root = Path(model_root).expanduser().resolve() if model_root else None
        self._loop_runner = AsyncLoopThread()
        self._runtime_session: InferenceRuntimeSession | None = None
        self._runtime_layout = None
        self._embedding_runtime: LocalEmbeddingRuntime | None = None
        self._closed = False

    def _release_runtime_resources(self) -> None:
        runtime_session = self._runtime_session
        runtime_layout = self._runtime_layout
        embedding_runtime = self._embedding_runtime
        self._runtime_session = None
        self._runtime_layout = None
        self._embedding_runtime = None

        try:
            if runtime_session is not None:
                self._loop_runner.run(runtime_session.close())
        finally:
            cleanup_runtime_project_layout(runtime_layout)
            if embedding_runtime is not None:
                embedding_runtime.shutdown()

    async def _load_async(self) -> None:
        if self._runtime_session is not None:
            return

        bundle_paths = resolve_component_bundle_paths(
            __file__,
            data_dir_override=(
                self._model_root / "data" if self._model_root is not None else None
            ),
            model_dir_override=(
                self._model_root / "model" if self._model_root is not None else None
            ),
        )
        embedding_runtime: LocalEmbeddingRuntime | None = None
        runtime_layout = None
        runtime_session = None
        try:
            embedding_runtime = bootstrap_local_embedding_runtime(bundle_paths.model_dir)
            runtime_layout = prepare_runtime_project_layout(
                data_dir=bundle_paths.data_dir,
                model_dir=bundle_paths.model_dir,
            )
            runtime_session = InferenceRuntimeSession(
                project_dir=str(runtime_layout.runtime_project_dir)
            )
            await runtime_session.load()
        except Exception:
            if runtime_session is not None:
                await runtime_session.close()
            cleanup_runtime_project_layout(runtime_layout)
            if embedding_runtime is not None:
                embedding_runtime.shutdown()
            raise

        self._runtime_layout = runtime_layout
        self._runtime_session = runtime_session
        self._embedding_runtime = embedding_runtime
        logger.info(
            "MEP runtime loaded. "
            "data_dir=%s source_project_dir=%s runtime_project_dir=%s copied=%s",
            runtime_layout.data_dir,
            runtime_layout.source_project_dir,
            runtime_layout.runtime_project_dir,
            runtime_layout.copied_to_runtime_dir,
        )

    def load(self):
        if self._closed:
            raise RuntimeError("CustomerModel has been cleaned up")
        try:
            self._loop_runner.run(self._load_async())
        except Exception as exc:
            logger.exception("CustomerModel.load failed")
            raise RuntimeError(f"CustomerModel.load failed: {exc}") from exc

    async def _calc_async(self, req_data):
        action = get_mep_action(req_data)
        if action == "query":
            return build_action_query_response(req_data)

        if self._runtime_session is None or self._runtime_layout is None:
            raise RuntimeError("CustomerModel is not loaded")

        normalized_request = normalize_mep_request(req_data)
        if (
            normalized_request.action == "create"
            and normalized_request.generate_path is None
        ):
            raise ValueError("generatePath is required for action=create")

        result = await self._runtime_session.run(normalized_request.inference_request)
        payload = build_result_payload(
            request=normalized_request,
            result=result,
            runtime_layout=self._runtime_layout,
        )
        maybe_write_result_payload(
            payload,
            generate_path=normalized_request.generate_path,
            result_filename=normalized_request.result_filename,
        )
        return build_recommend_success(
            payload,
            include_content=normalized_request.action is None,
        )

    def calc(self, req_Data):
        if self._closed:
            return build_recommend_error("CustomerModel has been cleaned up")
        try:
            return self._loop_runner.run(self._calc_async(req_Data))
        except Exception as exc:
            logger.exception("CustomerModel.calc failed")
            return build_recommend_error(str(exc))

    def event(self, req_Data):
        return self.calc(req_Data)

    def health(self):
        return not self._closed

    def cleanup(self):
        if self._closed:
            return
        try:
            self._release_runtime_resources()
        except Exception:
            logger.exception("CustomerModel cleanup failed")
        finally:
            self._closed = True
            try:
                self._loop_runner.close()
            except Exception:
                pass

    def __del__(self):
        self.cleanup()
