from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import export_mep_keyword_fallback_assets as exporter
from tools.validate_mep_full_chain_result import validate_result


def _write_keyword_model(model_dir_root: Path) -> Path:
    model_dir = exporter.keyword_model_dir(model_dir_root)
    model_dir.mkdir(parents=True)
    (model_dir / "gliner_config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model.safetensors").write_bytes(b"fake")
    return model_dir


def _write_keyword_wheelhouse(model_dir_root: Path, platform_tag: str) -> Path:
    wheelhouse_dir = exporter.keyword_wheelhouse_dir(model_dir_root, platform_tag)
    wheelhouse_dir.mkdir(parents=True)
    for name in (
        "gliner-0.2.26-py3-none-any.whl",
        "stanza-1.10.1-py3-none-any.whl",
        "onnxruntime-1.16.3-cp310-cp310-manylinux2014_aarch64.whl",
        "langdetect-1.0.9-py3-none-any.whl",
    ):
        (wheelhouse_dir / name).write_bytes(b"fake")
    return wheelhouse_dir


def test_validate_keyword_fallback_assets_uses_conventional_paths(tmp_path: Path):
    model_dir_root = tmp_path / "modelDir"
    _write_keyword_model(model_dir_root)
    _write_keyword_wheelhouse(model_dir_root, "linux-arm64-py3.10")

    result = exporter.validate_keyword_fallback_assets(
        model_dir_root=model_dir_root,
        platform_tag="linux-arm64-py3.10",
    )

    assert result["model_dir"].endswith(
        "data/models/keyword_extraction/knowledgator-gliner-x-small"
    )
    assert result["wheelhouse_dir"].endswith(
        "data/deps/keyword_wheelhouse/linux-arm64-py3.10"
    )
    assert result["wheel_count"] == 4


def test_export_keyword_fallback_assets_populates_model_and_wheels(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    model_dir_root = repo_root / "mep" / "model_packages" / "demo" / "modelDir"
    model_dir_root.mkdir(parents=True)

    def fake_download_model(*, model_id, output_dir, allow_patterns=()):
        assert model_id == "knowledgator/gliner-x-small"
        output_dir.mkdir(parents=True)
        (output_dir / "gliner_config.json").write_text("{}", encoding="utf-8")
        (output_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")
        (output_dir / "model.safetensors").write_bytes(b"fake")

    def fake_download_wheels(
        *,
        output_dir,
        platform_tag,
        python_bin,
        binary_requirements=(),
        pure_wheel_requirements=(),
    ):
        assert platform_tag == "linux-arm64-py3.10"
        assert python_bin == "python3"
        output_dir.mkdir(parents=True)
        for name in (
            "gliner-0.2.26-py3-none-any.whl",
            "stanza-1.10.1-py3-none-any.whl",
            "onnxruntime-1.16.3-cp310-cp310-manylinux2014_aarch64.whl",
            "langdetect-1.0.9-py3-none-any.whl",
        ):
            (output_dir / name).write_bytes(b"fake")
        return sorted(item.name for item in output_dir.iterdir())

    monkeypatch.setattr(exporter, "download_keyword_model_snapshot", fake_download_model)
    monkeypatch.setattr(exporter, "download_keyword_wheels", fake_download_wheels)

    result = exporter.export_keyword_fallback_assets(
        repo_root=repo_root,
        model_package="demo",
        platform_tag="linux-arm64-py3.10",
        python_bin="python3",
        model_id="knowledgator/gliner-x-small",
    )

    assert Path(result["model_dir"]).is_dir()
    assert Path(result["wheelhouse_dir"]).is_dir()
    assert result["wheel_count"] == 4


def _write_validation_files(
    tmp_path: Path,
    *,
    retrieval_result: dict,
) -> tuple[Path, Path]:
    generate_path = tmp_path / "generated"
    generate_path.mkdir()
    (generate_path / "gen.json").write_text(
        json.dumps(
            {
                "code": "0",
                "answer": "",
                "retrieval_result": retrieval_result,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    stdout_path = tmp_path / "stdout.json"
    stdout_path.write_text(
        json.dumps({"recommendResult": {"code": "0", "length": 1}}),
        encoding="utf-8",
    )
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "data": {
                    "retrieval_only": True,
                    "only_need_context": True,
                    "generatePath": str(generate_path),
                }
            }
        ),
        encoding="utf-8",
    )
    return stdout_path, request_path


def test_validate_full_chain_retrieval_only_requires_successful_gliner_keywords(
    tmp_path: Path,
):
    stdout_path, request_path = _write_validation_files(
        tmp_path,
        retrieval_result={
            "final_context_text": "context",
            "final_context_chunks": [],
            "high_level_keywords": ["主题"],
            "low_level_keywords": [],
            "keyword_source": "gliner_fallback",
            "keyword_strategy": "token_classification_fallback",
            "keyword_model": "/models/gliner",
            "keyword_model_device": "cpu",
            "keyword_model_error": None,
        },
    )

    summary = validate_result(stdout_path, request_path)

    assert summary["retrieval_only"] is True
    assert summary["keyword_source"] == "gliner_fallback"
    assert summary["high_level_keywords"] == ["主题"]


@pytest.mark.parametrize(
    ("retrieval_result", "match"),
    [
        (
            {
                "final_context_text": "context",
                "high_level_keywords": ["主题"],
                "low_level_keywords": [],
                "keyword_source": "gliner_fallback",
                "keyword_strategy": "token_classification_fallback",
                "keyword_model_error": "missing package",
            },
            "keyword_model_error",
        ),
        (
            {
                "final_context_text": "context",
                "high_level_keywords": [],
                "low_level_keywords": [],
                "keyword_source": "gliner_fallback",
                "keyword_strategy": "token_classification_fallback",
                "keyword_model_error": None,
            },
            "returned no high_level_keywords",
        ),
        (
            {
                "final_context_text": "context",
                "high_level_keywords": ["主题"],
                "low_level_keywords": [],
                "keyword_source": "request",
                "keyword_strategy": "request",
                "keyword_model_error": None,
            },
            "did not use GLiNER fallback",
        ),
    ],
)
def test_validate_full_chain_retrieval_only_rejects_missing_gliner_fallback(
    tmp_path: Path,
    retrieval_result: dict,
    match: str,
):
    stdout_path, request_path = _write_validation_files(
        tmp_path,
        retrieval_result=retrieval_result,
    )

    with pytest.raises(SystemExit, match=match):
        validate_result(stdout_path, request_path)
