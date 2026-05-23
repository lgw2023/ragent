from __future__ import annotations

import asyncio
from pathlib import Path

from ragent.kg.shared_storage import initialize_share_data
from ragent.kg.networkx_impl import NetworkXStorage


def test_load_nx_graph_accepts_legacy_empty_json_placeholder(tmp_path: Path):
    graph_path = tmp_path / "graph_chunk_entity_relation.graphml"
    graph_path.write_text("{}\n", encoding="utf-8")

    graph = NetworkXStorage.load_nx_graph(graph_path)

    assert graph is not None
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0


def test_networkx_storage_batch_methods_use_single_graph_snapshot(tmp_path: Path):
    async def run() -> None:
        initialize_share_data()
        storage = NetworkXStorage(
            namespace="chunk_entity_relation",
            workspace="",
            global_config={"working_dir": str(tmp_path)},
            embedding_func=None,
        )
        await storage.initialize()

        graph = await storage._get_graph()
        graph.add_node("A", description="alpha")
        graph.add_node("B", description="beta")
        graph.add_node("C", description="gamma")
        graph.add_edge("A", "B", weight=1.5)
        graph.add_edge("A", "C", weight=2.5)

        assert await storage.get_nodes_batch(["A", "missing", "B"]) == {
            "A": {"description": "alpha"},
            "B": {"description": "beta"},
        }
        assert await storage.node_degrees_batch(["A", "B", "missing"]) == {
            "A": 2,
            "B": 1,
            "missing": 0,
        }
        assert await storage.edge_degrees_batch([("A", "B"), ("A", "missing")]) == {
            ("A", "B"): 3,
            ("A", "missing"): 2,
        }
        assert await storage.get_edges_batch(
            [{"src": "A", "tgt": "B"}, {"src": "B", "tgt": "C"}]
        ) == {("A", "B"): {"weight": 1.5}}
        assert await storage.get_nodes_edges_batch(["A", "missing"]) == {
            "A": [("A", "B"), ("A", "C")],
            "missing": [],
        }

    asyncio.run(run())
