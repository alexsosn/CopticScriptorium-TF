"""Live pinned-SCRIPTORIUM SBL annotation conservation: no Greek corpus redistribution."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph, validate_graph
from copticscriptorium_tf.writer import write_graph

COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SOURCES = (
    ("sahidica.mark/sahidica.mark:Mark_02",
     "sahidica.mark/sahidica.mark_TT/Mark_02.tt"),
    ("sahidica.mark/sahidica.mark:Mark_16",
     "sahidica.mark/sahidica.mark_TT/Mark_16.tt"),
)


def audit(root: Path, output: Path) -> dict:
    from tf.fabric import Fabric

    documents = []
    raw_counts = Counter()
    for record, relpath in SOURCES:
        path = root / relpath
        if not path.is_file():
            raise ValueError(f"missing pinned source file: {relpath}")
        doc = parse_tt_record(path.read_bytes(), source_record_id=record,
            source_path=relpath, upstream_repository="CopticScriptorium/corpora",
            upstream_commit=COMMIT)
        documents.append(doc)
        for annotation in doc.sbl_annotations:
            raw_counts[annotation.kind] += 1
        # A known real source must not become an empty sample silently.
        if not any(a.kind == "sbl_greek" for a in doc.sbl_annotations):
            raise ValueError(f"no source sbl_greek annotations in {record}")
    graph = build_graph(documents)
    if errors := validate_graph(graph):
        raise ValueError("bad SBL native graph: " + "; ".join(errors[:4]))
    write_graph(graph, output)
    api = Fabric(locations=[str(output)], silent="deep").load(
        "value source_record_id render_mode sbl_verse_n "
        "start_after_word_ordinal end_after_word_ordinal", silent="deep")
    if not api:
        raise ValueError("native TF did not reload")
    for kind in ("sbl_greek", "sbl_apparatus"):
        expected = {
            (doc.source_record_id, kind, a.ordinal): a
            for doc in documents for a in doc.sbl_annotations if a.kind == kind
        }
        nodes = tuple(api.F.otype.s(kind))
        if len(nodes) != len(expected):
            raise ValueError(f"source/native SBL count mismatch for {kind}")
        for node in nodes:
            record = api.F.source_record_id.v(node)
            ordinal = next((n.source_ordinal for n in graph.nodes if n.id == node), None)
            ref = (record, kind, ordinal)
            if ref not in expected:
                raise ValueError(f"unpaired native source SBL occurrence: {ref}")
            annotation = expected[ref]
            if api.F.value.v(node) != annotation.value:
                raise ValueError(f"SBL literal changed at {record} occurrence {ordinal}")
            if api.F.render_mode.v(node) not in {"sbl_anchor", "sbl_span"}:
                raise ValueError(f"SBL annotation lacks span/anchor mode at {ref}")
            if api.F.sbl_verse_n.v(node) != annotation.source_verse_n:
                raise ValueError(f"SBL annotation verse scope changed at {ref}")
    return {
        "source_records": len(documents),
        "word_slots": len(graph.slots),
        "source_occurrences": dict(raw_counts),
        "native_occurrences": {kind: len(api.F.otype.s(kind)) for kind in ("sbl_greek","sbl_apparatus")},
        "status": "pass",
        "scope": "Pinned Mark chapters 2 and 16 only; no Coptic-to-Greek word alignment",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source_root", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(audit(args.source_root, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
