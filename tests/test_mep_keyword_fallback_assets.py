from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pytest

from tools import export_mep_keyword_fallback_assets as exporter
from tools import validate_mep_wheelhouse as wheelhouse_validator
from tools.validate_mep_full_chain_result import summarize_requests, validate_result


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


def _write_valid_wheel(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("demo/__init__.py", "")
        wheel.writestr("demo-1.0.0.dist-info/METADATA", "Name: demo\nVersion: 1.0.0\n")


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


def test_validate_keyword_fallback_assets_rejects_duplicate_required_wheels(
    tmp_path: Path,
):
    model_dir_root = tmp_path / "modelDir"
    _write_keyword_model(model_dir_root)
    wheelhouse_dir = exporter.keyword_wheelhouse_dir(
        model_dir_root,
        "linux-arm64-py3.10",
    )
    wheelhouse_dir.mkdir(parents=True)
    for name in (
        "gliner-0.2.26-py3-none-any.whl",
        "gliner-0.2.27-py3-none-any.whl",
        "stanza-1.10.1-py3-none-any.whl",
        "onnxruntime-1.16.3-cp310-cp310-manylinux2014_aarch64.whl",
        "langdetect-1.0.9-py3-none-any.whl",
    ):
        (wheelhouse_dir / name).write_bytes(b"fake")

    with pytest.raises(ValueError, match="duplicate required wheels"):
        exporter.validate_keyword_fallback_assets(
            model_dir_root=model_dir_root,
            platform_tag="linux-arm64-py3.10",
        )


def test_download_keyword_wheels_removes_stale_wheels(monkeypatch, tmp_path: Path):
    output_dir = tmp_path / "keyword_wheelhouse"
    output_dir.mkdir()
    (output_dir / "gliner-0.1.0-py3-none-any.whl").write_bytes(b"stale")

    def fake_run(command):
        if "--dest" in command:
            wheel_dir = Path(command[command.index("--dest") + 1])
        else:
            wheel_dir = Path(command[command.index("--wheel-dir") + 1])
        wheel_dir.mkdir(parents=True, exist_ok=True)
        (wheel_dir / "gliner-0.2.26-py3-none-any.whl").write_bytes(b"new")

    monkeypatch.setattr(exporter, "_run", fake_run)

    wheels = exporter.download_keyword_wheels(
        output_dir=output_dir,
        platform_tag="linux-arm64-py3.9",
        python_bin="python3",
        binary_requirements=("gliner==0.2.26",),
        pure_wheel_requirements=(),
    )

    assert wheels == ["gliner-0.2.26-py3-none-any.whl"]
    assert not (output_dir / "gliner-0.1.0-py3-none-any.whl").exists()
    assert (output_dir / "gliner-0.2.26-py3-none-any.whl").is_file()


def test_download_keyword_wheels_maps_platform_tag_to_pip_target_args(
    monkeypatch,
    tmp_path: Path,
):
    commands = []

    def fake_run(command):
        commands.append(command)
        wheel_dir = Path(command[command.index("--dest") + 1])
        _write_valid_wheel(wheel_dir / "onnxruntime-1.16.3-cp39-cp39.whl")

    monkeypatch.setattr(exporter, "_run", fake_run)

    exporter.download_keyword_wheels(
        output_dir=tmp_path / "keyword_wheelhouse",
        platform_tag="linux-arm64-py3.9",
        python_bin="python3",
        binary_requirements=("onnxruntime==1.16.3",),
        pure_wheel_requirements=(),
    )

    command = commands[0]
    assert command[command.index("--platform") + 1] == "manylinux2014_aarch64"
    assert command[command.index("--python-version") + 1] == "3.9"
    assert command[command.index("--abi") + 1] == "cp39"


def test_download_keyword_wheels_rejects_unsupported_platform(tmp_path: Path):
    with pytest.raises(ValueError, match="linux-arm64 CPython tags"):
        exporter.download_keyword_wheels(
            output_dir=tmp_path / "keyword_wheelhouse",
            platform_tag="linux-amd64-py3.9",
            python_bin="python3",
            binary_requirements=(),
            pure_wheel_requirements=(),
        )


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
        assert platform_tag == "linux-arm64-py3.9"
        assert python_bin == "python3"
        output_dir.mkdir(parents=True)
        for name in (
            "gliner-0.2.26-py3-none-any.whl",
            "stanza-1.10.1-py3-none-any.whl",
            "onnxruntime-1.16.3-cp39-cp39-manylinux2014_aarch64.whl",
            "langdetect-1.0.9-py3-none-any.whl",
        ):
            (output_dir / name).write_bytes(b"fake")
        return sorted(item.name for item in output_dir.iterdir())

    monkeypatch.setattr(exporter, "download_keyword_model_snapshot", fake_download_model)
    monkeypatch.setattr(exporter, "download_keyword_wheels", fake_download_wheels)

    result = exporter.export_keyword_fallback_assets(
        repo_root=repo_root,
        model_package="demo",
        platform_tag="linux-arm64-py3.9",
        python_bin="python3",
        model_id="knowledgator/gliner-x-small",
    )

    assert Path(result["model_dir"]).is_dir()
    assert Path(result["wheelhouse_dir"]).is_dir()
    assert result["wheel_count"] == 4


def test_validate_mep_wheelhouse_reports_missing_requested_keyword_platform(
    tmp_path: Path,
):
    model_dir_root = tmp_path / "modelDir"
    _write_valid_wheel(
        model_dir_root
        / "data"
        / "deps"
        / "wheelhouse"
        / "linux-arm64-py3.9"
        / "demo-1.0.0-py3-none-any.whl"
    )

    args = argparse.Namespace(
        wheelhouse_dir=[],
        model_dir_root=model_dir_root,
        platform_tag=("linux-arm64-py3.9",),
        include_keyword=True,
    )
    checked, invalid = wheelhouse_validator.validate_wheelhouse_dirs(
        wheelhouse_validator._iter_wheelhouse_dirs(args)
    )

    assert checked == 1
    assert any(
        "keyword_wheelhouse/linux-arm64-py3.9: directory does not exist" in detail
        for detail in invalid
    )


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
                "answer": retrieval_result.get("final_context_text") or "context",
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
            "graph_chunk_candidates": [
                {"chunk_id": "chunk-1", "content": "context", "source": "graph"}
            ],
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


def test_validate_full_chain_accepts_camel_case_explicit_keywords(tmp_path: Path):
    generate_path = tmp_path / "generated"
    generate_path.mkdir()
    (generate_path / "gen.json").write_text(
        json.dumps(
            {
                "code": "0",
                "answer": "context",
                "retrieval_result": {
                    "final_context_text": "context",
                    "high_level_keywords": ["指南"],
                    "low_level_keywords": [],
                    "keyword_source": "request",
                    "keyword_strategy": "request",
                    "keyword_model_error": None,
                    "graph_chunk_candidates": [
                        {"chunk_id": "chunk-1", "content": "context", "source": "graph"}
                    ],
                },
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
                    "onlyNeedContext": True,
                    "highLevelKeywords": ["指南"],
                    "generatePath": str(generate_path),
                }
            }
        ),
        encoding="utf-8",
    )

    summary = validate_result(stdout_path, request_path)

    assert summary["retrieval_only"] is True
    assert summary["keyword_source"] == "request"


def test_summarize_requests_uses_process_spec_aliases(tmp_path: Path):
    request_dir = tmp_path / "example" / "mep_requests"
    request_dir.mkdir(parents=True)
    (request_dir / "process_spec_retrieval.json").write_text(
        json.dumps(
            {
                "data": {
                    "fileInfo": [
                        {
                            "processSpec": [
                                {
                                    "fieldName": "retrievalOnly",
                                    "fieldValue": 1,
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_requests(tmp_path, "process_spec_retrieval.json")

    assert summary["requests_require_llm"] is False
    assert summary["requests_have_retrieval_only"] is True


def test_summarize_requests_defaults_unset_mode_to_retrieval_only(tmp_path: Path):
    request_dir = tmp_path / "example" / "mep_requests"
    request_dir.mkdir(parents=True)
    (request_dir / "onehop_request.json").write_text(
        json.dumps(
            {
                "data": {
                    "query_type": "onehop",
                    "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
                }
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_requests(tmp_path, "onehop_request.json")

    assert summary["requests_require_llm"] is False
    assert summary["requests_have_retrieval_only"] is True
    assert summary["requests"][0]["retrieval_only"] is True


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
        (
            {
                "final_context_text": "context",
                "high_level_keywords": ["主题"],
                "low_level_keywords": [],
                "keyword_source": "gliner_fallback",
                "keyword_strategy": "token_classification_fallback",
                "keyword_model_error": None,
                "final_context_chunks": [
                    {"content": "context", "source": "vector"}
                ],
                "graph_chunk_candidates": [],
            },
            "no graph chunk candidates",
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
