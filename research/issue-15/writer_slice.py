"""Issue #15 pinned, bounded real-TT slice save/reload gate.

This is a converter regression fixture, not a certification of upstream data.
External witness targets are absent from this bounded slice, so document
relations are explicitly omitted rather than treated as complete.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import html
import json
from pathlib import Path
import re
import resource
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import zipfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.writer import write_graph
from tf.fabric import Fabric

UPSTREAM = "CopticScriptorium/corpora"
COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
DIRECT = ("Mark_01.tt", "Mark_02.tt")
ARCHIVE_RECORD = "41_Mark_01.tt"
ORIG_GROUP_SOURCE_RE = re.compile(r'<orig_group\b[^>]*\borig_group="([^"]*)"')


def run(root: Path) -> dict[str, object]:
    began = monotonic()
    docs = []
    raw_mark_01: bytes | None = None
    for filename in DIRECT:
        relative = Path("sahidica.mark/sahidica.mark_TT") / filename
        raw = (root / relative).read_bytes()
        if filename == "Mark_01.tt":
            raw_mark_01 = raw
        docs.append(parse_tt_record(
            raw,
            source_record_id=f"sahidica.mark/sahidica.mark:{filename[:-3]}",
            source_path=relative.as_posix(),
            upstream_repository=UPSTREAM,
            upstream_commit=COMMIT,
            packaging="directory",
        ))
    archive_relative = Path("sahidica.nt/sahidica.nt_TT.zip")
    with zipfile.ZipFile(root / archive_relative) as archive:
        members = [
            member for member in archive.namelist()
            if member.rsplit("/", 1)[-1] == ARCHIVE_RECORD
        ]
        if len(members) != 1:
            raise ValueError(f"expected exactly one {ARCHIVE_RECORD} archive member, got {members!r}")
        member = members[0]
        raw = archive.read(member)
        docs.append(parse_tt_record(
            raw,
            source_record_id="sahidica.nt/sahidica.nt:41_Mark_01",
            source_path=f"{archive_relative.as_posix()}!/{member}",
            upstream_repository=UPSTREAM,
            upstream_commit=COMMIT,
            packaging="archive",
        ))
    expected_words = sum(len(doc.words) for doc in docs)
    if expected_words < 1000:
        raise AssertionError(f"real-source slice unexpectedly small: {expected_words} words")
    # Exclude external witness targets explicitly; focused fixtures cover the
    # relation writer and #16 owns the later full-corpus converter regression.
    graph = build_graph(docs, document_relations=())
    if len(graph.slots) != expected_words or validate_graph(graph):
        raise AssertionError("source/graph slot parity or graph validation failed")
    with TemporaryDirectory() as temporary:
        location = write_graph(graph, Path(temporary) / "tf")
        tf_files = sorted(location.glob("*.tf"))
        if not tf_files:
            raise AssertionError("writer produced no TF files")
        tf_feature_names = {path.stem for path in tf_files}
        forbidden = {name for name in tf_feature_names if name.endswith("_json")}
        if forbidden:
            raise AssertionError(f"writer emitted structural JSON features: {sorted(forbidden)!r}")
        api = Fabric(locations=[str(location)], silent="deep").load(
            "source_record_id scholarly_id norm lemma pos source_sha256 source_path corpus dataset "
            "dependency_head entity_head meta_document_cts_urn meta_license",
            silent="deep",
        )
        if api is False or api is None:
            raise AssertionError("real Text-Fabric reload failed")
        if api.F.otype.maxSlot != expected_words:
            raise AssertionError("real TF slot count differs from source TT norms")
        if api.F.otype.maxNode != expected_words + len(graph.nodes):
            raise AssertionError("real TF node count differs from graph")
        for doc in docs:
            document_nodes = [n for n in graph.nodes if n.otype == "document" and n.source_record_id == doc.source_record_id]
            if len(document_nodes) != 1:
                raise AssertionError(f"document not uniquely represented: {doc.source_record_id}")
            node = document_nodes[0]
            if api.T.nodeFromSection((doc.source_record_id,)) != node.id:
                raise AssertionError(f"section address lost: {doc.source_record_id}")
            if api.F.source_sha256.v(node.id) != doc.source_sha256:
                raise AssertionError(f"source hash lost: {doc.source_record_id}")
            if api.F.source_path.v(node.id) != doc.source_path:
                raise AssertionError(f"record source path lost: {doc.source_record_id}")
            if doc.metadata.get("document_cts_urn") is not None:
                if api.F.meta_document_cts_urn.v(node.id) != doc.metadata["document_cts_urn"]:
                    raise AssertionError(f"document CTS metadata lost: {doc.source_record_id}")
            if doc.metadata.get("license") is not None:
                if api.F.meta_license.v(node.id) != doc.metadata["license"]:
                    raise AssertionError(f"license metadata literal altered: {doc.source_record_id}")
        for slot in graph.slots:
            if api.F.norm.v(slot.id) != slot.norm:
                raise AssertionError(f"normalized word altered at slot {slot.id}")
        for edge in graph.edges:
            if edge.kind in {"dependency_head", "entity_head"}:
                if edge.target not in api.E.__getattribute__(edge.kind).f(edge.source):
                    raise AssertionError(f"lost {edge.kind} edge {edge.source}->{edge.target}")

        # Independent evidence for this rendering regression only: extract three
        # diplomatic group literals from the raw TT record, not parser helpers.
        if raw_mark_01 is None:
            raise AssertionError("Mark_01 raw evidence is missing")
        original_groups = [
            html.unescape(value)
            for value in ORIG_GROUP_SOURCE_RE.findall(raw_mark_01.decode("utf-8"))[:3]
        ]
        if len(original_groups) != 3:
            raise AssertionError("cannot extract three original groups from regression fixture")
        mark = next(node for node in graph.nodes if node.otype == "document" and node.source_record_id == "sahidica.mark/sahidica.mark:Mark_01")
        expected_diplomatic_prefix = " ".join(original_groups) + " "
        diplomatic = api.T.text(mark.id, fmt="text-diplomatic-full")
        normalized = api.T.text(mark.id, fmt="text-orig-full")
        if not diplomatic.startswith(expected_diplomatic_prefix):
            raise AssertionError(
                f"real diplomatic prefix mismatch: expected {expected_diplomatic_prefix!r}, "
                f"got {diplomatic[:len(expected_diplomatic_prefix) + 12]!r}"
            )
        if diplomatic == normalized:
            raise AssertionError("diplomatic text unexpectedly identical to normalized text")

        stats = {
            "source_records": len(docs),
            "source_words": expected_words,
            "tf_slots": api.F.otype.maxSlot,
            "tf_nodes": api.F.otype.maxNode,
            "tf_edge_counts": {kind: sum(edge.kind == kind for edge in graph.edges) for kind in ("dependency_head", "entity_head")},
            "native_metadata_features_checked": 2,
            "diplomatic_groups_checked": len(original_groups),
            "tf_files": len(tf_files),
            "tf_total_bytes": sum(path.stat().st_size for path in tf_files),
            "output_sha256": sha256(b"".join(path.read_bytes() for path in tf_files)).hexdigest(),
            "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1),
            "wall_seconds": round(monotonic() - began, 3),
            "relations_policy": "omitted explicitly from bounded slice; full-corpus converter regression belongs to issue 16",
        }
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.upstream)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
