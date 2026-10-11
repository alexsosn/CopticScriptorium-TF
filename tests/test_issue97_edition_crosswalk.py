"""RED-first actual-edition contract: 10 Bohairic Zechariah→LXX numbering candidates.

Source-translation-supported numbering only, NOT certified Coptic/Greek lexical alignment.
Real pinned bytes and Greek verse nodes are asserted in separate GitHub Actions CI.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from copticscriptorium_tf.parser import parse_tt_record
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_modules import write_reference_modules
from copticscriptorium_tf.lxx_versification import (
    BOHAIRIC_ZECH_CROSSWALK_VERSION, BOHAIRIC_ZECH_CHAPTER_SHA,
)

SOURCE_COMMIT = "3ac067f1709a0012daf39ea8da2fac79980176a5"


def source_document(chapter: int, verses: tuple[int, ...], *, witness="bohairic", cts=None,
                    meta_book=None, source_commit=SOURCE_COMMIT):
    if witness == "bohairic":
        corpus = dataset = "bohairic.ot"
        record = f"38_Zacharias_{chapter:02d}"
        edition = cts or f"urn:cts:copticLit:ot.zach.bohairic_ed:{chapter:02d}"
    else:
        corpus = dataset = "sahidic.ot"
        record = f"38_Zechariah_{chapter:02d}"
        edition = cts or f"urn:cts:copticLit:ot.zech.coptot:{chapter}"
    book_part = f' book="{meta_book}"' if meta_book else ""
    pieces = [f'<meta document_cts_urn="{edition}" corpus="{corpus}" chapter="{chapter}"{book_part}>']
    for i, v in enumerate(verses, 1):
        pieces.append(
            f'<verse_n verse_n="{v}">'
            f'<norm_group norm_group="w{i}"><norm xml:id="u{i}" '
            f'new_sent="true" func="root" norm="w{i}">w{i}</norm></norm_group>'
        )
    raw = "".join(pieces).encode("utf-8")
    doc = parse_tt_record(
        raw,
        source_record_id=f"{corpus}/{dataset}:{record}",
        source_path=f"{corpus}/{dataset}_TT.zip!{record}.tt",
        upstream_repository="CopticScriptorium/corpora",
        upstream_commit=source_commit,
        packaging="archive",
    )
    if witness == "bohairic" and source_commit == SOURCE_COMMIT:
        return replace(doc, source_sha256=BOHAIRIC_ZECH_CHAPTER_SHA[chapter])
    return doc


class BohairicZechariahEditionCrosswalkTests(unittest.TestCase):
    def test_versioned_two_batched_rules_and_original_coptic_verse_literals(self):
        self.assertEqual(BOHAIRIC_ZECH_CROSSWALK_VERSION, "bohairic-zach-lxx1935-v1")
        for c, source_verses, expected in (
            (1, (18,19,20,21), (1,2,3,4)),
            (2, (1,2,3,4,5,6), (5,6,7,8,9,10)),
        ):
            with self.subTest(source_chapter=c):
                doc = source_document(c, source_verses)
                looked_up = []
                def lookup(b, chapter, verse):
                    looked_up.append((b, chapter, verse))
                    return 700000 + verse
                mappings = resolve_coptic_lxx_references(doc, lookup=lookup)
                self.assertEqual([m.status for m in mappings],
                                 ["versification_candidate"] * len(source_verses))
                self.assertEqual([m.source_verse_n for m in mappings],
                                 [str(v) for v in source_verses])
                self.assertEqual([m.lxx_chapter for m in mappings], [2] * len(source_verses))
                self.assertEqual([m.lxx_verse for m in mappings], list(expected))
                self.assertEqual(looked_up, [("Zech", 2, n) for n in expected])
                for m in mappings:
                    self.assertIn(BOHAIRIC_ZECH_CROSSWALK_VERSION, m.evidence)
                    self.assertIn("not independently verified", m.reason)
                    self.assertEqual(m.shared_id, f"CenterBLC/LXX:1935:Zech:2:{m.lxx_verse}")

    def test_byte_drift_does_not_fall_back_to_false_identically_numbered_candidate(self):
        doc = source_document(2, (1, 2))
        changed = replace(doc, source_sha256="0" * 64)
        calls = []
        got = resolve_coptic_lxx_references(changed, lookup=lambda *key: calls.append(key) or 1)
        self.assertEqual([m.status for m in got], ["ambiguous", "ambiguous"])
        self.assertEqual(calls, [])
        self.assertTrue(all(m.lxx_node is None for m in got))

    def test_future_revision_wrong_edition_and_sahidic_not_shifted(self):
        cases = [
            source_document(2, (1,), witness="sahidic"),
            source_document(2, (1,), cts="urn:cts:copticLit:ot.zach.alternate:02"),
            source_document(2, (1,), source_commit="f" * 40),
            source_document(2, (7,)),
            source_document(1, (17,)),
        ]
        for doc in cases:
            with self.subTest(cts=doc.scholarly_id, verse=doc.words[0].verse_n):
                got = resolve_coptic_lxx_references(doc, lookup=lambda *_: 54)[0]
                self.assertNotEqual(got.status, "versification_candidate")

    def test_unreviewed_bohairic_zechariah_edition_must_not_fall_back_to_number_only(self):
        for chapter, verses in ((1, (18, 19)), (2, (1, 2, 7))):
            doc = source_document(
                chapter, verses,
                cts=f"urn:cts:copticLit:ot.zach.unreviewed_ed:{chapter:02d}",
            )
            calls = []
            got = resolve_coptic_lxx_references(
                doc, lookup=lambda *key: calls.append(key) or 456
            )
            self.assertEqual(
                [m.status for m in got], ["ambiguous"] * len(verses)
            )
            self.assertTrue(all(m.shared_id is None and m.lxx_node is None for m in got))
            self.assertEqual(calls, [], "unknown edition cannot reuse known mismatched Bohairic numbering")

    def test_unreviewed_remaining_bohairic_chapter_2_fails_closed_not_false_same_number(self):
        doc = source_document(2, (7, 8, 9, 10))
        calls = []
        got = resolve_coptic_lxx_references(
            doc, lookup=lambda *args: calls.append(args) or 123
        )
        self.assertEqual([m.status for m in got], ["ambiguous"] * 4)
        self.assertTrue(all(m.shared_id is None and m.lxx_node is None for m in got))
        self.assertEqual(calls, [], "uncertified source numbering must not claim Greek same-address candidates")
        self.assertEqual([m.source_verse_n for m in got], ["7", "8", "9", "10"])

    def test_crosswalk_missing_lxx_target_is_unresolved_not_fabricated(self):
        got = resolve_coptic_lxx_references(
            source_document(1, (18,)), lookup=lambda *key: None
        )[0]
        self.assertEqual(got.status, "unresolved")
        self.assertIsNone(got.lxx_node)
        self.assertIsNone(got.shared_id)

    def test_bilateral_native_modules_accept_explicit_versioned_candidate_status(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "modules"
            write_reference_modules(
                root,
                coptic_ref={1: "CenterBLC/LXX:1935:Zech:2:5"},
                coptic_status={1: "versification_candidate", 2: "unresolved"},
                lxx_ref={680260: "CenterBLC/LXX:1935:Zech:2:5"},
                lxx_count={680260: 1},
            )
            self.assertTrue((root / "coptic/coptic_lxx_ref_id.tf").is_file())
            self.assertIn("versification_candidate",
                          (root / "coptic/coptic_lxx_ref_status.tf").read_text())


if __name__ == "__main__":
    unittest.main()
