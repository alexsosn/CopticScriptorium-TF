"""Full pinned-corpus gate for issue #14 graph construction."""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import resource
import sys
import time

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from copticscriptorium_tf.graph import build_graph, graph_fingerprint, validate_graph
from copticscriptorium_tf.parser import parse_source_tree

UPSTREAM_REPOSITORY = "CopticScriptorium/corpora"
UPSTREAM_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
EXPECTED_SLOT_COUNT = 2_394_354
EXPECTED_NODE_COUNTS = {
    "document": 2_628,
    "sentence": 78_993,
    "orig_group": 736_574,
    "norm_group": 1_105_458,
    "orig": 1_565_993,
    "page": 3_294,
    "column": 3_291,
    "line": 47_933,
    "entity": 256_677,
    "translation": 52_346,
    "arabic_translation": 1_598,
}
EXPECTED_SAME_SCHOLARLY_CLASSES = {
    "alternate_analysis": 15,
    "byte_identical": 91,
    "core_identical_source_variant": 1,
    "textual_divergence": 1,
}
EXPECTED_DOCUMENTED_OVERLAP_CLASSES = {
    "alternate_analysis": 19,
    "textual_divergence": 17,
}
MIN_EXPECTED_WITNESS_EDGES = 35


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _snapshot(graph, *, seconds: float) -> dict[str, object]:
    node_counts = Counter(node.otype for node in graph.nodes)
    edge_counts = Counter(edge.kind for edge in graph.edges)
    same_scholarly_classes = Counter(
        edge.classification for edge in graph.edges if edge.kind == "same_scholarly"
    )
    documented_overlap_classes = Counter(
        edge.classification for edge in graph.edges if edge.kind == "documented_overlap"
    )
    return {
        "slot_count": len(graph.slots),
        "node_count": len(graph.nodes),
        "node_counts": {key: node_counts[key] for key in sorted(node_counts)},
        "edge_count": len(graph.edges),
        "edge_counts": {key: edge_counts[key] for key in sorted(edge_counts)},
        "same_scholarly_classifications": {
            key: same_scholarly_classes[key] for key in sorted(same_scholarly_classes)
        },
        "documented_overlap_classifications": {
            key: documented_overlap_classes[key] for key in sorted(documented_overlap_classes)
        },
        "node_ranges": [
            {"otype": item.otype, "start": item.start, "end": item.end, "count": item.count}
            for item in graph.node_ranges
        ],
        "fingerprint": graph_fingerprint(graph),
        "validation_errors": list(validate_graph(graph)),
        "build_seconds": round(seconds, 3),
        "peak_rss_mb": round(_rss_mb(), 1),
    }


def build_report(root: Path) -> dict[str, object]:
    parse_started = time.monotonic()
    documents = parse_source_tree(
        root,
        upstream_repository=UPSTREAM_REPOSITORY,
        upstream_commit=UPSTREAM_COMMIT,
    )
    parse_seconds = time.monotonic() - parse_started

    first_started = time.monotonic()
    first = build_graph(documents)
    first_snapshot = _snapshot(first, seconds=time.monotonic() - first_started)
    first_fingerprint = first_snapshot["fingerprint"]
    del first
    gc.collect()

    second_started = time.monotonic()
    second = build_graph(tuple(reversed(documents)))
    second_snapshot = _snapshot(second, seconds=time.monotonic() - second_started)

    return {
        "upstream_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": UPSTREAM_COMMIT,
        "document_count": len(documents),
        "parse_seconds": round(parse_seconds, 3),
        "peak_rss_mb": round(_rss_mb(), 1),
        "first": first_snapshot,
        "second_reversed_input": second_snapshot,
        "deterministic_under_reversed_input": first_fingerprint == second_snapshot["fingerprint"],
    }


def _failures(report: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if report["document_count"] != EXPECTED_NODE_COUNTS["document"]:
        failures.append(
            f"document count: expected {EXPECTED_NODE_COUNTS['document']}, got {report['document_count']}"
        )
    first = report["first"]
    second = report["second_reversed_input"]
    assert isinstance(first, dict) and isinstance(second, dict)
    for label, snapshot in (("first", first), ("second", second)):
        if snapshot["slot_count"] != EXPECTED_SLOT_COUNT:
            failures.append(
                f"{label} slot count: expected {EXPECTED_SLOT_COUNT}, got {snapshot['slot_count']}"
            )
        if snapshot["node_counts"] != EXPECTED_NODE_COUNTS:
            failures.append(
                f"{label} node counts: expected {EXPECTED_NODE_COUNTS}, got {snapshot['node_counts']}"
            )
        if snapshot["same_scholarly_classifications"] != EXPECTED_SAME_SCHOLARLY_CLASSES:
            failures.append(
                f"{label} same-scholarly classes: expected {EXPECTED_SAME_SCHOLARLY_CLASSES}, "
                f"got {snapshot['same_scholarly_classifications']}"
            )
        if snapshot["documented_overlap_classifications"] != EXPECTED_DOCUMENTED_OVERLAP_CLASSES:
            failures.append(
                f"{label} documented-overlap classes: expected {EXPECTED_DOCUMENTED_OVERLAP_CLASSES}, "
                f"got {snapshot['documented_overlap_classifications']}"
            )
        edge_counts = snapshot["edge_counts"]
        assert isinstance(edge_counts, dict)
        if int(edge_counts.get("witness", 0)) < MIN_EXPECTED_WITNESS_EDGES:
            failures.append(
                f"{label} witness edges: expected at least {MIN_EXPECTED_WITNESS_EDGES}, "
                f"got {edge_counts.get('witness', 0)}"
            )
        if snapshot["validation_errors"]:
            failures.append(f"{label} graph validation errors: {snapshot['validation_errors']}")
    if not report["deterministic_under_reversed_input"]:
        failures.append("graph fingerprint changes when physical input order is reversed")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args.upstream)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.validate:
        failures = _failures(report)
        if failures:
            print("\n".join(failures))
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
