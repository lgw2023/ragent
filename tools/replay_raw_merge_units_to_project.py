#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ragent.llm.openai import env_openai_complete, openai_embed  # noqa: E402
from ragent.offline_replay import (  # noqa: E402
    iter_raw_merge_units_jsonl,
    replay_raw_merge_units_jsonl_to_rag,
    replay_raw_merge_units_to_rag,
)
from ragent.ragent import Ragent  # noqa: E402
from ragent.vector_sidecar_artifacts import (  # noqa: E402
    DEFAULT_SIDECAR_PROFILE,
    vector_sidecar_build_enabled,
)
from ragent.utils import ModelUsageCollector, write_model_usage_report  # noqa: E402
from tools.build_vector_sidecars import build_profile_sidecars  # noqa: E402


def _prepare_output_dir(output_dir: Path, *, overwrite: bool, resume: bool) -> None:
    if overwrite and resume:
        raise ValueError("--overwrite and --resume cannot be used together.")
    if output_dir.exists():
        if overwrite:
            shutil.rmtree(output_dir)
        elif resume:
            output_dir.mkdir(parents=True, exist_ok=True)
            return
        elif any(output_dir.iterdir()):
            raise FileExistsError(
                f"Output directory is not empty: {output_dir}. Use --overwrite to replace it "
                "or --resume to continue into the existing project."
            )
    output_dir.mkdir(parents=True, exist_ok=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay raw Ragent extraction units into a final KG project using the "
            "online graph merge pipeline."
        )
    )
    parser.add_argument(
        "raw_units",
        nargs="+",
        help="Raw merge unit JSONL files or directories containing *.jsonl files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Final Ragent project directory to write.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output directory if it already exists.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Continue into an existing output project. Raw units with doc_status "
            "records already present in the target project are skipped."
        ),
    )
    parser.add_argument(
        "--workspace",
        default=os.getenv("WORKSPACE", ""),
        help="Optional Ragent workspace name. Defaults to WORKSPACE.",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("LLM_MODEL"),
        help="LLM model name. Defaults to LLM_MODEL from the environment.",
    )
    parser.add_argument(
        "--force-llm-summary-on-merge",
        type=int,
        default=None,
        help="Override Ragent force_llm_summary_on_merge for replay.",
    )
    parser.add_argument(
        "--llm-model-max-async",
        type=int,
        default=None,
        help="Override Ragent llm_model_max_async for deterministic replay runs.",
    )
    parser.add_argument(
        "--embedding-func-max-async",
        type=int,
        default=None,
        help="Override Ragent embedding_func_max_async for deterministic replay runs.",
    )
    parser.add_argument(
        "--embedding-batch-num",
        type=int,
        default=None,
        help="Override Ragent embedding_batch_num for low-rate replay runs.",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help=(
            "Load all raw units before replay. Use only for small debug datasets or "
            "non-contiguous source_group_key inputs."
        ),
    )
    parser.add_argument(
        "--allow-non-contiguous-source-groups",
        action="store_true",
        help=(
            "Use in-memory grouping when the same source_group_key can appear in "
            "multiple JSONL blocks. This is intended for small debug datasets."
        ),
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help=(
            "Continue replaying later source groups after a group failure. Failed "
            "groups are marked in doc_status and omitted from the strict final KG."
        ),
    )
    parser.add_argument(
        "--no-rollback-on-error",
        action="store_true",
        help=(
            "Do not roll back staged KV/VDB data after a source group failure. "
            "The default is to roll back staged full_docs/text_chunks/chunks_vdb "
            "and restore touched graph/vector records where possible."
        ),
    )
    parser.add_argument(
        "--no-vector-sidecar",
        action="store_true",
        help=(
            "Do not build the default project-local FAISS sidecar after replay. "
            "Use only for comparison/debug runs."
        ),
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output).expanduser().resolve()
    _prepare_output_dir(output_dir, overwrite=args.overwrite, resume=args.resume)

    if not args.llm_model:
        raise ValueError("Missing --llm-model or LLM_MODEL environment variable.")

    rag_kwargs = {
        "working_dir": str(output_dir),
        "workspace": args.workspace,
        "embedding_func": openai_embed,
        "llm_model_func": env_openai_complete,
        "llm_model_name": args.llm_model,
        "auto_manage_storages_states": False,
    }
    if args.force_llm_summary_on_merge is not None:
        rag_kwargs["force_llm_summary_on_merge"] = args.force_llm_summary_on_merge
    if args.llm_model_max_async is not None:
        rag_kwargs["llm_model_max_async"] = args.llm_model_max_async
    if args.embedding_func_max_async is not None:
        rag_kwargs["embedding_func_max_async"] = args.embedding_func_max_async
    if args.embedding_batch_num is not None:
        rag_kwargs["embedding_batch_num"] = args.embedding_batch_num

    collector = ModelUsageCollector("replay_raw_merge_units_to_project")
    stats_payload: dict | None = None
    vector_sidecar_manifest: dict | None = None
    try:
        with collector:
            rag: Ragent | None = None
            try:
                rag = Ragent(**rag_kwargs)
                await rag.initialize_storages()
                if args.in_memory or args.allow_non_contiguous_source_groups:
                    units = list(iter_raw_merge_units_jsonl(args.raw_units))
                    stats = await replay_raw_merge_units_to_rag(
                        rag,
                        units,
                        rollback_staged_data_on_error=not args.no_rollback_on_error,
                        continue_on_group_error=args.continue_on_error,
                    )
                else:
                    stats = await replay_raw_merge_units_jsonl_to_rag(
                        rag,
                        args.raw_units,
                        require_contiguous_source_groups=True,
                        rollback_staged_data_on_error=not args.no_rollback_on_error,
                        continue_on_group_error=args.continue_on_error,
                    )
                stats_payload = dict(stats.__dict__)
            finally:
                if rag is not None:
                    await rag.finalize_storages()
                    for attr_name in ("embedding_func", "llm_model_func"):
                        shutdown = getattr(
                            getattr(rag, attr_name, None), "shutdown", None
                        )
                        if callable(shutdown):
                            await shutdown()
            if (
                stats_payload is not None
                and vector_sidecar_build_enabled()
                and not getattr(args, "no_vector_sidecar", False)
            ):
                vector_sidecar_manifest = await asyncio.to_thread(
                    build_profile_sidecars,
                    project_dir=output_dir,
                    profile=DEFAULT_SIDECAR_PROFILE,
                )
    finally:
        report_path = write_model_usage_report(
            collector,
            str(output_dir),
            task_name="raw_replay",
            metadata={
                "raw_units": ", ".join(
                    str(Path(item).expanduser()) for item in args.raw_units
                ),
                "output": str(output_dir),
                "workspace": args.workspace,
            },
        )
        if stats_payload is not None:
            stats_payload["model_usage_report"] = report_path
            if vector_sidecar_manifest is not None:
                stats_payload["vector_sidecar"] = {
                    "profile": vector_sidecar_manifest.get("profile"),
                    "output_dir": str(output_dir / "vector_sidecars" / "default"),
                }

    if stats_payload is None:
        raise RuntimeError("raw replay finished without stats")
    print(json.dumps(stats_payload, ensure_ascii=False, indent=2))


def main() -> None:
    args = _parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
