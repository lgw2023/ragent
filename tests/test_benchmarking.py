import sqlite3
from pathlib import Path

from ragent.benchmarking import clear_query_cache_entries


def test_clear_query_cache_entries_recovers_malformed_sqlite_cache(tmp_path: Path):
    cache_path = tmp_path / "kv_store_llm_response_cache.sqlite"
    wal_path = tmp_path / "kv_store_llm_response_cache.sqlite-wal"
    cache_path.write_bytes(b"not a sqlite database")
    wal_path.write_bytes(b"stale wal")

    result = clear_query_cache_entries(tmp_path)

    assert result["cache_files"] == [str(cache_path)]
    assert result["deleted_entry_count"] == 0
    recovered_names = [Path(item).name for item in result["recovered_cache_files"]]
    assert any(
        name.startswith("kv_store_llm_response_cache.sqlite.malformed.")
        for name in recovered_names
    )
    assert any(
        name.startswith("kv_store_llm_response_cache.sqlite-wal.malformed.")
        for name in recovered_names
    )

    with sqlite3.connect(cache_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM query_cache_entries").fetchone()[0]

    assert count == 0


def test_clear_query_cache_entries_initializes_missing_table(tmp_path: Path):
    cache_path = tmp_path / "kv_store_llm_response_cache.sqlite"
    with sqlite3.connect(cache_path) as conn:
        conn.execute("CREATE TABLE unrelated (id TEXT PRIMARY KEY)")
        conn.commit()

    result = clear_query_cache_entries(tmp_path)

    assert result["deleted_entry_count"] == 0
    assert result["recovered_cache_files"] == []
    with sqlite3.connect(cache_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM query_cache_entries").fetchone()[0]

    assert count == 0
