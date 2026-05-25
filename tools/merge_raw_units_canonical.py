#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ragent.offline_replay import (  # noqa: E402
    iter_raw_merge_unit_jsonl_paths,
    iter_raw_merge_units_jsonl,
    raw_merge_unit_source_group_key,
    raw_merge_unit_to_json_obj,
)


@dataclass
class CanonicalMergeStats:
    sources: int = 0
    input_units: int = 0
    output_units: int = 0
    skipped_duplicate_doc_ids: int = 0
    source_units: dict[str, int] = field(default_factory=dict)
    output: str = ""


def _parse_input_spec(spec: str) -> tuple[str, Path]:
    if "=" in spec:
        label, raw_path = spec.split("=", 1)
        label = label.strip()
        if not label:
            raise ValueError(f"Input label is empty: {spec!r}")
        path = Path(raw_path).expanduser().resolve()
    else:
        path = Path(spec).expanduser().resolve()
        label = path.stem if path.is_file() else path.name

    if not path.exists():
        raise FileNotFoundError(f"Raw units input does not exist: {path}")
    return label, path


def _prepare_output(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {path}. Use --overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)


def merge_raw_units_canonical(
    input_specs: list[str],
    output: str | Path,
    *,
    prefix_source_group_key: bool = True,
    dedupe_doc_ids: bool = False,
    overwrite: bool = False,
) -> CanonicalMergeStats:
    output_path = Path(output).expanduser().resolve()
    parsed_inputs = [_parse_input_spec(spec) for spec in input_specs]
    input_jsonl_paths = [
        (label, list(iter_raw_merge_unit_jsonl_paths(path)))
        for label, path in parsed_inputs
    ]
    if any(output_path in paths for _label, paths in input_jsonl_paths):
        raise ValueError("Output JSONL must not also be one of the input JSONL files.")

    _prepare_output(output_path, overwrite=overwrite)

    stats = CanonicalMergeStats(sources=len(parsed_inputs), output=str(output_path))
    seen_doc_ids: set[str] = set()

    with output_path.open("w", encoding="utf-8") as output_file:
        for label, jsonl_paths in input_jsonl_paths:
            source_count = 0
            for unit in iter_raw_merge_units_jsonl(jsonl_paths):
                stats.input_units += 1
                source_count += 1
                if dedupe_doc_ids and unit.doc_id in seen_doc_ids:
                    stats.skipped_duplicate_doc_ids += 1
                    continue
                seen_doc_ids.add(unit.doc_id)

                if prefix_source_group_key:
                    source_group_key = raw_merge_unit_source_group_key(unit)
                    unit.source_group_key = f"{label}:{source_group_key}"

                output_file.write(
                    json.dumps(raw_merge_unit_to_json_obj(unit), ensure_ascii=False)
                    + "\n"
                )
                stats.output_units += 1
            stats.source_units[label] = stats.source_units.get(label, 0) + source_count

    return stats


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge raw merge-unit JSONL files into one canonical stream. "
            "By default each input label prefixes source_group_key to avoid "
            "cross-corpus source group collisions."
        )
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help=(
            "Raw-unit JSONL files or directories. Use label=/path to control the "
            "source_group_key prefix label."
        ),
    )
    parser.add_argument("-o", "--output", required=True, help="Output JSONL path.")
    parser.add_argument(
        "--no-prefix-source-group-key",
        action="store_true",
        help="Keep source_group_key values unchanged.",
    )
    parser.add_argument(
        "--dedupe-doc-ids",
        action="store_true",
        help="Skip later units whose doc_id was already written.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output JSONL.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    stats = merge_raw_units_canonical(
        args.inputs,
        args.output,
        prefix_source_group_key=not args.no_prefix_source_group_key,
        dedupe_doc_ids=args.dedupe_doc_ids,
        overwrite=args.overwrite,
    )
    print(json.dumps(asdict(stats), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
