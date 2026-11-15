"""RED-first contracts for source-evidence Psalm0/LXX1-2 boundary diagnoses (#201)."""
from __future__ import annotations

from dataclasses import replace
import unittest

from copticscriptorium_tf.psalm_boundary_crosscheck import (
    classify_psalm_boundary, inspect_selected_psalm, SELECTED_SOURCE_SHA,
    PsalmBoundaryReview,
)
from tests.test_issue199_psalm_zero import make_doc, norm


def gverses(chapter, verse):
    if chapter == 17:
        return {
            1: ("εἰς", "τὸ", "τέλος", "Σαουλ"),
            2: ("καὶ", "εἶπεν", "ἀγαπήσω", "σε", "κύριε"),
        }[verse]
    if chapter == 149:
        return {1: ("Ἀλληλούϊα", "Ἄσατε", "τῷ", "κυρίῳ"),
                2: ("εὐφρανθήτω", "Ισραηλ")}[verse]
    if chapter == 1:
        return {1: ("Μακάριος", "ἀνήρ"), 2: ("ἀλλ’", "ἐν")}[verse]
    if chapter == 3:
        return {1: ("Ψαλμὸς", "τῷ", "Δαυιδ", "Αβεσσαλωμ"),
                2: ("Κύριε", "τί", "ἐπληθύνθησαν")}[verse]
    if chapter == 51:
        return {1: ("Εἰς", "τὸ", "τέλος", "συνέσεως", "τῷ", "Δαυιδ"),
                2: ("ἐν", "τῷ", "ἐλθεῖν", "Δωηκ", "Αβιμελεχ")}[verse]
    return {1: ("ψαλμὸς", "τῷ", "Δαυιδ"), 2: ("κύριε", "τί")}[verse]


class PsalmBoundaryEvidenceTest(unittest.TestCase):
    def test_psalm_one_ellipsis_is_editorial_and_never_greek_word_mapping(self):
        r = classify_psalm_boundary(
            1, ("...",), ("ⲟⲩ", "ⲙⲁⲕⲁⲣⲓⲟⲥ"),
            gverses(1, 1), gverses(1, 2),
        )
        self.assertEqual(r["status"], "source_literal_ellipsis_no_greek_lexeme")
        self.assertFalse(r["greek_reference_verified"])
        self.assertTrue(r["source_ellipsis"])
        self.assertFalse(r["source0_to_greek_verse_whole"])

    def test_psalm_seventeen_meets_cross_greek_verse_anchor_not_global_shift(self):
        r = classify_psalm_boundary(
            17, ("ⲉ", "ⲡ", "ⲇⲁⲩⲓⲇ", "ⲟⲩⲟϩ", "ⲡⲉϫⲁ", "ϥ"),
            ("ϯ", "ⲛⲁ", "ⲙⲉⲛⲣⲓⲧ"),
            gverses(17, 1), gverses(17, 2),
        )
        self.assertEqual(r["status"], "cross_greek_verse_boundary_candidate")
        self.assertTrue(r["coptic_and_said_at_zero_end"])
        self.assertTrue(r["greek_and_said_at_verse_two_start"])
        self.assertFalse(r["source0_to_greek_verse_whole"])
        self.assertFalse(r["greek_reference_verified"])

    def test_psalm_seventeen_adversarial_wrong_greek_start_is_unverified(self):
        r = classify_psalm_boundary(
            17, ("ⲟⲩⲟϩ", "ⲡⲉϫⲁ", "ϥ"), ("ϯ",),
            gverses(17, 1), ("ἀγαπήσω", "καὶ", "εἶπεν"),
        )
        self.assertEqual(r["status"], "needs_primary_collation")
        r2 = classify_psalm_boundary(
            17, ("ⲥⲁⲟⲩⲗ", "ⲡⲉϫⲁ", "ϥ"), ("ϯ",),
            gverses(17, 1), gverses(17, 2),
        )
        self.assertEqual(r2["status"], "needs_primary_collation")

    def test_psalm_149_hallelujah_is_inside_first_greek_verse(self):
        r = classify_psalm_boundary(
            149, ("ⲁⲗⲗⲏⲗⲟⲩⲓⲁ",), ("ϫⲱ", "ⲙ", "ⲡ", "ϭⲟⲓⲥ"),
            gverses(149, 1), gverses(149, 2),
        )
        self.assertEqual(r["status"], "within_first_greek_verse_candidate")
        self.assertTrue(r["source_hallelujah"])
        self.assertTrue(r["greek_verse_one_begins_hallelujah"])
        self.assertFalse(r["source0_to_greek_verse_whole"])

    def test_psalm_three_first_greek_verse_is_named_title_candidate(self):
        r = classify_psalm_boundary(
            3, ("ⲛⲧⲉ", "ⲇⲁⲩⲓⲇ", "ⲃⲉⲥⲥⲁⲗⲱⲙ"),
            ("ⲡ", "ϭⲟⲓⲥ"),
            gverses(3, 1), gverses(3, 2),
        )
        self.assertEqual(r["status"], "title_in_first_greek_verse_candidate")
        self.assertTrue(r["david_absalom_title_in_coptic_and_greek_one"])
        self.assertFalse(r["greek_reference_verified"])
        self.assertEqual(
            classify_psalm_boundary(
                3, ("ⲛⲧⲉ", "ⲇⲁⲩⲓⲇ", "ⲃⲉⲥⲥⲁⲗⲱⲙ"),
                ("ⲡ", "ϭⲟⲓⲥ"), ("Ψαλμὸς", "Δαυιδ"), gverses(3, 2)
            )["status"], "needs_primary_collation"
        )

    def test_psalm_fifty_one_source_zero_contains_greek_verses_one_two_title(self):
        r = classify_psalm_boundary(
            51, ("ⲉ", "ⲡ", "ⲇⲁⲩⲓⲇ", "ⲇⲱⲏⲕ", "ⲁⲃⲓⲙⲉⲗⲉⲭ"),
            ("ϧⲁ", "ⲡ", "ϭⲟⲓⲥ"),
            gverses(51, 1), gverses(51, 2),
        )
        self.assertEqual(r["status"], "title_across_two_greek_verses_candidate")
        self.assertTrue(r["doeg_abimelech_in_coptic_zero_and_greek_two"])
        self.assertFalse(r["source0_to_greek_verse_whole"])
        self.assertEqual(
            classify_psalm_boundary(
                51, ("ⲇⲁⲩⲓⲇ", "ⲇⲱⲏⲕ", "ⲁⲃⲓⲙⲉⲗⲉⲭ"),
                ("ϧⲁ",), gverses(51, 1), ("ἐν", "τῷ", "ἐλθεῖν", "Δωηκ"),
            )["status"], "needs_primary_collation"
        )

    def test_psalm_151_remains_unclassified_without_source_greek_word_evidence(self):
        r = classify_psalm_boundary(
            151, ("ⲥⲉ", "ϫⲟϥ"), ("ⲁⲛⲟⲕ",),
            gverses(151, 1), gverses(151, 2),
        )
        self.assertEqual(r["status"], "needs_primary_collation")
        self.assertFalse(r["greek_reference_verified"])

    def test_wrong_source_record_sha_is_fatal_and_not_a_verified_mapping(self):
        doc = make_doc(body=(
            '<verse_n verse_n="0">' + norm("...", 1) +
            '<verse_n verse_n="1">' + norm("ⲟⲩ", 2)
        ))
        self.assertEqual(len(SELECTED_SOURCE_SHA), 6)
        with self.assertRaisesRegex(ValueError, "source|SHA|pin|hash"):
            inspect_selected_psalm(doc, greek_words=gverses)
        tampered = replace(doc, upstream_commit="0" * 40)
        with self.assertRaisesRegex(ValueError, "source|revision|pin"):
            inspect_selected_psalm(tampered, greek_words=gverses)

    def test_invalid_greek_word_order_or_missing_verse_must_fail(self):
        with self.assertRaisesRegex(ValueError, "Greek|word|verse"):
            classify_psalm_boundary(149, ("ⲁⲗⲗⲏⲗⲟⲩⲓⲁ",), ("ϫⲱ",), (), ("foo",))
        with self.assertRaisesRegex(ValueError, "Greek|word|verse"):
            classify_psalm_boundary(17, ("ⲟⲩⲟϩ", "ⲡⲉϫⲁ", "ϥ"), ("ϯ",),
                                    gverses(17, 1), ())

    def test_audit_rejects_duplicates_and_records_no_words(self):
        a = PsalmBoundaryReview()
        record = {
            "source_record_id": "bohairic.ot/bohairic.ot:19_Psalmi_017",
            "source_sha256": SELECTED_SOURCE_SHA[17],
            "chapter": 17, "source_zero_word_count": 59,
            "source_one_word_count": 9, "greek_verse_one_word_count": 30,
            "greek_verse_two_word_count": 10,
            "status": "cross_greek_verse_boundary_candidate",
            "evidence": {"coptic_and_said_at_zero_end": True},
            "greek_reference_verified": False,
        }
        a.add(record)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            a.add(dict(record))
        output = a.report()
        self.assertEqual(output["cases"], 1)
        self.assertEqual(output["statuses"], {"cross_greek_verse_boundary_candidate": 1})
        self.assertEqual(output["records"][0]["chapter"], 17)
        self.assertNotIn("ⲟⲩⲟϩ", str(output))
        self.assertNotIn("καὶ", str(output))


if __name__ == "__main__":
    unittest.main()
