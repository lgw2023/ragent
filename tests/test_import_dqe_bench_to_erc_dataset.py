from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "import_dqe_bench_to_erc_dataset.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("import_dqe_bench_to_erc_dataset", TOOL_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dqe_doc_candidates_maps_markdown_doc_to_pdf():
    module = _load_module()

    assert "成人高血压食养指南_2022.pdf" in module.dqe_doc_candidates(
        "成人高血压食养指南_2022_md"
    )
    assert "GBT1354-2018bz.pdf" in module.dqe_doc_candidates("GBT1354-2018bz_md")


def test_source_unit_mapping_uses_real_chunk_metadata_only(tmp_path: Path):
    module = _load_module()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    db_path = project_dir / "kv_store_text_chunks.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("create table kv_entries (key text primary key, entry_json text not null)")
        connection.execute(
            "insert into kv_entries values (?, ?)",
            (
                "chunk-real",
                json.dumps(
                    {
                        "content": "成人高血压食养指南_2022.pdf###### 每人每日食盐摄入量逐步降至5g以下；增加富钾食物摄入。",
                        "source_ref": "成人高血压食养指南_2022.pdf | p.10 | 三、食养原则和建议",
                        "file_path": "/repo/example/成人高血压食养指南_2022.pdf",
                        "page_numbers": [10],
                        "section_path": "三、食养原则和建议",
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        connection.execute(
            "insert into kv_entries values (?, ?)",
            (
                "chunk-wrong-doc",
                json.dumps(
                    {
                        "content": "每人每日食盐摄入量逐步降至5g以下；增加富钾食物摄入。",
                        "source_ref": "中国居民膳食指南_2022.pdf | p.1 | 其他",
                        "file_path": "/repo/example/中国居民膳食指南_2022.pdf",
                        "page_numbers": [1],
                        "section_path": "其他",
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        connection.commit()

    chunks = module.load_project_chunks(project_dir)
    chunks_by_doc = module.index_chunks_by_doc(chunks)
    source_units = {
        "成人高血压食养指南_2022_md::u0016": {
            "source_id": "成人高血压食养指南_2022_md::u0016",
            "doc_id": "成人高血压食养指南_2022_md",
            "section_path": ["三、食养原则和建议"],
            "content": "每人每日食盐摄入量逐步降至5g以下；增加富钾食物摄入。",
            "source_type": "paragraph",
        }
    }

    match = module.match_source_unit(
        "成人高血压食养指南_2022_md::u0016",
        source_units,
        {},
        chunks_by_doc,
    )

    assert match.matched is True
    assert match.chunk_id == "chunk-real"
    assert match.page_numbers == (10,)
    assert match.source_ref == "成人高血压食养指南_2022.pdf | p.10 | 三、食养原则和建议"


def test_source_unit_resolution_repairs_stale_id_from_gold_evidence():
    module = _load_module()
    source_units = {
        "doc_md::u0001": {
            "source_id": "doc_md::u0001",
            "doc_id": "doc_md",
            "content": "图片说明：五角星展示生活方式原则。",
        },
        "doc_md::u0002": {
            "source_id": "doc_md::u0002",
            "doc_id": "doc_md",
            "content": "每人每日食盐摄入量逐步降至 5g 以下；增加富钾食物摄入。",
        },
        "other_md::u0002": {
            "source_id": "other_md::u0002",
            "doc_id": "other_md",
            "content": "每人每日食盐摄入量逐步降至 5g 以下；增加富钾食物摄入。",
        },
    }
    by_doc = module.index_source_units_by_doc(source_units)

    resolution = module.resolve_source_unit_for_gold(
        "doc_md::u0001",
        "指南证据：每人每日食盐摄入量逐步降至 5g 以下；增加富钾食物摄入。",
        source_units,
        by_doc,
    )

    assert resolution["resolved_source_unit_id"] == "doc_md::u0002"
    assert resolution["source_id_resolution_status"] == "repaired_from_gold_evidence"


def test_table_like_mapping_allows_same_section_split_chunk(tmp_path: Path):
    module = _load_module()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    db_path = project_dir / "kv_store_text_chunks.sqlite"
    chunk_content = (
        "doc.pdf###### 指南\n## 四、华东地区\n"
        '<table><tr><td>早餐</td><td>蒸番薯（番薯150g）</td></tr>'
        "<tr><td>中餐</td><td>苦瓜炒蛋（苦瓜150g，鸡蛋50g）</td></tr></table>"
    )
    with sqlite3.connect(db_path) as connection:
        connection.execute("create table kv_entries (key text primary key, entry_json text not null)")
        connection.execute(
            "insert into kv_entries values (?, ?)",
            (
                "chunk-table",
                json.dumps(
                    {
                        "content": chunk_content,
                        "source_ref": "doc.pdf | p.34-36 | 四、华东地区",
                        "file_path": "/repo/example/doc.pdf",
                        "page_numbers": [34, 35, 36],
                        "section_path": "四、华东地区",
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        connection.commit()

    source_units = {
        "doc_md::u0063": {
            "source_id": "doc_md::u0063",
            "doc_id": "doc_md",
            "section_path": ["指南", "四、华东地区"],
            "content": (
                '<table><tr><td>早餐</td><td>蒸番薯（番薯150g）</td></tr>'
                "<tr><td>中餐</td><td>苦瓜炒蛋（苦瓜150g，鸡蛋50g）</td></tr>"
                "<tr><td>晚餐</td><td>清蒸鱼、米饭、蔬菜、牛奶、葡萄、坚果、豆类、杂粮、汤。</td></tr>"
                "<tr><td>加餐</td><td>苹果、核桃、酸奶。</td></tr>"
                "<tr><td>备注</td><td>本表还包含不同季节、多餐次、烹调方式、能量合计、蛋白质、脂肪、"
                "碳水化合物、钠、钾、钙、镁、膳食纤维和若干地区食谱说明。</td></tr></table>"
            ),
            "source_type": "table",
        }
    }

    match = module.match_source_unit(
        "doc_md::u0063",
        source_units,
        {},
        module.index_chunks_by_doc(module.load_project_chunks(project_dir)),
    )

    assert match.matched is True
    assert match.method == "doc_constrained_table_section_ngram"
    assert match.chunk_id == "chunk-table"


def test_balanced_selection_excludes_replace_and_requires_mapped_evidence():
    module = _load_module()
    samples = [
        {
            "question_id": "q1",
            "question_type": "fact_lookup",
            "difficulty": "hard",
            "metadata": {"document_scope": "multi_document"},
            "source_docs": ["a", "b"],
        },
        {
            "question_id": "q2",
            "question_type": "fact_lookup",
            "difficulty": "hard",
            "metadata": {"document_scope": "multi_document"},
            "source_docs": ["a", "b"],
        },
        {
            "question_id": "q3",
            "question_type": "fact_lookup",
            "difficulty": "hard",
            "metadata": {"document_scope": "multi_document"},
            "source_docs": ["a", "b"],
        },
    ]
    question_stats = {
        "q1": {"matched_evidence_count": 2, "evidence_source_count": 2},
        "q2": {"matched_evidence_count": 3, "evidence_source_count": 3},
        "q3": {"matched_evidence_count": 0, "evidence_source_count": 1},
    }
    decisions = {"q2": {"action": "replace", "reason": "low value"}}

    selected, decision_rows = module.select_balanced_subset(
        samples,
        question_stats,
        decisions,
        per_type=5,
    )

    assert [sample["question_id"] for sample in selected] == ["q1"]
    rows_by_id = {row["question_id"]: row for row in decision_rows}
    assert rows_by_id["q1"]["selection_action"] == "selected"
    assert "phase 8 replace" in rows_by_id["q2"]["selection_reason"]
    assert "no mapped project evidence" in rows_by_id["q3"]["selection_reason"]


def test_full_selection_keeps_replace_as_stress_candidate():
    module = _load_module()
    samples = [
        {
            "question_id": "q1",
            "question_type": "multi_document_text_reasoning",
            "difficulty": "hard",
            "metadata": {"document_scope": "multi_document", "modality": "text_document"},
            "source_docs": ["a", "b"],
        },
        {
            "question_id": "q2",
            "question_type": "comparison",
            "difficulty": "medium",
            "metadata": {"document_scope": "single_document", "modality": "text_document"},
            "source_docs": ["a"],
        },
    ]
    stats = {
        "q1": {"matched_evidence_count": 3, "evidence_source_count": 3},
        "q2": {"matched_evidence_count": 1, "evidence_source_count": 1},
    }
    decisions = {"q1": {"action": "replace", "reason": "stress"}}

    selected, decision_rows = module.select_all_mapped_questions(samples, stats, decisions)

    assert [sample["question_id"] for sample in selected] == ["q1", "q2"]
    rows_by_id = {row["question_id"]: row for row in decision_rows}
    assert rows_by_id["q1"]["selection_action"] == "selected"
    assert "phase8_action=replace" in rows_by_id["q1"]["selection_reason"]


def test_capability_tags_and_slice_manifest_capture_full_experiment_slices():
    module = _load_module()
    samples = [
        {
            "question_id": "q1",
            "question_type": "aggregation_calculation",
            "difficulty": "hard",
            "metadata": {"document_scope": "multi_document", "modality": "multimodal_document"},
            "source_docs": ["doc_a", "doc_b"],
            "answer_key_points": ["a", "b", "c", "d", "e"],
        }
    ]
    mapping_rows_by_qid = {
        "q1": [
            {
                "matched": True,
                "source_type": "table",
                "match_method": "doc_constrained_table_section_ngram",
                "source_id_resolution_status": "repaired_from_gold_evidence",
            },
            {
                "matched": True,
                "source_type": "paragraph",
                "match_method": "doc_constrained_substring",
                "source_id_resolution_status": "verified_original_source_unit",
            },
            {
                "matched": True,
                "source_type": "image_description",
                "match_method": "doc_constrained_substring",
                "source_id_resolution_status": "verified_original_source_unit",
            },
        ]
    }
    stats = {"q1": {"matched_evidence_count": 3}}
    decisions = {"q1": {"action": "replace"}}

    rows = module.build_capability_tags(samples, mapping_rows_by_qid, stats, decisions)
    manifest = module.build_slice_manifest(rows)

    tags = set(rows[0]["capability_tags"])
    assert {
        "multi_evidence_ge3",
        "multi_document",
        "table_or_multimodal",
        "source_unit_repair_review",
        "phase8_replace_stress",
        "calculation",
        "hard",
        "keypoint_dense",
        "selection_stress_candidate",
    } <= tags
    assert manifest["slices"]["dqe_full_mapped"]["count"] == 1
    assert manifest["slices"]["dqe_phase8_replace_stress"]["question_ids"] == ["q1"]
