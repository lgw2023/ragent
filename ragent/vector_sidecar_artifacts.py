from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from collections.abc import Iterable
from typing import Any, Literal

VECTOR_SIDECARS_DIRNAME = "vector_sidecars"
DEFAULT_VECTOR_SIDECAR_NAME = "default"
MANIFEST_FILE_NAME = "manifest.json"

DEFAULT_SIDECAR_PROFILE = "default_hnsw_v1"
EXACT_SIDECAR_PROFILE = "exact"
CUSTOM_SIDECAR_PROFILE = "custom"
SIDECAR_PROFILES = {
    DEFAULT_SIDECAR_PROFILE,
    EXACT_SIDECAR_PROFILE,
    CUSTOM_SIDECAR_PROFILE,
}

VDB_NAMESPACES = {
    "chunks": "vdb_chunks.json",
    "entities": "vdb_entities.json",
    "relationships": "vdb_relationships.json",
}

VectorRuntimeBackend = Literal["faiss_sidecar", "nano"]


class VectorSidecarArtifactError(RuntimeError):
    pass


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def vector_sidecar_build_enabled(default: bool = True) -> bool:
    return _env_flag("RAG_BUILD_VECTOR_SIDECAR", default)


def resolve_vector_runtime_backend(
    raw_value: str | None = None,
    *,
    default: VectorRuntimeBackend = "faiss_sidecar",
) -> VectorRuntimeBackend:
    value = (raw_value if raw_value is not None else os.getenv("RAG_VECTOR_RUNTIME_BACKEND"))
    normalized = str(value or default).strip().lower().replace("-", "_")
    if normalized in {"faiss", "faiss_sidecar", "sidecar"}:
        return "faiss_sidecar"
    if normalized in {"nano", "nanovector", "nano_vector", "nano_vectordb"}:
        return "nano"
    raise VectorSidecarArtifactError(
        "Unsupported RAG_VECTOR_RUNTIME_BACKEND value: "
        f"{value!r}. Expected faiss_sidecar or nano."
    )


def normalize_sidecar_profile(raw_profile: str | None) -> str:
    normalized = str(raw_profile or DEFAULT_SIDECAR_PROFILE).strip().lower()
    aliases = {
        "default": DEFAULT_SIDECAR_PROFILE,
        "default_hnsw": DEFAULT_SIDECAR_PROFILE,
        "default_hnsw_v1": DEFAULT_SIDECAR_PROFILE,
        "production": DEFAULT_SIDECAR_PROFILE,
        "exact": EXACT_SIDECAR_PROFILE,
        "flat": EXACT_SIDECAR_PROFILE,
        "custom": CUSTOM_SIDECAR_PROFILE,
    }
    profile = aliases.get(normalized)
    if profile is None:
        raise VectorSidecarArtifactError(
            f"Unsupported sidecar profile: {raw_profile!r}. "
            f"Expected one of {sorted(SIDECAR_PROFILES)}."
        )
    return profile


def default_vector_sidecar_dir(project_dir: str | os.PathLike[str]) -> Path:
    return (
        Path(project_dir).expanduser().resolve()
        / VECTOR_SIDECARS_DIRNAME
        / DEFAULT_VECTOR_SIDECAR_NAME
    )


def profile_vector_sidecar_dir(
    project_dir: str | os.PathLike[str],
    profile: str,
) -> Path:
    resolved_profile = normalize_sidecar_profile(profile)
    if resolved_profile == DEFAULT_SIDECAR_PROFILE:
        return default_vector_sidecar_dir(project_dir)
    return (
        Path(project_dir).expanduser().resolve()
        / VECTOR_SIDECARS_DIRNAME
        / resolved_profile
    )


def required_vdb_paths(project_dir: str | os.PathLike[str]) -> dict[str, Path]:
    root = Path(project_dir).expanduser().resolve()
    return {namespace: root / file_name for namespace, file_name in VDB_NAMESPACES.items()}


def has_required_vdb_files(project_dir: str | os.PathLike[str]) -> bool:
    return all(path.is_file() for path in required_vdb_paths(project_dir).values())


def load_vector_sidecar_manifest(
    sidecar_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    manifest_path = Path(sidecar_dir).expanduser().resolve() / MANIFEST_FILE_NAME
    if not manifest_path.is_file():
        raise VectorSidecarArtifactError(
            f"FAISS sidecar manifest not found: {manifest_path}"
        )
    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)
    if int(manifest.get("version") or 0) != 1:
        raise VectorSidecarArtifactError(
            f"Unsupported FAISS sidecar manifest version: {manifest_path}"
        )
    return manifest


def vector_sidecar_manifest_digest(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_vector_sidecar_manifest(
    project_dir: str | os.PathLike[str],
    sidecar_dir: str | os.PathLike[str],
    *,
    expected_profile: str | None = None,
    check_hashes: bool = True,
    required_namespaces: Iterable[str] | None = None,
) -> dict[str, Any]:
    project_root = Path(project_dir).expanduser().resolve()
    sidecar_root = Path(sidecar_dir).expanduser().resolve()
    manifest = load_vector_sidecar_manifest(sidecar_root)

    if expected_profile is not None:
        expected = normalize_sidecar_profile(expected_profile)
        if not manifest.get("profile"):
            raise VectorSidecarArtifactError(
                f"FAISS sidecar profile mismatch: expected {expected}, got missing."
            )
        actual = normalize_sidecar_profile(manifest.get("profile"))
        if actual != expected:
            raise VectorSidecarArtifactError(
                f"FAISS sidecar profile mismatch: expected {expected}, got {actual}."
            )

    namespaces = manifest.get("namespaces")
    if not isinstance(namespaces, dict):
        raise VectorSidecarArtifactError("FAISS sidecar manifest is missing namespaces.")

    namespace_names = (
        list(required_namespaces) if required_namespaces is not None else list(VDB_NAMESPACES)
    )
    for namespace in namespace_names:
        if namespace not in VDB_NAMESPACES:
            raise VectorSidecarArtifactError(
                f"Unknown FAISS sidecar namespace {namespace!r}."
            )
        file_name = VDB_NAMESPACES[namespace]
        namespace_manifest = namespaces.get(namespace)
        if not isinstance(namespace_manifest, dict):
            raise VectorSidecarArtifactError(
                f"FAISS sidecar manifest is missing namespace {namespace!r}."
            )

        source_file = str(namespace_manifest.get("source_file") or file_name)
        source_path = project_root / source_file
        if not source_path.is_file():
            raise VectorSidecarArtifactError(
                f"Source vector DB file for {namespace!r} not found: {source_path}"
            )

        expected_size = namespace_manifest.get("source_size_bytes")
        if expected_size is not None and source_path.stat().st_size != int(expected_size):
            raise VectorSidecarArtifactError(
                f"Source vector DB size mismatch for {namespace!r}: {source_path}"
            )

        expected_hash = namespace_manifest.get("source_sha256")
        if check_hashes and expected_hash and _sha256(source_path) != str(expected_hash):
            raise VectorSidecarArtifactError(
                f"Source vector DB hash mismatch for {namespace!r}: {source_path}"
            )

        for key in ("index_file", "metadata_file"):
            artifact = sidecar_root / str(namespace_manifest.get(key) or "")
            if not artifact.is_file():
                raise VectorSidecarArtifactError(
                    f"FAISS sidecar artifact {key} for {namespace!r} not found: "
                    f"{artifact}"
                )

    return {
        "sidecar_dir": str(sidecar_root),
        "manifest_path": str(sidecar_root / MANIFEST_FILE_NAME),
        "profile": normalize_sidecar_profile(manifest.get("profile")),
        "manifest_digest": vector_sidecar_manifest_digest(manifest),
        "namespaces": {
            name: {
                "index_type": item.get("index_type"),
                "count": item.get("count"),
                "search_params": item.get("search_params") or {},
            }
            for name, item in namespaces.items()
            if isinstance(item, dict)
        },
    }


def resolve_project_vector_sidecar(
    project_dir: str | os.PathLike[str],
    *,
    sidecar_dir: str | os.PathLike[str] | None = None,
    expected_profile: str | None = DEFAULT_SIDECAR_PROFILE,
    check_hashes: bool = True,
) -> dict[str, Any]:
    configured = sidecar_dir or os.getenv("RAG_VECTOR_SIDECAR_DIR")
    resolved_dir = (
        Path(configured).expanduser().resolve()
        if configured
        else default_vector_sidecar_dir(project_dir)
    )
    return validate_vector_sidecar_manifest(
        project_dir,
        resolved_dir,
        expected_profile=expected_profile,
        check_hashes=check_hashes,
    )
