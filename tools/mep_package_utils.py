from __future__ import annotations

import fnmatch
import json
import shutil
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path


IGNORE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
}
IGNORE_PATTERNS = (
    "*.pyc",
    "*.pyo",
)
HF_CONFIG_MARKER = "config.json"
HF_TOKENIZER_MARKERS = ("tokenizer.json", "tokenizer_config.json")
HF_WEIGHT_MARKERS = (
    "pytorch_model.bin",
    "model.safetensors",
    "tf_model.h5",
    "model.ckpt.index",
    "flax_model.msgpack",
    "pytorch_model.bin.index.json",
    "model.safetensors.index.json",
)
EXPECTED_MODEL_DIR_CHILDREN = {"model", "data", "meta"}
EXPECTED_COMPONENT_CONFIG = {
    "main_file": "process",
    "main_class": "CustomerModel",
}
REQUIRED_COMPONENT_PACKAGE_FILES = (
    "config.json",
    "package.json",
    "process.py",
    "init.py",
    "mep_dependency_bootstrap.py",
)
REQUIRED_COMPONENT_PACKAGE_DIRS = ("ragent",)
FORBIDDEN_COMPONENT_PACKAGE_TOP_LEVEL = {
    ".git",
    ".mep_build",
    ".mep_upload",
    ".venv",
    "MEP_platform_rule",
    "benchmark",
    "example",
    "mep",
    "presentation",
    "tests",
    "vendor",
}
REQUIRED_KG_SNAPSHOT_FILES = (
    "graph_chunk_entity_relation.graphml",
    "kv_store_text_chunks.json",
    "vdb_chunks.json",
    "vdb_entities.json",
    "vdb_relationships.json",
)
REQUIRED_VDB_FILES = (
    "vdb_chunks.json",
    "vdb_entities.json",
    "vdb_relationships.json",
)
ARCHIVE_FORMATS = {
    "zip": ("zip", ".zip"),
    "tar": ("tar", ".tar"),
    "tar.gz": ("gztar", ".tar.gz"),
    "tgz": ("gztar", ".tar.gz"),
    "gztar": ("gztar", ".tar.gz"),
}


def path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def ignore_by_name(ignore_names: set[str], _directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in ignore_names}
    for pattern in IGNORE_PATTERNS:
        ignored.update(name for name in names if fnmatch.fnmatchcase(name, pattern))
    return ignored


def ignore_generated(_directory: str, names: list[str]) -> set[str]:
    return ignore_by_name(IGNORE_NAMES, _directory, names)


def reset_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def validate_output_path_does_not_overlap(
    *,
    output: Path,
    repo_root: Path,
    protected_paths: Iterable[tuple[str, Path]],
    path_label: str = "Output directory",
) -> None:
    if output == repo_root:
        raise ValueError(f"{path_label} must not be the repository root: {output}")
    if output == repo_root.parent:
        raise ValueError(
            f"{path_label} must not be the repository parent: {output}"
        )

    for label, protected_path in protected_paths:
        protected_path = protected_path.expanduser().resolve()
        if path_is_relative_to(protected_path, output):
            raise ValueError(
                f"{path_label} must not contain the {label}: {output}"
            )
        if path_is_relative_to(output, protected_path):
            raise ValueError(
                f"{path_label} must not be inside the {label}: {output}"
            )


def normalize_archive_format(archive_format: str | None) -> tuple[str, str] | None:
    if archive_format is None:
        return None
    normalized = archive_format.strip().lower()
    if not normalized:
        return None
    if normalized not in ARCHIVE_FORMATS:
        supported = " | ".join(sorted(ARCHIVE_FORMATS))
        raise ValueError(f"Unsupported archive format: {archive_format!r}. Use {supported}")
    return ARCHIVE_FORMATS[normalized]


def default_archive_output(output: Path, archive_extension: str) -> Path:
    return output.with_name(output.name + archive_extension)


def resolve_archive_output_path(
    *,
    source_root: Path,
    archive_extension: str,
    archive_output: Path | None,
    source_label: str,
) -> Path:
    archive_path = (
        archive_output.expanduser().resolve()
        if archive_output is not None
        else default_archive_output(source_root, archive_extension)
    )
    if archive_path == source_root or path_is_relative_to(archive_path, source_root):
        raise ValueError(
            f"Archive output must be outside the {source_label} to avoid archiving "
            f"itself: {archive_path}"
        )
    if archive_path.exists() and archive_path.is_dir() and not archive_path.is_symlink():
        raise ValueError(
            f"Archive output must be a file path, not a directory: {archive_path}"
        )
    return archive_path


def safe_archive_stem(value: str, *, fallback: str) -> str:
    safe = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "-"
        for char in value.strip()
    ).strip(".-")
    return safe or fallback


def archive_members(root: Path) -> list[Path]:
    return sorted(
        root.rglob("*"),
        key=lambda item: item.relative_to(root).as_posix(),
    )


def _write_zip_archive(root: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in archive_members(root):
            arcname = path.relative_to(root).as_posix()
            if path.is_dir():
                zf.writestr(arcname + "/", "")
            else:
                zf.write(path, arcname)


def _write_tar_archive(root: Path, archive_path: Path, *, gzip: bool) -> None:
    mode = "w:gz" if gzip else "w"
    with tarfile.open(archive_path, mode) as tf:
        for path in archive_members(root):
            arcname = path.relative_to(root).as_posix()
            tf.add(path, arcname=arcname, recursive=False)


def write_archive(root: Path, archive_path: Path, *, archive_format: str) -> Path:
    normalized = normalize_archive_format(archive_format)
    if normalized is None:
        raise ValueError("Archive format must not be empty")
    normalized_format, _archive_extension = normalized

    if archive_path.exists() and archive_path.is_dir() and not archive_path.is_symlink():
        raise ValueError(
            f"Archive output must be a file path, not a directory: {archive_path}"
        )
    if archive_path.exists() or archive_path.is_symlink():
        reset_path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if normalized_format == "zip":
        _write_zip_archive(root, archive_path)
    elif normalized_format == "tar":
        _write_tar_archive(root, archive_path, gzip=False)
    elif normalized_format == "gztar":
        _write_tar_archive(root, archive_path, gzip=True)
    else:
        raise ValueError(f"Unsupported archive format: {archive_format!r}")
    return archive_path


def visible_model_root_children(model_root: Path) -> list[Path]:
    return sorted(
        (
            child
            for child in model_root.iterdir()
            if not child.name.startswith(".") and child.name not in IGNORE_NAMES
        ),
        key=lambda item: item.name,
    )


def validate_model_root(model_root: Path, *, model_root_label: str) -> None:
    children = visible_model_root_children(model_root)
    if not children:
        raise FileNotFoundError(
            f"{model_root_label} must contain Hugging Face model files: {model_root}"
        )

    has_config = (model_root / HF_CONFIG_MARKER).is_file()
    has_tokenizer = any((model_root / marker).is_file() for marker in HF_TOKENIZER_MARKERS)
    has_weights = any((model_root / marker).is_file() for marker in HF_WEIGHT_MARKERS)
    if has_config and has_tokenizer and has_weights:
        return

    nested_model_dirs = [
        child
        for child in children
        if child.is_dir()
        and (child / HF_CONFIG_MARKER).is_file()
        and any((child / marker).is_file() for marker in HF_TOKENIZER_MARKERS)
    ]
    if nested_model_dirs:
        nested_text = ", ".join(str(child) for child in nested_model_dirs)
        raise ValueError(
            f"{model_root_label} must directly contain Hugging Face model files; "
            f"nested model directories are not allowed: {nested_text}"
        )

    missing_requirements: list[str] = []
    if not has_config:
        missing_requirements.append(HF_CONFIG_MARKER)
    if not has_tokenizer:
        missing_requirements.append(f"one of {', '.join(HF_TOKENIZER_MARKERS)}")
    if not has_weights:
        missing_requirements.append(f"one of {', '.join(HF_WEIGHT_MARKERS)}")
    required = ", ".join(missing_requirements)
    raise FileNotFoundError(
        f"{model_root_label} must be a Hugging Face model directory containing "
        f"{required}: {model_root}"
    )


def validate_model_dir(
    model_dir_root: Path,
    *,
    model_dir_label: str = "MEP modelDir",
    required_dir_label: str = "MEP modelDir/{name}/",
    model_root_label: str = "MEP modelDir/model/",
) -> None:
    if not model_dir_root.is_dir():
        raise FileNotFoundError(f"{model_dir_label} not found: {model_dir_root}")

    required_dirs = {
        "model": model_dir_root / "model",
        "data": model_dir_root / "data",
        "meta": model_dir_root / "meta",
    }
    child_names = {child.name for child in visible_model_root_children(model_dir_root)}
    extra_children = child_names - EXPECTED_MODEL_DIR_CHILDREN
    if extra_children:
        extra_text = ", ".join(sorted(extra_children))
        noun = "entry" if len(extra_children) == 1 else "entries"
        raise ValueError(
            f"{model_dir_label} first-level entries must be exactly model, data, "
            f"and meta; unexpected {noun}: {extra_text}"
        )
    for name, source in required_dirs.items():
        if not source.is_dir():
            label = required_dir_label.format(name=name)
            raise FileNotFoundError(f"{label} not found: {source}")
    type_mf = required_dirs["meta"] / "type.mf"
    if not type_mf.is_file():
        raise FileNotFoundError(f"MEP modelDir/meta/type.mf not found: {type_mf}")
    if not type_mf.read_text(encoding="utf-8").strip():
        raise ValueError(f"MEP modelDir/meta/type.mf must not be empty: {type_mf}")
    validate_model_root(required_dirs["model"], model_root_label=model_root_label)


def read_properties(path: Path) -> dict[str, str]:
    properties: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"invalid properties line in {path}: {line!r}")
        key, value = stripped.split("=", 1)
        properties[key.strip()] = value.strip()
    return properties


def _read_vdb_embedding_dim(vdb_path: Path) -> int:
    try:
        payload = json.loads(vdb_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in KG vector store: {vdb_path}: {exc}") from exc
    embedding_dim = payload.get("embedding_dim") if isinstance(payload, dict) else None
    if not isinstance(embedding_dim, int):
        raise ValueError(f"KG vector store is missing integer embedding_dim: {vdb_path}")
    return embedding_dim


def _iter_existing_wheelhouse_platform_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    platform_dirs = [child for child in sorted(root.iterdir()) if child.is_dir()]
    if any(root.glob("*.whl")):
        platform_dirs.append(root)
    return platform_dirs


def _validate_wheelhouse_root(
    root: Path,
    *,
    label: str,
    required_platform_tags: tuple[str, ...],
) -> None:
    if not root.is_dir():
        raise FileNotFoundError(f"{label} not found: {root}")

    if required_platform_tags:
        for platform_tag in required_platform_tags:
            platform_dir = root / platform_tag
            if not platform_dir.is_dir():
                raise FileNotFoundError(
                    f"{label}/{platform_tag} not found: {platform_dir}"
                )
            if not any(platform_dir.glob("*.whl")):
                raise FileNotFoundError(
                    f"{label}/{platform_tag} contains no wheel files: {platform_dir}"
                )
        return

    platform_dirs = _iter_existing_wheelhouse_platform_dirs(root)
    if not platform_dirs:
        raise FileNotFoundError(f"{label} contains no platform wheelhouse: {root}")
    if not any(any(platform_dir.glob("*.whl")) for platform_dir in platform_dirs):
        raise FileNotFoundError(f"{label} contains no wheel files: {root}")


def validate_model_data_dir(
    data_dir: Path,
    *,
    required_platform_tags: tuple[str, ...] = (),
) -> None:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"MEP modelDir/data/ not found: {data_dir}")

    embedding_properties = data_dir / "config" / "embedding.properties"
    if not embedding_properties.is_file():
        raise FileNotFoundError(
            f"MEP embedding.properties not found: {embedding_properties}"
        )
    properties = read_properties(embedding_properties)
    raw_dimensions = properties.get("embedding.dimensions")
    if raw_dimensions is None:
        raise ValueError(
            f"MEP embedding.properties is missing embedding.dimensions: "
            f"{embedding_properties}"
        )
    try:
        embedding_dimensions = int(raw_dimensions)
    except ValueError as exc:
        raise ValueError(
            f"MEP embedding.dimensions must be an integer: {raw_dimensions!r}"
        ) from exc

    kg_dir = data_dir / "kg" / "sample_kg"
    if not kg_dir.is_dir():
        raise FileNotFoundError(f"MEP KG snapshot not found: {kg_dir}")
    for filename in REQUIRED_KG_SNAPSHOT_FILES:
        path = kg_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"MEP KG snapshot file not found: {path}")
    for filename in REQUIRED_VDB_FILES:
        vdb_path = kg_dir / filename
        vdb_dimensions = _read_vdb_embedding_dim(vdb_path)
        if vdb_dimensions != embedding_dimensions:
            raise ValueError(
                f"MEP KG vector dimension mismatch: {vdb_path} has "
                f"embedding_dim={vdb_dimensions}, but embedding.properties has "
                f"embedding.dimensions={embedding_dimensions}"
            )

    deps_dir = data_dir / "deps"
    if not deps_dir.is_dir():
        raise FileNotFoundError(f"MEP data/deps/ not found: {deps_dir}")
    _validate_wheelhouse_root(
        deps_dir / "wheelhouse",
        label="MEP data/deps/wheelhouse",
        required_platform_tags=required_platform_tags,
    )
    _validate_wheelhouse_root(
        deps_dir / "keyword_wheelhouse",
        label="MEP data/deps/keyword_wheelhouse",
        required_platform_tags=required_platform_tags,
    )


def validate_model_package_dir(
    model_package_dir: Path,
    *,
    required_platform_tags: tuple[str, ...] = (),
) -> None:
    if not model_package_dir.is_dir():
        raise FileNotFoundError(f"MEP model package not found: {model_package_dir}")
    child_names = [child.name for child in visible_model_root_children(model_package_dir)]
    if child_names != ["modelDir"]:
        raise ValueError(
            "MEP model package first-level entry must be exactly modelDir: "
            f"{model_package_dir} has {child_names}"
        )
    model_dir_root = model_package_dir / "modelDir"
    validate_model_dir(model_dir_root)
    validate_model_data_dir(
        model_dir_root / "data",
        required_platform_tags=required_platform_tags,
    )


def validate_component_package_dir(
    component_dir: Path,
    *,
    allow_local_runner: bool = False,
) -> None:
    if not component_dir.is_dir():
        raise FileNotFoundError(f"MEP component package not found: {component_dir}")

    for filename in REQUIRED_COMPONENT_PACKAGE_FILES:
        path = component_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"MEP component file not found: {path}")
    for dirname in REQUIRED_COMPONENT_PACKAGE_DIRS:
        path = component_dir / dirname
        if not path.is_dir():
            raise FileNotFoundError(f"MEP component directory not found: {path}")

    config_path = component_dir / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid MEP component config.json: {config_path}: {exc}") from exc
    for key, expected in EXPECTED_COMPONENT_CONFIG.items():
        if config.get(key) != expected:
            raise ValueError(
                f"MEP component config.json must set {key}={expected!r}: "
                f"{config_path}"
            )

    top_level_names = {child.name for child in visible_model_root_children(component_dir)}
    forbidden = top_level_names & FORBIDDEN_COMPONENT_PACKAGE_TOP_LEVEL
    if forbidden:
        forbidden_text = ", ".join(sorted(forbidden))
        raise ValueError(
            f"MEP component package contains source-only top-level path(s): "
            f"{forbidden_text}"
        )
    if not allow_local_runner and (component_dir / "run_mep_local.py").exists():
        raise ValueError(
            "MEP component package must not include run_mep_local.py unless "
            "a local debug package is explicitly requested"
        )

    process_path = component_dir / "process.py"
    process_text = process_path.read_text(encoding="utf-8")
    required_snippets = (
        "_configure_default_offline_environment()",
        'os.environ["HF_HUB_OFFLINE"] = "1"',
        'os.environ["TRANSFORMERS_OFFLINE"] = "1"',
        'os.environ["HF_DATASETS_OFFLINE"] = "1"',
        'os.environ["PIP_NO_INDEX"] = "1"',
        "PIP_CONFIG_FILE",
        "ensure_mep_offline_requirements(_CODE_ROOT)",
        "bootstrap_mep_data_dependencies(_CODE_ROOT)",
        "from ragent.runtime_env import",
    )
    missing = [snippet for snippet in required_snippets if snippet not in process_text]
    if missing:
        raise ValueError(
            f"MEP component process.py is missing required offline bootstrap "
            f"snippet(s): {', '.join(missing)}"
        )
    if not (
        process_text.index("_configure_default_offline_environment()")
        < process_text.index("ensure_mep_offline_requirements(_CODE_ROOT)")
        < process_text.index("bootstrap_mep_data_dependencies(_CODE_ROOT)")
        < process_text.index("from ragent.runtime_env import")
    ):
        raise ValueError(
            "MEP component process.py must configure offline mode, install offline "
            "requirements, and bootstrap data dependencies before importing ragent"
        )
