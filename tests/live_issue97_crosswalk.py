"""Live exact-source Bohairic Zechariah → LXX edition-qualified weft acceptance.

Published references remain *versification candidates*, not certified Coptic
↔ Greek translations. Original Coptic verse_n/vid_n/verse_vid untouched.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_modules import (
    LxxModuleError, project_reference_modules, validate_lxx_release,
)
from copticscriptorium_tf.lxx_versification import (
    BOHAIRIC_ZECH_CHAPTER_SHA, BOHAIRIC_ZECH_CROSSWALK_VERSION,
)
from copticscriptorium_tf.writer import write_graph

COPTIC_PIN = "3ac067f1709a0012daf39ea8da2fac79980176a5"
LXX_PIN = "f32a98eddf7eb239aa73ab863d70381e416d5076"


def source_document(upstream: Path, witness: str, chapter: int):
    corpus = "bohairic.ot" if witness == "bohairic" else "sahidic.ot"
    name = f"38_{'Zacharias' if witness == 'bohairic' else 'Zechariah'}_{chapter:02d}.tt"
    archive_rel = f"{corpus}/{corpus}_TT.zip"
    with ZipFile(upstream / archive_rel) as archive:
        members = [m for m in archive.namelist() if m.endswith("/" + name) or m == name]
        if len(members) != 1:
            raise ValueError(f"missing/nonunique actual source record {archive_rel}!{name}: {len(members)}")
        member = members[0]
        raw = archive.read(member)
    return parse_tt_record(
        raw,
        source_record_id=f"{corpus}/{corpus}:{name[:-3]}",
        source_path=f"{archive_rel}!{member}",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=COPTIC_PIN,
        packaging="archive",
    )


def run(upstream: Path, lxx_dir: Path) -> None:
    docs = (
        source_document(upstream, "bohairic", 1),
        source_document(upstream, "bohairic", 2),
        source_document(upstream, "sahidic", 2),  # negative control
    )
    for chapter, doc in enumerate(docs[:2], 1):
        assert doc.source_sha256 == BOHAIRIC_ZECH_CHAPTER_SHA[chapter]
        assert doc.metadata["document_cts_urn"] == (
            f"urn:cts:copticLit:ot.zach.bohairic_ed:{chapter:02d}"
        )

    with TemporaryDirectory(prefix="coptic-lxx-zech97-") as tmp:
        folder = Path(tmp)
        coptic_dir = folder / "coptic"
        write_graph(build_graph(docs), coptic_dir)
        coptic = Fabric(locations=[str(coptic_dir)], silent="deep").load(
            "source_record_id source_word_ordinal source_sha256 norm verse_n",
            silent="deep",
        )
        greek = Fabric(locations=[str(lxx_dir)], silent="deep").load(
            "book chapter verse subverse word orig_order", silent="deep"
        )
        assert coptic and greek
        validate_lxx_release(lxx_dir, greek)

        def greek_verse(book: str, chapter: int, verse: int):
            node = greek.T.nodeFromSection((book, chapter, verse))
            if node is not None:
                assert greek.F.otype.v(node) == "verse"
            return node

        expected_by_source = {
            (1, 18): 1, (1, 19): 2, (1, 20): 3, (1, 21): 4,
            (2, 1): 5, (2, 2): 6, (2, 3): 7,
            (2, 4): 8, (2, 5): 9, (2, 6): 10,
        }
        candidates = []
        for chapter, doc in enumerate(docs[:2], 1):
            refs = resolve_coptic_lxx_references(doc, lookup=greek_verse)
            focus = [r for r in refs if (chapter, int(r.source_verse_n or "0")) in expected_by_source]
            assert len(focus) == (4 if chapter == 1 else 6), (chapter, len(focus))
            if chapter == 2:
                # Real unreviewed remainder must stay visible but unlinked:
                # same-number Greek references exist yet would be misleading.
                unreviewed = [r for r in refs if r.source_verse_n and
                              r.source_verse_n.isascii() and r.source_verse_n.isdecimal()
                              and int(r.source_verse_n) >= 7]
                assert unreviewed, "pinned Bohairic Zech 2 has no boundary-control verses"
                assert all(r.status == "ambiguous" and r.shared_id is None
                           and r.lxx_node is None for r in unreviewed)
            for ref in focus:
                source_verse = int(ref.source_verse_n)
                target = expected_by_source[(chapter, source_verse)]
                assert ref.status == "versification_candidate", ref
                assert ref.evidence.endswith(BOHAIRIC_ZECH_CROSSWALK_VERSION), ref.evidence
                assert (ref.lxx_book, ref.lxx_chapter, ref.lxx_verse) == ("Zech", 2, target)
                assert ref.shared_id == f"CenterBLC/LXX:1935:Zech:2:{target}"
                assert ref.lxx_node == greek_verse("Zech", 2, target)
                candidates.append(ref)
        # The independently numbered Sahidic witness must not be remapped.
        for ref in resolve_coptic_lxx_references(docs[2], lookup=greek_verse):
            assert ref.status != "versification_candidate"

        output = folder / "paired-wefts"
        summary = project_reference_modules(
            docs, coptic_api=coptic, lxx_api=greek,
            lxx_tf_dir=lxx_dir, destination=output,
        )
        assert summary["versification_candidate"] == 10, summary
        assert not any(output.rglob("otype.tf"))
        assert not any(output.rglob("oslots.tf"))
        assert not any(output.rglob("*.json"))
        assert not any(output.rglob("*.tsv"))
        coptic_added = Fabric(
            locations=[str(coptic_dir), str(output / "coptic")], silent="deep"
        ).load("coptic_lxx_ref_id coptic_lxx_ref_status source_record_id verse_n", silent="deep")
        greek_added = Fabric(
            locations=[str(lxx_dir), str(output / "lxx")], silent="deep"
        ).load("coptic_lxx_ref_id coptic_lxx_source_span_count book chapter verse", silent="deep")
        assert coptic_added and greek_added
        assert coptic_added.F.otype.maxSlot == coptic.F.otype.maxSlot
        assert greek_added.F.otype.maxSlot == 623693
        for target in range(1, 11):
            node = greek_added.T.nodeFromSection(("Zech", 2, target))
            assert greek_added.F.coptic_lxx_ref_id.v(node) == f"CenterBLC/LXX:1935:Zech:2:{target}"
        for doc in docs[:2]:
            source_words = [
                n for n in range(1, coptic_added.F.otype.maxSlot + 1)
                if coptic_added.F.source_record_id.v(n) == doc.source_record_id
            ]
            verse_words = [n for n in source_words
                           if coptic_added.F.coptic_lxx_ref_status.v(n) == "versification_candidate"]
            assert verse_words
            assert all(coptic_added.F.verse_n.v(n) is not None for n in verse_words)
            # The source reference remains old (not replaced with Greek 2:5).
            if doc.metadata["chapter"] in {"2", "02"}:
                assert any(coptic_added.F.verse_n.v(n) == "1" and
                           coptic_added.F.coptic_lxx_ref_id.v(n) == "CenterBLC/LXX:1935:Zech:2:5"
                           for n in verse_words)
                raw_tail = [n for n in source_words if
                            (coptic_added.F.verse_n.v(n) or "").isdecimal() and
                            int(coptic_added.F.verse_n.v(n)) >= 7]
                assert raw_tail
                assert all(coptic_added.F.coptic_lxx_ref_status.v(n) == "ambiguous" and
                           coptic_added.F.coptic_lxx_ref_id.v(n) is None
                           for n in raw_tail)
        print(json.dumps({
            "result": "PASS pinned byte-qualified edition-local Bohairic Zechariah crosswalk",
            "status": "ten versification candidates, not verified translation pairs",
            "version": BOHAIRIC_ZECH_CROSSWALK_VERSION,
            "source_chapter_sha256": BOHAIRIC_ZECH_CHAPTER_SHA,
            "coptic_source_documents": len(docs),
            "crosswalk_candidate_source_spans": len(candidates),
            "pinned_greek_target_verses": 10,
            "summary": summary,
            "coptic_git": COPTIC_PIN,
            "lxx_git": LXX_PIN,
        }, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue97_crosswalk.py COPTIC_OT_ROOT LXX_TF")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
