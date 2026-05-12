from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from ragent.kg.backend_config import get_backend_config_value, load_backend_config


def _import_with_fake_optional_dependency(
    monkeypatch,
    *,
    module_name: str,
    dependency_name: str,
    dependency: types.ModuleType,
):
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name, package=None):
        if name == dependency_name:
            return importlib.machinery.ModuleSpec(name, loader=None)
        return original_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setitem(sys.modules, dependency_name, dependency)
    sys.modules.pop(module_name, None)
    try:
        return importlib.import_module(module_name)
    finally:
        sys.modules.pop(module_name, None)


def test_backend_config_prefers_env_then_config_then_default(
    monkeypatch,
    tmp_path: Path,
):
    config_path = tmp_path / "kg.ini"
    config_path.write_text(
        """
        [neo4j]
        uri = bolt://config

        [milvus]
        uri = ./config-milvus.db
        """,
        encoding="utf-8",
    )

    monkeypatch.setenv("NEO4J_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("NEO4J_URI", "bolt://env")

    config = load_backend_config("NEO4J_CONFIG_FILE")

    assert (
        get_backend_config_value(
            config,
            "neo4j",
            "uri",
            env_var="NEO4J_URI",
            fallback="bolt://default",
        )
        == "bolt://env"
    )

    monkeypatch.delenv("NEO4J_URI")
    assert (
        get_backend_config_value(
            config,
            "neo4j",
            "uri",
            env_var="NEO4J_URI",
            fallback="bolt://default",
        )
        == "bolt://config"
    )
    assert (
        get_backend_config_value(
            config,
            "neo4j",
            "missing",
            env_var="NEO4J_MISSING",
            fallback="bolt://default",
        )
        == "bolt://default"
    )


def test_backend_config_supports_shared_kg_config_env(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "kg.ini"
    config_path.write_text("[milvus]\nuri = ./shared-milvus.db\n", encoding="utf-8")

    monkeypatch.delenv("MILVUS_CONFIG_FILE", raising=False)
    monkeypatch.setenv("RAGENT_KG_CONFIG_FILE", str(config_path))

    config = load_backend_config("MILVUS_CONFIG_FILE")

    assert (
        get_backend_config_value(
            config,
            "milvus",
            "uri",
            env_var="MILVUS_URI",
            fallback="./default.db",
        )
        == "./shared-milvus.db"
    )


def test_neo4j_initialize_uses_config_fallback_without_name_error(
    monkeypatch,
    tmp_path: Path,
):
    config_path = tmp_path / "neo4j.ini"
    config_path.write_text(
        """
        [neo4j]
        uri = bolt://config
        username = config-user
        password = config-pass
        connection_pool_size = 17
        connection_timeout = 3.5
        connection_acquisition_timeout = 4.5
        max_transaction_retry_time = 5.5
        database = config-db
        """,
        encoding="utf-8",
    )
    for env_name in (
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_MAX_CONNECTION_POOL_SIZE",
        "NEO4J_CONNECTION_TIMEOUT",
        "NEO4J_CONNECTION_ACQUISITION_TIMEOUT",
        "NEO4J_MAX_TRANSACTION_RETRY_TIME",
        "NEO4J_DATABASE",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("NEO4J_CONFIG_FILE", str(config_path))

    class FakeResult:
        async def consume(self):
            return None

        async def single(self):
            return {"exists": True}

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def run(self, *args, **kwargs):
            return FakeResult()

    class FakeDriver:
        def session(self, *args, **kwargs):
            return FakeSession()

        async def close(self):
            return None

    class FakeAsyncGraphDatabase:
        calls: list[dict[str, object]] = []

        @classmethod
        def driver(cls, uri, **kwargs):
            cls.calls.append({"uri": uri, **kwargs})
            return FakeDriver()

    class FakeNeo4jError(Exception):
        code = ""

    fake_neo4j = types.ModuleType("neo4j")
    fake_neo4j.AsyncGraphDatabase = FakeAsyncGraphDatabase
    fake_neo4j.AsyncDriver = FakeDriver
    fake_neo4j.AsyncManagedTransaction = object
    fake_neo4j.exceptions = SimpleNamespace(
        ServiceUnavailable=FakeNeo4jError,
        TransientError=FakeNeo4jError,
        WriteServiceUnavailable=FakeNeo4jError,
        AuthError=FakeNeo4jError,
        ClientError=FakeNeo4jError,
        DatabaseError=FakeNeo4jError,
    )

    module = _import_with_fake_optional_dependency(
        monkeypatch,
        module_name="ragent.kg.neo4j_impl",
        dependency_name="neo4j",
        dependency=fake_neo4j,
    )

    storage = module.Neo4JStorage(
        namespace="test namespace",
        global_config={},
        embedding_func=None,
    )
    asyncio.run(storage.initialize())

    driver_call = FakeAsyncGraphDatabase.calls[0]
    assert driver_call["uri"] == "bolt://config"
    assert driver_call["auth"] == ("config-user", "config-pass")
    assert driver_call["max_connection_pool_size"] == 17
    assert driver_call["connection_timeout"] == 3.5
    assert driver_call["connection_acquisition_timeout"] == 4.5
    assert driver_call["max_transaction_retry_time"] == 5.5
    assert storage._DATABASE == "config-db"


def test_milvus_post_init_uses_config_fallback_without_name_error(
    monkeypatch,
    tmp_path: Path,
):
    config_path = tmp_path / "milvus.ini"
    config_path.write_text(
        """
        [milvus]
        uri = ./config-milvus.db
        user = config-user
        password = config-pass
        token = config-token
        db_name = config-db
        """,
        encoding="utf-8",
    )
    for env_name in (
        "MILVUS_URI",
        "MILVUS_USER",
        "MILVUS_PASSWORD",
        "MILVUS_TOKEN",
        "MILVUS_DB_NAME",
        "MILVUS_WORKSPACE",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("MILVUS_CONFIG_FILE", str(config_path))

    class FakeDataType:
        VARCHAR = "VARCHAR"
        FLOAT_VECTOR = "FLOAT_VECTOR"
        INT64 = "INT64"
        DOUBLE = "DOUBLE"

    class FakeFieldSchema:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeCollectionSchema:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeIndexParams:
        def add_index(self, **kwargs):
            return None

    class FakeMilvusClient:
        calls: list[dict[str, object]] = []

        def __init__(self, **kwargs):
            self.calls.append(kwargs)
            self.collections: set[str] = set()

        def list_collections(self):
            return sorted(self.collections)

        def has_collection(self, collection_name):
            return collection_name in self.collections

        def create_collection(self, *, collection_name, schema):
            self.collections.add(collection_name)

        def prepare_index_params(self):
            return FakeIndexParams()

        def create_index(self, **kwargs):
            return None

        def load_collection(self, collection_name):
            return None

    fake_pymilvus = types.ModuleType("pymilvus")
    fake_pymilvus.MilvusClient = FakeMilvusClient
    fake_pymilvus.DataType = FakeDataType
    fake_pymilvus.CollectionSchema = FakeCollectionSchema
    fake_pymilvus.FieldSchema = FakeFieldSchema

    module = _import_with_fake_optional_dependency(
        monkeypatch,
        module_name="ragent.kg.milvus_impl",
        dependency_name="pymilvus",
        dependency=fake_pymilvus,
    )

    module.MilvusVectorDBStorage(
        namespace="chunks",
        workspace="",
        global_config={
            "working_dir": str(tmp_path),
            "embedding_batch_num": 1,
            "vector_db_storage_cls_kwargs": {
                "cosine_better_than_threshold": 0.2,
            },
        },
        embedding_func=SimpleNamespace(embedding_dim=3),
    )

    client_call = FakeMilvusClient.calls[0]
    assert client_call == {
        "uri": "./config-milvus.db",
        "user": "config-user",
        "password": "config-pass",
        "token": "config-token",
        "db_name": "config-db",
    }
