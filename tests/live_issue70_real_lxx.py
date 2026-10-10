"""Audit real Coptic OT verse references against the pinned CenterBLC/LXX warp.

A matching reference address is a CANDIDATE, not proof of identical
versification, textual equivalence, or Greek/Coptic word correspondences.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tf.fabric import Fabric
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
SOURCE_ITEMS = (
    ("sahidic.ruth", "sahidic.ruth", "Ruth_02.tt"),
    ("sahidic.jonah", "sahidic.jonah", "Jonah_02.tt"),
    ("bohairic-habakkuk", "bohairic.habakkuk", "bohairic.Habakkuk_02.tt"),
)


def main(coptic_root: Path, lxx_tf: Path) -> None:
    api = Fabric(locations=[str(lxx_tf)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    assert api, "missing pinned LXX native TF data"
    assert api.F.otype.maxSlot == 623693, "unexpected LXX parent word-slot profile"
    assert api.F.otype.maxNode == 685732, "unexpected LXX parent node profile"
    assert len(api.F.otype.s("verse")) == 30371, "unexpected LXX verse schema"

    def lookup(book: str, chapter: int, verse: int) -> int | None:
        # Unlike CATSS-TF's get_span(...,subverse=None), direct verse section
        # lookup cannot hide verses made entirely of labelled subverses.
        node = api.T.nodeFromSection((book, chapter, verse))
        if node is None:
            return None
        assert api.F.otype.v(node) == "verse", (book, chapter, verse, node)
        return node

    for corpus, dataset, record in SOURCE_ITEMS:
        path = f"{corpus}/{dataset}_TT/{record}"
        document = parse_tt_record(
            (coptic_root / path).read_bytes(),
            source_record_id=f"{corpus}/{dataset}:{record[:-3]}",
            source_path=path,
            upstream_repository="CopticScriptorium/corpora",
            upstream_commit=COPTIC_PIN,
        )
        report = resolve_coptic_lxx_references(document, lookup=lookup)
        counts = Counter(item.status for item in report)
        assert report and counts["reference_candidate"], (
            "no exact-reference LXX candidates", path, counts
        )
        assert not counts["ambiguous"], ("contradictory Coptic source markers", path, report)
        # Every candidate is anchored to an existing LXX native verse node.
        for item in report:
            if item.status == "reference_candidate":
                assert item.lxx_node is not None
                assert api.F.otype.v(item.lxx_node) == "verse"
                assert item.shared_id.startswith("CenterBLC/LXX:1935:")
        print(json.dumps({
            "source_record_id": document.source_record_id,
            "source_chapter": document.metadata.get("chapter"),
            "coptic_source_verses": len(report),
            "candidate": counts["reference_candidate"],
            "unresolved": counts["unresolved"],
            "ambiguous": counts["ambiguous"],
            "first_candidate": next((
                {
                    "shared_id": item.shared_id,
                    "lxx_verse_node": item.lxx_node,
                    "coptic_word_count": len(item.source_word_ordinals),
                    "evidence": item.evidence,
                }
                for item in report if item.status == "reference_candidate"
            ), None),
            "unresolved_source_verse_n": [
                item.source_verse_n for item in report if item.status == "unresolved"
            ],
            "status_note": "candidate reference, not certified passage/word alignment",
        }, sort_keys=True))
    print("PASS real pinned Coptic OT verse reference candidates against actual CenterBLC/LXX verses")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue70_real_lxx.py COPTIC_ROOT LXX_TF")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
