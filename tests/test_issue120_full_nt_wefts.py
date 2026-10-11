"""RED-first source+parent TF release invariants for complete NT weft projection."""
from unittest import TestCase

from research.issue_120.full_nt_wefts import (
    EXPECTED_COUNTS, validate_full_counts, verify_native_feature_parity,
)

COUNTS = {
    "reference_candidate": 2301,
    "ambiguous": 437,
    "unresolved": 8,
    "edition_unavailable": 1,
    "coptic_annotated_sbl_nodes": 2747,
    "coptic_candidate_sbl_nodes": 2301,
    "greek_target_verse_nodes": 904,
}


class FullNtReleaseContracts(TestCase):
    def test_full_real_source_counts_are_an_exact_gate_not_minimum(self):
        self.assertEqual(validate_full_counts(COUNTS, physical=2628, annotated=48), COUNTS)
        for field in COUNTS:
            altered = dict(COUNTS)
            altered[field] += 1
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "count"):
                validate_full_counts(altered, physical=2628, annotated=48)

    def test_skipped_physical_records_and_unreviewed_statuses_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "count"):
            validate_full_counts(COUNTS, physical=2627, annotated=48)
        with self.assertRaisesRegex(ValueError, "count"):
            validate_full_counts(COUNTS, physical=2628, annotated=47)
        with self.assertRaisesRegex(ValueError, "count"):
            validate_full_counts({**COUNTS, "unclassified_source": 1}, physical=2628, annotated=48)

    def test_duplicate_source_witnesses_cannot_be_collapsed(self):
        altered = {**COUNTS, "reference_candidate": 2300,
                   "coptic_candidate_sbl_nodes": 2300}
        with self.assertRaisesRegex(ValueError, "count"):
            validate_full_counts(altered, physical=2628, annotated=48)

    def test_missing_non_candidates_cannot_be_declared_success(self):
        altered = {**COUNTS, "ambiguous": 0, "unresolved": 0,
                   "coptic_annotated_sbl_nodes": 2301}
        with self.assertRaisesRegex(ValueError, "count"):
            validate_full_counts(altered, physical=2628, annotated=48)

    def test_native_node_and_reference_multisets_must_match(self):
        coptic = {
            10: ("sbl_greek", "reference_candidate", "edition:Mark:2:1"),
            11: ("sbl_apparatus", "ambiguous", None),
            12: ("sbl_greek", "unresolved", None),
            13: ("sbl_greek", "reference_candidate", "edition:Mark:2:1"),
        }
        greek = {800: ("verse", "edition:Mark:2:1", 2)}
        counts = verify_native_feature_parity(
            coptic, greek, word_max=9, greek_max_slot=400,
        )
        self.assertEqual(counts["reference_candidate"], 2)
        self.assertEqual(counts["ambiguous"], 1)
        self.assertEqual(counts["unresolved"], 1)
        self.assertEqual(counts["distinct_greek_verses"], 1)
        self.assertEqual(counts["total_greek_occurrences"], 2)

    def test_reject_word_slot_and_nonverse_leakage(self):
        c = {1: ("word", "reference_candidate", "ref")}
        with self.assertRaisesRegex(ValueError, "Coptic"):
            verify_native_feature_parity(c, {800: ("verse", "ref", 1)},
                                         word_max=9, greek_max_slot=400)
        c = {10: ("sbl_greek", "reference_candidate", "ref")}
        with self.assertRaisesRegex(ValueError, "Greek"):
            verify_native_feature_parity(c, {800: ("word", "ref", 1)},
                                         word_max=9, greek_max_slot=400)

    def test_reject_foreign_ids_and_candidate_status_inconsistency(self):
        for pair in [
            ("ambiguous", "ref"),
            ("reference_candidate", None),
            ("not_a_status", None),
        ]:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                verify_native_feature_parity(
                    {10: ("sbl_greek", *pair)},
                    {800: ("verse", "ref", 1)},
                    word_max=9, greek_max_slot=400,
                )

    def test_reject_greek_occurrence_count_and_address_divergence(self):
        c = {10: ("sbl_greek", "reference_candidate", "ref")}
        for greek in [
            {800: ("verse", "ref", 2)},
            {800: ("verse", "other", 1)},
            {800: ("verse", "ref", True)},
            {800: ("verse", "ref", 0)},
        ]:
            with self.subTest(greek=greek), self.assertRaisesRegex(ValueError, "count|reference"):
                verify_native_feature_parity(c, greek, word_max=9, greek_max_slot=400)

    def test_reject_duplicate_greek_ref_on_two_verse_nodes(self):
        c = {10: ("sbl_greek", "reference_candidate", "ref")}
        with self.assertRaises(ValueError):
            verify_native_feature_parity(
                c, {800: ("verse", "ref", 1), 801: ("verse", "ref", 1)},
                word_max=9, greek_max_slot=400,
            )
