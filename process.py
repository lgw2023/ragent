from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_DEFAULT_ASCEND_ENV_SCRIPTS = (
    "/usr/local/Ascend/ascend-toolkit/set_env.sh",
    "/usr/local/Ascend/ascend-toolkit/latest/set_env.sh",
    "/usr/local/Ascend/nnal/atb/set_env.sh",
    "/usr/local/Ascend/nnal/atb/latest/atb/set_env.sh",
)
_SOURCED_ENV_IGNORED_KEYS = {"_", "SHLVL", "PWD", "OLDPWD"}


def _strict_offline_enabled() -> bool:
    raw_value = os.getenv("MEP_STRICT_OFFLINE")
    if raw_value is None:
        raw_value = os.getenv("RAGENT_MEP_STRICT_OFFLINE")
    if raw_value is None:
        return True
    normalized = raw_value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"Invalid MEP_STRICT_OFFLINE value: {raw_value!r}")


def _normalize_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _split_env_script_list(value: str) -> tuple[str, ...]:
    raw_parts: list[str] = []
    for chunk in value.replace(",", os.pathsep).split(os.pathsep):
        normalized = chunk.strip()
        if normalized:
            raw_parts.append(normalized)
    return tuple(raw_parts)


def _ascend_environment_bootstrap_enabled() -> bool:
    raw_value = os.getenv("RAGENT_ASCEND_ENV_BOOTSTRAP")
    if raw_value is None:
        return True
    return raw_value.strip().lower() not in _FALSE_VALUES


def _resolve_ascend_env_scripts() -> tuple[Path, ...]:
    configured_single = _normalize_optional_str(os.getenv("RAGENT_ASCEND_SET_ENV_SH"))
    configured_multi = _normalize_optional_str(os.getenv("RAGENT_ASCEND_ENV_SHS"))
    if configured_single is not None:
        raw_scripts = (configured_single,)
    elif configured_multi is not None:
        raw_scripts = _split_env_script_list(configured_multi)
    else:
        raw_scripts = _DEFAULT_ASCEND_ENV_SCRIPTS

    resolved: list[Path] = []
    seen: set[Path] = set()
    for raw_script in raw_scripts:
        candidate = Path(raw_script).expanduser()
        if not candidate.is_file():
            continue
        resolved_candidate = candidate.resolve()
        if resolved_candidate in seen:
            continue
        resolved.append(resolved_candidate)
        seen.add(resolved_candidate)
    return tuple(resolved)


def _load_env_after_sourcing_scripts(
    script_paths: tuple[Path, ...],
    base_env: dict[str, str],
) -> dict[str, str]:
    source_commands = "; ".join(
        f"source {shlex.quote(str(script_path))} >/dev/null 2>&1 || true"
        for script_path in script_paths
    )
    completed = subprocess.run(
        ["bash", "-lc", f"{source_commands}; env -0"],
        check=False,
        env=base_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        script_list = ", ".join(str(path) for path in script_paths)
        raise RuntimeError(
            f"failed to source Ascend environment scripts: {script_list}; {stderr}"
        )

    sourced_env: dict[str, str] = {}
    for raw_item in completed.stdout.split(b"\0"):
        if not raw_item or b"=" not in raw_item:
            continue
        key, value = raw_item.split(b"=", 1)
        sourced_env[key.decode("utf-8", errors="surrogateescape")] = value.decode(
            "utf-8",
            errors="surrogateescape",
        )
    return sourced_env


def _apply_sourced_environment(
    sourced_env: dict[str, str],
    base_env: dict[str, str],
) -> tuple[str, ...]:
    changed_keys: list[str] = []
    for key, value in sourced_env.items():
        if key in _SOURCED_ENV_IGNORED_KEYS or base_env.get(key) == value:
            continue
        os.environ[key] = value
        changed_keys.append(key)
    if sourced_env.get("PYTHONPATH") != base_env.get("PYTHONPATH"):
        _prepend_sys_path_from_pythonpath(sourced_env.get("PYTHONPATH"))
    return tuple(sorted(changed_keys))


def _prepend_sys_path_from_pythonpath(raw_pythonpath: str | None) -> None:
    if not raw_pythonpath:
        return
    entries = [entry for entry in raw_pythonpath.split(os.pathsep) if entry]
    for entry in reversed(entries):
        normalized = str(Path(entry).expanduser())
        if normalized in sys.path:
            sys.path.remove(normalized)
        sys.path.insert(0, normalized)


def _bootstrap_ascend_toolkit_environment() -> None:
    if not _ascend_environment_bootstrap_enabled():
        _log_bootstrap("Ascend environment bootstrap: disabled")
        return

    script_paths = _resolve_ascend_env_scripts()
    if not script_paths:
        _log_bootstrap("Ascend environment bootstrap: no set_env.sh found")
        return

    base_env = os.environ.copy()
    try:
        sourced_env = _load_env_after_sourcing_scripts(script_paths, base_env)
    except Exception as exc:
        _log_bootstrap(f"Ascend environment bootstrap failed: {exc}")
        return

    changed_keys = _apply_sourced_environment(sourced_env, base_env)
    os.environ["RAGENT_ASCEND_ENV_BOOTSTRAPPED"] = "1"
    os.environ["RAGENT_ASCEND_ENV_BOOTSTRAPPED_SCRIPTS"] = os.pathsep.join(
        str(path) for path in script_paths
    )
    changed_preview = ", ".join(changed_keys[:12])
    if len(changed_keys) > 12:
        changed_preview += ", ..."
    _log_bootstrap(
        "sourced Ascend environment from: "
        + ", ".join(str(path) for path in script_paths)
        + (f"; updated env keys: {changed_preview}" if changed_preview else "")
    )


def _configure_default_offline_environment() -> None:
    if not _strict_offline_enabled():
        _log_bootstrap("strict offline mode: disabled")
        return
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["PIP_NO_INDEX"] = "1"
    os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    os.environ.setdefault("PIP_CONFIG_FILE", os.devnull)
    _log_bootstrap(
        "strict offline mode: enabled; "
        "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 "
        "PIP_NO_INDEX=1 PIP_CONFIG_FILE=%s" % os.environ.get("PIP_CONFIG_FILE")
    )


def _log_bootstrap(message: str) -> None:
    raw_value = os.getenv("RAGENT_MEP_BOOTSTRAP_LOG", "1").strip().lower()
    if raw_value in {"0", "false", "no", "off"}:
        return
    print(f"[ragent.mep_process.bootstrap] {message}", file=sys.stderr, flush=True)


_bootstrap_ascend_toolkit_environment()
_configure_default_offline_environment()

_CODE_ROOT = Path(__file__).resolve().parent
if str(_CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CODE_ROOT))

from mep_dependency_bootstrap import (  # noqa: E402
    bootstrap_mep_data_dependencies,
    ensure_mep_offline_requirements,
)


_installed_requirements = ensure_mep_offline_requirements(_CODE_ROOT)
_bootstrapped_paths = bootstrap_mep_data_dependencies(_CODE_ROOT)
if _installed_requirements:
    _log_bootstrap(
        "installed offline requirements from: "
        + ", ".join(_installed_requirements)
    )
if _bootstrapped_paths:
    _log_bootstrap(
        "bootstrapped MEP data dependency paths: "
        + os.pathsep.join(_bootstrapped_paths)
    )
if str(_CODE_ROOT) in sys.path:
    sys.path.remove(str(_CODE_ROOT))
sys.path.insert(0, str(_CODE_ROOT))

from ragent.runtime_env import bootstrap_runtime_environment  # noqa: E402


bootstrap_runtime_environment(explicit_runtime_env="mep", repo_root=_CODE_ROOT)
_configure_default_offline_environment()

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
        logger.info(
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
            logger.info("MEP path diagnostic: %s", note)

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
        # The MSG async framework stores calc()'s return as response_content and
        # exposes it on action=query after the task finishes.
        return build_recommend_success(
            payload,
            include_content=normalized_request.action in {None, "create"},
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
