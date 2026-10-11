"""Opt-in source-free, bounded-memory histogram of native Coptic graph storage.

Shallow object sizes are NOT process RSS, unique retained heap, or a proof
that a compact representation would save their sum. The existing source
graph is never mutated and neither corpus text nor record IDs are emitted.
"""
from __future__ import annotations

from collections import Counter
from sys import getsizeof

from ._graph_core import Graph, NODE_TYPE_ORDER
from .writer import _EDGE_FEATURES


def graph_storage_census(graph: Graph) -> dict[str, object]:
    """Summarize per-object shallow footprint without retaining corpus objects.

    Complexity: O(number of graph slots + nodes + edges + locus segments)
    time, O(number of node and edge types) additional space.
    """
    nodes: Counter[str] = Counter()
    edges: Counter[str] = Counter()
    cardinality = {"empty": 0, "single_segment": 0, "multiple_segments": 0}
    shallow = {
        "graph_slot_objects": 0,
        "graph_node_objects": 0,
        "graph_edge_objects": 0,
        "node_range_containers": 0,
        "node_range_segment_tuples": 0,
        "graph_top_level_tuples": (
            getsizeof(graph.slots) + getsizeof(graph.nodes)
            + getsizeof(graph.edges) + getsizeof(graph.node_ranges)
        ),
    }
    with_ud = 0
    for slot in graph.slots:
        shallow["graph_slot_objects"] += getsizeof(slot)
        if slot.ud is not None:
            with_ud += 1

    segment_count = 0
    covered = 0
    max_segments = 0
    for node in graph.nodes:
        if node.otype not in NODE_TYPE_ORDER:
            raise ValueError("unrecognized graph node type")
        nodes[node.otype] += 1
        shallow["graph_node_objects"] += getsizeof(node)
        ranges = node.slot_ranges
        if not isinstance(ranges, tuple):
            raise ValueError("node slot range container is not a tuple")
        shallow["node_range_containers"] += getsizeof(ranges)
        n = len(ranges)
        segment_count += n
        if n > max_segments:
            max_segments = n
        cardinality["empty" if n == 0 else (
            "single_segment" if n == 1 else "multiple_segments"
        )] += 1
        for segment in ranges:
            if (not isinstance(segment, tuple) or len(segment) != 2
                or any(type(v) is not int or v <= 0 for v in segment)
                or segment[1] < segment[0]):
                raise ValueError("invalid graph slot range segment")
            shallow["node_range_segment_tuples"] += getsizeof(segment)
            covered += segment[1] - segment[0] + 1
    for edge in graph.edges:
        if edge.kind not in _EDGE_FEATURES:
            raise ValueError("unrecognized graph edge type")
        edges[edge.kind] += 1
        shallow["graph_edge_objects"] += getsizeof(edge)

    return {
        "status": "pass",
        "profile_schema": "graph-storage-shallow-v1",
        "graph_slots": len(graph.slots),
        "graph_nodes": len(graph.nodes),
        "graph_edges": len(graph.edges),
        "nodes_with_ud_supplement": with_ud,
        "node_types": dict(sorted(nodes.items())),
        "edge_types": dict(sorted(edges.items())),
        "range_cardinality": cardinality,
        "range_segments": segment_count,
        "range_covered_slot_occurrences": covered,
        "max_range_segments_on_node": max_segments,
        "shallow_bytes": shallow,
        "measurement_limitation": (
            "Shallow non-unique size estimates, NOT resident RSS or unique "
            "retained heap. Nested tuples can be shared; referent strings, "
            "dictionaries, native TF writer buffers and allocator arenas "
            "are not measured. Do not infer memory savings from these sums."
        ),
    }
