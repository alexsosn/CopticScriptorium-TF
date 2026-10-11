"""RED-first: verify TF-native SBL annotation identity, not merely node totals."""
from dataclasses import replace
import unittest

from copticscriptorium_tf.model import SblAnnotation
from research.issue_91.full_native_recheck import compare_occurrence


def source():
    return SblAnnotation(
        ordinal=2, kind="sbl_greek", value="⸀λόγος· ",
        word_ordinals=(2, 3), source_verse_n="2",
        start_word_ordinal=1, start_char=1, start_after_word_ordinal=0,
        end_word_ordinal=None, end_char=None, end_after_word_ordinal=3,
    )


def native():
    return {
        "source_ordinal": 2, "kind": "sbl_greek", "value": "⸀λόγος· ",
        "sbl_verse_n": "2", "render_mode": "sbl_span",
        "start_word_ordinal": 1, "start_char": 1, "start_after_word_ordinal": 0,
        "end_word_ordinal": None, "end_char": None, "end_after_word_ordinal": 3,
        "slots": (102, 103),
    }


class FullNativeSblParityTests(unittest.TestCase):
    def test_source_value_and_all_positions_match(self):
        compare_occurrence(source(), native(), first_slot=101)

    def test_unicode_trailing_whitespace_is_not_normalized(self):
        with self.assertRaisesRegex(ValueError, "value"):
            compare_occurrence(source(), native() | {"value": "⸀λόγος·"}, first_slot=101)

    def test_wrong_source_order_fails(self):
        with self.assertRaisesRegex(ValueError, "source_ordinal"):
            compare_occurrence(source(), native() | {"source_ordinal": 1}, first_slot=101)

    def test_forged_verse_number_fails(self):
        with self.assertRaisesRegex(ValueError, "sbl_verse_n"):
            compare_occurrence(source(), native() | {"sbl_verse_n": "3"}, first_slot=101)

    def test_reversed_char_boundaries_fail(self):
        with self.assertRaisesRegex(ValueError, "end_char"):
            compare_occurrence(source(), native() | {"end_char": 3}, first_slot=101)

    def test_spurious_partial_first_word_in_oslots_fails(self):
        with self.assertRaisesRegex(ValueError, "slots"):
            compare_occurrence(source(), native() | {"slots": (101, 102, 103)}, first_slot=101)

    def test_same_slot_ids_wrong_document_fail(self):
        with self.assertRaisesRegex(ValueError, "slots"):
            compare_occurrence(source(), native(), first_slot=201)

    def test_empty_present_value_is_preserved(self):
        compare_occurrence(replace(source(), value=""), native() | {"value": ""}, first_slot=101)

    def test_anchor_must_be_one_local_word_without_claiming_whole_span(self):
        annotation = replace(source(), word_ordinals=(), start_word_ordinal=1,
                             start_after_word_ordinal=0, end_word_ordinal=1,
                             end_char=3, end_after_word_ordinal=0)
        proof = native() | {
            "render_mode": "sbl_anchor", "slots": (101,),
            "end_word_ordinal": 1, "end_char": 3, "end_after_word_ordinal": 0,
        }
        compare_occurrence(annotation, proof, first_slot=101)
        with self.assertRaisesRegex(ValueError, "slots"):
            compare_occurrence(annotation, proof | {"slots": (101, 102)}, first_slot=101)

    def test_spurious_anchor_as_span_rejected(self):
        a = replace(source(), word_ordinals=(), end_word_ordinal=1,
                    end_char=3, end_after_word_ordinal=0)
        with self.assertRaisesRegex(ValueError, "render_mode"):
            compare_occurrence(a, native() | {"slots": (101,)}, first_slot=101)


if __name__ == "__main__":
    unittest.main()
