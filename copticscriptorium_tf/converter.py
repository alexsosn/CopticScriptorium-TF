"""End-to-end Coptic Scriptorium TT -> native Text-Fabric conversion.

This module deliberately composes the reviewed parser, graph builder, and writer.
It does not independently audit or certify upstream corpus data.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gc
import json
from pathlib import Path
import sys
from time import monotonic
from typing import Any

from .graph import build_graph
from .parser import parse_source_tree
from .writer import write_graph

try:  # Unix reports process high-water RSS; Windows has no stdlib equivalent.
    import resource
except ImportError:  # pragma: no cover - exercised only on non-Unix platforms.
    resource = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ConversionResult:
    """Operational summary for one converter run."""

    source_records: int
    slots: int
    nodes: int
    edges: int
    output_path: Path
    tf_files: int
    tf_bytes: int
    parse_seconds: float
    graph_seconds: float
    write_seconds: float
    peak_rss_mb: float
    missing_license_metadata_source_records: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["output_path"] = str(self.output_path)
        data["missing_license_metadata_source_records"] = list(
            self.missing_license_metadata_source_records
        )
        return data


def _peak_rss_mb() -> float:
    if resource is None:
        return 0.0
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # ru_maxrss is bytes on macOS, KiB on Linux and other BSD-style runners.
    if sys.platform == "darwin":
        return value / (1024.0 * 1024.0)
    return value / 1024.0


def convert_source_tree(
    source_root: Path | str,
    destination: Path | str,
    *,
    upstream_repository: str,
    upstream_commit: str,
) -> ConversionResult:
    """Convert one supported TT source tree to a native local TF dataset.

    The destination must not already exist. Parsing, graph construction, and TF
    writing are delegated to their reviewed components; this function only owns
    orchestration, phase timings, and object lifetime between phases.
    """
    target = Path(destination)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing TF dataset: {target}")

    parse_started = monotonic()
    documents = parse_source_tree(
        source_root,
        upstream_repository=upstream_repository,
        upstream_commit=upstream_commit,
    )
    parse_seconds = monotonic() - parse_started
    source_records = len(documents)
    if not documents:
        raise ValueError(f"no supported TT source records found under {Path(source_root)}")

    # Preserve literal per-document license metadata as TF features. Surface only
    # absence/blank values in the operational report, without assigning an
    # aggregate license or attempting to judge upstream license eligibility.
    # The parser already has the document models: do not reread the source tree.
    missing_license_metadata_source_records = tuple(
        document.source_record_id
        for document in documents
        if not document.metadata.get("license", "").strip()
    )

    graph_started = monotonic()
    graph = build_graph(documents)
    graph_seconds = monotonic() - graph_started
    slots = len(graph.slots)
    nodes = len(graph.nodes)
    edges = len(graph.edges)

    # The graph is self-contained. Do not retain the complete parser model while
    # the writer constructs another large representation for Fabric.save().
    del documents
    gc.collect()

    write_started = monotonic()
    output_path = write_graph(graph, target)
    write_seconds = monotonic() - write_started

    tf_paths = tuple(output_path.glob("*.tf"))
    return ConversionResult(
        source_records=source_records,
        slots=slots,
        nodes=nodes,
        edges=edges,
        output_path=output_path,
        tf_files=len(tf_paths),
        tf_bytes=sum(path.stat().st_size for path in tf_paths),
        parse_seconds=parse_seconds,
        graph_seconds=graph_seconds,
        write_seconds=write_seconds,
        peak_rss_mb=_peak_rss_mb(),
        missing_license_metadata_source_records=missing_license_metadata_source_records,
    )


def _write_summary(path: Path, result: ConversionResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert supported Coptic Scriptorium TT sources to native Text-Fabric."
    )
    parser.add_argument("source_root", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--upstream-repository", required=True)
    parser.add_argument("--upstream-commit", required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)

    try:
        result = convert_source_tree(
            args.source_root,
            args.destination,
            upstream_repository=args.upstream_repository,
            upstream_commit=args.upstream_commit,
        )
        if args.summary is not None:
            _write_summary(args.summary, result)
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(f"conversion failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
