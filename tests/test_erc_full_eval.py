from __future__ import annotations

import csv
import importlib.util
import json
import asyncio
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "benchmark" / "erc_evidence_questions.jsonl"
EVAL_TOOL_PATH = REPO_ROOT / "tools" / "erc_full_eval.py"
REPORT_TOOL_PATH = REPO_ROOT / "tools" / "erc_research_report.py"


def _load_eval_module():
    spec = importlib.util.spec_from_file_location("erc_full_eval", EVAL_TOOL_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_report_module():
    spec = importlib.util.spec_from_file_location("erc_research_report", REPORT_TOOL_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_erc_full_eval_generates_required_artifacts(tmp_path: Path):
    module = _load_eval_module()

    run = module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_full_eval_test",
    )
    output_dir = run["output_dir"]

    assert (output_dir / "results.jsonl").exists()
    assert (output_dir / "metrics.tsv").exists()
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "latency_cache_summary.md").exists()
    assert (output_dir / "judge_results.jsonl").exists()
    assert (output_dir / "commands.md").exists()
    assert (output_dir / "env_snapshot.txt").exists()
    assert (
        output_dir
        / "build_inference_separation"
        / "raw_units.jsonl"
    ).exists()
    assert (
        output_dir
        / "build_inference_separation"
        / "separation_summary.json"
    ).exists()

    results = [
        json.loads(line)
        for line in (output_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(results) == 240
    assert {
        (row["config_id"], row["question_id"])
        for row in results
        if row["cache_phase"] == "full_no_cache"
    } >= {("B0", "A01"), ("B2", "B01"), ("Full", "B10")}

    full_rows = [
        row
        for row in results
        if row["config_id"] == "Full" and row["cache_phase"] == "full_no_cache"
    ]
    assert len(full_rows) == 20
    assert all(row["backend_kind"] == "sanity" for row in full_rows)
    assert all(row["keyword_source"] == "gold_request_sanity" for row in full_rows)
    assert all(row["final_evidence_chunks"] for row in full_rows)
    assert all(row["citations"] for row in full_rows)
    assert all(row["stage_timings"] for row in full_rows)
    assert all(
        chunk.get("page") is None
        for row in full_rows
        for chunk in row["final_evidence_chunks"]
    )

    separation = json.loads(
        (
            output_dir
            / "build_inference_separation"
            / "separation_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert separation["online_vs_replay_match"] is True
    assert separation["readonly_snapshot_unchanged"] is True


def test_erc_full_eval_metrics_cover_configs_and_cache_phases(tmp_path: Path):
    module = _load_eval_module()

    run = module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_full_eval_test",
    )
    with (run["output_dir"] / "metrics.tsv").open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    no_cache_configs = {
        row["config_id"]
        for row in rows
        if row["cache_phase"] == "full_no_cache"
    }
    assert no_cache_configs == set(module.DEFAULT_CONFIG_ORDER)

    full_cache_phases = {
        row["cache_phase"] for row in rows if row["config_id"] == "Full"
    }
    assert full_cache_phases == set(module.FULL_CACHE_PHASES)

    full_row = next(
        row
        for row in rows
        if row["config_id"] == "Full" and row["cache_phase"] == "full_no_cache"
    )
    assert full_row["required_evidence_coverage"] == "1.0000"
    assert full_row["unsupported_claim_rate"] == "0.0000"

    summary = (run["output_dir"] / "summary.md").read_text(encoding="utf-8")
    assert "Dataset Statistics" in summary
    assert "Main Quality Results" in summary
    assert "Evidence Coverage" in summary
    assert "Latency And Cache" in summary
    assert "ERC Retrieval Path Case" in summary
    assert "Gold Replay Sanity" in summary


def test_erc_full_eval_configs_subset_does_not_require_full(tmp_path: Path):
    module = _load_eval_module()

    run = module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_full_eval_b0_only",
        config_ids=["B0"],
    )
    with (run["output_dir"] / "metrics.tsv").open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    assert {row["config_id"] for row in rows} == {"B0"}
    latency_summary = (run["output_dir"] / "latency_cache_summary.md").read_text(
        encoding="utf-8"
    )
    assert "No Full cache phases" in latency_summary


def test_erc_full_eval_can_filter_dataset_split(tmp_path: Path):
    module = _load_eval_module()

    run = module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_full_eval_dataset_a",
        config_ids=["B0"],
        datasets=["A_health_nutrition"],
    )
    results = [
        json.loads(line)
        for line in (run["output_dir"] / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(results) == 10
    assert {row["dataset"] for row in results} == {"A_health_nutrition"}
    manifest = json.loads((run["output_dir"] / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_filter"] == ["A_health_nutrition"]


def test_erc_live_annotation_preserves_manual_required_evidence(tmp_path: Path):
    module = _load_eval_module()
    record = {
        "id": "T01",
        "dataset": "manual",
        "question": "q",
        "gold_answer": "a",
        "required_source_refs": ["doc.pdf | section"],
        "required_chunk_ids": [],
        "required_evidence": [
            {
                "source_ref": "doc.pdf | p.7 | section",
                "chunk_id": "chunk-manual",
                "file_path": "doc.pdf",
                "page_numbers": [7],
                "section_path": "section",
                "annotation_status": "manual_project_chunk",
            }
        ],
    }

    annotated = module.annotate_dataset_with_project([record], tmp_path)

    assert annotated[0]["required_chunk_ids"] == ["chunk-manual"]
    assert annotated[0]["required_evidence"] == record["required_evidence"]


def test_erc_live_external_llm_guard_requires_deepseek_flash(tmp_path: Path, monkeypatch):
    module = _load_eval_module()
    blocked_output = tmp_path / "blocked_live_eval"

    monkeypatch.setenv("LLM_MODEL_URL", "https://api.deepseek.com")
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4-pro")

    with pytest.raises(ValueError, match="deepseek-v4-flash"):
        module.run_full_evaluation(
            dataset_path=DATASET_PATH,
            output_dir=blocked_output,
            backend="live",
            config_ids=["B0"],
            live_project_dir=tmp_path / "project",
            skip_live_build=True,
            question_limit=1,
            live_rag=object(),
        )

    assert not blocked_output.exists()


def test_erc_live_backend_smoke_with_fake_runtime(tmp_path: Path):
    module = _load_eval_module()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    async def fake_runner(_rag, record, config, cache_phase):
        stage_timings = [{"stage": "onehop_total", "seconds": 0.01}]
        if cache_phase == "answer_cache_warm":
            stage_timings.append({"stage": "answer_cache_hit", "seconds": 0.0})
        chunk = {
            "rank": 1,
            "chunk_id": "chunk-live-1",
            "source_ref": record["required_source_refs"][0],
            "file_path": record["required_source_refs"][0].split("|", 1)[0].strip(),
            "page": 1,
            "page_numbers": [1],
            "section": "范围",
            "section_path": "范围",
            "source": "fake-live",
            "content": record["gold_answer"],
        }
        return {
            "answer": record["gold_answer"],
            "retrieved_contexts": [chunk],
            "final_evidence_chunks": [chunk],
            "entities": record.get("required_entities", [])[:1],
            "relations": record.get("required_relations", [])[:1],
            "stage_timings": stage_timings,
            "cache_hit_stages": ["answer_cache_hit"] if cache_phase == "answer_cache_warm" else [],
            "keyword_source": "fake",
            "high_level_keywords": [],
            "low_level_keywords": [],
            "rerank_used": config.uses_rerank,
            "rerank_status": "fake",
            "latency_seconds": 0.01,
        }

    async def fake_judge(_record, _answer, _chunks, fallback):
        return {
            **fallback,
            "correctness": 1.0,
            "completeness": 1.0,
            "faithfulness": 1.0,
            "numerical_accuracy": 1.0,
            "unsupported_claim_rate": 0.0,
        }

    run = module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_live_smoke",
        backend="live",
        config_ids=["B0", "Full"],
        live_project_dir=project_dir,
        skip_live_build=True,
        question_limit=2,
        live_query_runner=fake_runner,
        judge_func=fake_judge,
        live_rag=object(),
        live_concurrency=2,
    )
    output_dir = run["output_dir"]
    results = [
        json.loads(line)
        for line in (output_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {row["backend_kind"] for row in results} == {"live"}
    judge_rows = [
        json.loads(line)
        for line in (output_dir / "judge_results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(judge_rows) == len([row for row in results if row["cache_phase"] == "full_no_cache"])
    assert (output_dir / "annotated_dataset.jsonl").exists()
    assert (output_dir / "judge_results.jsonl").read_text(encoding="utf-8").strip()
    separation = json.loads(
        (output_dir / "build_inference_separation" / "separation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert separation["build_mode"] == "existing_project_copy"


def test_erc_live_strict_cold_rows_clear_cache_per_request(tmp_path: Path, monkeypatch):
    module = _load_eval_module()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    clear_calls = []

    import ragent.benchmarking as benchmarking

    def fake_clear(project, *, cache_types, repo_root):
        clear_calls.append((Path(project), tuple(cache_types), Path(repo_root)))

    monkeypatch.setattr(benchmarking, "clear_query_cache_entries", fake_clear)

    async def fake_runner(_rag, record, config, cache_phase):
        chunk = {
            "rank": 1,
            "chunk_id": "chunk-live-1",
            "source_ref": record["required_source_refs"][0],
            "content": record["gold_answer"],
        }
        return {
            "answer": record["gold_answer"],
            "retrieved_contexts": [chunk],
            "final_evidence_chunks": [chunk],
            "entities": record.get("required_entities", [])[:1],
            "relations": record.get("required_relations", [])[:1],
            "stage_timings": [{"stage": "onehop_total", "seconds": 0.01}],
            "cache_hit_stages": [],
            "keyword_source": "fake",
            "high_level_keywords": [],
            "low_level_keywords": [],
            "rerank_used": config.uses_rerank,
            "rerank_status": "fake",
            "latency_seconds": 0.01,
        }

    async def fake_judge(_record, _answer, _chunks, fallback):
        return fallback

    run = module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_live_strict_cold",
        backend="live",
        config_ids=["B0"],
        live_project_dir=project_dir,
        skip_live_build=True,
        question_limit=2,
        live_query_runner=fake_runner,
        judge_func=fake_judge,
        live_rag=object(),
        live_concurrency=2,
        clear_cache_per_live_row=True,
    )

    copied_project = run["output_dir"] / "build_inference_separation" / "existing_project_copy"
    all_cache_types = ("answer", "retrieval", "render", "prompt", "keyword_candidate")
    assert clear_calls == [
        (copied_project, all_cache_types, REPO_ROOT),
        (copied_project, all_cache_types, REPO_ROOT),
        (copied_project, all_cache_types, REPO_ROOT),
    ]


def test_erc_live_configs_map_to_component_toggles():
    module = _load_eval_module()

    expected = {
        "B0": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": False,
            "enable_entity_retrieval": False,
            "enable_relation_retrieval": False,
            "enable_graph_expansion": False,
            "enable_query_variants": False,
            "enable_rerank": False,
            "enable_evidence_selection": False,
        },
        "B1": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": False,
            "enable_entity_retrieval": False,
            "enable_relation_retrieval": False,
            "enable_graph_expansion": False,
            "enable_query_variants": False,
            "enable_rerank": True,
            "enable_evidence_selection": False,
        },
        "B2": {
            "enable_chunk_retrieval": False,
            "enable_graph_retrieval": True,
            "enable_entity_retrieval": True,
            "enable_relation_retrieval": True,
            "enable_graph_expansion": True,
            "enable_query_variants": False,
            "enable_rerank": False,
            "enable_evidence_selection": False,
        },
        "B3": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": True,
            "enable_entity_retrieval": True,
            "enable_relation_retrieval": False,
            "enable_graph_expansion": False,
            "enable_query_variants": False,
            "enable_rerank": False,
            "enable_evidence_selection": False,
        },
        "B4": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": True,
            "enable_entity_retrieval": True,
            "enable_relation_retrieval": True,
            "enable_graph_expansion": False,
            "enable_query_variants": False,
            "enable_rerank": False,
            "enable_evidence_selection": False,
        },
        "B5": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": True,
            "enable_entity_retrieval": True,
            "enable_relation_retrieval": True,
            "enable_graph_expansion": True,
            "enable_query_variants": False,
            "enable_rerank": False,
            "enable_evidence_selection": False,
        },
        "B6": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": True,
            "enable_entity_retrieval": True,
            "enable_relation_retrieval": True,
            "enable_graph_expansion": True,
            "enable_query_variants": True,
            "enable_rerank": False,
            "enable_evidence_selection": False,
        },
        "B7": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": True,
            "enable_entity_retrieval": True,
            "enable_relation_retrieval": True,
            "enable_graph_expansion": True,
            "enable_query_variants": True,
            "enable_rerank": True,
            "enable_evidence_selection": False,
        },
        "Full": {
            "enable_chunk_retrieval": True,
            "enable_graph_retrieval": True,
            "enable_entity_retrieval": True,
            "enable_relation_retrieval": True,
            "enable_graph_expansion": True,
            "enable_query_variants": True,
            "enable_rerank": True,
            "enable_evidence_selection": True,
        },
    }

    for config_id, fields in expected.items():
        param = module._live_config_to_query_param(
            module.CONFIGS[config_id],
            "full_no_cache",
        )
        for field, value in fields.items():
            assert getattr(param, field) is value


def test_erc_live_chunk_normalization_parses_source_ref_pages():
    module = _load_eval_module()

    chunk = module._normalize_live_chunk(
        {
            "source_ref": "成人肥胖食养指南_2024.pdf | p.66-67 | 成人肥胖判定标准",
            "content": "BMI >= 28",
        },
        rank=1,
    )

    assert chunk["page"] == 66
    assert chunk["page_numbers"] == [66, 67]


def test_erc_live_judge_failure_is_retained():
    module = _load_eval_module()
    record = module.load_dataset(DATASET_PATH)[0]
    result = {
        "run_id": "test-run",
        "question_id": record["id"],
        "config_id": "B0",
        "cache_phase": "full_no_cache",
        "answer": "failed judge answer",
        "final_evidence_chunks": [],
        "metrics": {
            "correctness": 0.1,
            "completeness": 0.2,
            "relevance": 0.3,
            "faithfulness": 0.4,
            "numerical_accuracy": 0.5,
            "evidence_recall_at_k": 0.6,
            "final_evidence_recall": 0.7,
            "citation_precision": 0.8,
            "citation_recall": 0.9,
            "required_evidence_coverage": 0.25,
            "unsupported_claim_rate": 0.75,
        },
    }
    original_metrics = dict(result["metrics"])
    judge_rows = []

    async def failing_judge(_record, _answer, _chunks, _fallback):
        raise RuntimeError("judge unavailable")

    asyncio.run(
        module._score_live_result(
            record,
            result,
            judge_rows,
            "llm",
            failing_judge,
        )
    )

    assert result["metrics"] == original_metrics
    assert judge_rows == [
        {
            "run_id": "test-run",
            "question_id": "A01",
            "config_id": "B0",
            "judge_mode": "llm",
            "status": "failed",
            "judge": {
                "error": "judge unavailable",
                "error_type": "RuntimeError",
            },
        }
    ]


def test_erc_live_judge_parser_accepts_trailing_text():
    module = _load_eval_module()

    parsed = module._parse_json_from_text(
        '{"correctness": 0.8, "faithfulness": 0.7}\nextra evaluator note'
    )

    assert parsed == {"correctness": 0.8, "faithfulness": 0.7}


def test_erc_research_report_renders_full_eval_sections(tmp_path: Path):
    eval_module = _load_eval_module()
    report_module = _load_report_module()

    run = eval_module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_full_eval_test",
    )
    report = report_module.render_report(
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
        full_eval_dir=run["output_dir"],
    )

    assert "Full Evaluation Artifacts" in report
    assert "Fresh-build paper-table eligibility: `no`" in report
    assert "Paper-usable scope:" in report
    assert "Gold Replay Sanity Retrieval-Layer Results" in report
    assert "Gold Replay Sanity Downstream Answer Diagnostic Results" in report
    assert "Gold Replay Sanity Ablation Results" in report
    assert "Evidence Coverage" in report
    assert "Latency And Cache" in report
    assert "Build/Inference Separation" in report
    assert "ERC Retrieval Path Case" in report
    assert "LLM_MODEL=deepseek-v4-flash" in report
    assert "deepseek-v4-pro" in report
    assert "--output docs/research/erc_traceable_rag_report.md" in report


def test_erc_research_report_renders_strict_cold_control(tmp_path: Path):
    eval_module = _load_eval_module()
    report_module = _load_report_module()

    run = eval_module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_full_eval_test",
    )
    strict_dir = tmp_path / "erc_full_eval_strict_cold"
    strict_dir.mkdir()
    (strict_dir / "metrics.tsv").write_text(
        (run["output_dir"] / "metrics.tsv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (strict_dir / "run_manifest.json").write_text(
        json.dumps({"clear_cache_per_live_row": True}),
        encoding="utf-8",
    )
    (strict_dir / "results.jsonl").write_text(
        json.dumps({"question_id": "A01", "config_id": "Full"}) + "\n",
        encoding="utf-8",
    )
    (strict_dir / "judge_results.jsonl").write_text(
        json.dumps({"question_id": "A01", "config_id": "Full", "status": "ok"}) + "\n",
        encoding="utf-8",
    )

    report = report_module.render_report(
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
        full_eval_dir=run["output_dir"],
        strict_cold_eval_dir=strict_dir,
    )

    assert "Strict Per-Row Cold Cache Control" in report
    assert "Clear cache per live row: `True`" in report
    assert "main Full no-cache" in report
    assert "strict per-row cold Full" in report
    assert "row_cache_hit_distribution" in report


def test_erc_research_report_renders_interrupted_strict_cold_control(tmp_path: Path):
    eval_module = _load_eval_module()
    report_module = _load_report_module()

    run = eval_module.run_full_evaluation(
        dataset_path=DATASET_PATH,
        output_dir=tmp_path / "erc_full_eval_test",
    )
    strict_dir = tmp_path / "erc_full_eval_strict_partial"
    strict_dir.mkdir()
    (strict_dir / "results.jsonl").write_text(
        json.dumps(
            {
                "question_id": "A01",
                "config_id": "Full",
                "cache_phase": "full_no_cache",
                "cache_hit_stages": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (strict_dir / "judge_results.jsonl").write_text(
        json.dumps({"question_id": "A01", "config_id": "Full", "status": "ok"}) + "\n",
        encoding="utf-8",
    )
    Path(str(strict_dir) + ".terminal.log").write_text(
        "HTTPStatusError: 401 Unauthorized invalid_api_key\n",
        encoding="utf-8",
    )

    report = report_module.render_report(
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
        full_eval_dir=run["output_dir"],
        strict_cold_eval_dir=strict_dir,
    )

    assert "interrupted before `metrics.tsv` was written" in report
    assert "Strict no-cache row cache-hit distribution: `none=1`" in report
    assert "invalid_api_key" in report
