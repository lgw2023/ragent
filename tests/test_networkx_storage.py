from __future__ import annotations

from pathlib import Path

from ragent.kg.networkx_impl import NetworkXStorage


def test_load_nx_graph_accepts_legacy_empty_json_placeholder(tmp_path: Path):
    graph_path = tmp_path / "graph_chunk_entity_relation.graphml"
    graph_path.write_text("{}\n", encoding="utf-8")

    graph = NetworkXStorage.load_nx_graph(graph_path)

    assert graph is not None
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
