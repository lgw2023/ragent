from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "benchmark" / "erc_evidence_questions.jsonl"
QWEN4B_MINIMAL_DATASET_PATH = (
    REPO_ROOT / "benchmark" / "erc_evidence_questions_qwen4b_minimal.jsonl"
)
REPORT_TOOL_PATH = REPO_ROOT / "tools" / "erc_research_report.py"

REQUIRED_FIELDS = {
    "id",
    "dataset",
    "question",
    "gold_answer",
    "required_source_refs",
    "required_chunk_ids",
    "required_entities",
    "required_relations",
    "question_type",
    "difficulty",
    "requires_calculation",
}

SOURCE_PDFS = {
    "成人肥胖食养指南_2024.pdf",
    "成人高血压食养指南_2022.pdf",
    "中国居民膳食指南_2022.pdf",
    "GB-31607-2021.pdf",
    "GB29938-2020.pdf",
    "GB31647-2018.pdf",
    "GBT1354-2018bz.pdf",
    "GBT22106-2008dz.pdf",
}


def _load_records() -> list[dict]:
    records = []
    for line in DATASET_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_erc_gold_dataset_schema_and_split():
    records = _load_records()
    assert len(records) == 20
    assert len({record["id"] for record in records}) == len(records)

    datasets = {}
    for record in records:
        assert REQUIRED_FIELDS <= set(record)
        assert record["question"].strip()
        assert record["gold_answer"].strip()
        assert isinstance(record["required_source_refs"], list)
        assert record["required_source_refs"]
        assert isinstance(record["required_chunk_ids"], list)
        assert isinstance(record["required_entities"], list)
        assert isinstance(record["required_relations"], list)
        assert isinstance(record["requires_calculation"], bool)
        datasets[record["dataset"]] = datasets.get(record["dataset"], 0) + 1

    assert datasets == {
        "A_health_nutrition": 10,
        "B_food_standards": 10,
    }


def test_erc_gold_dataset_provenance_fields_do_not_use_pseudo_pages():
    records = _load_records()

    for record in records:
        for source_ref in record["required_source_refs"]:
            doc_name, _, section = source_ref.partition("|")
            assert doc_name.strip() in SOURCE_PDFS
            assert section.strip()

        for evidence in record.get("required_evidence", []):
            assert evidence["source_ref"]
            assert evidence["file_path"]
            assert evidence["annotation_status"] in {
                "matched_project_chunk",
                "unmatched_project_chunk",
                "manual_source_ref",
            }
            page_numbers = evidence.get("page_numbers", [])
            assert isinstance(page_numbers, list)
            assert all(isinstance(page, int) and page > 0 for page in page_numbers)
            if not evidence.get("chunk_id"):
                assert evidence.get("annotation_reason")


def test_qwen4b_minimal_dataset_has_true_project_provenance():
    records = _load_jsonl(QWEN4B_MINIMAL_DATASET_PATH)

    assert len(records) == 16
    assert {record["dataset"] for record in records} == {
        "A_health_nutrition_qwen4b_manual",
        "B_food_standards_qwen4b_manual",
    }

    for record in records:
        evidence = record.get("required_evidence", [])
        assert evidence
        assert record["required_chunk_ids"] == [item["chunk_id"] for item in evidence]
        for item in evidence:
            assert item["annotation_status"] == "manual_project_chunk"
            assert item["chunk_id"].startswith("chunk-")
            assert item["source_ref"]
            assert item["file_path"]
            assert item["page_numbers"]
            assert all(isinstance(page, int) and page > 0 for page in item["page_numbers"])
            assert "pseudo" not in json.dumps(item, ensure_ascii=False).lower()


def test_erc_report_renderer_uses_dataset_and_existing_artifacts():
    spec = importlib.util.spec_from_file_location("erc_research_report", REPORT_TOOL_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    report = module.render_report(
        dataset_path=DATASET_PATH,
        latency_path=REPO_ROOT / "benchmark" / "latency_smoke_matrix_20260422" / "results.tsv",
        retrieval_path=REPO_ROOT
        / "benchmark"
        / "retrieval_cross_no_cache_local_gliner_20260523_190243"
        / "results.tsv",
        keyword_cache_path=REPO_ROOT
        / "benchmark"
        / "keyword_cache_benefit_qwen4b_hybrid"
        / "results.tsv",
    )

    assert "Questions: `20`" in report
    assert "B0 | Flat Chunk RAG" in report
    assert "A_health_nutrition" in report
    assert "B_food_standards" in report
