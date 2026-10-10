"""Live pinned multi-book Coptic OT ZIP → real Greek verse candidate audit.

Do not infer textual equality, Greek/Coptic word alignment or exact
versification from reference-address coincidences.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.graph import build_graph
from copticscriptorium_tf.writer import write_graph
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_module import (
    LXX_PIN, materialize_lxx_reference_modules, verify_coptic_module_parent,
)
from tf.fabric import Fabric

COPTIC_REV = "3ac067f1709a0012daf39ea8da2fac79980176a5"
# Exact member paths measured by #77's full pinned real metadata work census.
EXAMPLES = (
    ("bohairic.ot", "01_Genesis_01.tt", "Gen", "candidate"),
    ("bohairic.ot", "19_Psalmi_001.tt", "Ps", "candidate"),
    ("bohairic.ot", "38_Zacharias_01.tt", "Zech", "candidate"),
    ("sahidic.ot", "21_Ecclesiastes_01.tt", "Qoh", "candidate"),
    ("sahidic.ot", "22_Song_of_Solomon_01.tt", "Cant", "candidate"),
    ("sahidic.ot", "75_Susanna_01.tt", None, "unclassified"),
    ("sahidic.ot", "67_Tobit_01.tt", None, "unclassified"),
)


def main(coptic_root: Path, lxx_path: Path) -> None:
    api = Fabric(locations=[str(lxx_path)], silent="deep").load(
        "book chapter verse subverse word orig_order", silent="deep"
    )
    assert api, "missing pinned real CenterBLC/LXX"
    assert api.F.otype.maxSlot == 623693
    assert api.F.otype.maxNode == 685732
    assert len(api.F.otype.s("verse")) == 30371

    archive_cache: dict[str, ZipFile] = {}
    documents = []
    try:
        for family, member, expected_book, category in EXAMPLES:
            zfile = archive_cache.get(family)
            if zfile is None:
                zfile = ZipFile(coptic_root / family / f"{family}_TT.zip")
                archive_cache[family] = zfile
            raw = zfile.read(member)
            doc = parse_tt_record(
                raw,
                source_record_id=f"{family}/{family}:{Path(member).stem}",
                source_path=f"{family}/{family}_TT.zip!{member}",
                upstream_repository="CopticScriptorium/corpora",
                upstream_commit=COPTIC_REV,
                packaging="archive",
            )
            documents.append(doc)
            looked_up: list[tuple[str, int, int]] = []

            def lookup(book: str, chapter: int, verse: int) -> int | None:
                looked_up.append((book, chapter, verse))
                node = api.T.nodeFromSection((book, chapter, verse))
                if node is not None:
                    assert api.F.otype.v(node) == "verse"
                return node

            rows = resolve_coptic_lxx_references(doc, lookup=lookup)
            counts = Counter(row.status for row in rows)
            if category == "candidate":
                assert expected_book is not None
                assert looked_up, f"no actual parent lookup in {member}: {counts}"
                assert all(key[0] == expected_book for key in looked_up), looked_up
                assert counts["reference_candidate"] > 0, (member, counts)
                assert all(
                    row.lxx_book == expected_book
                    for row in rows if row.status == "reference_candidate"
                )
            else:
                assert not looked_up, f"ambiguous edition wrongly resolved: {member}"
                assert not counts["reference_candidate"], member
                assert counts["unclassified_corpus"] > 0, (member, counts)

            print(json.dumps({
                "source_member": f"{family}_TT.zip!{member}",
                "source_cts_work": doc.metadata.get("document_cts_urn"),
                "source_chapter": doc.metadata.get("chapter"),
                "source_words": len(doc.words),
                "verse_groups": len(rows),
                "target_book_candidate": expected_book,
                "source_reference_statuses": dict(counts),
                "actual_lxx_address_lookups": len(looked_up),
                "unresolved_source_verses": [
                    row.source_verse_n for row in rows if row.status != "reference_candidate"
                ][:12],
                "status": "candidate addresses only, not textual/word equivalence",
            }, sort_keys=True), flush=True)
    finally:
        for zfile in archive_cache.values():
            zfile.close()
    # Prove that the expanded candidate resolver integrates with BOTH actual
    # native parent warps; raw word/verse counts and parent IDs must not cross.
    with TemporaryDirectory(prefix="coptic-batch-lxx-") as tmp:
        root = Path(tmp)
        coptic_tf = root / "coptic-parent"
        write_graph(build_graph(documents), coptic_tf)
        coptic_api = Fabric(locations=[str(coptic_tf)], silent="deep").load(
            "source_record_id source_word_ordinal", silent="deep"
        )
        assert coptic_api
        pair = root / "modules"
        summary = materialize_lxx_reference_modules(
            documents=documents, coptic_api=coptic_api, lxx_api=api,
            output_root=pair, lxx_parent_commit=LXX_PIN,
            coptic_source_commit=COPTIC_REV,
            coptic_parent_tf=coptic_tf, lxx_parent_tf=lxx_path,
        )
        assert summary.source_documents == len(EXAMPLES)
        assert summary.coptic_status_words == sum(len(doc.words) for doc in documents)
        assert summary.lxx_candidate_verses > 0
        verify_coptic_module_parent(pair / "coptic", coptic_tf)
        fresh_coptic = Fabric(
            locations=[str(coptic_tf), str(pair / "coptic")], silent="deep"
        ).load(
            "source_record_id source_word_ordinal coptic_lxx_ref_id "
            "coptic_lxx_ref_status", silent="deep"
        )
        fresh_greek = Fabric(
            locations=[str(lxx_path), str(pair / "lxx")], silent="deep"
        ).load("coptic_lxx_ref_id", silent="deep")
        assert fresh_coptic and fresh_greek
        assert fresh_coptic.F.otype.maxSlot == sum(len(doc.words) for doc in documents)
        assert fresh_greek.F.otype.maxSlot == 623693
        coptic_keys = {
            fresh_coptic.F.coptic_lxx_ref_id.v(word)
            for word in fresh_coptic.F.otype.s("word")
            if fresh_coptic.F.coptic_lxx_ref_id.v(word)
        }
        greek_keys = {
            fresh_greek.F.coptic_lxx_ref_id.v(verse)
            for verse in fresh_greek.F.otype.s("verse")
            if fresh_greek.F.coptic_lxx_ref_id.v(verse)
        }
        assert set(coptic_keys) == set(greek_keys)
        assert len(greek_keys) == summary.lxx_candidate_verses
        for word in fresh_coptic.F.otype.s("word"):
            status = fresh_coptic.F.coptic_lxx_ref_status.v(word)
            assert status is not None
            if status != "reference_candidate":
                assert fresh_coptic.F.coptic_lxx_ref_id.v(word) is None
        assert any(key.startswith("CenterBLC/LXX:1935:Gen:") for key in greek_keys)
        assert any(key.startswith("CenterBLC/LXX:1935:Ps:") for key in greek_keys)
        print(json.dumps({
            "stage": "real-multi-book-dual-native-tf-modules",
            "source_documents": summary.source_documents,
            "coptic_words": summary.coptic_status_words,
            "coptic_candidate_words": summary.coptic_candidate_words,
            "distinct_greek_verse_nodes": summary.lxx_candidate_verses,
            "scope": "real address candidates only, NOT textual equivalence",
        }, sort_keys=True), flush=True)
    print("PASS real pinned multi-book Coptic OT ZIP source/edition candidate gates", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python tests/live_issue78_cts_aliases.py COPTIC_ROOT LXX_TF")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
