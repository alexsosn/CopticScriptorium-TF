"""RED(#143): independent source TT norm-slot boundary parity, not just node counts."""
from __future__ import annotations

import unittest
from live_issue143_full_native import compare_pinned_multiword_spans


class ExactMultiwordBoundaryTests(unittest.TestCase):
    def test_group_sources_open_and_close_on_original_word_boundaries(self):
        raw = (
            b'<meta corpus="fixture"><multiword multiword="a b">'
            b'<norm norm="a">a</norm><norm norm="b">b</norm>'
            b'</multiword>'
        )
        expected = {("fixture/fixture:one", 1): ("a b", 0, 2)}
        self.assertEqual(compare_pinned_multiword_spans([
            ("fixture/fixture:one", raw)
        ], expected), 1)

    def test_cross_original_groups_and_adjacent_multiword_has_precise_offsets(self):
        raw = (
            b'<norm norm="first">first</norm>'
            b'<multiword multiword="a b">'
            b'<orig_group><norm_group><norm norm="a">a</norm>'
            b'</norm_group></orig_group>'
            b'<lb_n lb_n="2"><norm norm="b">b</norm></lb_n>'
            b'</multiword><norm norm="last">last</norm>'
        )
        self.assertEqual(compare_pinned_multiword_spans(
            [("fixture/fixture:one", raw)],
            {("fixture/fixture:one", 1): ("a b", 1, 3)}
        ), 1)

    def test_wrong_locus_fails_even_if_kind_count_value_and_ordinal_match(self):
        raw = b'<multiword multiword="a b"><norm>a</norm><norm>b</norm></multiword>'
        with self.assertRaisesRegex(ValueError, "multiword.*boundary"):
            compare_pinned_multiword_spans(
                [("fixture/fixture:one", raw)],
                {("fixture/fixture:one", 1): ("a b", 0, 1)},
            )

    def test_nested_opening_ordinals_follow_open_order_not_close_order(self):
        raw = (
            b'<multiword multiword="a c">'
            b'<norm>a</norm>'
            b'<multiword multiword="b"><norm>b</norm></multiword>'
            b'<norm>c</norm></multiword>'
        )
        expected = {
            ("fixture/fixture:one", 1): ("a c", 0, 3),
            ("fixture/fixture:one", 2): ("b", 1, 2),
        }
        self.assertEqual(compare_pinned_multiword_spans(
            [("fixture/fixture:one", raw)], expected
        ), 2)

    def test_orphan_and_unclosed_source_multiword_fail_closed(self):
        for raw in (
            b'<norm>a</norm></multiword>',
            b'<multiword multiword="x"><norm>a</norm>',
        ):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "multiword"):
                compare_pinned_multiword_spans(
                    [("fixture/fixture:one", raw)], {},
                )


if __name__ == "__main__":
    unittest.main()
