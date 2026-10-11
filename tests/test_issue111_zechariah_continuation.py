"""RED-first: seven real-evidence-supported Bohairic Zechariah references, one batch.

The live test reads the actual pinned 38_Zacharias_02.tt + Greek parent.
Pure tests isolate edition/byte isolation and no false same-number fallback.
"""
from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from copticscriptorium_tf.lxx_versification import (
    BOHAIRIC_ZECH_CROSSWALK_VERSION,
)
from tests.test_issue97_edition_crosswalk import source_document


class BohairicZechContinuationTests(unittest.TestCase):
    def test_seven_source_references_become_seven_versioned_shifted_candidates(self):
        doc = source_document(2, tuple(range(7, 14)))
        called = []
        def greek(book, chapter, verse):
            called.append((book, chapter, verse))
            return 680000 + verse
        rows = resolve_coptic_lxx_references(doc, lookup=greek)
        self.assertEqual(BOHAIRIC_ZECH_CROSSWALK_VERSION, "bohairic-zach-lxx1935-v2")
        self.assertEqual([r.source_verse_n for r in rows], [str(n) for n in range(7, 14)])
        self.assertEqual([r.status for r in rows], ["versification_candidate"] * 7)
        self.assertEqual([r.lxx_chapter for r in rows], [2] * 7)
        self.assertEqual([r.lxx_verse for r in rows], list(range(11, 18)))
        self.assertEqual(called, [("Zech", 2, n) for n in range(11, 18)])
        for n, row in zip(range(11, 18), rows):
            self.assertEqual(row.shared_id, f"CenterBLC/LXX:1935:Zech:2:{n}")
            self.assertIn(BOHAIRIC_ZECH_CROSSWALK_VERSION, row.evidence)
            self.assertIn("not independently verified", row.reason)

    def test_unreviewed_higher_verses_stay_quarantined_without_lookup(self):
        doc = source_document(2, (14, 15, 16))
        called = []
        rows = resolve_coptic_lxx_references(
            doc, lookup=lambda *args: called.append(args) or 42
        )
        self.assertEqual([r.status for r in rows], ["ambiguous"] * 3)
        self.assertEqual(called, [])
        self.assertTrue(all(r.lxx_node is None and r.shared_id is None for r in rows))

    def test_false_same_number_and_wrong_source_are_rejected(self):
        source = source_document(2, (7, 8, 13))
        for changed in (
            replace(source, source_sha256="e" * 64),
            replace(source, upstream_commit="f" * 40),
            replace(source, source_record_id="bohairic.ot/bohairic.ot:forged"),
            source_document(2, (7, 8, 13), cts="urn:cts:copticLit:ot.zach.other_ed:02"),
            source_document(2, (7, 8, 13), witness="sahidic"),
        ):
            with self.subTest(source=changed.source_record_id, cts=changed.scholarly_id):
                called = []
                result = resolve_coptic_lxx_references(
                    changed, lookup=lambda *key: called.append(key) or 9
                )
                self.assertTrue(all(r.status != "versification_candidate" for r in result))
                if changed.corpus == "bohairic.ot":
                    self.assertEqual(called, [],
                                     "altered Bohairic 2:7..13 must not fall back to false same-number LXX")

    def test_missing_real_greek_address_does_not_become_a_positive_candidate(self):
        doc = source_document(2, (7,))
        rows = resolve_coptic_lxx_references(doc, lookup=lambda *args: None)
        self.assertEqual(rows[0].status, "unresolved")
        self.assertIsNone(rows[0].shared_id)
        self.assertIsNone(rows[0].lxx_node)


if __name__ == "__main__":
    unittest.main()
