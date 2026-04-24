from __future__ import annotations

import json
import logging
import os
import site
import sys
from pathlib import Path


def _maybe_json_loads(value: str):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _resolve_component_runtime_data_dir(current_dir: Path) -> Path | None:
    for candidate in (current_dir, *current_dir.parents):
        if candidate.name == "component" and (candidate / "config.json").is_file():
            return (candidate.parent / "data").resolve()
    return None


def _resolve_sfs_data_dir() -> Path | None:
    raw_model_sfs = (os.getenv("MODEL_SFS") or "").strip()
    model_object_id = (os.getenv("MODEL_OBJECT_ID") or "").strip()
    if not raw_model_sfs or not model_object_id:
        return None
    payload = _maybe_json_loads(raw_model_sfs)
    if not isinstance(payload, dict):
        return None
    sfs_base_path = payload.get("sfsBasePath")
    if not isinstance(sfs_base_path, str) or not sfs_base_path.strip():
        return None
    return (Path(sfs_base_path).expanduser() / model_object_id / "data").resolve()


def _iter_mep_data_dir_candidates(current_dir: Path):
    explicit_data_dir = os.getenv("RAGENT_MEP_DATA_DIR")
    if explicit_data_dir:
        yield Path(explicit_data_dir).expanduser().resolve()

    runtime_data_dir = _resolve_component_runtime_data_dir(current_dir)
    if runtime_data_dir is not None:
        yield runtime_data_dir

    sfs_data_dir = _resolve_sfs_data_dir()
    if sfs_data_dir is not None:
        yield sfs_data_dir

    yield (current_dir / "data").resolve()


def _iter_mep_dependency_paths(data_dir: Path):
    deps_dir = data_dir / "deps"
    extra_pythonpath = os.getenv("RAGENT_MEP_EXTRA_PYTHONPATH") or ""
    for env_path in extra_pythonpath.split(os.pathsep):
        if env_path.strip():
            yield Path(env_path).expanduser().resolve()

    for relative_dir in (
        "pythonpath",
        "site-packages",
        "python",
    ):
        yield (deps_dir / relative_dir).resolve()

    wheelhouse_dir = deps_dir / "wheelhouse"
    if wheelhouse_dir.is_dir():
        yield from sorted(wheelhouse_dir.glob("*.whl"))


def _prepend_import_path(path: Path) -> bool:
    if not path.exists():
        return False
    path_text = str(path)
    if path.is_dir():
        site.addsitedir(path_text)
    if path_text in sys.path:
        sys.path.remove(path_text)
    sys.path.insert(0, path_text)
    return True


def _bootstrap_mep_data_dependencies(current_dir: Path) -> None:
    added_paths: list[str] = []
    seen_data_dirs: set[Path] = set()
    for data_dir in _iter_mep_data_dir_candidates(current_dir):
        if data_dir in seen_data_dirs:
            continue
        seen_data_dirs.add(data_dir)
        if not data_dir.is_dir():
            continue
        for dependency_path in _iter_mep_dependency_paths(data_dir):
            if _prepend_import_path(dependency_path):
                added_paths.append(str(dependency_path))
    if added_paths:
        os.environ["RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH"] = os.pathsep.join(added_paths)


_CODE_ROOT = Path(__file__).resolve().parent
_bootstrap_mep_data_dependencies(_CODE_ROOT)
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

from ragent.runtime_env import bootstrap_runtime_environment  # noqa: E402


bootstrap_runtime_environment(explicit_runtime_env="mep", repo_root=_CODE_ROOT)

from ragent.mep_adapter import (  # noqa: E402
    AsyncLoopThread,
    ComponentBundlePaths,
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
        self._bundle_paths: ComponentBundlePaths | None = None
        self._runtime_session: InferenceRuntimeSession | None = None
        self._runtime_layout = None
        self._embedding_runtime: LocalEmbeddingRuntime | None = None
        self._closed = False

    @staticmethod
    def _diagnostic_env_value(name: str, *, max_length: int = 256) -> str | None:
        raw_value = os.getenv(name)
        if raw_value is None:
            return None
        value = raw_value.strip()
        if len(value) <= max_length:
            return value
        return value[:max_length] + "...(truncated)"

    def _log_bundle_path_resolution(self, bundle_paths: ComponentBundlePaths) -> None:
        logger.debug(
            "Resolving MEP bundle paths. process_file=%s cwd=%s gpu_id=%s model_root=%s "
            "MODEL_SFS=%s MODEL_OBJECT_ID=%s MODEL_RELATIVE_DIR=%s MODEL_ABSOLUTE_DIR=%s "
            "path_appendix=%s RAGENT_MEP_MODEL_DIR=%s RAGENT_MEP_DATA_DIR=%s",
            __file__,
            Path.cwd(),
            self._gpu_id,
            self._model_root,
            self._diagnostic_env_value("MODEL_SFS"),
            self._diagnostic_env_value("MODEL_OBJECT_ID"),
            self._diagnostic_env_value("MODEL_RELATIVE_DIR"),
            self._diagnostic_env_value("MODEL_ABSOLUTE_DIR"),
            self._diagnostic_env_value("path_appendix"),
            self._diagnostic_env_value("RAGENT_MEP_MODEL_DIR"),
            self._diagnostic_env_value("RAGENT_MEP_DATA_DIR"),
        )
        logger.info(
            "Resolved MEP bundle paths. model_dir=%s source=%s exists=%s; "
            "data_dir=%s source=%s exists=%s; meta_dir=%s source=%s exists=%s",
            bundle_paths.model_dir,
            bundle_paths.model_source,
            bundle_paths.model_dir.exists(),
            bundle_paths.data_dir,
            bundle_paths.data_source,
            bundle_paths.data_dir.exists(),
            bundle_paths.meta_dir,
            bundle_paths.meta_source,
            bundle_paths.meta_dir.exists(),
        )
        for note in bundle_paths.diagnostics:
            logger.debug("MEP path diagnostic: %s", note)

    def _release_runtime_resources(self) -> None:
        runtime_session = self._runtime_session
        self._bundle_paths = None
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
            model_root=self._model_root,
        )
        self._bundle_paths = bundle_paths
        self._log_bundle_path_resolution(bundle_paths)
        embedding_runtime: LocalEmbeddingRuntime | None = None
        runtime_layout = None
        runtime_session = None
        try:
            embedding_runtime = bootstrap_local_embedding_runtime(
                bundle_paths.model_dir,
                data_dir=bundle_paths.data_dir,
            )
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
            "model_dir=%s data_dir=%s source_project_dir=%s runtime_project_dir=%s copied=%s",
            bundle_paths.model_dir,
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
