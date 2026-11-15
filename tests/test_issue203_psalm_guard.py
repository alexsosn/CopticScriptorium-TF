"""RED-first narrowly scoped source-byte Psalm1 false-positive guard tests (#203)."""
from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.lxx_psalm_guard import (
    blocked_same_number_psalm_verse1, SOURCE_SHA,
    RULE_ID,
)
from copticscriptorium_tf.lxx_reference import resolve_coptic_lxx_references
from tests.test_issue199_psalm_zero import make_doc, norm


def source_doc(chapter: int, *, corpus="bohairic.ot", edition="bohairic_ed",
               source_commit=None):
    return make_doc(
        chapter=chapter, corpus=corpus, edition=edition,
        source_commit=source_commit or "3ac067f1709a0012daf39ea8da2fac79980176a5",
        body=(
            '<verse_n verse_n="0">' + norm("source-title", 1) +
            '<verse_n verse_n="1">' + norm("source-body", 2) +
            '<verse_n verse_n="2">' + norm("next-body", 3)
        ),
    )


class PsalmFirstBodyGuardTests(unittest.TestCase):
    def test_three_exact_source_psalm_chapters_are_protected(self):
        self.assertEqual(set(SOURCE_SHA), {3, 17, 51})
        for chapter in SOURCE_SHA:
            with self.subTest(chapter=chapter):
                doc = source_doc(chapter)
                reason = blocked_same_number_psalm_verse1(
                    doc, lxx_book="Ps", source_chapter=chapter, source_verse=1
                )
                self.assertIsInstance(reason, str)
                self.assertIn(RULE_ID, reason)
                self.assertIn("sha", reason.lower())

    def test_unaffected_psalms_sources_and_verse_two_never_blocked(self):
        for chapter in (1, 149, 151):
            self.assertIsNone(blocked_same_number_psalm_verse1(
                source_doc(chapter), lxx_book="Ps",
                source_chapter=chapter, source_verse=1,
            ))
        self.assertIsNone(blocked_same_number_psalm_verse1(
            source_doc(17), lxx_book="Ps", source_chapter=17, source_verse=2
        ))
        self.assertIsNone(blocked_same_number_psalm_verse1(
            source_doc(17), lxx_book="Zech", source_chapter=17, source_verse=1
        ))
        self.assertIsNone(blocked_same_number_psalm_verse1(
            source_doc(3, corpus="sahidic.ot", edition="coptot"),
            lxx_book="Ps", source_chapter=3, source_verse=1,
        ))

    def test_source_drift_never_restores_numeric_candidate(self):
        doc = source_doc(17)
        for forged in (
            replace(doc, upstream_commit="0" * 40),
            replace(doc, upstream_repository="wrong/repo"),
            replace(doc, source_sha256=SOURCE_SHA[17]),
            replace(doc, source_record_id="bohairic.ot/bohairic.ot:forged"),
            replace(doc, metadata={**doc.metadata,
                "document_cts_urn": "urn:cts:copticLit:ot.pss.bohairic_ed:18"}),
        ):
            with self.subTest(forged=forged.source_record_id):
                reason = blocked_same_number_psalm_verse1(
                    forged, lxx_book="Ps", source_chapter=17, source_verse=1,
                )
                self.assertIsInstance(reason, str)
                self.assertIn("sha|source|revision".split("|")[0], reason.lower())

    def test_resolver_existing_equal_number_candidate_is_blocked_not_shifted(self):
        doc = source_doc(17)
        calls = []
        def lookup(book, ch, verse):
            calls.append((book, ch, verse))
            return 99
        refs = resolve_coptic_lxx_references(doc, lookup=lookup)
        verse1 = [ref for ref in refs if ref.source_verse_n == "1"]
        self.assertEqual(len(verse1), 1)
        ref = verse1[0]
        self.assertEqual(ref.status, "ambiguous")
        self.assertIsNone(ref.shared_id)
        self.assertIsNone(ref.lxx_node)
        self.assertIsNone(ref.lxx_chapter)
        self.assertIsNone(ref.lxx_verse)
        self.assertEqual(ref.source_verse_n, "1")
        self.assertIn(RULE_ID, ref.evidence)
        self.assertNotIn(("Ps", 17, 1), calls)

    def test_resolver_unrelated_psalm_references_still_map_as_candidates(self):
        for chapter in (1, 149, 151):
            doc = source_doc(chapter)
            refs = resolve_coptic_lxx_references(doc, lookup=lambda *args: 55)
            verse1 = next(r for r in refs if r.source_verse_n == "1")
            self.assertEqual(verse1.status, "reference_candidate")
            self.assertEqual(
                verse1.shared_id, f"CenterBLC/LXX:1935:Ps:{chapter}:1"
            )
        doc = source_doc(17)
        refs = resolve_coptic_lxx_references(doc, lookup=lambda *args: 55)
        verse2 = next(r for r in refs if r.source_verse_n == "2")
        # Issue #205 independently established this adjacent false
        # same-number source2 -> Greek title/previous-body reference.
        self.assertEqual(verse2.status, "ambiguous")
        self.assertIsNone(verse2.shared_id)
        self.assertIn(RULE_ID, verse2.evidence)

    def test_guard_only_follows_valid_corpus_cts_and_no_bohairic_zechariah(self):
        d = source_doc(3)
        self.assertIsNone(blocked_same_number_psalm_verse1(
            replace(d, source_record_id="sahidic.ot/sahidic.ot:19_Psalmi_003",
                corpus="sahidic.ot", dataset="sahidic.ot"),
            lxx_book="Ps", source_chapter=3, source_verse=1,
        ))


if __name__ == "__main__":
    unittest.main()
