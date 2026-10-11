"""RED-first reviewed Mark 15:28 edition absence: no fabricated Greek node."""
from dataclasses import replace
import unittest

from test_issue113_nt_reference import make_doc
from copticscriptorium_tf.nt_reference import (
    MORPHGNT_ABSENT, morphgnt_verse_is_absent, resolve_coptic_sbl_references,
)


class Mark15MissingVerse(unittest.TestCase):
    def test_explicit_mark1528_absence_does_not_call_greek_lookup(self):
        d = make_doc(book="Mark", work="mark", code="41N", chapter=15, verse=28,
                     include_vid_n=False)
        calls = []
        r, = resolve_coptic_sbl_references(
            d, lookup=lambda *ref: calls.append(ref) or 900001
        )
        self.assertTrue(morphgnt_verse_is_absent("Mark", 15, 28))
        self.assertEqual(r.status, "edition_unavailable")
        self.assertEqual(r.target_book, "Mark")
        self.assertEqual((r.target_chapter, r.target_verse), (15, 28))
        self.assertIsNone(r.target_node)
        self.assertIsNone(r.shared_id)
        self.assertEqual(calls, [])
        self.assertEqual(r.reason, "verse absent from pinned MorphGNT edition")

    def test_neighbors_27_29_can_retain_actual_verse_candidates(self):
        self.assertFalse(morphgnt_verse_is_absent("Mark", 15, 27))
        self.assertFalse(morphgnt_verse_is_absent("Mark", 15, 29))
        for verse in (27, 29):
            with self.subTest(verse=verse):
                d = make_doc(chapter=15, verse=verse, include_vid_n=False)
                r, = resolve_coptic_sbl_references(d, lookup=lambda *ref: 912345)
                self.assertEqual(r.status, "reference_candidate")
                self.assertEqual(r.target_verse, verse)
                self.assertEqual(r.target_node, 912345)

    def test_other_missing_mark_verse_remains_unresolved(self):
        self.assertFalse(morphgnt_verse_is_absent("Mark", 15, 30))
        d = make_doc(chapter=15, verse=30, include_vid_n=False)
        r, = resolve_coptic_sbl_references(d, lookup=lambda *ref: None)
        self.assertEqual(r.status, "unresolved")
        self.assertIsNone(r.target_node)

    def test_wrong_work_editor_or_source_provenance_is_not_absence(self):
        d = make_doc(chapter=15, verse=28, include_vid_n=False)
        cases = (
            replace(d, metadata={**d.metadata, "Greek_source": ""}),
            make_doc(chapter=15, verse=28, label_verse=27, include_vid_n=False),
            make_doc(chapter=15, verse=28, work="john", include_vid_n=False),
            replace(d, metadata_duplicates={**d.metadata_duplicates,
                                             "chapter": ("15", "16")}),
        )
        for altered in cases:
            with self.subTest(meta=altered.metadata, duplicate=altered.metadata_duplicates):
                r, = resolve_coptic_sbl_references(altered, lookup=lambda *ref: None)
                self.assertNotEqual(r.status, "edition_unavailable")
                self.assertIsNone(r.target_node)
                self.assertIsNone(r.shared_id)

    def test_no_complete_coptic_word_is_still_unresolved_not_edition_absent(self):
        d = make_doc(chapter=15, verse=28, include_vid_n=False)
        anno = replace(d.sbl_annotations[0], word_ordinals=())
        r, = resolve_coptic_sbl_references(
            replace(d, sbl_annotations=(anno,)),
            lookup=lambda *ref: None,
        )
        self.assertEqual(r.status, "unresolved")

    def test_other_explicit_edition_absences_untouched(self):
        self.assertTrue(morphgnt_verse_is_absent("John", 7, 53))
        self.assertTrue(morphgnt_verse_is_absent("John", 8, 1))
        self.assertTrue(morphgnt_verse_is_absent("John", 8, 11))
        self.assertFalse(morphgnt_verse_is_absent("John", 8, 12))
        self.assertEqual(len(MORPHGNT_ABSENT), 13)


if __name__ == "__main__":
    unittest.main()
