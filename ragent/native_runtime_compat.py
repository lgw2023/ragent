from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from ragent.utils import logger


_OPENMP_PATTERN = re.compile(r"lib(?:iomp|omp|gomp|vcomp)[^/\s)]*", re.IGNORECASE)
_DARWIN_PRIVATE_FAISS_LIBOMP = "@loader_path/.dylibs/libomp.dylib"


def _flag_enabled(name: str, *, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _compat_policy() -> str:
    value = (os.getenv("RAG_FAISS_OPENMP_COMPAT_POLICY") or "auto").strip().lower()
    if value not in {"auto", "warn", "error", "off"}:
        raise ValueError(
            "RAG_FAISS_OPENMP_COMPAT_POLICY must be one of auto, warn, error, off"
        )
    return value


def _find_package_dir(package_name: str) -> Path | None:
    spec = importlib.util.find_spec(package_name)
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def _find_faiss_extension() -> Path | None:
    package_dir = _find_package_dir("faiss")
    if package_dir is None:
        return None
    candidates = sorted(
        path
        for path in package_dir.glob("_swigfaiss*")
        if path.suffix in {".so", ".pyd"}
    )
    return candidates[0] if candidates else None


def _find_torch_extension() -> Path | None:
    package_dir = _find_package_dir("torch")
    if package_dir is None:
        return None
    lib_dir = package_dir / "lib"
    lib_candidates = sorted(
        path
        for pattern in ("libtorch_cpu*", "libtorch_python*", "libtorch_global_deps*")
        for path in lib_dir.glob(pattern)
        if path.suffix in {".so", ".dylib", ".dll"}
    )
    if lib_candidates:
        return lib_candidates[0]
    candidates = sorted(
        path for path in package_dir.glob("_C*") if path.suffix in {".so", ".pyd"}
    )
    if candidates:
        return candidates[0]
    return None


def _dependency_command(binary_path: Path) -> list[str] | None:
    if sys.platform == "darwin":
        return ["otool", "-L", str(binary_path)]
    if sys.platform.startswith("linux"):
        return ["ldd", str(binary_path)]
    return None


def _read_binary_dependencies(binary_path: Path) -> str | None:
    command = _dependency_command(binary_path)
    if command is None:
        return None
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _extract_openmp_dependencies(dependencies: str | None) -> list[str]:
    if not dependencies:
        return []
    entries: list[str] = []
    for line in dependencies.splitlines():
        if _OPENMP_PATTERN.search(line):
            entries.append(line.strip())
    return entries


def _openmp_names(entries: list[str]) -> set[str]:
    names: set[str] = set()
    for entry in entries:
        match = _OPENMP_PATTERN.search(entry)
        if match:
            names.add(match.group(0).lower())
    return names


def _is_known_darwin_private_openmp_split(
    faiss_entries: list[str], torch_entries: list[str]
) -> bool:
    if sys.platform != "darwin":
        return False
    faiss_joined = "\n".join(faiss_entries)
    torch_joined = "\n".join(torch_entries)
    return (
        _DARWIN_PRIVATE_FAISS_LIBOMP in faiss_joined
        and "libomp.dylib" in torch_joined
    )


def check_native_openmp_compatibility() -> dict[str, Any]:
    """Inspect FAISS/PyTorch OpenMP linkage without importing either package.

    This is intentionally diagnostic-only. It does not rewrite installed wheels
    or set duplicate-OpenMP escape hatches, because those are environment fixes
    rather than library behavior.
    """

    if not _flag_enabled("RAG_NATIVE_OPENMP_CHECK", default=True):
        return {"status": "disabled", "platform": sys.platform}

    faiss_extension = _find_faiss_extension()
    if faiss_extension is None:
        return {"status": "faiss_missing", "platform": sys.platform}

    torch_extension = _find_torch_extension()
    if torch_extension is None:
        return {
            "status": "torch_missing",
            "platform": sys.platform,
            "faiss_extension": str(faiss_extension),
        }

    try:
        faiss_dependencies = _read_binary_dependencies(faiss_extension)
        torch_dependencies = _read_binary_dependencies(torch_extension)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return {
            "status": "unverified",
            "platform": sys.platform,
            "faiss_extension": str(faiss_extension),
            "torch_extension": str(torch_extension),
            "reason": str(exc),
        }

    faiss_openmp = _extract_openmp_dependencies(faiss_dependencies)
    torch_openmp = _extract_openmp_dependencies(torch_dependencies)
    faiss_names = _openmp_names(faiss_openmp)
    torch_names = _openmp_names(torch_openmp)
    shared_names = sorted(faiss_names & torch_names)
    mixed_names = bool(faiss_names and torch_names and not shared_names)
    known_private_split = _is_known_darwin_private_openmp_split(
        faiss_openmp, torch_openmp
    )
    status = "compatible"
    if known_private_split:
        status = "known_incompatible"
    elif mixed_names:
        status = "mixed_openmp"
    elif not faiss_openmp or not torch_openmp:
        status = "openmp_not_detected"

    return {
        "status": status,
        "platform": sys.platform,
        "faiss_extension": str(faiss_extension),
        "torch_extension": str(torch_extension),
        "faiss_openmp": faiss_openmp,
        "torch_openmp": torch_openmp,
        "shared_openmp_names": shared_names,
    }


def _compatibility_error(result: dict[str, Any]) -> RuntimeError:
    return RuntimeError(
        "FAISS and PyTorch appear to load incompatible OpenMP runtimes in this "
        "Python environment. Ragent does not mutate installed wheels at import "
        "time. Use a dependency set where FAISS and PyTorch share one OpenMP "
        "runtime, such as a Linux container/runtime image verified for ragent, "
        "conda-forge packages from the same environment, or a locally rebuilt "
        "FAISS linked against the same OpenMP runtime as PyTorch. Do not use "
        "KMP_DUPLICATE_LIB_OK for production. "
        f"diagnostic={result}"
    )


def ensure_faiss_import_compatibility() -> dict[str, Any]:
    """Run pre-import native compatibility checks for FAISS sidecar backends."""

    policy = _compat_policy()
    if policy == "off":
        return {"status": "disabled", "platform": sys.platform}

    result = check_native_openmp_compatibility()
    status = str(result.get("status") or "")
    should_error = policy == "error" or (
        policy == "auto" and status == "known_incompatible"
    )
    should_warn = policy in {"auto", "warn"} and status == "mixed_openmp"

    if should_error:
        raise _compatibility_error(result)
    if should_warn:
        logger.warning(
            "FAISS/PyTorch OpenMP linkage is mixed; continuing because policy=%s: %s",
            policy,
            result,
        )
    return result
