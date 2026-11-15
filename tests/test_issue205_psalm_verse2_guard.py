"""RED-first test of the *second* mismatched Bohairic Psalm body verses (#205)."""
from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.lxx_psalm_guard import (
    blocked_same_number_psalm_body, SOURCE_SHA, RULE_ID,
)
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from tests.test_issue203_psalm_guard import source_doc
from tests.test_issue199_psalm_zero import make_doc, norm


class PsalmAdjacentFalseCandidateTests(unittest.TestCase):

    def test_exact_three_source_verse2_references_are_blocked_without_shift(self):
        self.assertEqual(set(SOURCE_SHA), {3, 17, 51})
        for chapter in (3, 17, 51):
            with self.subTest(chapter=chapter):
                doc = source_doc(chapter)
                reason = blocked_same_number_psalm_body(
                    doc, lxx_book="Ps", source_chapter=chapter, source_verse=2
                )
                self.assertIsInstance(reason, str)
                self.assertIn(RULE_ID, reason)
                self.assertIn("verse 2", reason)
                lookups = []
                def greek_lookup(*ref):
                    lookups.append(ref)
                    return 99
                refs = resolve_coptic_lxx_references(doc, lookup=greek_lookup)
                verse2 = [r for r in refs if r.source_verse_n == "2"]
                self.assertEqual(len(verse2), 1)
                ref = verse2[0]
                self.assertEqual(ref.status, "ambiguous")
                self.assertIsNone(ref.shared_id)
                self.assertIsNone(ref.lxx_node)
                self.assertIsNone(ref.lxx_chapter)
                self.assertIsNone(ref.lxx_verse)
                self.assertEqual(ref.source_verse_n, "2")
                self.assertIn(RULE_ID, ref.evidence)
                self.assertNotIn(("Ps", chapter, 2), lookups)

    def test_existing_verse1_guards_are_preserved(self):
        for chapter in (3, 17, 51):
            doc = source_doc(chapter)
            r = next(r for r in resolve_coptic_lxx_references(
                doc, lookup=lambda *_: 99
            ) if r.source_verse_n == "1")
            self.assertEqual(r.status, "ambiguous")
            self.assertIsNone(r.shared_id)
            self.assertIn(RULE_ID, r.evidence)

    def test_original_third_verse_not_assumed_part_of_global_shift(self):
        for chapter in (3, 17, 51):
            body = (
                '<verse_n verse_n="0">' + norm("heading", 1)
                + '<verse_n verse_n="1">' + norm("first", 2)
                + '<verse_n verse_n="2">' + norm("second", 3)
                + '<verse_n verse_n="3">' + norm("third", 4)
            )
            doc = make_doc(chapter=chapter, body=body)
            refs = resolve_coptic_lxx_references(doc, lookup=lambda *_: 77)
            third = next(r for r in refs if r.source_verse_n == "3")
            self.assertEqual(third.status, "reference_candidate")
            self.assertEqual(
                third.shared_id, f"CenterBLC/LXX:1935:Ps:{chapter}:3"
            )
            self.assertIsNone(blocked_same_number_psalm_body(
                doc, lxx_book="Ps", source_chapter=chapter, source_verse=3
            ))

    def test_other_psalms_dialects_and_other_books_unaffected(self):
        for chapter in (1, 149, 151):
            doc = source_doc(chapter)
            ref = next(r for r in resolve_coptic_lxx_references(
                doc, lookup=lambda *_: 99
            ) if r.source_verse_n == "2")
            self.assertEqual(ref.status, "reference_candidate")
        doc = source_doc(17, corpus="sahidic.ot", edition="coptot")
        self.assertIsNone(blocked_same_number_psalm_body(
            doc, lxx_book="Ps", source_chapter=17, source_verse=2
        ))
        doc = source_doc(17)
        self.assertIsNone(blocked_same_number_psalm_body(
            doc, lxx_book="Zech", source_chapter=17, source_verse=2
        ))

    def test_forged_evidence_does_not_revive_same_number_candidate(self):
        doc = source_doc(51)
        for variant in (
            replace(doc, upstream_commit="0" * 40),
            replace(doc, upstream_repository="forged/corpora"),
            replace(doc, source_sha256="0" * 64),
            replace(doc, source_text=doc.source_text + "TAMPERED"),
            replace(doc, source_record_id="bohairic.ot/bohairic.ot:forged"),
            replace(doc, metadata={
                **doc.metadata,
                "document_cts_urn": "urn:cts:copticLit:ot.pss.wrong:51"
            }),
        ):
            with self.subTest(variant=variant.source_record_id):
                reason = blocked_same_number_psalm_body(
                    variant, lxx_book="Ps", source_chapter=51, source_verse=2
                )
                self.assertIsNotNone(reason)
                r = next(r for r in resolve_coptic_lxx_references(
                    variant, lookup=lambda *_: 99
                ) if r.source_verse_n == "2")
                self.assertNotEqual(r.status, "reference_candidate")
                self.assertIsNone(r.shared_id)

    def test_repeated_or_invalid_source_literals_do_not_get_forged_greek_id(self):
        bad = make_doc(
            chapter=3,
            body=(
                '<verse_n verse_n="0">' + norm("title", 1)
                + '<verse_n verse_n="2">' + norm("x", 2)
                + '<verse_n verse_n="2">' + norm("y", 3)
            ),
        )
        refs = resolve_coptic_lxx_references(bad, lookup=lambda *_: 99)
        self.assertTrue(all(r.shared_id is None for r in refs
                            if r.source_verse_n == "2"))

if __name__ == "__main__":
    unittest.main()
