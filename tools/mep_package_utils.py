from __future__ import annotations

import fnmatch
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
