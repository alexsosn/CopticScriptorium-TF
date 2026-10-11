"""Adversarial RED: source edition literal parity beyond matching opening counts."""
import unittest

from live_issue140_full_native import compare_pinned_edition_literals


def raw(value="0001"):
    return (
        b'<ed_page_n ed_page_n="' + value.encode() + b'">'
        b'<norm norm="a">a</norm>'
        b'</ed_page_n><ed_line_n ed_line_n="7"></ed_line_n>'
    )


class EditionValueSourceParityTests(unittest.TestCase):
    def test_exact_value_kind_and_original_ordinal_agree(self):
        records = [("a/a:one", raw())]
        native = {
            ("a/a:one", 1): ("ed_page_n", "0001"),
            ("a/a:one", 2): ("ed_line_n", "7"),
        }
        counts = compare_pinned_edition_literals(records, native)
        self.assertEqual(counts["ed_page_n"], 1)
        self.assertEqual(counts["ed_line_n"], 1)

    def test_value_corruption_cannot_pass_count_only_gate(self):
        native = {
            ("a/a:one", 1): ("ed_page_n", "1"),
            ("a/a:one", 2): ("ed_line_n", "7"),
        }
        with self.assertRaisesRegex(ValueError, "edition.*value"):
            compare_pinned_edition_literals([("a/a:one", raw())], native)

    def test_missing_duplicate_or_wrong_kind_is_rejected(self):
        native = {
            ("a/a:one", 1): ("ed_page_n", "0001"),
            ("a/a:one", 2): ("ed_line_n", "7"),
        }
        for changed in (
            {("a/a:one", 1): native[("a/a:one", 1)]},
            {**native, ("a/a:one", 3): ("ed_pg_n", "5")},
            {**native, ("a/a:one", 2): ("ed_pg_n", "7")},
        ):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "edition"):
                compare_pinned_edition_literals([("a/a:one", raw())], changed)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare_pinned_edition_literals([("a/a:one",raw()),("a/a:one",raw())],native)

    def test_empty_value_is_preserved_not_dropped(self):
        data=b'<ed_line_n ed_line_n=""></ed_line_n>'
        counts=compare_pinned_edition_literals(
            [("a/a:one",data)],{("a/a:one",1):("ed_line_n","")}
        )
        self.assertEqual(counts["ed_line_n"],1)

    def test_missing_or_duplicate_original_literal_is_an_error(self):
        for data in (
            b'<ed_page_n class="p"></ed_page_n>',
            b'<ed_page_n ed_page_n="1" ed_page_n="2"></ed_page_n>',
        ):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "edition"):
                compare_pinned_edition_literals(
                    [("a/a:one",data)], {("a/a:one",1):("ed_page_n","1")}
                )


if __name__=="__main__":
    unittest.main()
