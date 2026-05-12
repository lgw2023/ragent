from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def _write_minimal_wheel(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("demo_pkg/__init__.py", "")


def test_validate_mep_wheelhouse_accepts_valid_wheel(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    model_dir_root = tmp_path / "modelDir"
    _write_minimal_wheel(
        model_dir_root
        / "data"
        / "deps"
        / "wheelhouse"
        / "test-platform"
        / "demo_pkg-1.0.0-py3-none-any.whl"
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "tools" / "validate_mep_wheelhouse.py"),
            "--model-dir-root",
            str(model_dir_root),
            "--platform-tag",
            "test-platform",
            "--no-include-keyword",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 0
    assert "validated 1 wheel(s)" in completed.stdout


def test_validate_mep_wheelhouse_reports_lfs_pointer_payload(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    model_dir_root = tmp_path / "modelDir"
    corrupt_wheel = (
        model_dir_root
        / "data"
        / "deps"
        / "wheelhouse"
        / "test-platform"
        / "demo_pkg-1.0.0-py3-none-any.whl"
    )
    corrupt_wheel.parent.mkdir(parents=True, exist_ok=True)
    corrupt_wheel.write_text(
        "\n".join(
            [
                "version https://git-lfs.github.com/spec/v1",
                "oid sha256:0000000000000000000000000000000000000000000000000000000000000000",
                "size 123",
                "",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "tools" / "validate_mep_wheelhouse.py"),
            "--model-dir-root",
            str(model_dir_root),
            "--platform-tag",
            "test-platform",
            "--no-include-keyword",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 1
    assert str(corrupt_wheel) in completed.stderr
    assert "looks like a Git LFS pointer" in completed.stderr
