from __future__ import annotations

import argparse
from pathlib import Path

from tools import export_mep_vllm_ascend_wheelhouse as exporter


def test_default_extra_requirements_include_mep_runtime_gaps():
    assert {
        "ascii-colors==0.11.21",
        "cbor2==5.9.0",
        "configparser==7.2.0",
        "dotenv==0.9.9",
        "future==1.0.0",
        "nano-vectordb==0.0.4.3",
        "pipmaster==1.1.2",
        "pyuca==1.2",
        "tenacity==9.1.4",
        "wcwidth==0.6.0",
    }.issubset(set(exporter.DEFAULT_EXTRA_REQUIREMENTS))


def test_default_resolvable_local_prefixes_support_full_repo_mount():
    assert exporter.DEFAULT_RESOLVABLE_LOCAL_FILE_PREFIXES == (
        "/tmp/ragent",
        "/tmp/ragent-mep-test",
    )


def test_export_wheelhouse_resolves_only_validated_tmp_local_wheels(
    monkeypatch,
    tmp_path: Path,
):
    freeze_file = tmp_path / "validated.freeze.txt"
    freeze_file.write_text(
        "\n".join(
            [
                "requests==2.32.3",
                "func-timeout==4.3.5",
                (
                    "triton-ascend @ "
                    "file:///tmp/ragent-mep-test/"
                    "triton_ascend-3.2.0-cp310-cp310-manylinux_2_27_aarch64."
                    "manylinux_2_28_aarch64.whl"
                ),
                "te @ file:///home/mep/selfgz/share/te-0.4.0-py3-none-any.whl",
                "editable-package @ git+https://example.invalid/repo.git",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "wheelhouse"
    downloaded_requirements: list[str] = []

    def fake_download_requirement(requirement: str, **kwargs):
        downloaded_requirements.append(requirement)
        if requirement == "func-timeout==4.3.5":
            (Path(kwargs["output_dir"]) / "func_timeout-4.3.5.tar.gz").write_bytes(
                b"fake sdist"
            )
            return False, "no wheel"
        wheel_name = requirement.replace("-", "_").replace("==", "-")
        (Path(kwargs["output_dir"]) / f"{wheel_name}-py3-none-any.whl").write_bytes(
            b"fake wheel"
        )
        return True, "ok"

    monkeypatch.setattr(exporter, "_download_requirement", fake_download_requirement)

    manifest = exporter.export_wheelhouse(
        argparse.Namespace(
            freeze_file=freeze_file,
            output=output_dir,
            local_wheel_dir=[],
            resolve_local_file_wheels=False,
            resolvable_local_file_prefix=[Path("/tmp/ragent-mep-test")],
            extra_requirement=[],
            python_version="310",
            implementation="cp",
            platform=["manylinux_2_28_aarch64"],
            abi=["cp310"],
            index_url=None,
            extra_index_url=[],
            timeout_seconds=60,
        )
    )

    assert downloaded_requirements == [
        "requests==2.32.3",
        "func-timeout==4.3.5",
        "triton-ascend==3.2.0",
    ]
    assert manifest.resolved_local_file_requirements == ["triton-ascend==3.2.0"]
    assert manifest.source_archives == ["func_timeout-4.3.5.tar.gz"]
    assert (output_dir / "source-archives.txt").read_text(encoding="utf-8") == (
        "func_timeout-4.3.5.tar.gz\n"
    )
    assert manifest.local_file_requirements == [
        (
            "triton-ascend @ "
            "file:///tmp/ragent-mep-test/"
            "triton_ascend-3.2.0-cp310-cp310-manylinux_2_27_aarch64."
            "manylinux_2_28_aarch64.whl"
        ),
        "te @ file:///home/mep/selfgz/share/te-0.4.0-py3-none-any.whl",
    ]
    assert manifest.skipped_non_pinned_requirements == [
        "editable-package @ git+https://example.invalid/repo.git"
    ]
