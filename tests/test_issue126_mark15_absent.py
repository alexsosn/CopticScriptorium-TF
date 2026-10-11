"""RED-first source-evidenced MorphGNT verse absence regression (#126).

Edition absence is not a Greek token alignment, an editorial reconstruction,
or a blanket permission to trust forged Coptic source metadata.
"""
from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.nt_reference import (
    morphgnt_verse_is_absent, resolve_coptic_sbl_references,
)
from tests.test_issue113_nt_reference import make_doc


class PinnedMark1528EditionAbsence(unittest.TestCase):
    def test_real_mark1528_reference_with_no_parent_becomes_explicit_absence(self):
        self.assertTrue(morphgnt_verse_is_absent("Mark", 15, 28))
        source = make_doc(
            chapter=15, verse=28, greek="(missing in SBL)",
            include_vid_n=False,
        )
        looked_up = []
        (result,) = resolve_coptic_sbl_references(
            source, lookup=lambda *key: looked_up.append(key) or 101,
        )
        self.assertEqual(result.status, "edition_unavailable")
        self.assertEqual((result.target_book, result.target_chapter, result.target_verse),
                         ("Mark", 15, 28))
        self.assertIsNone(result.target_node)
        self.assertIsNone(result.shared_id)
        self.assertEqual(looked_up, [])

    def test_adjacent_real_mark_verses_still_require_parent_lookup(self):
        self.assertFalse(morphgnt_verse_is_absent("Mark", 15, 27))
        self.assertFalse(morphgnt_verse_is_absent("Mark", 15, 29))
        for verse in (27, 29):
            with self.subTest(verse=verse):
                document = make_doc(chapter=15, verse=verse, include_vid_n=False)
                calls = []
                (item,) = resolve_coptic_sbl_references(
                    document, lookup=lambda *key: calls.append(key) or 12345,
                )
                self.assertEqual(item.status, "reference_candidate")
                self.assertEqual(calls, [("Mark", 15, verse)])
                self.assertIsNotNone(item.shared_id)

    def test_forged_provenance_and_contradictory_source_evidence_do_not_map(self):
        doc = make_doc(chapter=15, verse=28, greek="(missing in SBL)")
        calls = []
        lookup = lambda *key: calls.append(key) or 2
        with self.assertRaisesRegex(ValueError, "source revision"):
            resolve_coptic_sbl_references(
                replace(doc, upstream_commit="untrusted"), lookup=lookup,
            )
        with self.subTest(variant="foreign work"):
            (item,) = resolve_coptic_sbl_references(
                make_doc(chapter=15, verse=28, work="foreign"), lookup=lookup,
            )
            self.assertEqual(item.status, "ambiguous")
        with self.subTest(variant="wrong chapter label"):
            (item,) = resolve_coptic_sbl_references(
                make_doc(chapter=15, verse=28, label_verse=29), lookup=lookup,
            )
            self.assertEqual(item.status, "ambiguous")
        with self.subTest(variant="missing Greek source provenance"):
            (item,) = resolve_coptic_sbl_references(
                make_doc(chapter=15, verse=28, greek_source=""), lookup=lookup,
            )
            self.assertEqual(item.status, "unclassified_source")
        self.assertEqual(calls, [])

    def test_unrelated_missing_verse_does_not_get_edition_absence_status(self):
        self.assertFalse(morphgnt_verse_is_absent("Mark", 15, 30))
        self.assertFalse(morphgnt_verse_is_absent("1_Corinthians", 15, 28))
        source = make_doc(chapter=15, verse=30, include_vid_n=False)
        (item,) = resolve_coptic_sbl_references(source, lookup=lambda *key: None)
        self.assertEqual(item.status, "unresolved")
        self.assertIsNone(item.target_node)
        self.assertIsNone(item.shared_id)

    def test_preexisting_john_edition_absence_policy_is_unchanged(self):
        self.assertTrue(morphgnt_verse_is_absent("John", 7, 53))
        self.assertTrue(morphgnt_verse_is_absent("John", 8, 1))
        self.assertTrue(morphgnt_verse_is_absent("John", 8, 11))
        self.assertFalse(morphgnt_verse_is_absent("John", 8, 12))


if __name__ == "__main__":
    unittest.main()
