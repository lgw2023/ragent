from __future__ import annotations

from pathlib import Path

import pytest


def test_bge_m3_model_package_layout_exists():
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "mep" / "model_packages" / "bge-m3" / "modelDir"

    assert package_root.exists()
    assert (package_root / "meta" / "type.mf").exists()
    assert not (package_root / "model" / "sysconfig.properties").exists()
    assert (package_root / "data" / "config" / "embedding.properties").exists()
    assert (package_root / "data").is_dir()
    assert (package_root / "data" / "kg" / "sample_kg").is_dir()
    assert (
        package_root / "data" / "kg" / "sample_kg" / "graph_chunk_entity_relation.graphml"
    ).exists()
    assert (
        package_root / "data" / "kg" / "sample_kg" / "kv_store_text_chunks.json"
    ).exists()
    assert (package_root / "data" / "kg" / "sample_kg" / "vdb_chunks.json").exists()
    assert (package_root / "data" / "samples" / "sample.json").exists()
    assert (package_root / "data" / "deps" / "README.md").exists()
    assert (package_root / "model" / "config.json").exists()
    assert (package_root / "model" / "tokenizer.json").exists()
    assert (package_root / "model" / "pytorch_model.bin").exists()
    assert (package_root / "model" / "1_Pooling" / "config.json").exists()
    assert not (package_root / "model" / "baai_bge_m3" / "config.json").exists()


def test_qwen3_embedding_4b_model_package_layout_exists():
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "mep" / "model_packages" / "qwen3-embedding-4b" / "modelDir"

    assert package_root.exists()
    assert (package_root / "meta" / "type.mf").exists()
    assert not (package_root / "data" / "config" / "embedding.properties").exists()
    kg_dir = package_root / "data" / "kg" / "sample_kg"
    assert (kg_dir / "graph_chunk_entity_relation.graphml").exists()
    assert (kg_dir / "kv_store_text_chunks.sqlite").exists()
    for filename in ("vdb_chunks.json", "vdb_entities.json", "vdb_relationships.json"):
        with (kg_dir / filename).open("r", encoding="utf-8") as handle:
            assert '"embedding_dim": 2560' in handle.read(256)
    if not (package_root / "model" / "config.json").exists():
        pytest.skip("Qwen3-Embedding-4B local model is not linked")
    assert (package_root / "model" / "config.json").exists()
    assert (package_root / "model" / "tokenizer.json").exists()
    assert (package_root / "model" / "model.safetensors.index.json").exists()
    assert (package_root / "model" / "1_Pooling" / "config.json").exists()
