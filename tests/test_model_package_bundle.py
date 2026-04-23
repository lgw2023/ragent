from __future__ import annotations

from pathlib import Path


def test_bge_m3_model_package_layout_exists():
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "model_packages" / "bge-m3" / "modelDir"

    assert package_root.exists()
    assert (package_root / "meta" / "type.mf").exists()
    assert (package_root / "model" / "sysconfig.properties").exists()
    assert (package_root / "data").is_dir()
    assert (package_root / "data" / "sample_kg").is_dir()
    assert (
        package_root / "data" / "sample_kg" / "graph_chunk_entity_relation.graphml"
    ).exists()
    assert (package_root / "data" / "sample_kg" / "kv_store_text_chunks.json").exists()
    assert (package_root / "data" / "sample_kg" / "vdb_chunks.json").exists()
    assert (package_root / "model" / "baai_bge_m3" / "config.json").exists()
    assert (package_root / "model" / "baai_bge_m3" / "tokenizer.json").exists()
