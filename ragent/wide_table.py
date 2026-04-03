from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Callable

import pandas as pd

from .utils import clean_text


@dataclass(frozen=True)
class WideTableImportConfig:
    """Configuration for importing a sample-feature wide table."""

    entity_name_column: str
    entity_type: str = "sample"
    sheet_name: str | int | None = None
    feature_columns: list[str] | None = None
    excluded_columns: list[str] = field(default_factory=list)
    include_null_values: bool = False
    feature_name_map: dict[str, str] = field(default_factory=dict)
    table_name: str | None = None


@dataclass(frozen=True)
class WideTableRowRecord:
    row_index: int
    source_ref: str
    entity_name: str
    entity_description: str
    chunk_content: str


@dataclass(frozen=True)
class PreparedWideTableImport:
    doc_name: str
    file_path: str
    doc_content: str
    rows: list[WideTableRowRecord]


def load_wide_table_dataframe(
    source: str | Path | pd.DataFrame,
    *,
    sheet_name: str | int | None = None,
) -> tuple[pd.DataFrame, str]:
    if isinstance(source, pd.DataFrame):
        return _normalize_wide_table_dataframe(source.copy()), "wide_table"

    source_path = Path(source).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Wide-table source not found: {source_path}")

    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        dataframe = pd.read_csv(source_path)
    elif suffix in {".tsv", ".txt"}:
        dataframe = pd.read_csv(source_path, sep="\t")
    elif suffix in {".xlsx", ".xlsm"}:
        read_excel_kwargs = {}
        if sheet_name is not None:
            read_excel_kwargs["sheet_name"] = sheet_name
        dataframe = pd.read_excel(source_path, **read_excel_kwargs)
    else:
        raise ValueError(
            f"Unsupported wide-table file format: {source_path.suffix or '<none>'}"
        )

    if isinstance(dataframe, dict):
        first_sheet_name, dataframe = next(iter(dataframe.items()))
        if not isinstance(dataframe, pd.DataFrame):
            raise ValueError(
                f"Unable to load worksheet '{first_sheet_name}' from wide table: {source_path}"
            )

    return _normalize_wide_table_dataframe(dataframe), str(source_path)


def prepare_wide_table_import(
    source: str | Path | pd.DataFrame,
    config: WideTableImportConfig,
    *,
    doc_name: str | None = None,
    file_path: str | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> PreparedWideTableImport:
    dataframe, detected_file_path = load_wide_table_dataframe(
        source, sheet_name=config.sheet_name
    )
    if config.entity_name_column not in dataframe.columns:
        raise ValueError(
            f"Column '{config.entity_name_column}' not found in wide table: "
            f"{list(dataframe.columns)}"
        )

    resolved_file_path = file_path or detected_file_path
    table_name = config.table_name or doc_name or Path(resolved_file_path).stem
    feature_columns = _resolve_feature_columns(dataframe, config)

    rows: list[WideTableRowRecord] = []
    skipped_rows = 0

    total_source_rows = len(dataframe.index)

    for row_index, (_, row) in enumerate(dataframe.iterrows()):
        raw_name = row.get(config.entity_name_column)
        if _is_missing_value(raw_name):
            skipped_rows += 1
            if progress_callback is not None:
                progress_callback(
                    {
                        "stage": "prepare_rows",
                        "current": row_index + 1,
                        "total": total_source_rows,
                        "row_index": row_index + 1,
                        "entity_name": "",
                        "source_ref": f"row={row_index + 1}",
                        "skipped": True,
                        "valid_rows": len(rows),
                        "skipped_rows": skipped_rows,
                    }
                )
            continue

        entity_name = clean_text(str(raw_name))
        if not entity_name:
            skipped_rows += 1
            if progress_callback is not None:
                progress_callback(
                    {
                        "stage": "prepare_rows",
                        "current": row_index + 1,
                        "total": total_source_rows,
                        "row_index": row_index + 1,
                        "entity_name": "",
                        "source_ref": f"row={row_index + 1}",
                        "skipped": True,
                        "valid_rows": len(rows),
                        "skipped_rows": skipped_rows,
                    }
                )
            continue

        feature_lines: list[str] = []
        for column_name in feature_columns:
            raw_value = row.get(column_name)
            if _is_missing_value(raw_value):
                if not config.include_null_values:
                    continue
                value_text = "null"
            else:
                value_text = _stringify_feature_value(raw_value)

            feature_label = config.feature_name_map.get(column_name, column_name)
            feature_lines.append(f"- {feature_label}: {value_text}")

        source_ref = f"row={row_index + 1}"
        chunk_lines = [
            f"{config.entity_type}: {entity_name}",
            f"source_table: {table_name}",
            f"source_ref: {source_ref}",
            "feature_profile:",
        ]
        chunk_lines.extend(feature_lines or ["- no_features_available"])

        rows.append(
            WideTableRowRecord(
                row_index=row_index,
                source_ref=source_ref,
                entity_name=entity_name,
                entity_description=(
                    f"{config.entity_type} imported from wide table '{table_name}'"
                ),
                chunk_content="\n".join(chunk_lines),
            )
        )
        if progress_callback is not None:
            progress_callback(
                {
                    "stage": "prepare_rows",
                    "current": row_index + 1,
                    "total": total_source_rows,
                    "row_index": row_index + 1,
                    "entity_name": entity_name,
                    "source_ref": source_ref,
                    "skipped": False,
                    "valid_rows": len(rows),
                    "skipped_rows": skipped_rows,
                }
            )

    if not rows:
        raise ValueError("No valid rows found in wide table after preprocessing")

    feature_preview = ", ".join(feature_columns[:8])
    if len(feature_columns) > 8:
        feature_preview += ", ..."
    entity_preview = ", ".join(row.entity_name for row in rows[:5])

    doc_lines = [
        f"wide_table_name: {table_name}",
        f"file_path: {resolved_file_path}",
        f"entity_name_column: {config.entity_name_column}",
        f"entity_type: {config.entity_type}",
        f"row_count: {len(rows)}",
        f"feature_count: {len(feature_columns)}",
        f"feature_columns: {feature_preview}",
    ]
    if entity_preview:
        doc_lines.append(f"sample_entities: {entity_preview}")
    if skipped_rows:
        doc_lines.append(f"skipped_rows: {skipped_rows}")

    return PreparedWideTableImport(
        doc_name=table_name,
        file_path=resolved_file_path,
        doc_content="\n".join(doc_lines),
        rows=rows,
    )


def build_wide_table_chunk_result(
    row: WideTableRowRecord,
    chunk_id: str,
    *,
    entity_type: str,
    file_path: str,
) -> tuple[dict[str, list[dict[str, Any]]], dict[tuple[str, str], list[dict[str, Any]]]]:
    maybe_nodes: dict[str, list[dict[str, Any]]] = {
        row.entity_name: [
            {
                "entity_name": row.entity_name,
                "entity_type": entity_type,
                "description": row.entity_description,
                "source_id": chunk_id,
                "file_path": file_path,
            }
        ],
        chunk_id: [
            {
                "entity_name": chunk_id,
                "entity_type": "chunk_text",
                "description": row.chunk_content,
                "source_id": chunk_id,
                "file_path": file_path,
            }
        ],
    }
    maybe_edges: dict[tuple[str, str], list[dict[str, Any]]] = {
        (row.entity_name, chunk_id): [
            {
                "src_id": row.entity_name,
                "tgt_id": chunk_id,
                "weight": 5.0,
                "description": "source",
                "keywords": "belong to",
                "source_id": chunk_id,
                "file_path": file_path,
            }
        ]
    }
    return maybe_nodes, maybe_edges


def _resolve_feature_columns(
    dataframe: pd.DataFrame,
    config: WideTableImportConfig,
) -> list[str]:
    if config.feature_columns is not None:
        missing_columns = [
            column_name
            for column_name in config.feature_columns
            if column_name not in dataframe.columns
        ]
        if missing_columns:
            raise ValueError(
                f"Feature columns not found in wide table: {missing_columns}"
            )
        return list(config.feature_columns)

    excluded_columns = set(config.excluded_columns)
    excluded_columns.add(config.entity_name_column)
    return [
        column_name
        for column_name in dataframe.columns
        if column_name not in excluded_columns
    ]


def _is_missing_value(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _stringify_feature_value(value: Any) -> str:
    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float):
        return format(value, ".15g")

    return clean_text(str(value))


def _normalize_wide_table_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized_columns = [_normalize_wide_table_column_name(name) for name in dataframe.columns]
    deduplicated_columns = _deduplicate_column_names(normalized_columns)
    if list(dataframe.columns) == deduplicated_columns:
        return dataframe

    normalized_dataframe = dataframe.copy()
    normalized_dataframe.columns = deduplicated_columns
    return normalized_dataframe


def _normalize_wide_table_column_name(column_name: Any) -> str:
    text = str(column_name)
    text = text.replace("_x000D_", " ")
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = text.replace("\t", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or "unnamed_column"


def _deduplicate_column_names(column_names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    deduplicated: list[str] = []

    for column_name in column_names:
        occurrence = seen.get(column_name, 0) + 1
        seen[column_name] = occurrence
        if occurrence == 1:
            deduplicated.append(column_name)
        else:
            deduplicated.append(f"{column_name} ({occurrence})")

    return deduplicated
